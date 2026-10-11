"""Monthly market-cap series for the T2 universe and the T1 cohort.

One `market_chart/range` call per coin returns a daily series, which is far
cheaper than a `/history` call per coin per month. The paid key reaches back two
years, so the window now starts before T1 (2025-04) and the series spans the
whole study window instead of starting part-way through it.

Writes data/raw/cg_series.json: {coin_id: {"YYYY-MM": market_cap}}, month-end
values. Resumable.
"""

import datetime as dt
import json
import os
import pathlib
import time

import requests

from cg_collect import API, DELAY

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = RAW / "cg_series.json"
TO = int(dt.datetime(2026, 9, 1).timestamp())
FROM = int(dt.datetime(2025, 3, 1).timestamp())


def month_ends(points):
    """Last observation within each calendar month, as {"YYYY-MM": value}."""
    out = {}
    for ms, value in points:
        d = dt.datetime.fromtimestamp(ms / 1000)
        out[f"{d.year}-{d.month:02d}"] = value
    return out


def main():
    universe = {c["id"] for c in json.loads((RAW / "cg_details.json").read_text())}
    panel = {m["coin_id"] for m in
             json.loads((RAW / "panel_matches.json").read_text()).values()}
    todo = sorted(universe | panel)

    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [c for c in todo if c not in out]
    print(f"universe {len(universe)}, panel {len(panel)}, to fetch {len(todo)}",
          flush=True)

    session = requests.Session()
    for i, coin in enumerate(todo, 1):
        r = session.get(f"{API}/coins/{coin}/market_chart/range", timeout=60,
                        params={"vs_currency": "usd", "from": FROM, "to": TO,
                                "x_cg_pro_api_key":
                                    os.environ["COINGECKO_API_KEY"]})
        if r.status_code == 429:
            time.sleep(30)
            continue
        # A coin with no data in the window is a real outcome (delisted, or
        # listed after the window), not an error; record it as empty.
        out[coin] = (month_ends(r.json().get("market_caps", []))
                     if r.status_code == 200 else {})
        if i % 25 == 0 or i == len(todo):
            OUT.write_text(json.dumps(out))
            print(f"  {i}/{len(todo)} saved", flush=True)
        time.sleep(DELAY)

    OUT.write_text(json.dumps(out))
    print(f"\n{len(out)} coins, {sum(1 for v in out.values() if v)} with data "
          f"-> {OUT}")


if __name__ == "__main__":
    main()
