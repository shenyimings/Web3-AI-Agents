"""Build the T1 cohort as a union of CoinGecko's AI categories, from web archives.

A single category understates the construct: Zerebro sat in AI Meme, Griffain and
MyShell in AI Agent Launchpad, NEAR in Artificial Intelligence -- none of them in
AI Agents. So the cohort is the union of every AI category whose page the Wayback
Machine captured near 6 April 2025. Two categories (ai-applications, ai-framework)
have no capture in that window and are simply absent; the rest contribute their
first page, i.e. their hundred largest members by market capitalisation.

AI Meme is captured and reported, but held out of the cohort: its members are
coins that joke about AI rather than agent projects, and the paper's taxonomy has
no meme bucket. Holding it out costs little -- the market-capitalisation decline
is -34% to -39% across every frame -- and the four frames are written out
together so that robustness can be shown rather than asserted.

Membership comes from the archive; values come from the API, which serves any
known id at any date inside the paid tier's two-year window.
"""
import gzip, json, re, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "wayback"
KEY = dict(l.strip().split("=", 1) for l in open(ROOT / ".env") if "=" in l)["COINGECKO_API_KEY"]
T1 = "06-04-2025"

# closest capture to T1 for each category that has one
# the cohort (frame B); AI Meme is fetched for the sensitivity table only
COHORT = {"artificial-intelligence", "ai-agents", "ai-agent-launchpad", "defai"}

SNAPSHOTS = {
    "artificial-intelligence": "20250406081705",
    "ai-meme-coins":           "20250402070344",
    "ai-agents":               "20250413001133",
    "ai-agent-launchpad":      "20250415084551",
    "defai":                   "20250421175318",
}


def wayback(cat, ts):
    cached = RAW / f"cg_{cat}_{ts}.html"
    if not cached.exists():
        url = f"http://web.archive.org/web/{ts}id_/https://www.coingecko.com/en/categories/{cat}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
        d = urllib.request.urlopen(req, timeout=200).read()
        cached.write_text((gzip.decompress(d) if d[:2] == b"\x1f\x8b" else d).decode("utf-8", "replace"))
    return cached.read_text(encoding="utf-8")


def parse(html):
    """Rows carry the coin's site slug, its ticker in the logo alt text, and exact
    numbers in data-sort attributes; the market cap is the largest of those."""
    rows = []
    for tr in html.split("<tr")[1:]:
        m = re.search(r'href="/en/coins/([a-z0-9-]+)"', tr)
        if not m:
            continue
        alt = re.search(r'<img[^>]*alt="([^"]+)"', tr)
        ds = [float(x) for x in re.findall(r'data-sort="(-?[0-9.eE+]+)"', tr)]
        if ds and max(ds) > 1000:
            rows.append({"slug": m.group(1), "symbol": (alt.group(1) if alt else "").lower(),
                         "snapshot_mcap": max(ds)})
    return rows


