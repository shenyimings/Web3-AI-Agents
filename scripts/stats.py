r"""Every number in the paper, computed once.

This module holds no formatting and draws nothing. It reads
``data/processed/*.json`` and returns plain Python values, so that
``numbers.py`` (which writes ``paper/numbers.tex``) and ``figures.py`` (which
draws into ``paper/figures/``) cannot disagree about what the data says. A
number that appears in both a figure and a sentence is computed here or it is a
bug.

Deliberately small. Aggregation is one generic function (:func:`agg`) plus a
key function per cut; anything specific to one figure's layout, or to one
sentence's wording, belongs in the caller.

Frames -- the four populations the paper must never mix. Function names carry
the frame, and so do the macros generated from them:

    pop    the screened T2 population (2026-09-01), aggregates and concentration
    cls    the classified projects, every per-project attribute
    coh    the T1 cohort fixed from web archives, survival and value change
    rep    the token-frame vs repo-frame coverage comparison
"""

import json
import pathlib
import statistics

from crossmatch import ALIVE_USD, STALE_DAYS  # noqa: F401  (re-exported)

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"

# The taxonomy's own vocabulary. `labels` carries subcategory slugs; two of them
# are not guessable from the slug, so the mapping is written out rather than
# derived: `copilot` is Infrastructure's AI-powered Development, and
# `digital-twin` (a T1 label with no T2 rows) folds into Game & Metaverse.
PRIMARY = {
    "builder": "incubation", "launchpad": "incubation",
    "infrastructure": "infrastructure", "trust": "infrastructure",
    "copilot": "infrastructure",
    "defai": "financial", "analytics": "financial",
    "game": "creative", "digital-twin": "creative",
    "content-creation": "creative", "rwa": "creative",
}
PRIMARY_ORDER = ["incubation", "infrastructure", "financial", "creative"]
SUBCAT_ORDER = ["builder", "launchpad", "infrastructure", "trust", "copilot",
                "defai", "analytics", "game", "content-creation", "rwa"]
FACET_ORDER = ["chain", "compute", "model", "data"]
# Not subcategories: a row carrying either of these is not a classified project.
RESIDUAL = {"out-of-scope", "unclassifiable"}
# T1-only labels that have no T2 subcategory of their own. Folding them here
# keeps the panel's subcategory cuts comparable with the T2 taxonomy.
FOLD = {"digital-twin": "game"}


def read(name):
    return json.loads((PROC / f"{name}.json").read_text())


def read_raw(name):
    return json.loads((ROOT / f"data/raw/{name}.json").read_text())


# --- generic aggregation -----------------------------------------------------

def mcap(row):
    return row.get("market_cap_usd") or 0.0


def agg(rows, key):
    """Group ``rows`` by ``key(row) -> iterable of keys``, summing count and value.

    A row with several keys counts once under each, so counts sum to
    assignments rather than to projects wherever labels overlap. Callers that
    report such a total say so.
    """
    out = {}
    for row in rows:
        for k in key(row):
            bucket = out.setdefault(k, {"n": 0, "mcap": 0.0})
            bucket["n"] += 1
            bucket["mcap"] += mcap(row)
    for bucket in out.values():
        bucket["mean"] = bucket["mcap"] / bucket["n"]
    return out


def gini(values):
    v = sorted(x for x in values if x > 0)
    n = len(v)
    return sum((2 * i - n - 1) * x for i, x in enumerate(v, 1)) / (n * sum(v))


def top_share(values, fraction):
    """Share of total value held by the largest ``fraction`` of items."""
    v = sorted((x for x in values if x > 0), reverse=True)
    k = max(1, round(len(v) * fraction))
    return sum(v[:k]) / sum(v), k


def tiers(values, edges):
    """Count and value in each band of ``edges``, as [(lo, hi, n, mcap), ...]."""
    bounds = [0.0] + list(edges) + [float("inf")]
    out = []
    for lo, hi in zip(bounds, bounds[1:]):
        band = [x for x in values if lo <= x < hi]
        out.append((lo, hi, len(band), sum(band)))
    return out


