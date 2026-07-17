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
    COUNT(*) AS high_risk_accounts,
    ROUND(SUM(total_refund_amount)::numeric, 2) AS fraud_exposure,
    ROUND(SUM(total_refund_amount) * 0.5, 2) AS potential_recovery,
    ROUND(AVG(refund_rate_percent)::numeric, 2) AS avg_fraud_rate
FROM high_risk_customers;