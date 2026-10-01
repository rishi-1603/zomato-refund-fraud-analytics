-- Query: Refund exposure concentration (Pareto) with cumulative share
-- Business Question: How concentrated is refund exposure, and where should the
--                     investigation cut-off sit given limited review capacity?
-- Technique: window functions — ROW_NUMBER + cumulative SUM OVER ordered total.
-- Verified pattern (Python/reports): top 1% of customers ≈ 26.9% of refund
-- value; top 5% ≈ 60.6%; top 10% ≈ 75.6%; top 20% ≈ 95.1%.
-- Decision: set the review cut-off where cumulative share crosses the team's
-- capacity line; customers below the line enter the watchlist, not review.

WITH customer_refunds AS (
    SELECT "Customer_ID",
           COUNT(*) AS total_orders,
           SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
           ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount
    FROM public.orders
    GROUP BY "Customer_ID"
    HAVING SUM("Refund_Amount") > 0
),
ranked AS (
    SELECT "Customer_ID",
           total_refund_amount,
           ROW_NUMBER() OVER (ORDER BY total_refund_amount DESC) AS refund_rank,
           SUM(total_refund_amount) OVER (ORDER BY total_refund_amount DESC) AS cumulative_value,
           SUM(total_refund_amount) OVER () AS grand_total,
           COUNT(*) OVER () AS customers_with_refunds
    FROM customer_refunds
)
SELECT refund_rank,
       "Customer_ID",
       total_refund_amount,
       ROUND(cumulative_value * 100.0 / grand_total, 2) AS cumulative_share_pct,
       ROUND(refund_rank * 100.0 / customers_with_refunds, 2) AS customer_percentile_pct
FROM ranked
ORDER BY refund_rank
LIMIT 100;

-- Companion: the concentration headline in one row
-- Business Question: what share of refund value do the top 5% of customers hold?
WITH customer_refunds AS (
    SELECT "Customer_ID", SUM("Refund_Amount") AS total_refund_amount
    FROM public.orders
    GROUP BY "Customer_ID"
    HAVING SUM("Refund_Amount") > 0
),
ranked AS (
    SELECT total_refund_amount,
           SUM(total_refund_amount) OVER (ORDER BY total_refund_amount DESC) AS cumulative_value,
           SUM(total_refund_amount) OVER () AS grand_total,
           COUNT(*) OVER () AS n_customers
    FROM customer_refunds
)
SELECT ROUND(MAX(CASE WHEN refund_rank <= CEIL(n_customers * 0.05)
                      THEN cumulative_value * 100.0 / grand_total END), 1) AS top_5pct_share_pct
FROM (
    SELECT total_refund_amount, cumulative_value, grand_total, n_customers,
           ROW_NUMBER() OVER (ORDER BY total_refund_amount DESC) AS refund_rank
    FROM ranked
) x;
