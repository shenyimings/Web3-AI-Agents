# Web3-AI Agent Artifact

**Yiming Shen<sup>1</sup>**, **Jiashuo Zhang<sup>2</sup>**, **Zhenzhe Shao<sup>1</sup>**, **Wenxuan Luo<sup>3</sup>**, **Yanlin Wang<sup>1</sup>**, **Ting Chen<sup>3</sup>**, **Lingfeng Bao<sup>4,5</sup>**, **Jiachi Chen<sup>4,5</sup>**

<sup>1</sup> School of Software Engineering, Sun Yat-sen University, Zhuhai, Guangdong, China  
<sup>2</sup> College of Computer Science and Technology, Zhejiang University, Hangzhou, Zhejiang, China  
<sup>3</sup> School of Computer Science and Engineering (School of Cyber Security), University of Electronic Science and Technology of China, Chengdu, Sichuan, China  
<sup>4</sup> The State Key Laboratory of Blockchain and Data Security, Zhejiang University, Hangzhou, Zhejiang, China  
<sup>5</sup> Hangzhou High-Tech Zone (Binjiang) Institute of Blockchain and Data Security, Hangzhou, Zhejiang, China  

This is the code and data artifact for the paper "Web3 × AI Agents: Landscape, Integrations, and Foundational Challenges". This repository is made available under the Public Domain Dedication and License v1.0 whose full text can be found at: http://opendatacommons.org/licenses/pddl/1.0/ - see the [LICENSE](./LICENSE) file for details.

## Study Design

This research uses a longitudinal two-timepoint study design to track the Web3-AI Agent ecosystem.

**Timepoint 1 (T1, 6 April 2025):** Membership is reconstructed from Internet Archive Wayback Machine captures of CoinGecko's AI category pages near T1 (`artificial-intelligence`, `ai-agents`, `ai-agent-launchpad`, `defai`), screened with the same rules as T2, with capitalization read from CoinGecko at both T1 and T2. This gives 275 members, followed to T2. Date-restricted Google search (keywords joined with OR, bounded with `after:`/`before:`) adds 133 projects, 77 of them capitalized, which are traced to T2 through the full CoinGecko coin list with renames and contract-address fallback.

**Timepoint 2 (T2, 1 September 2026):** 1,837 CoinGecko listings under seven AI categories are screened (rules S1 to S5) to 979 tokens, of which 855 are classified into 4 primary categories and 10 subcategories. GitHub repositories matching the keyword set and created between the two cutoffs (6 April 2025 to 1 September 2026) form the repository discovery pool. All data collection cutoffs are set to 1 September 2026.

**On-chain measurement:** ERC-8004 Identity and Reputation registries across sixteen chains, and x402 settlements on Base (one contract, SettlementRouter, all USDC settlements). Data are taken from Dune query results; each file in `queries/` names its Dune query id.

## Repository Layout

The artifact is organized as follows:

```
scripts/              # Data pipeline: collection, screening, coding, and paper output
data/
  raw/                # Collected inputs from CoinGecko, GitHub, and Internet Archive
  processed/          # Analysis inputs: screened populations, taxonomy, cohorts, 
                      # on-chain data, and macros (every number in the paper)
coding/               # Screening rules, coding manual, hand decisions
queries/              # Dune SQL queries (each file names its Dune query id)
old/                  # The first artifact release (T1 project list, web3-projects.xlsx)
```

Key processed files:
- `t2_population.json`: 979 screened T2 tokens
- `t2_taxonomy.json`: Coding of all 979 tokens with labels, facet, confidence, and evidence
- `t1_cohort.json`, `t1_t2_cohort.json`: T1 membership followed to T2
- `macros.json`: Every number appearing in the paper, computed from this data

## Quick Start: Reproduce Paper Numbers

To regenerate the paper's reported figures from included data:

```bash
uv run python scripts/macros.py       # Write ../paper/numbers.tex
uv run python scripts/tables.py       # Write ../paper/tables/taxonomy.tex
uv run python scripts/figures.py      # Write ../paper/figures/*.pdf
uv run python scripts/check_numbers.py  # Verify consistency
```

This step requires no API keys or external data; all inputs are included. `stats.py` computes every number and is imported by the other four scripts. Outputs are written into a sibling `paper/` directory, so create `../paper/tables` and `../paper/figures` first when running the artifact on its own.

## Full Pipeline

The complete data collection and analysis pipeline is run from the repository root with environment variables set for API access:

```bash
set -a && . ./.env && set +a
uv run python scripts/<name>.py
```

Required environment variables (see `.env.example`; T2 tokens must be collected before GitHub joins and T1 follow-up): `COINGECKO_API_KEY` (paid tier for historical values) and `GITHUB_TOKEN`.

**Pipeline stages:**

1. **T2 token collection:** `cg_collect.py`, `cg_descriptions.py`, `cg_links.py`, `fetch_descriptions.py`, `cg_history.py`, `cg_series.py`, `cg_repos.py`. All collectors are resumable.

2. **GitHub discovery:** `gh_discover.py` (imports from `gh_probe.py` and `gh_newkeywords.py`), `gh_resolve.py`, `standards_census.py`

3. **T1 cohort reconstruction:** `t1_union_cohort.py` (parses the Wayback captures into `data/raw/wayback/t1_union_raw.json`), `t1_cohort_followup.py`, `panel_resolve.py`, `panel_attrition.py`. The T1 cohort used in the paper is `t1_t2_cohort.json` (with `t1_cohort.json`); the `t1_union_cohort.json` that `t1_union_cohort.py` also writes is an earlier construction and is not used in the paper.

4. **Screening and coding:** `build_cohorts.py`, `classify_t2.py` (applies rules then merges `coding/decisions-*.json`), `t1_t2_cohort_analysis.py`

5. **Data joins:** `crossmatch.py`, `rq3_governance.py`

6. **Paper outputs:** See Quick Start section above.

## Notes

**T1 cohort matching:** Match T1 projects against CoinGecko's full coin list, not the AI category listing alone. Projects that left the AI category may still be trading.

**GitHub repository window:** Discovery is restricted to repositories created between the two cutoffs (6 April 2025 to 1 September 2026), but the repositories that CoinGecko tokens link to are measured without that restriction, so the code of established projects is measured in full.

**x402 scope:** All x402 figures cover the Base settlement record only (SettlementRouter contract, USDC settlements).

## Citation

```bibtex
@article{shen2026web3ai,
  title={Web3 × AI Agents: Landscape, Integrations, and Foundational Challenges},
  author={Shen, Yiming and Zhang, Jiashuo and Shao, Zhenzhe and Luo, Wenxuan and Wang, Yanlin and Chen, Ting and Bao, Lingfeng and Chen, Jiachi},
  journal={arXiv preprint arXiv:2508.02773},
  year={2025}
}
```

## Contact

For questions about this artifact, please contact: [shenym7@mail2.sysu.edu.cn](mailto:shenym7@mail2.sysu.edu.cn)
