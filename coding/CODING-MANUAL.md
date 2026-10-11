# Coding manual — T2 taxonomic categorization

The T2 population (the screened tokens; 979 at the 2026-09-01 cutoff) is classified into the **same** four primary
categories and ten subcategories that the T1 card sort produced. The taxonomy is
not re-derived, so the two timepoints remain comparable. What follows is that
taxonomy restated as decision rules, so that a rater can apply it without having
taken part in the original card-sorting sessions.

Evidence for each decision, in priority order:

1. the project's own description (CoinGecko `description.en`, which is the
   project-supplied blurb),
2. its CoinGecko category labels,
3. its homepage domain, where the name alone is uninformative.

A project may carry **more than one** subcategory, as in T1, where 27 of 133 did.
Multi-assignment requires the description to make two functions explicit; a
project that merely *could* be used two ways gets one label.

## Primary categories and subcategories

### AI Agent Incubation
Platforms for creating, deploying and monetizing agents. The test is whether the
product's user is *someone building an agent*.

- **`builder` — Builder & Marketplace.** Frameworks, SDKs, no-code agent
  builders, agent app stores, agent hosting. CG signal: `AI Framework`.
  *Not* a general LLM API with a token bolted on.
- **`launchpad` — Monetization & Launchpad.** Token-launch rails for agents,
  bonding curves, agent IPOs, revenue sharing to agent creators. CG signal:
  `AI Agent Launchpad`, `Virtuals Protocol Ecosystem`, `Pump.fun Ecosystem`
  *when the description is about launching agents rather than memecoins*.

### Infrastructure
Foundational technology that agents run on. The test is whether removing the
project would stop agents from running, not from being built.

- **`infrastructure` — Agent Protocol & DePIN.** L1/L2s positioning as agent
  chains, compute and inference networks, storage, bandwidth, data availability,
  agent messaging protocols. CG signal: `DePIN`, `Infrastructure`,
  `Layer 1 (L1)`, `Smart Contract Platform`.
- **`trust` — Trust Layer.** Verification, attestation, TEE, ZK proof of
  inference, oracles, reputation and identity registries, knowledge graphs used
  for provenance. CG signal: `Oracle`, `Zero Knowledge (ZK)`.
- **`copilot` — AI-powered Development.** Tooling that helps *humans* write
  Web3 code or interact with chains: contract generators, auditing copilots,
  chat interfaces to a chain. Distinguished from `builder` by the artifact
  produced — code and transactions, not an agent.

### Financial Services
Agents applied to capital. The test is whether the product moves or evaluates
money.

- **`defai` — DeFAI Agents.** Autonomous trading, portfolio management, yield
  routing, intent-based execution, agent wallets that transact. CG signal:
  `DeFAI`, `Decentralized Finance (DeFi)`.
- **`analytics` — Investment Analytics.** Market intelligence, signal and alpha
  feeds, risk scoring, on-chain research assistants, prediction markets. The
  product is *information*; if it also executes, it is also `defai`.
  CG signal: `Analytics`.

### Creative & Virtual
Agents as characters, creators or asset managers.

- **`game` — Game & Metaverse.** Agent NPCs, autonomous game worlds, agent
  competitions, virtual companions and digital twins. CG signal:
  `Gaming (GameFi)`, `Metaverse`.
- **`content-creation` — Content Creation.** Agents that produce media — text,
  image, music, video — and agent personalities whose output is social content.
  Memecoins with an agent persona and no other product belong here, not in
  `builder`. CG signal: `NFT`, `Meme`, `AI Meme`.
- **`rwa` — AI-powered RWA.** Agents managing physical or off-chain assets:
  property, supply chain, logistics, commodities. CG signal:
  `Real World Assets (RWA)`.

### Refinement of `infrastructure` (T2 only, strictly nested)

In the T2 classified set, Agent Protocol & DePIN (`infrastructure`) holds 226 of
the 855 classified projects and 73.6% of their capitalization. Because a single
subcategory carries most of the ecosystem's value, T2 records a second, finer
field on these projects.

**This is a refinement, not an extension.** The four facets partition
`infrastructure` exactly: every `infrastructure` project takes one and only one,
and their union is the subcategory unchanged. The subcategory label is what all
cross-timepoint comparisons use, so T1 and T2 remain exactly comparable; the
facet is reported only for T2. No other subcategory
is faceted.

- **`chain` — Agent-native chain.** L1s and L2s positioning themselves as the
  settlement or execution layer for agents. The test is that the project ships a
  chain. *NEAR, Internet Computer, Qubic, ZIGChain, Sahara AI.*
