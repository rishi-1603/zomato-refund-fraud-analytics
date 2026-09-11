-- Query 1: Overall Refund Summary
-- Business Question: What is the overall refund situation?

SELECT 
    COUNT(*) AS total_orders,
    SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
    ROUND(
        SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
    ) AS refund_rate_percent,
    ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount
FROM public.orders;

-- Query 2: Top Fraud Suspects by Refund Rate
-- Business Question: Which customers have suspiciously high refund rates?

SELECT 
    "Customer_ID",
    COUNT(*) AS total_orders,
    SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
    ROUND(
        SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
    ) AS refund_rate_percent,
    ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount
FROM public.orders
GROUP BY "Customer_ID"
HAVING COUNT(*) >= 5
AND SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 30
ORDER BY refund_rate_percent DESC, total_refund_amount DESC
LIMIT 20;

-- Query 3: Repeated Refund Reasons (Fraud Signal #2)
-- Business Question: Which customers always use the same refund reason?

SELECT 
    "Customer_ID",
    "Refund_Reason",
    COUNT(*) AS reason_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY "Customer_ID"), 2
    ) AS reason_percentage
FROM public.orders
WHERE "Refund_Requested" = TRUE
AND "Customer_ID" IN (
    SELECT "Customer_ID"
    FROM public.orders
    GROUP BY "Customer_ID"
    HAVING COUNT(*) >= 5
    AND SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 30
)
GROUP BY "Customer_ID", "Refund_Reason"
ORDER BY "Customer_ID", reason_count DESC
LIMIT 20;

-- Query 4: Refund Impact by City
-- Business Question: Which cities have the highest fraud exposure?

SELECT 
    "City",
    COUNT(*) AS total_orders,
    SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
    ROUND(
        SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
    ) AS refund_rate_percent,
    ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount,
    ROUND(AVG("Refund_Amount")::numeric, 2) AS avg_refund_amount
FROM public.orders
GROUP BY "City"
ORDER BY total_refund_amount DESC;

-- Query 5: Executive Fraud Summary
-- Business Question: What is the total business impact of high-risk accounts?

WITH high_risk_customers AS (
    SELECT 
        "Customer_ID",
        COUNT(*) AS total_orders,
        SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) AS total_refunds,
        ROUND(
            SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
        ) AS refund_rate_percent,
        ROUND(SUM("Refund_Amount")::numeric, 2) AS total_refund_amount
    FROM public.orders
    GROUP BY "Customer_ID"
    HAVING COUNT(*) >= 5
    AND SUM(CASE WHEN "Refund_Requested" = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 30
)
SELECT
    COUNT(*) AS flagged_accounts,
    ROUND(SUM(total_refund_amount)::numeric, 2) AS refund_exposure_held_by_flagged,
    ROUND(AVG(refund_rate_percent)::numeric, 2) AS avg_refund_rate_of_flagged
FROM high_risk_customers;
-- Note: no recovery/recovery-rate is computed anywhere. Recovery assumptions
-- are not supported by this data (see reports/pareto_analysis.md).

-- Query 9: Refund Exposure Concentration (Pareto)
-- Business Question: How concentrated is refund value among customers?
-- (Mirrors scripts/pareto_analysis.py; reconciliation in Phase 5.)

WITH customer_refunds AS (
    SELECT
        "Customer_ID",
        SUM("Refund_Amount") AS refund_value
    FROM public.orders
    WHERE "Refund_Requested" = TRUE
    GROUP BY "Customer_ID"
),
ranked AS (
    SELECT
        "Customer_ID",
        refund_value,
        ROW_NUMBER() OVER (ORDER BY refund_value DESC, "Customer_ID") AS value_rank,
        SUM(refund_value) OVER (ORDER BY refund_value DESC, "Customer_ID") AS cum_value,
        SUM(refund_value) OVER () AS total_value,
        (SELECT COUNT(DISTINCT "Customer_ID") FROM public.orders) AS all_customers
    FROM customer_refunds
)
SELECT
    ROUND(100.0 * MAX(CASE WHEN value_rank <= CEIL(all_customers * 0.01)  THEN cum_value END) / MAX(total_value), 1) AS top_1pct_share,
    ROUND(100.0 * MAX(CASE WHEN value_rank <= CEIL(all_customers * 0.05)  THEN cum_value END) / MAX(total_value), 1) AS top_5pct_share,
    ROUND(100.0 * MAX(CASE WHEN value_rank <= CEIL(all_customers * 0.10)  THEN cum_value END) / MAX(total_value), 1) AS top_10pct_share,
    ROUND(100.0 * MAX(CASE WHEN value_rank <= CEIL(all_customers * 0.20)  THEN cum_value END) / MAX(total_value), 1) AS top_20pct_share,
    MIN(CASE WHEN cum_value >= 0.5 * total_value THEN value_rank END) AS customers_to_cover_50pct,
    MIN(CASE WHEN cum_value >= 0.8 * total_value THEN value_rank END) AS customers_to_cover_80pct
FROM ranked;
-- Interpretation: a small customer share holds a disproportionate share of
-- refund VALUE. Concentration is a prioritization signal — never evidence
-- that any individual customer is fraudulent (see reports/pareto_analysis.md).
