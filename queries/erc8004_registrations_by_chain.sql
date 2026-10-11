-- ERC-8004 IdentityRegistry.register census across every chain Dune decodes,
-- through the study cutoff. Dune query 8617117. Free tier, ~1.7 credits.
--
-- per_registrant separates two different inflation patterns: values near 1
-- (bnb, monad) mean many addresses each registering one agent — airdrop
-- farming; high values (celo 41, avalanche 35) mean few addresses registering
-- many agents each. Reporting only the total conflates them.
--
-- Ethereum mainnet is decoded under its own namespace (ethereum_ethereum)
-- rather than inside agent_erc8004_multichain, so it must be unioned in
-- explicitly. It is the same contract: the registry is deployed at
-- 0x8004a169fb4a3325136eb29fa0ceb6d2e539a432 on all sixteen chains.

SELECT
  chain,
  count(*)                                   AS registrations,
  count(DISTINCT call_tx_from)               AS distinct_registrants,
  round(count(*) * 1.0
        / nullif(count(DISTINCT call_tx_from), 0), 1) AS per_registrant,
  min(call_block_date)                       AS first_seen,
  max(call_block_date)                       AS last_seen
FROM agent_erc8004_multichain.identityregistry_call_register
WHERE call_success
  AND call_block_date < DATE '2026-09-01'
GROUP BY chain

UNION ALL

SELECT
  'ethereum',
  count(*),
  count(DISTINCT call_tx_from),
  round(count(*) * 1.0
        / nullif(count(DISTINCT call_tx_from), 0), 1),
  min(call_block_date),
  max(call_block_date)
FROM ethereum_ethereum.identityregistry_call_register
WHERE call_success
  AND call_block_date < DATE '2026-09-01'

ORDER BY registrations DESC;
