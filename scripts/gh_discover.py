"""Collect the GitHub discovery pool for the T1->T2 window.

Uses the 15 ecosystem keywords plus 12 covering the 2026 agent-standards
ecosystem, which that set predates. The stars>=5 gate keeps every
query under the Search API's 1000-result cap while staying screenable.
Writes data/raw/gh_discovery.json.
"""

import json
import os
import pathlib
import time

import requests

from gh_probe import KEYWORDS as LEGACY_KEYWORDS, WINDOW, API
from gh_newkeywords import NEW_KEYWORDS

MIN_STARS = 5
OUT = pathlib.Path(__file__).resolve().parents[1] / "data/raw/gh_discovery.json"

FIELDS = [
    "full_name", "html_url", "homepage", "description", "created_at",
    "pushed_at", "updated_at", "stargazers_count", "forks_count",
    "open_issues_count", "size", "language", "topics", "fork", "archived",
]


def search_all(session, query):
    out, page = [], 1
    while True:
        r = session.get(API, params={
            "q": query, "per_page": 100, "page": page, "sort": "stars"})
        if r.status_code == 403:
            time.sleep(60)
            continue
        r.raise_for_status()
        items = r.json()["items"]
        out.extend(items)
        if len(items) < 100 or page >= 10:
            return out
        page += 1
        time.sleep(2.2)


def slim(repo, keyword, era):
    row = {f: repo.get(f) for f in FIELDS}
    row["license"] = (repo.get("license") or {}).get("spdx_id")
    row["owner"] = repo["owner"]["login"]
    row["owner_type"] = repo["owner"]["type"]
    row["matched_keywords"] = [keyword]
    row["keyword_era"] = [era]
    return row


def main():
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    })

    pool = {}
    plan = ([(kw, "legacy") for kw in LEGACY_KEYWORDS]
            + [(kw, "standards") for kw in NEW_KEYWORDS])

    for kw, era in plan:
        query = f'"{kw}" in:name,description {WINDOW} stars:>={MIN_STARS}'
        repos = search_all(session, query)
        for repo in repos:
            key = repo["full_name"]
            if key in pool:
                pool[key]["matched_keywords"].append(kw)
                if era not in pool[key]["keyword_era"]:
                    pool[key]["keyword_era"].append(era)
            else:
                pool[key] = slim(repo, kw, era)
        print(f"{era:9s} {kw:26s} fetched={len(repos):4d} pool={len(pool)}",
              flush=True)
        time.sleep(2.2)

    OUT.write_text(json.dumps(list(pool.values()), indent=2))

    legacy_only = sum(1 for r in pool.values() if r["keyword_era"] == ["legacy"])
    std_only = sum(1 for r in pool.values() if r["keyword_era"] == ["standards"])
    both = len(pool) - legacy_only - std_only
    print(f"\nunique repos: {len(pool)}")
    print(f"  legacy keywords only:    {legacy_only}")
    print(f"  standards keywords only: {std_only}")
    print(f"  reachable by both:       {both}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
