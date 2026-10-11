-- x402 SettlementRouter activity on Base, by month, through the study cutoff.
-- Dune query 8573849. Free tier, ~0.5 credits.
-- One implementation of x402, not the whole protocol: facilitator-settled
-- traffic using direct USDC transferWithAuthorization is not captured here, so
-- these figures are a lower bound on a named contract.

SELECT
  date_trunc('month', evt_block_date) AS month,
  count(*)                            AS settlements,
  count(DISTINCT payer)               AS unique_payers,
  count(DISTINCT payTo)               AS unique_payees,
  count(DISTINCT token)               AS tokens,
  sum(CAST(amount AS double) / 1e6)   AS volume_6dp
FROM x402x_base.settlementrouter_evt_settled
WHERE evt_block_date < DATE '2026-09-01'
GROUP BY 1
ORDER BY 1;
