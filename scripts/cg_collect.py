"""Collect the CoinGecko AI-agent token population.

Two passes: category listings give the coin universe, then per-coin detail gives
the GitHub repo list that joins this population to the GitHub side.
Detail fetching is resumable — rerun after an interruption and it skips what is
already on disk.
Writes data/raw/cg_markets.json and data/raw/cg_details.json.
"""

import json
import os
import pathlib
import time

import requests

API = "https://pro-api.coingecko.com/api/v3"
RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
MARKETS = RAW / "cg_markets.json"
DETAILS = RAW / "cg_details.json"

CATEGORIES = [
    "ai-agents", "defai", "ai-agent-launchpad", "ai-framework",
    "ai-applications", "ai-meme-coins", "artificial-intelligence",
]

# Pro "Basic" allows 300 calls/min.
DELAY = 0.25


def get(session, path, **params):
    params["x_cg_pro_api_key"] = os.environ["COINGECKO_API_KEY"]
    for attempt in range(4):
        r = session.get(f"{API}{path}", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(30)
            continue
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json()
    r.raise_for_status()


def collect_markets(session):
    coins = {}
    for cat in CATEGORIES:
        page = 1
        while True:
            rows = get(session, "/coins/markets", vs_currency="usd",
                       category=cat, per_page=250, page=page)
            for row in rows:
                entry = coins.setdefault(row["id"], {**row, "categories": []})
                entry["categories"].append(cat)
            print(f"  {cat} page{page}: {len(rows)} (universe={len(coins)})",
                  flush=True)
            if len(rows) < 250:
                break
            page += 1
    MARKETS.write_text(json.dumps(list(coins.values()), indent=2))
    return coins


def collect_details(session, coin_ids):
    details = {}
    if DETAILS.exists():
        details = {d["id"]: d for d in json.loads(DETAILS.read_text())}
        print(f"resuming: {len(details)} details already on disk")

    todo = [c for c in coin_ids if c not in details]
    for i, coin_id in enumerate(todo, 1):
        try:
            d = get(session, f"/coins/{coin_id}", localization="false",
                    tickers="false", market_data="true", community_data="false",
                    developer_data="true", sparkline="false")
        except requests.HTTPError as e:
            print(f"  !! {coin_id}: {e}", flush=True)
            continue
        details[coin_id] = {
            "id": d["id"],
            "symbol": d.get("symbol"),
            "name": d.get("name"),
            "homepage": [u for u in d["links"].get("homepage", []) if u],
            "github_repos": d["links"].get("repos_url", {}).get("github", []),
            "platforms": d.get("platforms", {}),
            "genesis_date": d.get("genesis_date"),
            "market_cap_usd": d["market_data"]["market_cap"].get("usd"),
            "fdv_usd": d["market_data"].get(
                "fully_diluted_valuation", {}).get("usd"),
            "volume_24h_usd": d["market_data"]["total_volume"].get("usd"),
            "last_updated": d.get("last_updated"),
            "categories": d.get("categories", []),
        }
        if i % 25 == 0 or i == len(todo):
            DETAILS.write_text(json.dumps(list(details.values()), indent=2))
            print(f"  detail {i}/{len(todo)} (saved)", flush=True)

    DETAILS.write_text(json.dumps(list(details.values()), indent=2))
    return details


def in_scope(coin):
    """The old detail-fetch gate, kept as a label rather than a filter.

    Detail is now fetched for the whole universe so that screening and
    classification decide what is in scope, not the collection step. This
    predicate -- not a pure meme token, and above $100k -- is recorded on each
    detail row as `in_scope` so the narrower subset stays reproducible.
    """
    return (coin["categories"] != ["ai-meme-coins"]
            and (coin.get("market_cap") or 0) > 1e5)


def main():
    session = requests.Session()
    print("=== pass 1: category listings ===")
    coins = collect_markets(session)
    print(f"universe: {len(coins)} coins -> {MARKETS}")

    scoped = {c for c, v in coins.items() if in_scope(v)}
    print(f"detail: all {len(coins)} coins ({len(scoped)} meet the old "
          f"in_scope predicate)\n")

    print("=== pass 2: coin detail ===")
    details = collect_details(session, list(coins))
    for cid, d in details.items():
        d["in_scope"] = cid in scoped
    DETAILS.write_text(json.dumps(list(details.values()), indent=2))
    with_repo = sum(1 for d in details.values() if d["github_repos"])
    print(f"\ndetails: {len(details)}, with github repos: {with_repo}")
    print(f"wrote {DETAILS}")


if __name__ == "__main__":
    main()
