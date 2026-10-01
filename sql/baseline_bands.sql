-- Query: Volume-band baselines — is a flagged customer's refund rate abnormal
--         for their order volume?
-- Business Question: Which of the 279 flagged customers are probably false
--                     positives (refund rate NORMAL for their volume band)?
-- Technique: CASE banding + PERCENTILE_CONT (P95) per band + eligibility join.
-- Verified (Python/reports): 113 of 279 flagged (40.5%) sit below their band
-- P95 — likely false positives; de-prioritise or move to watchlist.
-- Decision: review above-baseline flags first; below-baseline flags get a
-- lighter-touch check, not a full investigation.

WITH customer_stats AS (
    SELECT "Customer_ID",
           COUNT(*) AS total_orders,
           SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
           ROUND(SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0
                 / COUNT(*), 2) AS refund_rate_pct,
           ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount
    FROM public.orders
    GROUP BY "Customer_ID"
),
banded AS (
    SELECT cs.*,
           CASE WHEN cs.total_orders BETWEEN 1 AND 2  THEN '1-2 orders'
                WHEN cs.total_orders BETWEEN 3 AND 5  THEN '3-5 orders'
                WHEN cs.total_orders BETWEEN 6 AND 10 THEN '6-10 orders'
                WHEN cs.total_orders BETWEEN 11 AND 20 THEN '11-20 orders'
                ELSE '21+ orders'
           END AS volume_band
    FROM customer_stats cs
),
baselines AS (
    SELECT volume_band,
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY refund_rate_pct) AS band_p95_refund_rate,
           COUNT(*) AS customers_in_band
    FROM banded
    GROUP BY volume_band
),
flagged AS (  -- eligibility funnel: docs/risk_scoring_methodology.md
    SELECT b.*
    FROM banded b
    WHERE b.total_orders >= 5
      AND b.refund_rate_pct > 30
)
SELECT f."Customer_ID",
       f.total_orders,
       f.refund_rate_pct,
       f.total_refund_amount,
       f.volume_band,
       bas.band_p95_refund_rate,
       bas.customers_in_band,
       CASE WHEN f.refund_rate_pct > bas.band_p95_refund_rate
            THEN 'above baseline — investigate first'
            ELSE 'below baseline — likely false positive, watchlist'
       END AS baseline_status
FROM flagged f
JOIN baselines bas ON f.volume_band = bas.volume_band
ORDER BY f.total_refund_amount DESC;

-- Band reference table (for the dashboard's baseline context panel)
-- Business Question: what does 'normal' refund behaviour look like at each volume?
SELECT volume_band,
       COUNT(*) AS customers,
       ROUND(AVG(refund_rate_pct), 2) AS mean_refund_rate_pct,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY refund_rate_pct) AS p95_refund_rate_pct
FROM banded
GROUP BY volume_band
ORDER BY MIN(total_orders);
