"""Card-sort the T2 detail set into the T1 taxonomy.

Two layers, both recorded so a second rater can see which is which.

*Rules.* A small set of CoinGecko category labels map onto exactly one
subcategory and nothing else. Where one fires, the assignment is deterministic
and its provenance is `rule`. Generic labels (`Artificial Intelligence (AI)`,
`Layer 1 (L1)`, ecosystem tags) are deliberately not in this table: they carry
no functional information and firing on them would manufacture agreement.

*Reading.* Everything a rule does not settle goes to coding/worklist-*.json,
is coded against coding/CODING-MANUAL.md, and comes back in
coding/decisions-NN.json with a one-line justification per project. Provenance
`read`.

  uv run python scripts/classify_t2.py worklist   # emit what needs reading
  uv run python scripts/classify_t2.py merge      # fold decisions back in

Writes data/processed/t2_taxonomy.json.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, PROC, DRAFT = ROOT / "data/raw", ROOT / "data/processed", ROOT / "coding"

# A CoinGecko label earns a place here only if it names a function rather than a
# theme, and maps to one subcategory without needing the description.
RULES = {
    "AI Agent Launchpad": "launchpad",
    "AI Framework": "builder",
    "DeFAI": "defai",
    "DePIN": "infrastructure",
    "Analytics": "analytics",
    "Real World Assets (RWA)": "rwa",
    "Gaming (GameFi)": "game",
    "Metaverse": "game",
    "Oracle": "trust",
    "Zero Knowledge (ZK)": "trust",
}

SUBCATS = ["builder", "launchpad", "infrastructure", "trust", "copilot",
           "defai", "analytics", "game", "content-creation", "rwa"]
RESIDUAL = ["out-of-scope", "unclassifiable"]

# A strict refinement of `infrastructure`, recorded separately from `labels`.
FACETS = ["chain", "compute", "model", "data"]


def load():
    """The universe is the screened T2 population (data/processed/t2_population.json).

    It supersedes the narrower cg_descriptions detail set used earlier;
    the two are kept in one shape so the rule layer below is unchanged.
    """
    pop = json.loads((PROC / "t2_population.json").read_text())
    desc, detail = {}, {}
    for r in pop["projects"]:
        desc[r["id"]] = {"name": r["name"], "categories": r.get("coingecko_labels", []),
                         "homepage": [r.get("homepage") or ""],
                         "description": r.get("description")}
        detail[r["id"]] = {"market_cap_usd": r.get("market_cap_usd"),
                           "platforms": r.get("platforms", {})}
    return desc, detail


def clean(text):
    """CoinGecko blurbs carry HTML links and boilerplate; strip to prose."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_rules(desc):
    out = {}
    for cid, d in desc.items():
        labels = sorted({RULES[c] for c in d.get("categories", []) if c in RULES})
        if labels:
            fired = sorted({c for c in d.get("categories", []) if c in RULES})
            out[cid] = {
                "labels": labels,
                "provenance": "rule",
                "confidence": "high",
                "why": "CoinGecko category " + ", ".join(f"`{c}`" for c in fired),
            }
    return out


def cmd_worklist():
    desc, detail = load()
    ruled = apply_rules(desc)
    todo = []
    for cid, d in desc.items():
        if cid in ruled:
            continue
        todo.append({
            "id": cid,
            "name": d.get("name"),
            "mcap": detail[cid]["market_cap_usd"],
            "categories": d.get("categories", []),
            "homepage": (d.get("homepage") or [""])[0],
            "description": clean(d.get("description"))[:700],
        })
    todo.sort(key=lambda r: -(r["mcap"] or 0))
    n = 60
    chunks = [todo[i:i + n] for i in range(0, len(todo), n)]
    for i, ch in enumerate(chunks, 1):
        (DRAFT / f"worklist-{i:02d}.json").write_text(json.dumps(ch, indent=1))
    print(f"{len(ruled)} settled by rule, {len(todo)} to read "
          f"across {len(chunks)} worklists")


def cmd_merge():
    desc, detail = load()
    out = apply_rules(desc)
    # Coded rows that the screened population no longer contains
    # (delisted, or removed by S5) are dropped: the population is the universe.
    dropped = []
    for f in sorted(DRAFT.glob("decisions-*.json")):
        for cid, rec in json.loads(f.read_text()).items():
            if cid not in desc:
                dropped.append(cid)
                continue
            out[cid] = {"labels": rec["labels"],
                        "provenance": rec.get("provenance", "read"),
                        "confidence": rec["confidence"], "why": rec["why"]}
            if rec.get("sibling"):
                out[cid]["sibling"] = rec["sibling"]
            if rec.get("facet"):
                out[cid]["facet"] = rec["facet"]

    if dropped:
        print(f"{len(sorted(set(dropped)))} coded rows dropped: not in the "
              f"screened population, e.g. {sorted(set(dropped))[:5]}")

    missing = [c for c in desc if c not in out]
    if missing:
        print(f"WARNING: {len(missing)} unassigned, e.g. {missing[:5]}")

    for cid, rec in out.items():
        bad = [l for l in rec["labels"] if l not in SUBCATS + RESIDUAL]
        assert not bad, f"{cid}: unknown label {bad}"
        facet = rec.get("facet")
        # The facet partitions `infrastructure` exactly: required there, absent
        # everywhere else, so that dropping it reproduces the T1-comparable coding.
        if "infrastructure" in rec["labels"]:
            assert facet in FACETS, f"{cid}: infrastructure needs a facet, got {facet!r}"
        else:
            assert facet is None, f"{cid}: facet {facet!r} outside infrastructure"
        rec["name"] = desc[cid].get("name")
        rec["market_cap_usd"] = detail[cid]["market_cap_usd"]
        rec["platforms"] = detail[cid]["platforms"]

    (PROC / "t2_taxonomy.json").write_text(json.dumps(out, indent=1))
    print(f"{len(out)} classified -> {PROC / 't2_taxonomy.json'}")


if __name__ == "__main__":
    {"worklist": cmd_worklist, "merge": cmd_merge}[sys.argv[1]]()
