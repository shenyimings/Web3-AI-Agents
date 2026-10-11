"""Resolve the 133 T1 search projects against the FULL CoinGecko coin list.

Matching these projects against the AI-agent category listing alone is wrong: it
scores a project that merely left the category as dead. NEAR, Venice and
Fetch.ai (now the Artificial Superintelligence Alliance) all fail that way,
and Venice is in fact the largest token in the T2 universe.

This resolves names against every coin CoinGecko lists, so "no longer in the
AI-agent category" and "no longer traded" stay separate outcomes. Writes
data/raw/cg_coin_list.json and data/raw/panel_matches.json.
"""

import csv
import json
import os
import pathlib
import re

import requests

from cg_collect import API

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PAPER_CSV = ROOT / "data/raw/t1_search_projects.csv"
LIST = RAW / "cg_coin_list.json"
OUT = RAW / "panel_matches.json"

# Renames and rebrands between the two snapshots. Verified by hand against the
# CoinGecko entry; without these the panel scores live projects as dead.
ALIASES = {
    "fetch ai/uagents": "artificial-superintelligence-alliance",
    "fetch.ai": "artificial-superintelligence-alliance",
    "singularitynet": "artificial-superintelligence-alliance",
    "ocean protocol": "artificial-superintelligence-alliance",
    "venice.ai": "venice-token",
    "eliza": "ai16z",
}


PLATFORMS = {
    "eth": "ethereum", "ethereum": "ethereum",
    "bsc": "binance-smart-chain", "bnb": "binance-smart-chain",
    "base": "base", "sol": "solana", "solana": "solana",
    "arb": "arbitrum-one", "polygon": "polygon-pos", "avax": "avalanche",
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def lookup_contract(platform, contract):
    """Exact resolution by token contract. Returns a coin id or None.

    A 429 must not be reported as "not listed" — that would score a live
    project as dead. Back off and retry; only a real 404 returns None.
    """
    import time
    for _ in range(4):
        r = requests.get(f"{API}/coins/{platform}/contract/{contract}",
                         timeout=60,
                         params={"x_cg_demo_api_key":
                                 os.environ["COINGECKO_API_KEY"]})
        if r.status_code == 429:
            time.sleep(30)
            continue
        time.sleep(2.5)
        return r.json().get("id") if r.status_code == 200 else None
    raise RuntimeError(f"rate-limited resolving {platform}/{contract}")


def main():
    if LIST.exists():
        coins = json.loads(LIST.read_text())
        print(f"using cached coin list: {len(coins)}")
    else:
        r = requests.get(f"{API}/coins/list", timeout=60, params={
            "x_cg_demo_api_key": os.environ["COINGECKO_API_KEY"]})
        r.raise_for_status()
        coins = r.json()
        LIST.write_text(json.dumps(coins))
        print(f"fetched full coin list: {len(coins)}")

    by_name, by_symbol = {}, {}
    for c in coins:
        by_name.setdefault(norm(c["name"]), c["id"])
        by_symbol.setdefault(norm(c["symbol"]), c["id"])
    ids = {c["id"] for c in coins}

    with PAPER_CSV.open(encoding="utf-8-sig") as f:
        panel = list(csv.DictReader(f))

    matches, unresolved = {}, []
    for p in panel:
        name = p["project"]
        n = norm(name)
        alias = ALIASES.get(name.lower().strip())
        cid = None
        how = None
        if alias and alias in ids:
            cid, how = alias, "alias"
        elif n in by_name:
            cid, how = by_name[n], "name"
        else:
            # Coin ids keep their hyphens, so compare the raw slug to ids and
            # only the normalised form to normalised names. Normalising before
            # the id comparison silently loses every hyphenated slug.
            raw_slug = (p.get("slug") or "").strip().lower()
            slug = norm(raw_slug)
            if raw_slug in ids:
                cid, how = raw_slug, "slug-id"
            elif slug and slug in by_name:
                cid, how = by_name[slug], "slug"
        if cid:
            matches[name] = {"coin_id": cid, "how": how}
        else:
            unresolved.append(p)

    # Names drift between snapshots (Freysa -> "Freysa AI", Phala Network ->
    # "PHALA", Trias -> "TriasLab"), so fall back to the contract address,
    # which does not. Only worth the calls for panel members that had a T1
    # market cap; the rest were never tokenised.
    still = []
    for p in unresolved:
        addr = (p.get("address") or "").strip()
        if not (p.get("market_cap") or "").strip() or ":" not in addr:
            still.append(p["project"])
            continue
        # The address column holds one "chain: 0x..." pair per deployment,
        # comma-separated. Splitting only on the first colon feeds the entire
        # remainder to the API as one contract and always 404s.
        cid = None
        for part in addr.split(","):
            chain, _, contract = part.partition(":")
            platform = PLATFORMS.get(chain.strip().lower())
            if not platform or not contract.strip():
                continue
            cid = lookup_contract(platform, contract.strip())
            if cid:
                break
        if cid:
            matches[p["project"]] = {"coin_id": cid, "how": "contract"}
        else:
            still.append(p["project"])
    unresolved = still

    OUT.write_text(json.dumps(matches, indent=2))
    print(f"\nresolved {len(matches)}/{len(panel)}")
    from collections import Counter
    print("  by method:", Counter(m["how"] for m in matches.values()))
    print(f"\nunresolved ({len(unresolved)}):")
    for n in unresolved:
        print(f"    {n}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
