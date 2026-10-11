"""Repo-level census of the 2026 agent-standards layer.

Reported separately from the project taxonomy on purpose: the unit here is a
repository, and one protocol routinely accounts for dozens of them, so folding
these counts into project categories would inflate them.
"""

import json
import pathlib
import re
from collections import Counter, defaultdict

RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"

STANDARDS = {
    "x402": re.compile(r"\bx402\b", re.I),
    "ERC-8004": re.compile(r"erc[-\s]?8004|trustless agent", re.I),
    "A2A": re.compile(r"\ba2a\b|agent2agent|agent-to-agent", re.I),
    "MCP": re.compile(r"\bmcp\b|model context protocol", re.I),
    "AP2/ACP": re.compile(r"\bap2\b|agent payments protocol|agent commerce protocol", re.I),
    "AA (4337/7702)": re.compile(r"erc[-\s]?(4337|7702)|account abstraction|smart wallet", re.I),
}


def main():
    repos = json.loads((RAW / "gh_discovery.json").read_text())
    print(f"discovery pool: {len(repos)} repos\n")

    tagged = defaultdict(list)
    for r in repos:
        text = f"{r['full_name']} {r.get('description') or ''} {' '.join(r.get('topics') or [])}"
        for name, pat in STANDARDS.items():
            if pat.search(text):
                tagged[name].append(r)

    print("=== repos per standard ===")
    for name in STANDARDS:
        hits = tagged[name]
        if not hits:
            print(f"  {name:16s}   0")
            continue
        stars = sorted((h["stargazers_count"] for h in hits), reverse=True)
        print(f"  {name:16s} {len(hits):4d} repos | "
              f"{sum(stars):6d}★ total | median {stars[len(stars)//2]:4d}★ | "
              f"max {stars[0]}★")

    print("\n=== monthly repo creation, by standard ===")
    months = sorted({r["created_at"][:7] for r in repos})
    header = "  month    " + "".join(f"{n[:8]:>10s}" for n in STANDARDS)
    print(header)
    for m in months:
        row = f"  {m}  "
        for name in STANDARDS:
            row += f"{sum(1 for r in tagged[name] if r['created_at'][:7] == m):10d}"
        print(row)

    untagged = [r for r in repos
                if not any(r in tagged[n] for n in STANDARDS)]
    print(f"\nrepos matching no standard: {len(untagged)} "
          f"({100*len(untagged)/len(repos):.0f}%)")

    print("\n=== top repos per standard ===")
    for name in STANDARDS:
        hits = sorted(tagged[name], key=lambda x: -x["stargazers_count"])[:5]
        if not hits:
            continue
        print(f"  {name}:")
        for h in hits:
            print(f"     {h['stargazers_count']:6d}  {h['full_name'][:46]:46s} "
                  f"{h['created_at'][:7]}")

    owners = Counter(r["owner"] for r in repos)
    print(f"\ndistinct owners: {len(owners)} | "
          f"top: {owners.most_common(5)}")


if __name__ == "__main__":
    main()
