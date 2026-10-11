"""Fetch the project text needed to card-sort the T2 detail set.

The detail pass in cg_collect.py kept only the fields the market analysis
needed, so the in-scope tokens carry no prose. Taxonomic categorization
reads a project's own description of itself, so this pass re-fetches
description, homepage and the CoinGecko category labels for each of them.

Resumable: rerun after an interruption and it skips what is already on disk.
Writes data/raw/cg_descriptions.json.
"""

import json
import os
import pathlib
import sys
import time

import requests

API = "https://pro-api.coingecko.com/api/v3"
RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
DETAILS = RAW / "cg_details.json"
OUT = RAW / "cg_descriptions.json"

DELAY = 0.25


def get(session, path, **params):
    params["x_cg_pro_api_key"] = os.environ["COINGECKO_API_KEY"]
    for _ in range(4):
        r = session.get(f"{API}{path}", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(30)
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json()
    r.raise_for_status()


def main():
    ids = [c["id"] for c in json.loads(DETAILS.read_text())]
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    session = requests.Session()
    todo = [i for i in ids if i not in done]
    print(f"{len(ids)} in scope, {len(todo)} to fetch", flush=True)

    for n, cid in enumerate(todo, 1):
        d = get(session, f"/coins/{cid}", localization="false", tickers="false",
                market_data="false", community_data="false",
                developer_data="false", sparkline="false")
        if d is None:
            done[cid] = {"id": cid, "missing": True}
        else:
            links = d.get("links") or {}
            done[cid] = {
                "id": cid,
                "name": d.get("name"),
                "symbol": d.get("symbol"),
                "description": (d.get("description") or {}).get("en") or "",
                "homepage": [u for u in (links.get("homepage") or []) if u],
                "categories": [c for c in (d.get("categories") or []) if c],
            }
        if n % 25 == 0 or n == len(todo):
            OUT.write_text(json.dumps(done, indent=1))
            print(f"  {n}/{len(todo)} saved", flush=True)

    OUT.write_text(json.dumps(done, indent=1))
    empty = sum(1 for v in done.values() if not v.get("description"))
    print(f"\n{len(done)} coins, {len(done) - empty} with description -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
