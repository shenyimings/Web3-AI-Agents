-- Distribution of individual x402 settlement amounts on Base.
-- Dune query 8573851. Free tier, ~0.34 credits.
-- The mean is not a useful summary here: a single $9,997 settlement dominates
-- it while the median payment is roughly one tenth of a cent. Report the
-- median and the sub-cent share instead.

WITH s AS (
  SELECT CAST(amount AS double) / 1e6 AS usd, payer, payTo
  FROM x402x_base.settlementrouter_evt_settled
  WHERE evt_block_date < DATE '2026-09-01'
)
SELECT
  count(*)                                        AS settlements,
  count(DISTINCT payer)                           AS payers,
  count(DISTINCT payTo)                           AS payees,
  round(sum(usd), 2)                              AS total_usd,
  round(avg(usd), 6)                              AS mean_usd,
  round(approx_percentile(usd, 0.5), 6)           AS p50,
  round(approx_percentile(usd, 0.9), 6)           AS p90,
  round(approx_percentile(usd, 0.99), 4)          AS p99,
  round(max(usd), 2)                              AS max_usd,
  sum(CASE WHEN usd < 0.01 THEN 1 ELSE 0 END)     AS under_1_cent,
  sum(CASE WHEN usd < 1 THEN 1 ELSE 0 END)        AS under_1_dollar
FROM s;
