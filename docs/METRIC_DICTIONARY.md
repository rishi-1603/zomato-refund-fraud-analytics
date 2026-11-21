# FoodTrust — Metric Dictionary

**Single source of truth for metric definitions.** The same definitions drive `dashboard/kpi_engine.py`, `sql/fraud_queries.sql`, and the dashboard. Machine-readable layer: `data/metrics.json`. Reconciliation evidence: `reports/kpi_reconciliation.md` (8 KPIs, pandas ↔ SQL, zero mismatches).

**Conventions**
- All amounts in ₹ (INR).
- "Eligible order" = any of the 45,584 rows in the processed dataset (every row is a delivered-order line from the public dataset).
- "Refund request" = a row with `Refund_Requested == True` (3,596 rows). A customer may have several.
- "Flagged" = passes the review-pool eligibility rule. **Flagged ≠ fraudulent** — see the language policy below.
- Population basis is stated per metric; requested vs paid vs exposure values are never mixed.

---

## A. Volume & request metrics

| Metric | Definition | Numerator / Denominator | Basis | Verified value |
|---|---|---|---|---|
| Total orders | Count of order lines in the processed dataset | rows / — | all rows | 45,584 |
| Distinct customers | Count of distinct synthetic Customer_IDs | distinct IDs / — | all rows | 9,895 |
| Refund requests | Count of rows with a refund request | `Refund_Requested==True` rows / — | all rows | 3,596 |
| **Refund request rate** | Share of orders carrying a refund request | refund-request rows / total order rows | all rows | 7.89% |
| Refund-claiming customers | Distinct customers with ≥1 refund request | distinct IDs among request rows / — | all rows | computed at runtime |

*Guardrail:* refund request rate is **row-based** (order-line grain), matching the dataset's grain. Customer-level rates are separate metrics and always state their customer denominator.

## B. Financial metrics

| Metric | Definition | Numerator / Denominator | Basis | Verified value |
|---|---|---|---|---|
| **Total refund value (exposure)** | Sum of refund amounts across request rows | Σ Refund_Amount / — | request rows | ₹974,343.55 |
| Average refund amount | Mean refund amount per request row | Σ Refund_Amount / request-row count | request rows | runtime |
| Median refund amount | 50th percentile of refund amounts | — | request rows | runtime |
| Pool refund value | Σ Refund_Amount across eligible flagged customers | Σ Refund_Amount (pool) / — | request rows in pool | ₹377,892 (38.78%) |
| **Refund value share of pool** | Pool refund value / total refund value | pool Σ / total Σ | request rows | 38.78% |
| Modelled policy net value | Modelled recovery − modelled costs, under the stated assumptions | per `alert_economics` model | policy scenario | ₹8,274 / ₹92,125 / ₹65,006 by policy |

*Guardrails:* "Exposure" and "value held by pool" are descriptive concentrations. No metric in this project is ever labelled a **confirmed loss** — the dataset has no confirmed-fraud outcomes.

## C. Risk & review metrics

| Metric | Definition | Numerator / Denominator | Basis | Verified value |
|---|---|---|---|---|
| **Eligibility rule** | Flagged ⇔ orders ≥ 5 AND refund rate > 30% | — | customer level | defines pool |
| Review pool size | Customers passing the eligibility rule | qualifying customers / — | customers | 279 |
| Customer refund rate | Refund-request rows / that customer's orders | request rows / customer order rows | per customer | — |
| Review score | 0.40·rate + 0.30·reason-repetition + 0.20·frequency + 0.10·reason-length (weights documented, uncalibrated) | — | pool customers | — |
| High-tier customers | Top risk band within pool | — | pool | 8 |
| **Below-baseline flagged** | Flagged customers whose refund rate ≤ their volume band's P95 baseline | count / 279 | pool | 113 (40.5% of pool) |
| Precision vs planted labels | Agreement of a review policy with planted High/Medium labels | correct reviews / reviews made | policy scenario | 100.0% / 87.8% / 46.9% |
| Break-even precision | Precision at which modelled policy value = 0, under stated assumptions | — | economics model | 28.2% |

*Guardrails:* precision values measure **agreement with planted synthetic labels**, not real-world fraud detection. The below-baseline figure is descriptive — the eligibility rule is applied before the baseline comparison, so it is **not** a measured false-positive rate.

## D. Volume-band baseline metrics

| Metric | Definition | Notes |
|---|---|---|
| Volume bands | 1–2, 3–5, 6–10, 11–20, 21+ orders | Must stay identical to `scripts/baseline_normalization.py` |
| Band P95 refund rate | 95th percentile of customer refund rates within a band | The fair-comparison benchmark |
| Band-relative flag | Customer rate > band P95 | Context signal shown per flagged customer |

## E. Monitoring & quality metrics

| Metric | Definition | Evidence |
|---|---|---|
| KPI reconciliation mismatches | Count of pandas↔SQL disagreements across the 8 headline KPIs | 0 (`reports/kpi_reconciliation.md`) |
| PSI (weekly, per score input) | Population Stability Index on score inputs by ISO week | `reports/drift_monitor.md` — inputs stable in seeded stream |
| Data-quality status | Pass / known-gap / disclosed, per check | `reports/data_quality_report.md` |
| MoM change badges | Relative % and percentage-point month-over-month changes; **suppressed in partial months** | Final partial month: to 6 Apr 2022 |

## F. Language policy (binding)

| We say | We never say |
|---|---|
| Flagged / review candidate / High-tier | Fraudster, guilty, confirmed fraud |
| Score is uncalibrated (70 ≠ 70% probability) | Probability of fraud |
| Modelled net value under assumptions | Realised savings, money saved |
| Agreement with planted labels | Precision on real fraud |
| Descriptive concentration | Proven abuse |

Any new metric must be added here **and** to `data/metrics.json` **and** covered by a reconciliation or unit test before it appears on the dashboard.