def cg(path):
    for i in range(4):
        try:
            req = urllib.request.Request("https://pro-api.coingecko.com/api/v3" + path,
                                         headers={"x-cg-pro-api-key": KEY, "User-Agent": "research"})
            return json.loads(urllib.request.urlopen(req, timeout=120).read())
        except urllib.error.HTTPError as e:
            return {"__http__": e.code}
        except Exception:
            if i == 3:
                return {"__http__": "read-error"}
            time.sleep(2)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    union, per_cat = {}, {}
    for cat, ts in SNAPSHOTS.items():
        html = wayback(cat, ts)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
        size = re.search(r"Showing 1 to ([\d,]+) of ([\d,]+) results", text)
        rows = parse(html)
        per_cat[cat] = {"snapshot": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                        "category_size": int(size.group(2).replace(",", "")) if size else None,
                        "rows_captured": len(rows)}
        for r in rows:
            u = union.setdefault(r["slug"], {**r, "categories": []})
            u["categories"].append(cat)
        print(f"  {cat:26} {per_cat[cat]['snapshot']}  {len(rows):3} rows of {per_cat[cat]['category_size']}", flush=True)
    print(f"union: {len(union)} distinct coins", flush=True)

    active = cg("/coins/list?status=active")
    ids = {c["id"] for c in active}
    by_sym = {}
    for c in active:
        by_sym.setdefault(c["symbol"].lower(), []).append(c["id"])

    for u in union.values():
        if u["slug"] in ids:
            u["cg_id"] = u["slug"]
        else:
            cands = by_sym.get(u["symbol"], [])
            u["cg_id"] = cands[0] if len(cands) == 1 else (cands[0] if cands else u["slug"])

    cache = RAW / "t1_union_raw.json"
    if cache.exists():
        have = {c["slug"]: c.get("t1_market_cap") for c in json.loads(cache.read_text())}
    else:
        have = {}
    todo = [u for u in union.values() if u["slug"] not in have]
    for u in union.values():
        if u["slug"] in have:
            u["t1_market_cap"] = have[u["slug"]]
    print(f"pulling T1 market caps for {len(todo)} coins ({len(union) - len(todo)} cached) ...", flush=True)
    for i, u in enumerate(todo, 1):
        d = cg(f"/coins/{u['cg_id']}/history?date={T1}&localization=false")
        u["t1_market_cap"] = (None if "__http__" in d
                              else ((d.get("market_data") or {}).get("market_cap") or {}).get("usd"))
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(0.22)

    (RAW / "t1_union_raw.json").write_text(json.dumps(list(union.values()), indent=2))

    t2 = {m["id"]: m for m in json.loads((ROOT / "data/raw/cg_markets.json").read_text()) if m.get("market_cap")}
    taxonomy = set(json.loads((ROOT / "data/processed/t2_taxonomy.json").read_text()))

    def gini(v):
        v, n = sorted(v), len(v)
        return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(v)) / (n * sum(v))

    def frame(cats):
        sel = [u for u in union.values() if set(u["categories"]) & cats]
        cap = [u for u in sel if u["t1_market_cap"]]
        pairs = [{"id": u["cg_id"], "slug": u["slug"], "symbol": u["symbol"],
                  "categories": u["categories"], "t1": u["t1_market_cap"],
                  "t2": t2[u["cg_id"]]["market_cap"]} for u in cap if u["cg_id"] in t2]
        exits = [{"id": u["cg_id"], "t1": u["t1_market_cap"]} for u in cap if u["cg_id"] not in t2]
        t1v = [p["t1"] for p in pairs]
        t2v = [p["t2"] for p in pairs]
        top = max(1, len(pairs) // 10)
        return {
            "members": len(sel), "capitalised_at_t1": len(cap), "matched_into_t2": len(pairs),
            "survival": round(len(pairs) / len(cap), 4),
            "t1_total_usd": sum(t1v), "t2_total_usd": sum(t2v),
            "value_change": round(sum(t2v) / sum(t1v) - 1, 4),
            "gini_t1": round(gini(t1v), 4), "gini_t2": round(gini(t2v), 4),
            "top_decile_share_t1": round(sum(sorted(t1v, reverse=True)[:top]) / sum(t1v), 4),
            "top_decile_share_t2": round(sum(sorted(t2v, reverse=True)[:top]) / sum(t2v), 4),
            "in_t2_taxonomy": len({p["id"] for p in pairs} & taxonomy),
            "exits": sorted(exits, key=lambda e: -e["t1"]),
            "pairs": sorted(pairs, key=lambda p: -p["t1"]),
        }

    ALL = set(SNAPSHOTS)
    primary = frame(COHORT)
    out = {
        "t1_date": "2025-04-06", "cohort_categories": sorted(COHORT),
        "per_category": per_cat, "union_distinct": len(union),
        **primary,
        "sensitivity": {
            "A_all_categories": {k: v for k, v in frame(ALL).items() if k not in ("pairs", "exits")},
            "B_cohort_no_ai_meme": {k: v for k, v in primary.items() if k not in ("pairs", "exits")},
            "C_agent_only": {k: v for k, v in frame({"ai-agents", "ai-agent-launchpad", "defai"}).items()
                             if k not in ("pairs", "exits")},
            "D_ai_agents_only": {k: v for k, v in frame({"ai-agents"}).items()
                                 if k not in ("pairs", "exits")},
        },
    }
    (ROOT / "data/processed/t1_union_cohort.json").write_text(json.dumps(out, indent=2))
    print(f"\ncohort (B): {primary['members']} members, {primary['capitalised_at_t1']} capitalised at T1, "
          f"{primary['matched_into_t2']} into T2 ({primary['survival']:.1%})")
    print(f"${primary['t1_total_usd']:,.0f} -> ${primary['t2_total_usd']:,.0f} ({primary['value_change']:+.1%})  "
          f"Gini {primary['gini_t1']:.3f} -> {primary['gini_t2']:.3f}")


if __name__ == "__main__":
    main()
