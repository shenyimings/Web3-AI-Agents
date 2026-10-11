"""Test keywords covering the 2026 agent-standards ecosystem.

The ecosystem keyword set predates ERC-8004, x402, A2A and MCP, so it cannot
reach the repos that evidence the standards layer. This measures what an
extended keyword set would add.
Writes data/raw/gh_newkeywords.json.
"""

import json
import os
import pathlib
import re
import time

import requests

from gh_probe import WINDOW, API

NEW_KEYWORDS = [
    "ERC-8004", "erc8004", "x402", "trustless agent", "agent registry",
    "agentic payments", "agent commerce protocol", "A2A protocol",
    "onchain agent", "agent wallet", "MCP blockchain", "agent payments",
]

POOL = pathlib.Path(__file__).resolve().parents[1] / "data/raw/gh_candidates.json"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data/raw/gh_newkeywords.json"

STANDARDS = {
    "erc-8004": re.compile(r"erc[-\s]?8004", re.I),
    "x402": re.compile(r"\bx402\b", re.I),
    "a2a": re.compile(r"\ba2a\b", re.I),
    "mcp": re.compile(r"\bmcp\b", re.I),
    "erc-4337/7702": re.compile(r"erc[-\s]?(4337|7702)|account abstraction", re.I),
}


def count(session, q):
    r = session.get(API, params={"q": q, "per_page": 1})
    if r.status_code == 403:
        time.sleep(60)
        r = session.get(API, params={"q": q, "per_page": 1})
    r.raise_for_status()
    time.sleep(2.2)
    return r.json()["total_count"]


def main():
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    })

    print("=== how far the 2026 keywords reach ===")
    results = {}
    for kw in NEW_KEYWORDS:
        phrase = f'"{kw}"'
        row = {
            "window": count(session, f"{phrase} in:name,description {WINDOW}"),
            "window_stars1": count(
                session, f"{phrase} in:name,description {WINDOW} stars:>=1"),
            "window_stars5": count(
                session, f"{phrase} in:name,description {WINDOW} stars:>=5"),
        }
        results[kw] = row
        print(f"  {kw:26s} {row}", flush=True)
    OUT.write_text(json.dumps(results, indent=2))

    print("\n=== standards mentioned in the existing 534-repo pool ===")
    repos = json.loads(POOL.read_text())
    for name, pat in STANDARDS.items():
        hits = [r for r in repos
                if pat.search(f"{r['full_name']} {r.get('description') or ''}")]
        print(f"  {name:14s} {len(hits):3d} repos")
        for r in sorted(hits, key=lambda x: -x["stargazers_count"])[:5]:
            print(f"      {r['stargazers_count']:4d} {r['full_name']}")


if __name__ == "__main__":
    main()
