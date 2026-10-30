# Food-Delivery Refund Risk & Operations Analytics

A refund-review case study built around a limited investigation queue: **which customer records deserve a closer look, and what does that review policy cost?**

[Open the dashboard](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/) · [Executive findings](docs/EXECUTIVE_FINDINGS_REPORT.md) · [SQL queries](sql/fraud_queries.sql) · [Data dictionary](data/DATA_DICTIONARY.md)

[![CI](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml)

![Refund analytics dashboard and investigation queue](docs/screenshots/v2_console_overview.png)

> The delivery attributes come from a public dataset. Customer IDs, refund events, amounts and risk labels are synthetic and seeded. No real fraud was detected and no real customer is implicated. This is an independent portfolio project, not an official Zomato product.

## The problem

A high refund rate is easy to flag. Deciding whether it is unusual—and worth an analyst's time—is harder. Customers have different order volumes, investigations have a cost, and a risk score cannot establish intent.

This project follows that workflow from metric reconciliation through customer comparisons and review-policy scenarios. The Streamlit app is the place to explore the records; SQL, Python and the reports provide the calculations behind them.

## Data in scope

| Measure | Value |
|---|---:|
| Delivery orders | 45,584 |
| Observed customer IDs | 9,895 |
| Refund requests | 3,596 |
| Synthetic refund amount | ₹974,343.55 |
| Customers meeting the review rule | 279 |
| Refund amount held by those customers | 38.78% |

The current review rule requires **at least five orders and a refund rate above 30%**. A weighted score then ranks that eligible pool. The score is uncalibrated and pool-relative: a score of 70 is not a 70% probability of fraud.

## What the analysis found

### Customer activity changes the interpretation

**113 of 279 flagged customers** are at or below their order-volume band's P95 refund-rate baseline. That is useful review context, not a measured false-positive rate or an automatic reason to clear an account.

The eligibility rule also limits coverage. Of 299 generated High labels, 131 enter the review pool and eight reach the High score tier. The reports distinguish generated labels from labels with observed orders: one generated High customer has no order record. These denominators should not be mixed.

[Volume-band comparisons](reports/baseline_normalization.md) · [Score validation](reports/score_validation.md) · [Review funnel](docs/REFUND_RISK_FUNNEL.md)

### Reviewing everyone is not the most valuable scenario

I compared three policies using an assumed ₹250 review cost, ₹100 false-positive friction cost and 50% recovery of a planted High customer's refund exposure.

| Policy | Reviews | Precision against planted labels | Modeled net value |
|---|---:|---:|---:|
| High tier | 8 | 100.0% | ₹8,274 |
| High + Medium tiers | 115 | 87.8% | ₹92,125 |
| All flagged customers | 279 | 46.9% | ₹65,006 |

Under those assumptions, High + Medium tiers return more modeled value than reviewing everyone. Break-even precision is **28.2%**. The result needs operating-cost and investigation-outcome data before it could inform an actual policy; these are not realized savings.

[Policy calculations and sensitivity grid](reports/alert_economics.md)

### The ring hypothesis was not supported

Shared delivery-person, restaurant-cell and drop-cell networks provide a way to test whether flagged behavior has a network pattern. The delivery-person permutation test returned **p = 0.76**, with no evidence of High-label clustering beyond chance.

Raw component size was misleading too: a 788-customer restaurant-cell component reflected a busy location, not evidence of collusion. The report keeps the null result and separates shared attributes from claims about intent.

[Network analysis](reports/network_analysis.md)

### Calendar coverage matters

The order history ends on **6 April 2022**. Comparing April's total with March's full-month total can look like a sharp operational decline when it is largely a coverage problem. The dashboard flags partial observed periods and suppresses the order/exposure KPI change badges in that case. It preserves the totals without presenting them as a like-for-like trend.

## Using the dashboard

- **Overview:** scope, headline metrics and the highest-ranked records.
- **Refund Patterns:** reasons, concentration and customer-level patterns.
- **Investigation:** score components, volume-band context and customer evidence.
- **Delivery Context:** traffic, weather and other delivery attributes.

Use the city and customer-volume controls to explore a narrower population. Investigation filters apply to the review queue. A flag means review the evidence, not deny a refund or restrict an account.

The dashboard may need waking after Streamlit inactivity. A [local-demo guide](docs/DEMO_FALLBACK_GUIDE.md) is included if the hosted app is unavailable.

## Checks behind the analysis

Eight headline KPIs are independently calculated in pandas and SQL, with **zero reconciliation discrepancies** within the documented tolerance. The automated check uses SQLite adaptations; the PostgreSQL-oriented query files are available for database review.

The weekly PSI monitor reports the seeded stream as stable. Its tripwire is tested with injected shifts and a separate public airline-passenger dataset. That validates the monitoring calculation, not a live fraud-monitoring system.

The investigation assistant retrieves evidence through deterministic tools. A small authored benchmark passed **6/6 grounded cases and 6/6 refusals**, with no fabricated numbers in those cases. Optional LLM narration is outside that evaluation.

The audited regression suite contains **139 tests**. The [publication audit](docs/FINAL_RELEASE_AUDIT.md) records what was executed and what remains unverified, including exhaustive filters, exports, AI-provider paths, accessibility and load testing.

[KPI reconciliation](reports/kpi_reconciliation.md) · [Drift monitor](reports/drift_monitor.md) · [Evidence-tool evaluation](reports/investigator_eval.md) · [Provenance and external validation](reports/external_validation.md)

## Run locally

Use Python 3.11, matching CI. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
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
```

The dashboard and evidence tools work without an API key. Optional narration reads `OPENAI_API_KEY` or `GOOGLE_API_KEY`; keep credentials in environment variables or platform secrets, never in the repository.

## Where to look in the repository

| Path | Contents |
|---|---|
| `dashboard/` | Streamlit app, KPI functions and evidence tools |
| `data/` | Public delivery inputs, generated refund fields, metric definitions and external reference data |
| `sql/` | Business queries, volume-band baselines and Pareto analysis |
| `scripts/` | Reconciliation, validation and analysis scripts |
| `evals/` | Authored investigator benchmark |
| `notebooks/` | Generation, exploration, scoring and database walkthroughs |
| `tests/` | Data, analytical, dashboard and evidence-tool checks |
| `reports/`, `docs/` | Findings, methodology and verification records |

## Limits of the recommendation

The analysis uses planted risk labels, not confirmed investigation outcomes. Scores change with the eligible population, and small customer histories can produce extreme rates. Delivery-attribute findings are descriptive associations. Neither a high rate, a shared location nor a model rank establishes fraud.

Before piloting a review policy, I would collect investigator outcomes, measure customer friction, revisit the eligibility funnel and compare policies at a fixed review capacity. Those checks matter more than adding a more complex model.

[Full assumptions](reports/assumptions_and_limitations.md) · [Rules versus models](reports/model_comparison.md) · [Evidence index](RESUME_EVIDENCE.md)
