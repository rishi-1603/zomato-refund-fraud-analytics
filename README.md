# FoodTrust — Food Delivery Fraud, Trust & Marketplace Risk Intelligence Platform

A trust-and-risk intelligence case study built around one question: **which refund records deserve human review first, what does that review policy cost, and how do we avoid harming legitimate customers while doing it?**

[Open the dashboard](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/) · [Project report (PDF)](reports/FoodTrust_Project_Report.pdf) · [Problem statement & business value](docs/PROBLEM_STATEMENT_AND_BUSINESS_VALUE.md) · [Metric dictionary](docs/METRIC_DICTIONARY.md) · [Initial audit](docs/INITIAL_AUDIT.md) · [Executive findings](docs/EXECUTIVE_FINDINGS_REPORT.md) · [SQL queries](sql/fraud_queries.sql) · [Data dictionary](data/DATA_DICTIONARY.md)

[![CI](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml)

> **Data disclosure.** The delivery attributes come from a public dataset (45,584 orders). Customer IDs, refund events, amounts and risk labels are **synthetic and seeded**. No real fraud was detected and no real customer is implicated. FoodTrust is an independent portfolio platform inspired by food-delivery marketplace workflows — not an official Zomato product, with no access to internal Zomato data.

## Overview

An interactive Streamlit dashboard and reproducible Python/SQL analysis that help a refund-review team decide which customers to examine first. The project covers metric reconciliation, customer comparisons against order-volume baselines, a weighted review score, and a comparison of review policies at a fixed capacity.

## The problem

A high refund rate is easy to flag. Deciding whether it is unusual, and worth an analyst's time, is harder. Customers place different numbers of orders, investigations cost time, and a risk score cannot establish intent. A review team therefore needs three things: a fair comparison (rate against customers with similar order volume), a bounded queue, and an honest account of what a policy costs.

## What this project does

1. Reconcile headline refund KPIs between pandas and SQL.
2. Describe where refund value concentrates across customers, reasons and operating conditions.
3. Rank customers for review using a transparent, documented score, with its eligibility rule.
4. Test whether flagged behaviour is unusual for its order-volume band.
5. Compare review policies under explicit cost and recovery assumptions.
6. Check whether shared delivery attributes (riders, restaurants, drop cells) show a network pattern.
7. Monitor whether the score inputs drift over time.
8. Report data-quality status and reproduce every metric from a single source of truth.

## Data

| Item | Value | Provenance |
|---|---|---|
| Delivery orders | 45,584 | Public delivery dataset, unmodified (`data/raw/`) |
| Observed customer IDs | 9,895 | Generated from seed 42 (synthetic) |
| Refund requests | 3,596 | Generated (synthetic) |
| Refund value | ₹974,343.55 | Generated (synthetic) |
| Review pool (≥5 orders and refund rate >30%) | 279 customers | Derived |
| Refund value held by the review pool | 38.78% | Derived |

The order history runs from February to **6 April 2022**. Partial months are flagged on the dashboard, and their change badges are suppressed so that they are not read as a trend.

Field-level provenance, generated columns and metric definitions: [data dictionary](data/DATA_DICTIONARY.md).

## Tech stack

- **Application:** Streamlit (5 pages, button-bar navigation, sidebar filters, downloads).
- **Analysis:** pandas, NumPy, scikit-learn (model comparison), Plotly (charts).
- **Excel:** a formula-driven review workbook generated from the same data (`reports/FoodTrust_Review_Workbook.xlsx`).
- **SQL:** queries in `sql/`, validated against pandas on SQLite; PostgreSQL-oriented files are included for database review.
- **Testing and CI:** pytest (220 tests) and GitHub Actions.
- **Optional:** OpenAI or Gemini for narration. The app runs without any API key.

## Methodology

- **Eligibility rule:** at least five orders and a refund rate above 30%. This defines the 279-customer review pool.
- **Risk score:** a weighted formula: refund rate 40%, reason repetition 30%, refund frequency 20%, reason length 10%. The score ranks the pool. It is **uncalibrated**: a score of 70 is not a 70% probability of fraud. Details: [methodology](docs/risk_scoring_methodology.md).
- **Volume-band baseline:** each customer is compared with customers in the same order-volume band (1–2, 3–5, 6–10, 11–20, 21+ orders), using the band's P95 refund rate.
- **Policy economics:** three review policies are costed with an assumed ₹250 review cost, ₹100 false-positive friction and 50% recovery of a planted High customer's refund exposure. Sensitivity grid: [alert economics](reports/alert_economics.md).
- **Network check:** shared delivery-person, restaurant-cell and drop-cell components, each scored against the dataset baseline.
- **Drift monitor:** population stability index (PSI) on weekly score inputs.
- **Ground truth:** synthetic planted risk labels exist for validation only and are disclosed as such on the dashboard.

## The dashboard

Five pages, one set of sidebar filters (city type, customer volume band, last-order date, risk tier). Use the page bar at the top of the app to switch pages. Every figure is recomputed from the source data for the current filter scope.

| Page | What it answers |
|---|---|
| Executive Overview | Headline KPIs, the monthly trend, refund reasons by city, and the top of the review queue |
| Refund Analysis | Where refund value concentrates, how amounts distribute, and how refund rate varies by customer volume band |
| Customer Risk Review | Why a customer is flagged, how they compare with their volume band, the full review list, and the AI investigation |
| Review Operations | Capacity-limited review planning, cost and recovery scenarios, a downloadable decision record, and the deterministic queue copilot |
| Data & Methodology | Data provenance, validation, KPI formulas, risk methodology and limitations |

### Executive Overview

Six KPI cards (orders, refund requests, refund value, accounts flagged for review, potential exposure, average refund) sit above the review queue snapshot, a dual-axis monthly trend, refund reasons, and city mix.

### Refund Analysis

Concentration metrics and a Pareto/Lorenz view of where refund value sits, refund amount distributions, and refund rate by customer volume band (with the full-history denominator).

### Customer Risk Review

Per-customer score explanation against the flagged population, volume-band baseline comparison, the full review list with export, and an optional AI investigation that cites the evidence it used.

### Review Operations

Review-queue planning under an explicit capacity and cost assumption, scenario outputs, a downloadable decision record, and a deterministic question tool over the current queue.

### Excel review workbook

`reports/FoodTrust_Review_Workbook.xlsx` is generated from the same source data. The Orders sheet holds order-level rows, and the KPI, reason, city, tier and daily sheets are live Excel formulas over it (COUNTA, COUNTIF, SUMIF, AVERAGEIF), so every total traces back to the rows behind it. The review queue is filterable, with conditional formatting on score and exposure. Regenerate it with `python scripts/build_excel_workbook.py`; `tests/test_excel_workbook.py` checks the workbook against the KPI engine.

## Results

**Concentration.** The 279-customer pool holds 38.78% of refund value (₹377,892 of ₹974,344). This is a descriptive result.

**Volume-band context.** 113 of the 279 flagged customers are at or below their volume band's P95 refund-rate baseline. The eligibility rule is applied before the baseline comparison, so this result describes the pool only. It is not a measured false-positive rate.

**Policy comparison** (assumed costs, planted labels):

| Policy | Reviews | Precision vs planted labels | Modelled net value |
|---|---:|---:|---:|
| High tier | 8 | 100.0% | ₹8,274 |
| High + Medium tiers | 115 | 87.8% | ₹92,125 |
| All flagged customers | 279 | 46.9% | ₹65,006 |

On those assumptions the High + Medium policy returns the most modelled value, with a break-even precision of 28.2%. These are modelled values, not realised savings; a real rollout needs actual investigation costs and outcomes.

**Network check.** The delivery-person permutation test gives p = 0.76, with no evidence of High-label clustering beyond chance. A 788-customer restaurant-cell component reflected a busy location, so the analysis ranks components by excess refund rate, not by size.

**Stability.** The weekly PSI monitor reports the monitored features as stable in the seeded stream ([report](reports/drift_monitor.md)).

**Reconciliation.** Eight headline KPIs match between pandas and SQL, with zero mismatches ([report](reports/kpi_reconciliation.md)).

**Evidence tool.** The deterministic investigation tool passed a 12-case authored benchmark: 6/6 answerable questions grounded, and 6/6 unanswerable or unknown-ID questions refused ([report](reports/investigator_eval.md)).

Full findings: [executive summary](reports/executive_summary.md) and [executive findings](docs/EXECUTIVE_FINDINGS_REPORT.md).

## Running it locally

Use Python 3.11, matching CI. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

streamlit run dashboard/app.py

# In another terminal, with the same environment active:
python -m pytest -q
```

To reproduce the main reports:

```bash
python scripts/validate_risk_score.py
python scripts/kpi_reconciliation.py
python scripts/model_comparison.py
python scripts/network_analysis.py
python scripts/alert_economics.py
python scripts/drift_monitor.py
python scripts/investigator_eval.py
python scripts/external_validation.py
python scripts/build_excel_workbook.py
```

The dashboard and evidence tools need no API key. Optional narration reads `OPENAI_API_KEY` or `GOOGLE_API_KEY` from environment variables. Keep credentials out of the repository. If the hosted app is asleep or unavailable, see the [local demo guide](docs/DEMO_FALLBACK_GUIDE.md).

## Project structure

| Path | Contents |
|---|---|
| `dashboard/` | Streamlit app, KPI functions and evidence tools |
| `data/` | Public delivery inputs, generated refund fields, metric definitions and external reference data |
| `sql/` | Business queries, volume-band baselines and Pareto analysis |
| `scripts/` | Reconciliation, validation, analysis and workbook generation |
| `evals/` | Authored investigator benchmark |
| `notebooks/` | Data generation, exploration, scoring and database walkthroughs |
| `tests/` | Data, analytical, dashboard and evidence-tool checks |
| `reports/`, `docs/` | Findings, methodology and verification records |

## Limitations

- The refund layer is **synthetic**, and the risk labels are **planted**. Results describe the simulation, not real customers.
- There are no confirmed investigation outcomes, so precision values measure agreement with planted labels only.
- Scores depend on the eligible population. Customers with short histories can show extreme rates.
- Delivery-attribute findings are descriptive associations, not causes.
- Policy values use assumed costs and recovery rates. They are not realised savings.
- The live LLM narration path has not been run in the verification environment. Only the deterministic path is verified.
- The 6 April 2022 end date means the final month is partial.

The full list is in [assumptions and limitations](reports/assumptions_and_limitations.md).

## What's next

- Collect investigator outcomes to measure precision on real reviews, not planted labels.
- Measure customer friction before any policy pilot.
- Re-run and document the live LLM narration path with a key on a local machine.
- Run a PostgreSQL pass of the SQL files.

## Links

[Assumptions](reports/assumptions_and_limitations.md) · [Excel workbook](reports/FoodTrust_Review_Workbook.xlsx) · [Rules versus models](reports/model_comparison.md) · [Decision workflow](docs/BUSINESS_VALUE_DECISION_ENGINE.md) · [Problem statement](docs/PROBLEM_STATEMENT_AND_BUSINESS_VALUE.md) · [Metric dictionary](docs/METRIC_DICTIONARY.md) · [Initial audit](docs/INITIAL_AUDIT.md) · [Publication audit](docs/FINAL_RELEASE_AUDIT.md) · [Security audit](docs/SECURITY_AUDIT.md)