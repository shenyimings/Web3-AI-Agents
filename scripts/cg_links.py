"""Fetch the link block for coins CoinGecko has no description for.

The description pass keeps only homepage, but CoinGecko also carries a
whitepaper URL and social handles. For a coin with no prose those links are the
only route to a description, so they are collected separately rather than by
re-running the whole description pass.
Writes data/raw/cg_links.json. Resumable.
"""

import json
import os
import pathlib
import time

import requests

from cg_collect import API, DELAY

RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
OUT = RAW / "cg_links.json"

KEEP = ("homepage", "whitepaper", "announcement_url", "twitter_screen_name",
        "repos_url")


def main():
    desc = json.loads((RAW / "cg_descriptions.json").read_text())
    todo = [k for k, v in desc.items() if not (v.get("description") or "").strip()]
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [k for k in todo if k not in done]
    print(f"{len(todo)} undescribed coins to fetch links for", flush=True)

    session = requests.Session()
    for n, cid in enumerate(todo, 1):
        r = session.get(f"{API}/coins/{cid}", timeout=60, params={
            "localization": "false", "tickers": "false", "market_data": "false",
            "community_data": "false", "developer_data": "false",
            "x_cg_pro_api_key": os.environ["COINGECKO_API_KEY"]})
        if r.status_code == 429:
            time.sleep(30)
            continue
        links = (r.json().get("links") or {}) if r.status_code == 200 else {}
        done[cid] = {k: links.get(k) for k in KEEP}
        if n % 50 == 0 or n == len(todo):
            OUT.write_text(json.dumps(done, indent=1))
            print(f"  {n}/{len(todo)} saved", flush=True)
        time.sleep(DELAY)

    OUT.write_text(json.dumps(done, indent=1))
    wp = sum(1 for v in done.values() if v.get("whitepaper"))
    hp = sum(1 for v in done.values() if v.get("homepage") and any(v["homepage"]))
    print(f"\n{len(done)} coins: {wp} with a whitepaper link, {hp} with a homepage -> {OUT}")


if __name__ == "__main__":
    main()
