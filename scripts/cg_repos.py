"""Fetch GitHub metadata for repos referenced by CoinGecko coins.

This is the measurement use of GitHub, deliberately NOT restricted to the
discovery window: an established token project's repos usually predate
2025-04, and window-filtering them would misclassify the project as having no
repository at all.
Writes data/raw/cg_repo_meta.json.
"""

import json
import os
import pathlib
import time
from urllib.parse import urlparse

import requests

RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
IN = RAW / "cg_details.json"
OUT = RAW / "cg_repo_meta.json"


def parse_ref(url):
    """Classify a github link as ('repo', 'owner/name') or ('owner', 'owner')."""
    try:
        path = urlparse(url).path.strip("/")
    except ValueError:
        return None
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return "repo", f"{parts[0]}/{parts[1]}"
    if len(parts) == 1:
        return "owner", parts[0]
    return None


def main():
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    })

    coins = json.loads(IN.read_text())
    repo_refs, owner_refs = set(), set()
    for c in coins:
        for url in c["github_repos"]:
            parsed = parse_ref(url)
            if not parsed:
                continue
            kind, value = parsed
            (repo_refs if kind == "repo" else owner_refs).add(value)

    print(f"coins: {len(coins)}  repo refs: {len(repo_refs)}  "
          f"owner-only refs: {len(owner_refs)}")

    out = {}
    if OUT.exists():
        out = json.loads(OUT.read_text())
        print(f"resuming: {len(out)} already fetched")

    def save():
        OUT.write_text(json.dumps(out, indent=2))

    todo = [r for r in sorted(repo_refs) if f"repo:{r}" not in out]
    for i, full_name in enumerate(todo, 1):
        r = session.get(f"https://api.github.com/repos/{full_name}")
        if r.status_code == 404:
            out[f"repo:{full_name}"] = {"kind": "repo", "missing": True}
        elif r.status_code == 403:
            time.sleep(60)
            continue
        else:
            r.raise_for_status()
            d = r.json()
            out[f"repo:{full_name}"] = {
                "kind": "repo", "full_name": d["full_name"],
                "owner": d["owner"]["login"], "stars": d["stargazers_count"],
                "forks": d["forks_count"], "created_at": d["created_at"],
                "pushed_at": d["pushed_at"], "archived": d["archived"],
                "size": d["size"], "language": d["language"],
            }
        if i % 50 == 0:
            save()
            print(f"  repo {i}/{len(todo)}", flush=True)
        time.sleep(0.15)
    save()

    todo = [o for o in sorted(owner_refs) if f"owner:{o}" not in out]
    for i, owner in enumerate(todo, 1):
        r = session.get(f"https://api.github.com/users/{owner}/repos",
                        params={"per_page": 100, "sort": "pushed"})
        if r.status_code in (404, 451):
            out[f"owner:{owner}"] = {"kind": "owner", "missing": True}
        elif r.status_code == 403:
            time.sleep(60)
            continue
        else:
            r.raise_for_status()
            repos = r.json()
            out[f"owner:{owner}"] = {
                "kind": "owner", "owner": owner, "repo_count": len(repos),
                "stars": sum(x["stargazers_count"] for x in repos),
                "pushed_at": max((x["pushed_at"] for x in repos), default=None),
                "created_at": min((x["created_at"] for x in repos), default=None),
                "top_repos": [x["full_name"] for x in repos[:5]],
            }
        if i % 50 == 0:
            save()
            print(f"  owner {i}/{len(todo)}", flush=True)
        time.sleep(0.15)
    save()

    print(f"\nfetched {len(out)} refs -> {OUT}")


if __name__ == "__main__":
    main()
