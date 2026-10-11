# Screening criteria for the T2 population

Every rule is mechanically checkable from files in `data/raw/`, and every rule
carries the measurement error it exists to prevent. Counts are as of T2 = 2026-09-01.

## Frame

The population is every token listed in any of seven CoinGecko AI categories
(`ai-agents`, `ai-agent-launchpad`, `ai-applications`, `ai-framework`,
`ai-meme-coins`, `defai`, `artificial-intelligence`), with market capitalization
read at the cutoff date rather than at the collection date. **1,837 tokens.**

## The rule that governs the other rules

**No screening rule may reference market capitalization rank or value share.**
The study measures dilution and concentration, so any value-based cut is
endogenous to its own finding: as concentration rises, a fixed value-share
threshold admits fewer tokens, and a Gini computed inside that threshold is
partly a restatement of the threshold. The single value-adjacent split below
(S1) turns on whether a token trades at all, which is a fact about listing
rather than about size.

The `>$100k` cut used in the earlier collection is therefore retained only as a
recorded label (`in_scope` in `cg_details.json`), never as a filter.

## Rules

| | rule | removed | value | prevents |
|---|---|---|---|---|
| **S1** | Trades at the cutoff — a market capitalization exists on 2026-09-01 | 545 not capitalized | — | counting a listing as a live project |
| **S2a** | Not a claim on another token in the population (liquid-staking, wrapped, bridged, restaked) | 3 | $1.64B | double-counting one project's capitalization |
| **S2b** | One token per project — where a project lists several tokens, the primary one is kept | 12 (from 13 groups) | $0.23B | double-counting one project |
| **S3** | A self-description exists, from CoinGecko, the project site, its whitepaper or its repository | 82 | $230M | classifying a project from its ticker |
| **S4** | The description carries AI or agent content | measured after S3 | — | admitting tokens that are only category-tagged as AI |
| **S5** | Excluded: listings whose only frame category is `ai-meme-coins` | 216 | $497M | a meme listing counting as a project with a product |

After the mechanical rules S1, S2a, S2b and S5: **1,061 tokens, $16.26B**.
After S3: **979 tokens, $16.03B**. The 82 removed for having no description
anywhere are worth $230M, 1.4% of the screened value, and are listed in
`t2_population.json` under `unclassifiable_no_description` rather than
discarded.

### S5 removes meme-only listings, not every token CoinGecko calls a meme

The rule turns on the frame category a listing enters the population under, not
on CoinGecko's coin-level `Meme` / `AI Meme` label. Screening on that label
instead would remove 285 rather than 216 tokens, and the extra 69 include
ai16z, aixbt, GRIFFAIN and pippin -- the ecosystem's most-cited agent projects,
several of them T1 cohort members. A token that qualifies for the population on
any non-meme category stays in.

This also aligns the two timepoints: the T1 cohort's frame B already excluded
`ai-meme-coins`, so after S5 both ends of the study window rest on the same
category logic.

### S2 detection, and why it is hand-checked

Candidates are flagged by CoinGecko instrument labels (`Liquid Staking Tokens`,
`Wrapped-Tokens`, `Crypto-Backed Tokens`, `Liquid Staking`) and by a
word-boundary match on *staked / wrapped / bridged / restaked / synthetic* in the
name; S2b groups tokens that share a homepage. CoinGecko's `Derivatives` label
is deliberately **not** used: it marks a project's sector, so it tags Derive,
Arkham and AWE Network, which are ordinary projects. Because the labels are
unreliable in both directions the flagged set is small enough to verify by hand
in full — 3 rows for S2a, 13 groups for S2b — and each decision is recorded.

Largest S2a flag: Staked TAO (Root), $1.58B, a staking derivative of Bittensor's
own $2.21B listing. Left in, it would count Bittensor's capitalization twice
and overstate concentration.

### S3 evidence hierarchy

Sources are tried in order and the one used is recorded per row as
`desc_source`, because the sources are not equivalent evidence: a CoinGecko
description is the project-supplied summary hosted by CoinGecko, a project site
is the project's own fuller self-description, a whitepaper is a formal claim.
Reporting the mix lets a reader judge the evidence behind each classification.

Measured on the screened population (`scripts/fetch_descriptions.py`):

| source | rows | evidence it is |
|---|---|---|
| CoinGecko description | 828 | project-supplied summary |
| Project homepage | 135 | self-description |
| GitHub repository | 10 | a developer's one-line summary |
| Whitepaper or docs site | 6 | a formal claim |
| **none** | **82** | removed by S3, recorded in `t2_population.json` |

233 screened projects had no CoinGecko prose; 151 were recovered (64.8%),
carrying 87% of that group's capitalization.
