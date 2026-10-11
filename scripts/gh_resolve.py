"""Resolve GitHub repos into projects (the many-to-one step).

Primary grouping key is the owner account, which merges the common case of one
venture shipping several SDKs. Homepage domains are carried as a secondary
signal: a group whose repos point at disagreeing domains is a candidate for
manual splitting, and is reported rather than split automatically.
Writes data/raw/gh_projects.json.
"""

import json
import pathlib
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
IN = RAW / "gh_discovery.json"
OUT = RAW / "gh_projects.json"

# Hosts where each subdomain is a different project, so the full host is the
# identity rather than the registrable domain.
MULTITENANT = {
    "github.io", "vercel.app", "netlify.app", "pages.dev", "herokuapp.com",
    "gitbook.io", "notion.site", "readthedocs.io", "streamlit.app", "web.app",
}

# Self-references and package registries: present on many repos, identify none.
NOT_PRODUCT_SITES = {
    "github.com", "npmjs.com", "pypi.org", "nuget.org", "crates.io",
    "docs.rs", "pkg.go.dev", "hex.pm", "rubygems.org",
}


def domain_of(url):
    if not url:
        return None
    try:
        host = urlparse(url if "//" in url else f"//{url}").hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower().removeprefix("www.")
    labels = host.split(".")
    if len(labels) >= 3:
        registrable = ".".join(labels[-2:])
        if registrable in MULTITENANT:
            return host
        return registrable
    return host


def main():
    repos = json.loads(IN.read_text())
    print(f"repos in: {len(repos)}")

    groups = defaultdict(list)
    for r in repos:
        groups[r["owner"]].append(r)

    projects = []
    for owner, members in groups.items():
        domains = {d for d in (domain_of(r.get("homepage")) for r in members) if d}
        domains -= NOT_PRODUCT_SITES
        keywords = sorted({k for r in members for k in r["matched_keywords"]})
        eras = sorted({e for r in members for e in r["keyword_era"]})
        projects.append({
            "project_key": owner,
            "owner_type": members[0]["owner_type"],
            "repo_count": len(members),
            "repos": [r["full_name"] for r in members],
            "domains": sorted(domains),
            "total_stars": sum(r["stargazers_count"] for r in members),
            "max_stars": max(r["stargazers_count"] for r in members),
            "earliest_created": min(r["created_at"] for r in members),
            "latest_push": max(r["pushed_at"] for r in members),
            "languages": sorted({r["language"] for r in members if r["language"]}),
            "matched_keywords": keywords,
            "keyword_era": eras,
            "description": max(
                (r.get("description") or "" for r in members), key=len),
        })

    projects.sort(key=lambda p: -p["total_stars"])
    OUT.write_text(json.dumps(projects, indent=2))

    sizes = Counter(p["repo_count"] for p in projects)
    print(f"projects out: {len(projects)}  (compression {len(repos)/len(projects):.2f} repos/project)")
    print(f"group size distribution: {dict(sorted(sizes.items()))}")

    multi = [p for p in projects if p["repo_count"] > 1]
    print(f"\nmulti-repo projects: {len(multi)}")
    for p in sorted(multi, key=lambda x: -x["repo_count"])[:12]:
        print(f"  {p['repo_count']:2d} repos  {p['project_key'][:28]:28s} "
              f"{p['total_stars']:6d}★  domains={p['domains'] or '-'}")

    ambiguous = [p for p in projects if len(p["domains"]) > 1]
    print(f"\ngroups with disagreeing domains (manual split candidates): {len(ambiguous)}")
    for p in ambiguous[:10]:
        print(f"  {p['project_key'][:26]:26s} {p['domains']}")

    print(f"\nby keyword era: "
          f"{Counter(tuple(p['keyword_era']) for p in projects).most_common()}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
