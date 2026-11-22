# DATA & KPI VALIDATION

Source: `data/processed/zomato_with_refunds.csv` (45,584 rows), `reports/fraud_suspects.csv` (279 rows)
Recalculated independently with pandas; every figure below verified against source.

## Dataset profile

| Item | Value |
|---|---|
| Delivery orders | 45,584 |
| Unique customers | 9,895 |
| Refund requests | 3,596 |
| Refund request rate | 7.89% |
| Total refund amount | ₹9,74,343.55 |
| Avg refund amount | ₹270.95 |
| Max refund | ₹799.77 |
| Date range | 11 Feb 2022 – 06 Apr 2022 |
| Active days | 44 |
| Customers with ≥1 refund | 2,515 |

## Flagged population (eligibility: ≥5 orders AND refund rate >30%)

| Item | Value |
|---|---|
| Flagged accounts | 279 |
| Flagged refund exposure | ₹3,77,891.92 |
| Flagged exposure share of refunds | 38.78% |
| High tier (>70) | 8 |
| Medium tier (41–70) | 107 |
| Low tier (≤40) | 164 |
| Above peer P95 | 166 |
| At/below peer P95 | 113 |
| 166 + 113 | 279 ✓ |

## Volume-band refund rates (order-level denominator; bands from full unfiltered history)

| Band | Customers | Orders | Refunds | Rate |
|---|---|---|---|---|
| 1–2 orders | 1,514 | 2,549 | 200 | 7.85% |
| 3–5 orders | 5,331 | 21,308 | 1,680 | 7.88% |
| 6–10 orders | 2,978 | 20,889 | 1,663 | 7.96% |
| 11–20 orders | 72 | 838 | 53 | 6.32% |

No band shows 100% — rates are 6.3%–8.0%. Prior "100%" chart issue was fixed (denominator is all orders, never refunded-only).

## Refund reasons

| Reason | Count | % of requests |
|---|---|---|
| Wrong Item | 862 | 24.0% |
| Item Not Received | 594 | 16.5% |
| Missing Item | 550 | 15.3% |
| Late Delivery | 550 | 15.3% |
| Damaged Packaging | 535 | 14.9% |
| Poor Quality | 505 | 14.0% |

Count (862) and percentage (24.0%) are consistent — no discrepancy.

## Concentration

| Metric | Value | Note |
|---|---|---|
| Flagged exposure share | 38.78% | Share of refund value held by 279 flagged accounts |
| Top-10% customer share | 75.6% | Top 990 of 9,895 customers — distinct metric from flagged share |

## Data quality checks (computed, not assumed)

| Check | Status | Detail |
|---|---|---|
| Missing values in required columns | PASS | 0 nulls across ID, Customer_ID, Order_Date, Refund_Requested, Refund_Amount, City, Refund_Reason |
| Duplicate order IDs | PASS | 0 duplicates |
| Date range validity | PASS | 11 Feb – 6 Apr 2022, 44 active days |
| Refund amounts non-negative | PASS | 0 negative amounts |
| Refund records positive amount | PASS | 0 zero-amount refunds |
| Flagged customers exist in orders | PASS | 0 orphaned flagged IDs |
| Refund request grain | INFO | 3,596 requests across 2,515 customers (some customers have multiple requests) |

## Reconciliation

- Pandas vs SQL: 8 headline KPIs reconciled with zero mismatches (`reports/kpi_reconciliation.md`)
- Customer-level vs order-level rates: never mixed; each formula documents its grain
- Partial-period handling: April (6 Apr) is incomplete; MoM comparisons suppressed with a coverage note