- **`compute` — Compute, bandwidth and delivery.** Rented physical capacity:
  GPU and CPU marketplaces, decentralized cloud, inference-serving capacity,
  CDN, streaming and bandwidth. The test is that the product is metered hardware
  time or throughput. *Render, Akash, Golem, Aethir, io.net, Theta, Livepeer,
  AIOZ.*
- **`model` — Training and inference network.** Networks whose output is a
  model or a model's answer, and which coordinate and reward the participants
  producing it. Distinguished from `compute` by what is sold: an answer or a set
  of weights, not machine time. *Bittensor and its subnets, Targon, Sentient,
  Score.*
- **`data` — Data, storage and indexing.** Persistent storage, indexing,
  crawling, data availability and data marketplaces --- the resource layer the
  agent stack reads from. *Arweave, The Graph, SQD, Ocean Protocol, Grass.*

Three boundary rules:

- A project that sells GPU hours *and* runs a model marketplace on top is
  `model`; the facet follows the layer the token is actually sold for.
- A chain whose pitch is an agent chain is `chain` even when it also sells
  compute; shipping consensus dominates.
- A Bittensor subnet takes the facet of **what the subnet does**, not
  Bittensor's own. Most are `model`; a subnet renting GPUs is `compute`.

Facets are recorded in a separate `facet` field, never inside `labels`, so that
dropping the field reproduces the T1-comparable coding exactly.

### No eleventh subcategory

T2 contains a small number of agents in domains T1 had no instance of, such as
science, law, medicine, recruitment and mental health. They are too few to carry
a subcategory of their own, so the ten inherited subcategories stand unchanged
and these projects are coded into them on the same tests as everything else:
conversational health and companionship agents are virtual companions (`game`),
credential and dispute verification is `trust`, medical data platforms are a
resource layer (`infrastructure`), and a research assistant is coded `copilot`.

## Residual outcomes

Screening removes meme-only listings and listings with no description before the
population reaches the coder (`SCREENING-CRITERIA.md`, rules S3 and S5). There is
no market-capitalization floor: the \$100k cut used in the earlier collection
survives only as the `in_scope` flag in `cg_details.json` and is never evidence
for a coding decision. Two residual outcomes remain:

- **`out-of-scope`** — the description carries neither AI nor agent content
  (rule S4). The bar follows T1's inclusion test, *substantive Web3 and AI
  integration*, rather than the presence of the word "agent": T1 admitted
  projects with no agent of their own, such as DePIN and compute networks under
  Infrastructure, auditing and development tooling under AI-powered Development,
  and marketplaces under Content Creation. A token that serves the agent stack
  is in scope even when no agent appears in its own description.
- **`unclassifiable`** — a description exists but supports no functional
  reading: it is pure price marketing or a bare exchange listing note. Counted
  and reported, never guessed at.

Both residuals are reported explicitly rather than folded into a category, and
are excluded from all per-project results.

## Two consistency rules

- **T1 precedence.** Where a project was coded in T1, the T1 label is retained
  even when the T2 blurb reads otherwise --- Alchemist AI reads as `copilot` but
  T1 coded it Builder & Marketplace; Delysium reads as a virtual world but T1
  coded it Agent Protocol. Inheriting a taxonomy means inheriting its case law:
  re-coding the same project at the second timepoint would make its apparent
  category change an artifact of the coder rather than of the project.
- **Consistency pairs.** Where two projects are the same shape, they take the
  same label, and the justification names the sibling. Crowdsourced AI
  training-data marketplaces (Tagger, PublicAI, Reppo) are all `infrastructure`,
  on the same reading that puts DePIN there --- they supply a resource the agent
  stack consumes; AI-driven trading applications (Rift AI, Polymtrade) are both
  `analytics`, since the product they ship is signals. For AI health projects,
  what decides is what the project ships: a data or model resource others
  consume is `infrastructure` --- Galeon, whose hospital data feeds "Blockchain
  Swarm Learning" for decentralized model training, is coded
  `infrastructure`/`data` --- while a clinical service business whose AI is
  internal is `out-of-scope` (ZayaAI, whose business units comprise a medical
  clinic and a pathology lab).

## Rater workflow

Coding proceeds in two layers, and each row records which one produced it.

- **Rule layer (`scripts/classify_t2.py`).** Where a CoinGecko category label
  names a function rather than a theme and maps to exactly one subcategory, the
  assignment is made from that label. Provenance `rule`.
- **Reading layer.** Every remaining project is read individually and coded
  against this manual. Provenance `read`.

Two researchers code independently (Cohen's $\kappa = 0.87$) and a third
adjudicates disagreements. Every assignment records its label, its provenance
(`rule` or `read`) and a one-line justification quoting the evidence.
