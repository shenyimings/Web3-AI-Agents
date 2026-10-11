"""Cohort statistics for the T1 union cohort followed to T2 by date.

Membership is fixed at T1 from the web archives; each member's T2 value is its own
market capitalisation on 1 September 2026, so a member counts as gone only when it has
none. Frames differ only in which archived categories contribute members, which
lets the same statistics be recomputed as a robustness check.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COHORT = {"artificial-intelligence", "ai-agents", "ai-agent-launchpad", "defai"}
FRAMES = {
    "A_all_categories": COHORT | {"ai-meme-coins"},
    "B_cohort_no_ai_meme": COHORT,
    "C_agent_only": {"ai-agents", "ai-agent-launchpad", "defai"},
    "D_ai_agents_only": {"ai-agents"},
}


def gini(v):
    v, n = sorted(v), len(v)
    return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(v)) / (n * sum(v))


def stats(rows):
    alive = [r for r in rows if r["t2_market_cap"]]
    dead = sorted((r for r in rows if not r["t2_market_cap"]), key=lambda r: -r["t1_market_cap"])
    t1_all = sum(r["t1_market_cap"] for r in rows)
    t1p = [r["t1_market_cap"] for r in alive]
    t2p = [r["t2_market_cap"] for r in alive]
    top = max(1, len(alive) // 10)
    return {
        "n_t1": len(rows), "n_survived": len(alive), "survival": round(len(alive) / len(rows), 4),
        "t1_cohort_usd": t1_all,
        "t2_cohort_usd": sum(t2p),
        "cohort_value_change": round(sum(t2p) / t1_all - 1, 4),
        "t1_survivors_usd": sum(t1p), "t2_survivors_usd": sum(t2p),
        "survivor_value_change": round(sum(t2p) / sum(t1p) - 1, 4),
        "value_lost_to_exits": t1_all - sum(t1p),
        "exit_value_share": round((t1_all - sum(t1p)) / t1_all, 4),
        "gini_t1_survivors": round(gini(t1p), 4), "gini_t2": round(gini(t2p), 4),
        "gini_t1_full_cohort": round(gini([r["t1_market_cap"] for r in rows]), 4),
        "top_decile_t1": round(sum(sorted(t1p, reverse=True)[:top]) / sum(t1p), 4),
        "top_decile_t2": round(sum(sorted(t2p, reverse=True)[:top]) / sum(t2p), 4),
        "largest_exits": [{"id": r["cg_id"], "t1": r["t1_market_cap"]} for r in dead[:15]],
    }


def main():
    rows = json.loads((ROOT / "data/raw/wayback/t1_cohort_followup.json").read_text())
    taxonomy = set(json.loads((ROOT / "data/processed/t2_taxonomy.json").read_text()))
    primary = [r for r in rows if set(r["categories"]) & COHORT]
    out = {
        "t1_date": "2025-04-06", "t2_date": "2026-09-01",
        "cohort_categories": sorted(COHORT),
        "design": "membership fixed at T1 from web archives; T2 value read per coin by date",
        **stats(primary),
        "in_t2_taxonomy": len({r["cg_id"] for r in primary if r["t2_market_cap"]} & taxonomy),
        "sensitivity": {k: {kk: vv for kk, vv in stats([r for r in rows if set(r["categories"]) & cats]).items()
                            if kk != "largest_exits"} for k, cats in FRAMES.items()},
        "members": sorted(({"id": r["cg_id"], "slug": r["slug"], "symbol": r["symbol"],
                            "categories": r["categories"], "t1": r["t1_market_cap"],
                            "t2": r["t2_market_cap"]} for r in primary), key=lambda r: -r["t1"]),
    }
    (ROOT / "data/processed/t1_t2_cohort.json").write_text(json.dumps(out, indent=2))
    print(f"cohort n={out['n_t1']}  survived {out['n_survived']} ({out['survival']:.1%})")
    print(f"cohort value ${out['t1_cohort_usd']:,.0f} -> ${out['t2_cohort_usd']:,.0f} ({out['cohort_value_change']:+.1%})")
    print(f"survivors only ${out['t1_survivors_usd']:,.0f} -> ${out['t2_survivors_usd']:,.0f} ({out['survivor_value_change']:+.1%})")
    print(f"Gini among survivors {out['gini_t1_survivors']:.3f} -> {out['gini_t2']:.3f}  (full cohort at T1 {out['gini_t1_full_cohort']:.3f})   top decile {out['top_decile_t1']:.1%} -> {out['top_decile_t2']:.1%}")
    print(f"exits {out['n_t1']-out['n_survived']} worth ${out['value_lost_to_exits']:,.0f} ({out['exit_value_share']:.1%} of T1)")
    print(f"in T2 taxonomy: {out['in_t2_taxonomy']}")
    print("\nsensitivity:")
    print(f"  {'frame':22}{'n':>5}{'surv':>6}{'surv%':>8}{'cohortΔ':>10}{'GiniT1':>8}{'GiniT2':>8}")
    for k, v in out["sensitivity"].items():
        print(f"  {k:22}{v['n_t1']:5}{v['n_survived']:6}{v['survival']:8.1%}{v['cohort_value_change']:10.1%}"
              f"{v['gini_t1_survivors']:8.3f}{v['gini_t2']:8.3f}")


if __name__ == "__main__":
    main()
