# Final Release Report — Food-Delivery Refund Risk & Operations Analytics
**Date:** 2026-11-28 · **Release commit:** 8229640 · **CI:** green (222 tests)

## A. Overall result
**READY WITH DISCLOSED LIMITATIONS** — refund layer is synthetic/seeded (disclosed); risk score is triage support, never a fraud verdict.

## B. Work completed (this release)
- README header now links the interview prep pack and scoring methodology for recruiter discoverability

## C. Features & verification
| Feature | Status |
|---|---|
| 5-page Streamlit console (Executive Overview, Refund Analysis, Customer Risk Review, Review Operations, Data & Methodology) | Live on Streamlit Cloud |
| 4-signal risk score + tiering | Validated vs recovered ground truth: 100% High-tier precision, 0.94 in-pool AUC |
| Baseline normalization + false-positive analysis | 113 flags (40.5%) identified as FP candidates |
| AI Investigation Assistant | `tests/test_ai_investigator.py` + UI tests |
| SQL/Python KPI reconciliation | 8/8 KPIs, zero discrepancies |

## D. Data & models
- 45,584 real Kaggle delivery orders + transparent synthetic refund layer (seeded; ground truth recoverable)
- Score-validation report regenerable via `scripts/validate_risk_score.py` (runs in CI)

## E. Quality
222 tests green (risk pipeline, KPI engine, all analysis scripts, AI assistant + UI). CI runs ground-truth validation before tests.

## F. Known issues / disclosed limitations
1. Refund layer synthetic — methods are the story, not the numbers
2. Eligibility funnel (≥5 orders) excludes ~56% of planted high-risk customers — documented coverage gap
3. Flat 30% refund-rate threshold is the main false-positive driver — recommendation documented

## H. Deployment
Live: https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/ (verified after release)

---

## Release v2 (2026-10-21) — evaluation-depth week (Days 2–6)

| Evidence | Status |
|---|---|
| Calibration + cost-based thresholds / decision curves | Published + CI-pinned |
| Naive-baseline / rules-vs-ML / temporal comparisons | Published with honest verdicts |
| Error analysis with concrete failure cases | `reports/error_analysis.md` |
| Metric-registry entries for every new metric | `data/metrics.json` |
| New analysis scripts run in CI on every push | ✅ |
| Interview-prep eval-depth Q&A | ✅ |

**Test totals:** Zomato — 222 tests green (full suite), all passing.

**Notable honest findings shipped this week:** flagged queue concentration (top 10% hold 75.6% of refund value); rule-based score treated as triage support, never a fraud verdict; synthetic layer disclosed; AI narration deterministic fallback verified.

**Status unchanged:** READY / READY WITH DISCLOSED LIMITATIONS — nothing this week weakened a claim; several were tightened downward on purpose.
