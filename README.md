# Food-Delivery Refund Risk Triage & Operations Analytics

**An analytics-first case study** using a public food-delivery order dataset to build a reconciled KPI layer, investigate refund patterns, quantify review-queue coverage and false-positive risk, and compare transparent rules with supervised models.

[Live investigation dashboard](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/) · [Executive summary](reports/executive_summary.md) · [KPI reconciliation](reports/kpi_reconciliation.md) · [Score validation](reports/score_validation.md) · [Rules vs. ML](reports/model_comparison.md) · [Alert economics](reports/alert_economics.md) · [Drift monitor](reports/drift_monitor.md) · [Data dictionary](data/DATA_DICTIONARY.md) · [Tests](tests/) · [Release gates](docs/RELEASE_GATES.md)

[![CI](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions/workflows/ci.yml)

> **Critical data notice:** The order/logistics rows come from a public Kaggle dataset. Refund events, refund amounts, and risk labels are generated synthetically and seeded. **No real fraud was detected; no real customer is implicated.** The score is an uncalibrated review-prioritization heuristic—not a fraud probability, verdict, or basis for automated customer action. This is an independent portfolio project, not an official Zomato product.

## Executive summary

The central operational question is not simply “Which model has the highest AUC?” It is: **Can an investigation team find unusual cases at a fixed review capacity, understand why they were flagged, and see who the eligibility funnel excludes?**

The project builds a four-signal review score, a customer-level dashboard, a Python/SQL KPI audit, volume-band baselines, false-positive and error analyses, a rules-versus-ML evaluation, priced alert economics, and a weekly drift-monitoring console. On the seeded labels, all three systems tie at 100% precision in the top 8 and top 20. The more important limitation is coverage: the current eligibility filter exposes only about 44% of planted high-risk labels, and the current High tier captures 8 of 299 (2.7%) at its chosen cut. **The evidence supports improving the funnel and keeping a human in the loop before replacing the interpretable score with a more complex model.**

**Role emphasis:** Data Analyst first (KPI definition, SQL, reconciliation, segmentation, funnel and concentration analysis, dashboard, operational recommendations); applied Data Science second (ranking evaluation, model comparison, capacity metrics, error analysis, alert economics, drift monitoring, guardrail audits, and an optional evidence-grounded LLM layer).

## At a glance

| Measure | Result | Interpretation |
|---|---:|---|
| Delivery-order rows | **45,584** | Public order dataset with synthetic refund attributes added |
| Customer IDs observed in orders | **9,895** | Customer-level analysis population |
| Total refund amount | **₹974,344** | Synthetic historical amount; not a verified loss |
| Customers in current score pool | **279** | Eligibility: at least 5 orders and refund rate above 30% |
| Refund exposure held by score pool | **38.78%** | A queue-sizing statistic, not proof of abuse |
| High tier | **8 customers; 100% precision against planted labels** | Small validation slice (n=8), synthetic-label result only |
| End-to-end High-tier recall | **2.7% (8/299 planted High labels)** | The funnel and conservative final cut miss most planted labels |
| Volume-adjusted screening | **113/279 (40.5%)** at or below their order-volume band’s P95 | A baseline review signal, not a measured real-world false-positive rate |

The metric definitions and population boundaries are recorded in [`data/metrics.json`](data/metrics.json). The validation reports use slightly different denominators where one generated customer has no observed order; see the report protocol before comparing counts.

## 1. Analyst workflow and decision questions

### Business questions answered

| Question | Analysis and artifact | Operational use |
|---|---|---|
| How large is refund exposure, and how is it distributed? | KPI layer, Pareto concentration, monthly summaries | Size the review queue and monitor concentration; concentration alone is not evidence of wrongdoing. |
| Which customer records meet the current review rule? | Eligibility filter, score tiers, evidence breakdown, CSV export | Prioritize human investigation; never auto-deny a refund from a score. |
| Is a high refund rate unusual for that customer's activity level? | P95 baselines by order-volume band | Avoid treating one refund in one order as equivalent to repeated behaviour across many orders. |
| Do Python and SQL tell the same story? | Independent KPI calculations and reconciliation | Detect definition drift before dashboard numbers are shared. |
| What does the system miss? | Funnel coverage, capacity curves, false-positive and error catalogs | Fix eligibility, tier cutoffs, and queue tie-breaking before tuning model complexity. |

### Selected analytical findings

- **Headline KPI consistency:** eight KPIs—including order count, refund amount, flagged customers, flagged exposure, and refund rate—match between independent pandas and SQL calculations. The monetary tolerance is ₹0.01. See [`reports/kpi_reconciliation.md`](reports/kpi_reconciliation.md).
- **Exposure concentration:** the top 10% of customers by synthetic refund value account for **75.6%** of that value. This can inform capacity planning; it does not establish intent or loss.
- **Volume matters:** 113 of the 279 currently flagged customers (40.5%) are at or below their order-volume band's P95 refund-rate baseline. This is a candidate-review signal, not a real-world false-positive rate or an automatic reason to clear an account. See [`reports/baseline_normalization.md`](reports/baseline_normalization.md).
- **The funnel is the main product issue:** the ≥5-order and >30%-refund-rate eligibility rule keeps many low-volume customers out of scoring. Among the 299 generated High labels, 131 enter the score pool and only 8 reach the High tier at the current cut. A proposed next analysis is to score every customer with at least one refund, then report end-to-end recall at a fixed investigation capacity.
- **Human review is a requirement:** MinMax scores are pool-relative and uncalibrated. A score of 70 is not a stable probability threshold across periods, and a flag means “review this evidence,” never “guilty.”

## 2. Data and metric design

### Data provenance

| Component | Provenance | Size / grain |
|---|---|---|
| Delivery and logistics fields | Public Kaggle food-delivery dataset | 45,584 order rows |
| Refund events and amounts | Seeded synthetic generator | Added to the order-level data |
| Risk labels | Seeded planted categories, recovered for validation | Labels are a test oracle for this simulation—not independent investigation outcomes |
| Processed customer base | Aggregated from observed orders | 9,895 customer IDs |

Column-level definitions and generation notes: [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) · [`docs/risk_scoring_methodology.md`](docs/risk_scoring_methodology.md).

### KPI and SQL layer

The dashboard reads a single metric registry, [`data/metrics.json`](data/metrics.json), so definitions and caveats are visible alongside the numbers. SQL files document business questions including refund summary, customer ranking, repeated reasons, city patterns, Pareto concentration, and volume-band baselines. The reconciliation script uses an SQLite adaptation of the SQL logic for automated parity checks; PostgreSQL-oriented query files are provided for review and use in a database environment.

## 3. Dashboard and investigation experience

[Open the live dashboard](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/)

![Refund analytics console overview](docs/screenshots/v2_console_overview.png)

The Streamlit console provides an overview, refund-pattern summaries, a customer investigation view, and delivery context. Filters support customer-volume and risk-tier exploration; the review queue exposes score components and baseline comparisons. The assistant can retrieve customer risk, refund history, and volume-band context through deterministic tools. An optional LLM can narrate tool-returned evidence; without an API key, the dashboard can display the evidence directly.

## 4. Applied Data Science (supporting layer)

### Transparent score

The current score is a weighted, MinMax-scaled composite over the eligible pool:

| Signal | Weight |
|---|---:|
| Refund rate | 40% |
| Repetition of the most common refund reason | 30% |
| Refund frequency | 20% |
| Average reason length | 10% |

Eligibility is **at least 5 total orders and refund rate above 30%**. Because refund rate is both part of eligibility and the largest score component, the score is best understood as triage within a pre-filtered pool—not an independent fraud detector. Full definition and thresholds: [`docs/risk_scoring_methodology.md`](docs/risk_scoring_methodology.md).

### Rules-versus-model evaluation

Logistic Regression and Gradient Boosting were compared with the rule score using 5-fold stratified out-of-fold predictions on the same eligible pool (279 customers; 131 planted High labels). Results are pinned in [`reports/model_comparison.md`](reports/model_comparison.md) and [`reports/model_comparison_metrics.json`](reports/model_comparison_metrics.json).

| System | ROC-AUC | PR-AUC | Precision@8 | Precision@20 |
|---|---:|---:|---:|---:|
| Rule score | 0.9422 | 0.9403 | 100% | 100% |
| Logistic Regression | 0.9611 | 0.9663 | 100% | 100% |
| Gradient Boosting | 0.9782 | 0.9813 | 100% | 100% |

**Decision:** the higher AUC of Gradient Boosting does not improve precision at the review capacities tested. Keep the transparent rule score for the current in-pool queue; address coverage and volume normalization first. The comparison uses synthetic labels whose behaviour was generated from the planted risk category, so the score differences do **not** establish real-world model superiority.

### Error analysis and safeguards

The error catalog separates customers excluded before scoring, cases ranked below the review cut, and high-rate records with small denominators. It recommends making low-volume cases visible, using order-volume context, and adding a secondary exposure sort for tied scores. It does **not** recommend automated bans, blocks, or refund denials. See [`reports/error_analysis.md`](reports/error_analysis.md) and [`reports/false_positive_analysis.md`](reports/false_positive_analysis.md).

### Alert economics, drift monitoring, and guardrail audits

The score is paired with the analyses an operations team needs before acting on it:

- **Alert economics** ([`reports/alert_economics.md`](reports/alert_economics.md)): the investigation alert is priced as a decision. **Break-even precision is 28.2%** — below that hit rate the alert program loses money at the base cost assumptions, so queue capacity is sized against a measured threshold rather than a fixed top-N.
- **Drift monitoring** ([`reports/drift_monitor.md`](reports/drift_monitor.md)): a weekly console computes per-feature PSI (conventions: <0.10 stable · 0.10–0.25 moderate · >0.25 significant) alongside the refund-rate business metric. An injected-drift proof run reaches **PSI 11.88 and fires the tripwire**; the retrain rule is explicit — any feature PSI > 0.25 for two consecutive weeks.
- **Account-network check** ([`reports/network_analysis.md`](reports/network_analysis.md)): a fraud-ring layer over real delivery attributes (shared delivery people; 200-shuffle null) returns an **honest null** — observed clustering 2.07% versus a 2.15% chance mean. The refund signal is individual-level on this dataset, not network-level; the null is reported, not hidden.
- **Assistant guardrail audit** ([`reports/investigator_eval.md`](reports/investigator_eval.md)): the LLM investigator is benchmarked on answerable and unanswerable prompts — **6/6 grounded in tool-returned data, 6/6 refused, 0 fabricated answers**. Every number is recomputed from the raw CSV; a mismatch is scored as a fabrication.
- **External validation** ([`reports/external_validation.md`](reports/external_validation.md)): the pipeline is checked against a real public schema — **20 columns (83% of the schema) are real** — and the drift tripwire is proven on real external data (airline passengers 1949–1960), so the analytics degrade loudly rather than silently.

## 5. Reproduce locally

The CI workflow uses Python 3.11. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

# Regenerate validation outputs
python scripts/validate_risk_score.py
python scripts/model_comparison.py
python scripts/kpi_reconciliation.py

# Launch the dashboard
streamlit run dashboard/app.py

# Run all automated checks
python -m pytest -q
```

Notebook-only dependencies (Jupyter, plotting, and PostgreSQL drivers) are listed in comments in [`requirements.txt`](requirements.txt); they are not required for the deployed dashboard or CI test suite.

## Repository map

```text
├── data/                 # raw public orders, synthetic refund layer, labels, metric registry
├── notebooks/            # generation, EDA, scoring, and SQL walkthroughs
├── scripts/              # validation, KPI parity, model comparison, alert economics, drift, network, baseline and error analyses
├── sql/                  # business queries, Pareto and volume-band analysis
├── dashboard/            # Streamlit console, evidence tools, screenshots
├── reports/              # executive, KPI, score, model, error, and limitation reports
├── docs/                 # scoring methodology, governance, model evaluation, release checks
└── tests/                # 136 automated tests across data, analysis, dashboard, and assistant
```

## Limitations and responsible-use boundary

- Refund events, refund amounts, and risk labels are synthetic. Performance against planted labels is not validation against actual fraud cases.
- The High-tier result is based on only eight records in a clean synthetic setup; it should not be generalized.
- The current eligibility rule and score are partly circular; MinMax scaling changes with the scored population.
- A high refund rate can reflect service or restaurant problems, a small denominator, or a genuine customer issue. These analyses do not identify cause or intent.
- No monetary loss prevented, customer savings, or business impact is measured. Any policy should be evaluated with human investigation outcomes, customer-protection metrics, and a fixed-capacity design.

The release decision and evidence are in [`docs/RELEASE_GATES.md`](docs/RELEASE_GATES.md); latest audited suite: **136 tests passed** (2026-10-18).
