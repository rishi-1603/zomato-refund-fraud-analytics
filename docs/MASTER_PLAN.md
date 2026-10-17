# MASTER PLAN — Zomato Refund & Fraud Analytics
### Portfolio project · week of 2026-10-15 · status: COMPLETE

## Objective
A refund-abuse detection and investigation product over a synthetic dataset of
45,584 delivery orders: KPI engine, 4-signal risk score, recovered ground-truth
validation, rules-vs-ML comparison, false-positive analysis, and an investigator
console — with honest verdicts published even when they favor simple rules.

## Scope
**In:** KPI reconciliation (Python vs SQL), risk scoring, ground-truth recovery,
supervised comparison (LR/GBM), capacity/FP analysis, error catalog, Streamlit
console.
**Out:** real fraud claims, production serving, LLM-based fraud decisions.

## Timeline
| Day | Plan | Status |
|---|---|---|
| D1 | Baseline + evidence layer | Done |
| D4 (Oct 18) | Rules vs LR/GBM comparison | Done |
| D6 | Error catalog, metric registry, CI pinning | Done |
| D7 | Resume/interview/release kit | Done |

## Success criteria — all met
- Defensible "ship X because Y" verdict: reports/model_comparison.md
- PR-AUC reported alongside ROC-AUC on imbalanced labels: yes (3% base rate)
- Tests pin the comparison numbers: tests/test_model_comparison.py (136/136 green)

## Key links
- Live console: https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/
- Comparison report: reports/model_comparison.md
- Score validation: reports/score_validation.md
- Error catalog: reports/error_analysis.md
- Release gates: docs/RELEASE_GATES.md
