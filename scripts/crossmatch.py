"""Join the token side and the repo side, and build the two matrices.

Coverage matrix asks which evidence exists for a project; liveness matrix asks
whether that evidence is still warm at the T2 cutoff. The token-NO/repo-NO cell
is structurally empty: a project with neither a token nor a repository is
invisible to both sampling frames, so the matrices are conditional on discovery.
Writes data/processed/projects.json and prints both matrices.
"""

import json
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from gh_resolve import domain_of

RAW = pathlib.Path(__file__).resolve().parents[1] / "data/raw"
PROC = pathlib.Path(__file__).resolve().parents[1] / "data/processed"
PROC.mkdir(parents=True, exist_ok=True)

# The cutoff is read from the population file rather than written here: this
# module is imported by stats.py for its thresholds, and a hardcoded date drifts
# out of step with the population the moment it is re-collected.
T2 = datetime.fromisoformat(
    json.loads((pathlib.Path(__file__).resolve().parents[1]
                / "data/processed/t2_population.json").read_text())["timepoint"]
).replace(tzinfo=timezone.utc)
STALE_DAYS = 180
ALIVE_USD = 1e6


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def owner_of(url):
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    return parts[0] if parts else None


def population_ids():
    """The screened T2 population: the token frame the paper reports.

    ``cg_details.json`` is the whole collection, memes and uncapitalized shells
    included. Screening those out here keeps the coverage comparison on the same
    token frame as every other result.
    """
    pop = json.loads((PROC / "t2_population.json").read_text())
    return {p["id"] for p in pop["projects"]}


def load():
    keep = population_ids()
    return (
        [c for c in json.loads((RAW / "cg_details.json").read_text())
         if c["id"] in keep],
        json.loads((RAW / "cg_repo_meta.json").read_text()),
        json.loads((RAW / "gh_projects.json").read_text()),
        json.loads((RAW / "cg_history_t2.json").read_text())
        if (RAW / "cg_history_t2.json").exists() else {},
    )


def repo_evidence(coin, repo_meta):
    """Best repo signal for a coin: does code exist, and when was it last pushed."""
    best_push, has_code, names = None, False, []
    for url in coin["github_repos"]:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if len(parts) >= 2:
            key = f"repo:{parts[0]}/{parts[1]}"
        elif len(parts) == 1:
            key = f"owner:{parts[0]}"
        else:
            continue
        meta = repo_meta.get(key)
        if not meta or meta.get("missing"):
            continue
        has_code = True
        names.append(meta.get("full_name") or meta.get("owner"))
        pushed = parse_ts(meta.get("pushed_at"))
        if pushed and (best_push is None or pushed > best_push):
            best_push = pushed
    return has_code, best_push, names


def main():
    coins, repo_meta, gh_projects, hist = load()
    print(f"token side: {len(coins)} coins | repo side: {len(gh_projects)} "
          f"projects | repo meta: {len(repo_meta)} refs\n")

    gh_by_owner = {p["project_key"].lower(): p for p in gh_projects}
    gh_by_domain = defaultdict(list)
    for p in gh_projects:
        for d in p["domains"]:
            gh_by_domain[d].append(p)

    matched_gh = set()
    records = []

    for coin in coins:
        has_code, best_push, repo_names = repo_evidence(coin, repo_meta)
        owners = {owner_of(u) for u in coin["github_repos"] if owner_of(u)}
        domains = {domain_of(u) for u in coin["homepage"]} - {None}

        hit = None
        for o in owners:
            if o and o.lower() in gh_by_owner:
                hit = gh_by_owner[o.lower()]
                break
        if hit is None:
            for d in domains:
                if d in gh_by_domain:
                    hit = gh_by_domain[d][0]
                    break
        if hit:
            matched_gh.add(hit["project_key"])
            gh_push = parse_ts(hit["latest_push"])
            if gh_push and (best_push is None or gh_push > best_push):
                best_push = gh_push
            has_code = True

        mcap_t2 = (hist.get(coin["id"]) or {}).get("market_cap_usd")
        records.append({
            "project": coin["name"],
            "coin_id": coin["id"],
            "source": "coingecko",
            "discovered_by_github": bool(hit),
            "has_token": True,
            "has_repo": has_code,
            "market_cap_now": coin["market_cap_usd"],
            "market_cap_t2": mcap_t2,
            "last_push": best_push.isoformat() if best_push else None,
            "repos": repo_names,
            "categories": coin["categories"],
            "platforms": list(coin["platforms"]),
        })

    for p in gh_projects:
        if p["project_key"] in matched_gh:
            continue
        records.append({
            "project": p["project_key"],
            "coin_id": None,
            "source": "github",
            "discovered_by_github": True,
            "has_token": False,
            "has_repo": True,
            "market_cap_now": None,
            "market_cap_t2": None,
            "last_push": p["latest_push"],
            "repos": p["repos"],
            "categories": p["keyword_era"],
            "platforms": [],
        })

    for r in records:
        push = parse_ts(r["last_push"])
        r["repo_active"] = bool(push and (T2 - push).days < STALE_DAYS)
        mcap = r["market_cap_t2"] if r["market_cap_t2"] is not None else r["market_cap_now"]
        r["token_alive"] = bool(mcap and mcap > ALIVE_USD)

    (PROC / "projects.json").write_text(json.dumps(records, indent=2))

    def cell(pred):
        return sum(1 for r in records if pred(r))

    print(f"unified projects: {len(records)}")
    print(f"  matched on both sides: {len(matched_gh)}\n")

    print("=== coverage matrix (what evidence exists) ===")
    print("                repo YES    repo NO")
    print(f"  token YES     {cell(lambda r: r['has_token'] and r['has_repo']):8d}   "
          f"{cell(lambda r: r['has_token'] and not r['has_repo']):8d}")
    print(f"  token NO      {cell(lambda r: not r['has_token'] and r['has_repo']):8d}   "
          f"{'  n/a':>8s}   (structurally undiscoverable)")

    both = [r for r in records if r["has_token"] and r["has_repo"]]
    print(f"\n=== liveness matrix, within the {len(both)} token+repo projects ===")
    print("                repo active   repo stale")
    print(f"  token alive   {sum(1 for r in both if r['token_alive'] and r['repo_active']):10d}   "
          f"{sum(1 for r in both if r['token_alive'] and not r['repo_active']):10d}")
    print(f"  token dead    {sum(1 for r in both if not r['token_alive'] and r['repo_active']):10d}   "
          f"{sum(1 for r in both if not r['token_alive'] and not r['repo_active']):10d}")
    print(f"\n  (token alive = mcap > ${ALIVE_USD:,.0f} at T2; "
          f"repo active = pushed within {STALE_DAYS}d of {T2.date()})")

    gh_only = [r for r in records if not r["has_token"]]
    print(f"\nrepo-only projects (development without capitalisation): {len(gh_only)}")
    print(f"  of which active at T2: {sum(1 for r in gh_only if r['repo_active'])}")
    print(f"\nwrote {PROC / 'projects.json'}")


if __name__ == "__main__":
    main()