# --- pop: the screened T2 population ----------------------------------------

def pop():
    p = read("t2_population")
    values = [mcap(r) for r in p["projects"]]
    return {
        "date": p["timepoint"],
        "n": p["n"],
        "mcap": p["market_cap_usd"],
        "mean": p["market_cap_usd"] / p["n"],
        "median": sorted(values)[len(values) // 2],
        "gini": gini(values),
        "values": values,
        "no_description": len(p["unclassifiable_no_description"]),
        "flag_s2a": len(p["flags"]["s2a"]),
        "flag_s2b": len(p["flags"]["s2b_groups"]),
        "flag_s5": len(p["flags"]["s5"]),
        "projects": p["projects"],
    }


def screening():
    """The funnel from the raw frame to the screened population.

    The frame, the S1 cut and the value removed by each rule are properties of
    the collection rather than of the screened file, so they are recomputed
    from the raw capture. Market capitalization is read at the cutoff date
    (``cg_history_t2.json``), never at the collection date.
    """
    frame = json.loads((ROOT / "data/raw/cg_details.json").read_text())
    hist = json.loads((ROOT / "data/raw/cg_history_t2.json").read_text())
    mechanical = json.loads((PROC / "t2_screened_ids.json").read_text())
    p = read("t2_population")

    def value(ids):
        return sum(hist.get(i, {}).get("market_cap_usd") or 0 for i in ids)

    capitalised = [r["id"] for r in frame if hist.get(r["id"], {}).get("market_cap_usd")]
    return {
        "frame": len(frame),
        "capitalised": len(capitalised),
        "not_capitalised": len(frame) - len(capitalised),
        "s2a": len(p["flags"]["s2a"]),
        "s2a_value": value(p["flags"]["s2a"]),
        "s2b_groups": len(p["flags"]["s2b_groups"]),
        # Distinct listings removed, not the sum over groups: a token that is a
        # secondary listing of two grouped projects would otherwise be counted
        # twice and the screening funnel would not add up.
        "s2b": len({i for g in p["flags"]["s2b_groups"] for i in g[1:]}),
        "s5": len(p["flags"]["s5"]),
        "s5_value": value(p["flags"]["s5"]),
        "mechanical": len(mechanical),
        "mechanical_mcap": value(mechanical),
        "no_description": len(p["unclassifiable_no_description"]),
        "no_description_value": value(p["unclassifiable_no_description"]),
        "screened": p["n"],
        "screened_mcap": p["market_cap_usd"],
    }


# --- cls: the classified projects -------------------------------------------

def cls():
    """Rows the coder assigned at least one subcategory.

    ``out-of-scope`` and ``unclassifiable`` are residual outcomes of coding, not
    categories: excluding only the former would let 37 uncoded rows into every
    per-project result.
    """
    rows = read("t2_taxonomy")
    return [r | {"id": k} for k, r in rows.items()
            if not RESIDUAL & set(r["labels"])]


def residual():
    rows = read("t2_taxonomy")
    return {name: sum(1 for r in rows.values() if name in r["labels"])
            for name in sorted(RESIDUAL)}


def by_subcategory(rows):
    return agg(rows, lambda r: r["labels"])


def by_primary(rows):
    return agg(rows, lambda r: {PRIMARY[l] for l in r["labels"]})


def by_facet(rows):
    return agg(rows, lambda r: [r["facet"]] if r.get("facet") else [])


def by_platform(rows, floor=1):
    """One entry per deployment. Tokens with no platform are native coins of
    their own chain and are dropped rather than guessed at."""
    out = agg(rows, lambda r: [p for p in (r.get("platforms") or {}) if p])
    return {k: v for k, v in out.items() if v["n"] >= floor}


def coding(rows):
    """How the labels were produced, for the reliability paragraph."""
    def tally(field):
        out = {}
        for r in rows:
            out[r[field]] = out.get(r[field], 0) + 1
        return out
    return {
        "provenance": tally("provenance"),
        "confidence": tally("confidence"),
        "multi_label": sum(1 for r in rows if len(r["labels"]) > 1),
        "multi_label_mcap": sum(mcap(r) for r in rows if len(r["labels"]) > 1),
    }


# --- coh: the T1 cohort, fixed from web archives -----------------------------

def coh():
    """The T1 cohort: membership fixed at T1 from archived category pages.

    ``t1_union_cohort.json`` is an earlier, wider construction with different
    membership and is not read here.
    """
    c = read("t1_t2_cohort")
    values = [r["t1_market_cap_usd"] for r in read("t1_cohort")["projects"]]
    return c | {"values": [v for v in values if v]}


def t1_labels():
    """The T1 search set recoded under the T2 coding manual.

    Same coder, same manual, so a composition comparison between the timepoints
    cannot be an artifact of the coding. The breadths differ, which is why only
    composition is compared and never pooled.
    """
    labels = read("t1_labels")
    panel = {r["coin_id"]: r for r in read("panel_attrition") if r.get("coin_id")}
    return [{"id": i, "labels": ls,
             "market_cap_usd": (panel.get(i) or {}).get("t1") or 0.0}
            for i, ls in labels.items()]


def panel():
    """The 133 T1 projects from date-restricted Google search, traced forward.

    Outcomes are reported over the members that carried a capitalization at T1,
    since a project with no T1 value has no retention to measure. Value at the
    far end is read at the T2 cutoff (``t2``), never at the collection date
    (``now``): every other statistic in the paper is dated at the cutoff, and a
    retention ratio measured days later would be the one exception.
    """
    rows = read("panel_attrition")
    cap = [r for r in rows if r["t1"]]
    status = {}
    for r in cap:
        status[r["status"]] = status.get(r["status"], 0) + 1
    listed = [r for r in cap if r["status"] == "in category"]
    kept = [r for r in listed if r["t2"]]
    retention = sorted(r["t2"] / r["t1"] for r in kept)
    # The aggregate is a value-weighted statistic, so what holds it up is the
    # largest surviving holding, not the largest ratio.
    by_value = sorted(kept, key=lambda r: -r["t2"])
    rest = by_value[2:]
    return {
        "n": len(rows),
        "capitalised_t1": len(cap),
        "t1_mcap": sum(r["t1"] for r in cap),
        "matched": sum(1 for r in cap if r["t2"]),
        "t2_mcap": sum(r["t2"] or 0 for r in cap),
        "status": status,
        "listed": len(listed),
        "kept": len(kept),
        "kept_uncapitalised": len(listed) - len(kept),
        "kept_t1": sum(r["t1"] for r in kept),
        "kept_t2": sum(r["t2"] for r in kept),
        "kept_median": retention[len(retention) // 2],
        "grew": sum(1 for x in retention if x > 1),
        "lost_ninety": sum(1 for x in retention if x < 0.10),
        "lost_ninetynine": sum(1 for x in retention if x < 0.01),
        "top": sorted(kept, key=lambda r: -(r["t2"] / r["t1"]))[:2],
        "holdings": by_value[:2],
        "holdings_share": sum(r["t2"] for r in by_value[:2]) / sum(r["t2"] for r in kept),
        "ex_holdings": sum(r["t2"] for r in rest) / sum(r["t1"] for r in rest),
        "rows": rows,
    }


def panel_by_subcategory():
    """Median value retained, and the share still above $1M, per subcategory."""
    out = {}
    for r in read("panel_attrition"):
        if not r["t1"]:
            continue
        for label in {FOLD.get(c.strip(), c.strip())
                      for c in (r["category"] or "").split(",") if c.strip()}:
            b = out.setdefault(label, {"n": 0, "alive": 0, "retention": []})
            b["n"] += 1
            b["alive"] += bool((r["t2"] or 0) > ALIVE_USD)
            if r["t2"] and r["status"] == "in category":
                b["retention"].append(r["t2"] / r["t1"])
    for b in out.values():
        b["median"] = statistics.median(b["retention"]) if b["retention"] else None
        b["alive_share"] = b["alive"] / b["n"]
    return out


# --- rep: token frame vs repo frame ------------------------------------------

def rep():
    rows = read("projects")
    token = [r for r in rows if r["has_token"]]
    repo = [r for r in rows if r["has_repo"]]
    return {
        "n": len(rows),
        "token_only": sum(1 for r in rows if r["has_token"] and not r["has_repo"]),
        "repo_only": sum(1 for r in rows if r["has_repo"] and not r["has_token"]),
        "both": sum(1 for r in rows if r["has_token"] and r["has_repo"]),
        "token": len(token),
        "repo": len(repo),
        "repo_active": sum(1 for r in rows if r["repo_active"]),
        "token_alive": sum(1 for r in rows if r["token_alive"]),
        "rows": rows,
    }


# --- the standards layer -----------------------------------------------------

def governance():
    return read("rq3_governance")


SUSTAINED_FROM = "2026-02"   # first month after the launch burst


def x402():
    """Monthly aggregates plus the settlement-level distribution.

    The distribution figures are transcribed from the Dune queries named in
    ``x402_settlements.json``; the free tier has no export, so that file is the
    record of what those queries returned.
    """
    months = read("x402_monthly")
    dist = read("x402_settlements")
    # The two launch months are a different regime -- the first is one payer
    # pair repeating, the second the wash-trading burst -- so the payee range
    # that characterises ordinary months is taken from the sustained period.
    sustained = [m for m in months if m["month"] >= SUSTAINED_FROM]
    return {
        **dist,
        "months": months,
        "n_months": len(months),
        "first": months[0]["month"], "last": months[-1]["month"],
        "settlements": sum(m["settlements"] for m in months),
        "usd": sum(m["usd"] for m in months),
        "peak_settlements": max(m["settlements"] for m in months),
        "sustained_from": SUSTAINED_FROM,
        "payees_sustained_low": min(m["payees"] for m in sustained),
        "payees_sustained_high": max(m["payees"] for m in sustained),
        "payers_sustained_low": min(m["payers"] for m in sustained),
        "payers_sustained_high": max(m["payers"] for m in sustained),
        # The second dollar-scale month. The record is sub-cent apart from this
        # month and the December burst, so the prose may not call either unique.
        "second": max((m for m in months if m["month"] != dist["burst"]["date"][:7]),
                      key=lambda m: m["usd"]),
    }


def standards():
    """Repo-level census of the agent-standards layer.

    The unit is a repository, not a project: one protocol routinely accounts
    for dozens, so these counts never fold into the taxonomy. Patterns live in
    ``standards_census.py``, which prints the same census by month.
    """
    import standards_census as sc

    repos = read_raw("gh_discovery")
    out = {"pool": len(repos)}
    for name, pat in sc.STANDARDS.items():
        hits = [r for r in repos
                if pat.search(f"{r['full_name']} {r.get('description') or ''} "
                              f"{' '.join(r.get('topics') or [])}")]
        stars = sorted((h["stargazers_count"] for h in hits), reverse=True)
        out[name] = {"repos": len(hits), "stars": sum(stars)}
    return out


def erc8004():
    """Identity registrations per chain, plus the reputation registry.

    ``registrants`` is counted per chain, so the cross-chain total is an upper
    bound on unique entities. ``per_registrant`` is the ratio that separates the
    two Sybil regimes: near 1.0 is many wallets registering one agent each,
    tens is a few wallets registering thousands.
    """
    chains = sorted(read("erc8004_chains"),
                    key=lambda c: -c["registrations"])
    for c in chains:
        c["per_registrant"] = c["registrations"] / c["registrants"]
    rep = read("erc8004_reputation")["chains"]
    rep.sort(key=lambda c: -c["calls"])
    calls = sum(c["calls"] for c in rep)
    senders = sum(c["senders"] for c in rep)
    registrations = sum(c["registrations"] for c in chains)
    registrants = sum(c["registrants"] for c in chains)
    return {
        "chains": chains,
        "by_chain": {c["chain"]: c for c in chains},
        "n_chains": len(chains),
        "registrations": registrations,
        "registrants": registrants,
        "tail": sum(c["registrations"] for c in chains[3:]),
        "n_tail": len(chains) - 3,
        "top": chains[0],
        "reputation": rep,
        "rep_by_chain": {c["chain"]: c for c in rep},
        "rep_calls": calls,
        "rep_senders": senders,
        "rep_sender_share": senders / registrants,
    }


def pairs(rows, top=4):
    """The commonest subcategory co-occurrences among multi-label projects."""
    out = {}
    for r in rows:
        labels = sorted(r["labels"])
        for i, a in enumerate(labels):
            for b in labels[i + 1:]:
                out[(a, b)] = out.get((a, b), 0) + 1
    return sorted(out.items(), key=lambda kv: -kv[1])[:top]


def chains(rows):
    """Deployment structure: how many projects list a chain, and on how many."""
    listed = [r for r in rows if r.get("platforms")]
    per = [len([p for p in r["platforms"] if p]) for r in listed]
    by = by_platform(rows)
    return {
        "listed": len(listed),
        "deployments": sum(per),
        "networks": len(by),
        "multichain": sum(1 for n in per if n > 1),
        "by": by,
    }


def repo_activity(rows):
    """Active-development rate per primary category, over projects with a repo.

    Repository evidence comes from the crossmatch frame, so this is conditional
    on a project publishing a repository at all and is an upper bound.
    """
    ev = {r["coin_id"]: r for r in read("projects") if r.get("coin_id")}
    out = {}
    for r in rows:
        e = ev.get(r["id"])
        if not e or not e["has_repo"]:
            continue
        for c in {PRIMARY[l] for l in r["labels"]}:
            b = out.setdefault(c, {"n": 0, "active": 0})
            b["n"] += 1
            b["active"] += bool(e["repo_active"])
    for b in out.values():
        b["rate"] = b["active"] / b["n"]
    # Distinct projects, not the sum over categories: a multi-label project
    # appears in each of its categories but is one project with one repository.
    out["_projects"] = sum(1 for r in rows
                           if (e := ev.get(r["id"])) and e["has_repo"])
    return out


def liveness():
    """The 2x2 of dual-evidence projects: a live token against live code."""
    rows = [r for r in read("projects") if r["has_token"] and r["has_repo"]]
    cell = lambda t, c: sum(1 for r in rows
                            if r["token_alive"] == t and r["repo_active"] == c)
    return {
        "n": len(rows),
        "both": cell(True, True), "neither": cell(False, False),
        "code_only": cell(False, True), "token_only": cell(True, False),
        "both_share": cell(True, True) / len(rows),
    }


def gh():
    """The GitHub discovery pool, and how little the two keyword sets overlap."""
    pool = read_raw("gh_discovery")
    groups = read_raw("gh_projects")
    era = lambda rows, want: sum(1 for r in rows
                                 if sorted(r["keyword_era"]) == want)
    return {
        "pool": len(pool),
        "legacy": era(pool, ["legacy"]),
        "standards": era(pool, ["standards"]),
        "both": era(pool, ["legacy", "standards"]),
        "groups": len(groups),
        "single": sum(1 for g in groups if g["repo_count"] == 1),
        "single_share": sum(1 for g in groups if g["repo_count"] == 1) / len(groups),
        "largest": max(g["repo_count"] for g in groups),
    }


def trend():
    """The monthly series behind the trend figure, so its caption is generated."""
    series = read_raw("cg_series")
    ids = {r["id"] for r in cls()}
    tracked = {c: v for c, v in series.items() if c in ids}
    cutoff = pop()["date"][:7]
    months = [m for m in sorted({m for v in tracked.values() for m in v})
              if m <= cutoff]
    live = [sum(1 for v in tracked.values() if (v.get(m) or 0) > 0) for m in months]
    value = [sum(v.get(m) or 0 for v in tracked.values()) for m in months]
    return {
        "tracked": len(tracked), "months": months,
        "first": months[0], "last": months[-1], "span": len(months),
        "live_first": live[0], "live_last": live[-1],
        "value_first": value[0], "value_last": value[-1],
    }
