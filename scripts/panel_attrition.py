"""Matched-panel survival: what became of the 133 T1 projects found through date-restricted search.

The ecosystem-level T1/T2 comparison mixes composition change with price change.
This traces the *same* projects forward, using the exact identifiers resolved by
panel_resolve.py against the full CoinGecko coin list.

Three outcomes are kept distinct, because collapsing them is what makes naive
versions of this analysis wrong:
  - still in the AI-agent category
  - still traded, but no longer categorised as an AI agent
  - no longer traded at all
A project that merely left the category is not a dead project.
"""

import csv
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PAPER_CSV = ROOT / "data/raw/t1_search_projects.csv"

ALIVE_USD = 1e6


def main():
    with PAPER_CSV.open(encoding="utf-8-sig") as f:
        panel = list(csv.DictReader(f))
    matches = json.loads((RAW / "panel_matches.json").read_text())
    markets = json.loads((RAW / "cg_markets.json").read_text())
    hist_path = RAW / "cg_history_t2.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {}

    in_category = {c["id"]: (c.get("market_cap") or 0) for c in markets}

    rows = []
    for p in panel:
        m = matches.get(p["project"])
        cid = m["coin_id"] if m else None
        raw_t1 = (p.get("market_cap") or "").replace(",", "").strip()
        t1 = float(raw_t1) if raw_t1 else None

        if cid is None:
            status = "no token"
        elif cid in in_category:
            status = "in category"
        else:
            status = "traded, left category"

        rows.append({
            "project": p["project"],
            "category": p.get("category", ""),
            "coin_id": cid,
            "matched_by": m["how"] if m else None,
            "status": status,
            "t1": t1,
            "t2": (hist.get(cid) or {}).get("market_cap_usd") if cid else None,
            "now": in_category.get(cid),
        })

    print(f"panel: {len(rows)} T1 search projects")
    print("  resolution:", Counter(r["matched_by"] for r in rows))
    print("  status:    ", Counter(r["status"] for r in rows))

    priced = [r for r in rows if r["t1"]]
    print(f"\nof the {len(priced)} projects that had a market cap at T1:")
    print("  ", Counter(r["status"] for r in priced))

    tracked = [r for r in priced if r["status"] == "in category"]
    left = [r for r in priced if r["status"] == "traded, left category"]
    print(f"\n  still in the AI-agent category: {len(tracked)} "
          f"({len(tracked)/len(priced):.0%})")
    print(f"  traded but left the category:   {len(left)} "
          f"({len(left)/len(priced):.0%})")
    print(f"  above ${ALIVE_USD:,.0f} today:          "
          f"{sum(1 for r in priced if (r['now'] or 0) > ALIVE_USD)}")

    t1_sum = sum(r["t1"] for r in tracked)
    now_sum = sum(r["now"] or 0 for r in tracked)
    if t1_sum:
        print(f"\naggregate over the {len(tracked)} still-categorised projects:")
        print(f"  T1:  ${t1_sum/1e9:.2f}B")
        print(f"  now: ${now_sum/1e9:.2f}B  ({now_sum/t1_sum:.2f}x)")

    print(f"\n=== largest panel members, T1 vs now ===")
    for r in sorted(priced, key=lambda x: -x["t1"])[:20]:
        now = r["now"]
        shown = f"${now/1e6:8,.1f}M" if now is not None else "     n/a"
        ratio = f"{now/r['t1']:5.2f}x" if now else "     -"
        print(f"  {r['project'][:28]:28s} ${r['t1']/1e6:8,.1f}M -> {shown}"
              f"  {ratio}  [{r['status']}]")

    print(f"\n=== survival by category (still in category and above $1M) ===")
    cats, alive = Counter(), Counter()
    for r in priced:
        for c in (r["category"] or "").split(","):
            c = c.strip()
            if not c:
                continue
            cats[c] += 1
            if (r["now"] or 0) > ALIVE_USD:
                alive[c] += 1
    for c, n in cats.most_common():
        print(f"  {c:18s} {alive[c]:3d}/{n:3d} ({alive[c]/n:4.0%})")

    out = ROOT / "data/processed/panel_attrition.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
