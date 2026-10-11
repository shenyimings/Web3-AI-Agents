"""Fetch market cap at T2 (2026-09-01) for the in-scope coins.

Current market cap reflects the collection date, not the study cutoff, so the
cutoff value is fetched explicitly. T1 is not derived here: it comes from the
Wayback cohort pipeline (t1_union_cohort.py), which fixes cohort membership
from archived category pages rather than from present-day category labels.
Writes data/raw/cg_history_t2.json.
"""

import json
import os
import pathlib
import time

import requests

from cg_collect import API, DELAY

T2 = "01-09-2026"
RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
IN = RAW / "cg_details.json"
OUT = RAW / "cg_history_t2.json"


def main():
    session = requests.Session()
    coins = json.loads(IN.read_text())

    out = {}
    if OUT.exists():
        out = json.loads(OUT.read_text())
        print(f"resuming: {len(out)} already fetched")

    todo = [c["id"] for c in coins if c["id"] not in out]
    print(f"fetching T2 ({T2}) market cap for {len(todo)} coins")

    for i, coin_id in enumerate(todo, 1):
        params = {"date": T2, "localization": "false",
                  "x_cg_pro_api_key": os.environ["COINGECKO_API_KEY"]}
        r = session.get(f"{API}/coins/{coin_id}/history", params=params,
                        timeout=60)
        if r.status_code == 429:
            time.sleep(30)
            continue
        if r.status_code != 200:
            out[coin_id] = {"market_cap_usd": None, "error": r.status_code}
        else:
            md = r.json().get("market_data") or {}
            out[coin_id] = {
                "market_cap_usd": (md.get("market_cap") or {}).get("usd"),
                "price_usd": (md.get("current_price") or {}).get("usd"),
                "volume_24h_usd": (md.get("total_volume") or {}).get("usd"),
            }
        if i % 25 == 0 or i == len(todo):
            OUT.write_text(json.dumps(out, indent=2))
            print(f"  {i}/{len(todo)} (saved)", flush=True)
        time.sleep(DELAY)

    OUT.write_text(json.dumps(out, indent=2))
    listed = sum(1 for v in out.values() if v.get("market_cap_usd"))
    print(f"\n{len(out)} coins; {listed} had a market cap at T2 -> {OUT}")


if __name__ == "__main__":
    main()
