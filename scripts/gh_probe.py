"""Probe GitHub search volume for the paper's keyword set.

Answers: how many repos exist in the T1->T2 collection window, and how fast
does the count collapse as quality gates are applied.
Writes data/raw/gh_probe.json.
"""

import json
import os
import pathlib
import time

import requests

WINDOW = "created:2025-04-01..2026-06-01"

# The 15 keywords from the paper's ecosystem keyword group (paper/tex/03-methodology.tex).
KEYWORDS = [
    "Web3 AI", "blockchain AI", "Web3 agent", "Crypto agent", "DeFi agent",
    "Web3 AI Agent", "Crypto AI Agent", "Crypto LLM Agent", "Crypto LLM",
    "Crypto AI", "Blockchain Agent", "Chain Agent", "Decentralized AI Agent",
    "Blockchain LLM", "DeFi AI",
]

API = "https://api.github.com/search/repositories"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data/raw/gh_probe.json"


def count(session, q):
    """Return total_count for a search query, pacing against the 30/min limit."""
    r = session.get(API, params={"q": q, "per_page": 1})
    if r.status_code == 403:
        time.sleep(60)
        r = session.get(API, params={"q": q, "per_page": 1})
    r.raise_for_status()
    time.sleep(2.2)
    return r.json()["total_count"]


def main():
    token = os.environ["GITHUB_TOKEN"]
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })

    results = {}
    for kw in KEYWORDS:
        phrase = f'"{kw}"'
        row = {
            "name_desc_all_time": count(session, f"{phrase} in:name,description"),
            "name_desc_window": count(session, f"{phrase} in:name,description {WINDOW}"),
            "readme_window": count(session, f"{phrase} in:readme {WINDOW}"),
            "window_stars1": count(
                session, f"{phrase} in:name,description {WINDOW} stars:>=1"),
            "window_stars10": count(
                session, f"{phrase} in:name,description {WINDOW} stars:>=10"),
        }
        results[kw] = row
        print(f"{kw:24s} {row}", flush=True)

    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
