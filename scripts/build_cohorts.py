"""Apply the screening criteria and emit the two analysis files.

coding/SCREENING-CRITERIA.md states the rules; this applies the mechanical ones.
S4 (does the description carry AI or agent content) is a reading judgement and
is left to classification, which is why it is the classifier's first decision
rather than a filter here.

  uv run python scripts/build_cohorts.py        # screen, write both files

Writes data/processed/t2_screened_ids.json (the fetch worklist),
data/processed/t2_population.json and data/processed/t1_cohort.json.
"""

import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"

T1_DATE, T2_DATE = "2025-04-06", "2026-09-01"
FRAME_B = {"artificial-intelligence", "ai-agents", "ai-agent-launchpad", "defai"}

# S2a: CoinGecko labels that name an instrument type. `Derivatives` is excluded
# on purpose -- it names a sector, so it tags ordinary projects.
INSTRUMENT = {"Liquid Staking Tokens", "Wrapped-Tokens", "Crypto-Backed Tokens",
              "Liquid Staking"}
INSTRUMENT_NAME = re.compile(r"\b(staked|wrapped|bridged|restaked|synthetic)\b", re.I)


def norm_home(url):
    return re.sub(r"^https?://(www\.)?|/$", "", (url or "").lower())


def screen(det, mk, cap):
    """Return (kept ids, funnel, flag detail). Rules S1, S2a, S2b, S5."""
    listed = list(det)
    capd = [k for k in listed if cap(k) > 0]

    s2a = {k for k in capd
           if (INSTRUMENT & set(det[k].get("categories") or []))
           or INSTRUMENT_NAME.search(det[k].get("name") or "")}

    groups = collections.defaultdict(set)
    for k in capd:
        for h in det[k].get("homepage") or []:
            if norm_home(h):
                groups[norm_home(h)].add(k)
    # Keep the largest listing of a project, drop the rest.
    s2b, dup_groups = set(), []
    for members in groups.values():
        if len(members) > 1:
            ranked = sorted(members, key=lambda k: -cap(k))
            dup_groups.append(ranked)
            s2b |= set(ranked[1:])

    s5 = {k for k in capd if set(mk[k]["categories"]) == {"ai-meme-coins"}}
    kept = [k for k in capd if k not in s2a | s2b | s5]

    funnel = [
        ("S0  listed in the collection frame", len(listed), sum(cap(k) for k in listed)),
        ("S1  capitalised at the cutoff", len(capd), sum(cap(k) for k in capd)),
        ("S2a removed: claim on another listed token", -len(s2a), -sum(cap(k) for k in s2a)),
        ("S2b removed: second+ token of one project", -len(s2b), -sum(cap(k) for k in s2b)),
        ("S5  removed: meme-only listing", -len(s5), -sum(cap(k) for k in s5)),
        ("    surviving mechanical screening", len(kept), sum(cap(k) for k in kept)),
    ]
    return kept, funnel, {"s2a": sorted(s2a), "s2b_groups": dup_groups, "s5": sorted(s5)}


def build_t2(kept, det, mk, desc, hist, fetched):
    rows = []
    for k in kept:
        d, cg = det[k], desc.get(k, {})
        text = (cg.get("description") or "").strip()
        source = "coingecko" if text else None
        if not text and k in fetched:
            text = fetched[k].get("description") or ""
            source = fetched[k].get("desc_source")
        rows.append({
            "id": k,
            "name": d.get("name"),
            "symbol": d.get("symbol"),
            "market_cap_usd": hist[k]["market_cap_usd"],
            "frame_categories": mk[k]["categories"],
            "coingecko_labels": d.get("categories") or [],
            "homepage": (d.get("homepage") or [None])[0],
            "github_repos": d.get("github_repos") or [],
            "platforms": {c: a for c, a in (d.get("platforms") or {}).items() if a},
            "description": text or None,
            "desc_source": source,
            "in_scope_legacy": d.get("in_scope"),
        })
    rows.sort(key=lambda r: -r["market_cap_usd"])
    return rows


def build_t1(followup, det):
    rows = []
    for u in followup:
        if not (set(u["categories"]) & FRAME_B and u["t1_market_cap"]):
            continue
        d = det.get(u["cg_id"], {})
        rows.append({
            "id": u["cg_id"],
            "name": d.get("name") or u["slug"],
            "symbol": u["symbol"],
            "archived_categories": u["categories"],
            "t1_market_cap_usd": u["t1_market_cap"],
            "t2_market_cap_usd": u["t2_market_cap"],
            "survived": bool(u["t2_market_cap"]),
        })
    rows.sort(key=lambda r: -r["t1_market_cap_usd"])
    return rows


def main():
    det = {d["id"]: d for d in json.loads((RAW / "cg_details.json").read_text())}
    mk = {c["id"]: c for c in json.loads((RAW / "cg_markets.json").read_text())}
    desc = json.loads((RAW / "cg_descriptions.json").read_text())
    hist = json.loads((RAW / "cg_history_t2.json").read_text())
    cap = lambda k: (hist.get(k) or {}).get("market_cap_usd") or 0

    kept, funnel, flags = screen(det, mk, cap)
    (PROC / "t2_screened_ids.json").write_text(json.dumps(kept, indent=1))
    for label, n, v in funnel:
        print(f"  {label:46s} {n:+6d}   ${v/1e9:+7.2f}B" if n < 0
              else f"  {label:46s} {n:6d}   ${v/1e9:7.2f}B")

    f = RAW / "fetched_descriptions.json"
    fetched = json.loads(f.read_text()) if f.exists() else {}
    rows = build_t2(kept, det, mk, desc, hist, fetched)
    withtext = [r for r in rows if r["description"]]
    dropped = [r for r in rows if not r["description"]]
    print(f"\n  S3  with a description: {len(withtext)}  "
          f"${sum(r['market_cap_usd'] for r in withtext)/1e9:.2f}B")
    print(f"  S3  removed, no description anywhere: {len(dropped)}  "
          f"${sum(r['market_cap_usd'] for r in dropped)/1e6:,.1f}M")
    by = collections.Counter(r["desc_source"] for r in withtext)
    print("      desc_source:", dict(by))

    out = {"timepoint": T2_DATE, "screening": "coding/SCREENING-CRITERIA.md",
           "n": len(withtext),
           "market_cap_usd": sum(r["market_cap_usd"] for r in withtext),
           "unclassifiable_no_description": [r["id"] for r in dropped],
           "flags": flags, "projects": withtext}
    (PROC / "t2_population.json").write_text(json.dumps(out, indent=1))

    followup = json.loads((RAW / "wayback/t1_cohort_followup.json").read_text())
    t1 = build_t1(followup, det)
    alive = [r for r in t1 if r["survived"]]
    print(f"\n  T1 cohort (frame B): {len(t1)}  survived {len(alive)} "
          f"({len(alive)/len(t1):.1%})  "
          f"${sum(r['t1_market_cap_usd'] for r in t1)/1e9:.2f}B -> "
          f"${sum(r['t2_market_cap_usd'] for r in alive)/1e9:.2f}B")
    (PROC / "t1_cohort.json").write_text(json.dumps(
        {"t1_date": T1_DATE, "t2_date": T2_DATE,
         "membership": "archived CoinGecko category pages, April 2025; "
                       "top 100 rows per category",
         "frame": sorted(FRAME_B), "n": len(t1), "n_survived": len(alive),
         "projects": t1}, indent=1))
    print(f"\n  wrote {PROC/'t2_population.json'}, {PROC/'t1_cohort.json'}")


if __name__ == "__main__":
    main()
