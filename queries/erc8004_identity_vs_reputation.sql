-- ERC-8004 identity registrations vs reputation feedback, per chain, through
-- the study cutoff. Dune query 8617120. Free tier, ~2.0 credits.
--
-- Reputation is NOT under-adopted: feedback volume (207,331) is comparable to
-- registration volume (252,103) and exceeds it threefold on Base. The finding
-- is in distinct_senders — those entries come from ~9% as many addresses,
-- with 93 addresses behind BNB's 29,469 and exactly one address behind all of
-- Gnosis. Report the sender concentration, not the call counts alone.
--
-- Ethereum mainnet is decoded under ethereum_ethereum, not inside
-- agent_erc8004_multichain, and is unioned in explicitly on both legs.

SELECT 'identity: register' AS action, chain,
       count(*) AS calls, count(DISTINCT call_tx_from) AS distinct_senders
FROM agent_erc8004_multichain.identityregistry_call_register
WHERE call_success AND call_block_date < DATE '2026-09-01'
GROUP BY chain
UNION ALL
SELECT 'identity: register', 'ethereum',
       count(*), count(DISTINCT call_tx_from)
FROM ethereum_ethereum.identityregistry_call_register
WHERE call_success AND call_block_date < DATE '2026-09-01'
UNION ALL
SELECT 'reputation: giveFeedback', chain,
       count(*), count(DISTINCT call_tx_from)
FROM agent_erc8004_multichain.reputationregistry_call_givefeedback
WHERE call_success AND call_block_date < DATE '2026-09-01'
GROUP BY chain
UNION ALL
SELECT 'reputation: giveFeedback', 'ethereum',
       count(*), count(DISTINCT call_tx_from)
FROM ethereum_ethereum.reputationregistry_call_givefeedback
WHERE call_success AND call_block_date < DATE '2026-09-01'
ORDER BY action, calls DESC;
