"""RQ3 governance salience across the T2 classified population.

RQ3 was written as survey prose with no measurement behind it. This supplies
one: how often governance appears at all in the classified projects, and how
much of that is agents *doing* governance rather than a token conferring voting
rights on its holders. The split is the point -- a regex on "governance" alone
would report every project whose description ends with a governance-utility
clause and say nothing.

The co-occurring descriptions were read by hand and coded into the three
classes below; the ids are recorded here rather than inferred so the coding is
auditable. Run from bcra-artifact/: uv run python scripts/rq3_governance.py
"""
import json
import re

import stats

ROOT = stats.ROOT

# Governance as a token utility: holders vote on the protocol. The agent in the
# sentence is what the protocol builds, not what governs it.
TOKEN_UTILITY = ["virtual-protocol", "cookie", "humans-ai", "kuvi",
                 "xeleb-protocol", "theoriq", "think-protocol", "arc",
                 "gemach", "anita-ai", "starly-the-star-guide",
                 "carv", "druid-ai", "hive-protocol-2", "misato", "morphware",
                 "neutaro", "sealcoin", "shogun", "theta-token", "vana",
                 "x402guard", "xiiid"]
# Agents act as governance participants: they delegate, vote, or decide.
AGENT_AS_ACTOR = ["autonolas", "ai16z", "thirdfy", "sentismai", "chirper-ai",
                  "agixbt-by-virtuals", "internet-computer", "juliaos",
                  "owockibot", "qudeai-framework"]
# Governance *of* agents: rules constraining agent behaviour, not agents voting.
AGENT_AS_SUBJECT = ["quack-ai", "odei", "pha", "newton-protocol", "uomi",
                    "covenant-foundation", "ember-3", "gitlawb", "nave-shares",
                    "robo-token-2", "victorai-by-virtuals"]

GOV = re.compile(r"\b(governance|DAOs?|vote[srd]?|voting|proposals?|quorum|"
                 r"delegat\w*|referend\w*)\b", re.I)
AGENT = re.compile(r"\b(agents?|agentic|AI|autonomous)\b", re.I)


def main():
    desc = json.loads((ROOT / "data/raw/cg_descriptions.json").read_text())
    scope = {r["id"]: r for r in stats.cls()}

    described, gov, co = {}, [], []
    for k, v in scope.items():
        d = (desc.get(k) or {}).get("description") or ""
        if not d.strip():
            continue
        described[k] = v
        sents = re.split(r"(?<=[.!?])\s+|\n+", d)
        g = [s for s in sents if GOV.search(s)]
        if g:
            gov.append(k)
            if any(AGENT.search(s) for s in g):
                co.append(k)

    coded = TOKEN_UTILITY + AGENT_AS_ACTOR + AGENT_AS_SUBJECT
    assert sorted(coded) == sorted(co), sorted(set(co) ^ set(coded))

    def cap(ids):
        return sum(stats.mcap(scope[i]) for i in ids)

    total = cap(scope)
    out = {
        "classified": len(scope),
        "with_description": len(described),
        "governance_vocabulary": len(gov),
        "governance_with_agent": len(co),
        "token_utility": {"n": len(TOKEN_UTILITY), "ids": TOKEN_UTILITY,
                          "mcap_usd": cap(TOKEN_UTILITY)},
        "agent_as_actor": {"n": len(AGENT_AS_ACTOR), "ids": AGENT_AS_ACTOR,
                           "mcap_usd": cap(AGENT_AS_ACTOR)},
        "agent_as_subject": {"n": len(AGENT_AS_SUBJECT),
                             "ids": AGENT_AS_SUBJECT,
                             "mcap_usd": cap(AGENT_AS_SUBJECT)},
        "total_mcap_usd": total,
    }
    # One general-purpose L1 carries almost all of the actor class's value, so
    # the class total on its own would overstate how much capital sits behind
    # agents that actually govern.
    largest = max(AGENT_AS_ACTOR, key=lambda i: stats.mcap(scope[i]))
    out["agent_as_actor"]["largest"] = scope[largest]["name"]
    out["agent_as_actor"]["mcap_ex_largest_usd"] = (
        cap(AGENT_AS_ACTOR) - stats.mcap(scope[largest]))
    for key in ("token_utility", "agent_as_actor", "agent_as_subject"):
        out[key]["share"] = out[key]["mcap_usd"] / total
    (ROOT / "data/processed/rq3_governance.json").write_text(
        json.dumps(out, indent=1) + "\n")

    print(f"{out['classified']} classified, {out['with_description']} with a "
          f"description")
    print(f"  governance vocabulary anywhere : {out['governance_vocabulary']} "
          f"({out['governance_vocabulary']/out['with_description']:.1%})")
    print(f"  ... in a sentence with an agent: {out['governance_with_agent']}")
    for key in ("token_utility", "agent_as_actor", "agent_as_subject"):
        r = out[key]
        print(f"    {key:17s} {r['n']:3d}  ${r['mcap_usd']/1e6:8.1f}M  "
              f"{r['mcap_usd']/total:5.2%} of ${total/1e9:.2f}B")


if __name__ == "__main__":
    main()
