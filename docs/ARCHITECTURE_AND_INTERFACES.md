# ARCHITECTURE & INTERFACES — Zomato

## Data flow
```
synthetic orders (45,584 rows, seeded, planted labels)
   └─> scripts/validate_risk_score.py  (build_risk_table -> risk tiers)
         ├─> dashboard/ (Streamlit console: KPIs, suspects, investigation view)
         └─> reports/ (validation, comparison, FP analysis)
scripts/model_comparison.py: rules vs LR vs GBM on recovered labels (5-fold OOF)
scripts/{baseline_normalization, false_positive_analysis, sensitivity_analysis,
         pareto_analysis, cohort_analysis, kpi_reconciliation}.py
```

## Module interfaces
| Module | Input | Output |
|---|---|---|
| validate_risk_score.py | orders + refunds | risk table (importable: build_risk_table, recover_ground_truth) |
| kpi_engine.py | order/refund frames | 8 headline KPIs (mirrored by SQL) |
| model_comparison.py | recovered labels | reports/model_comparison.md + metrics JSON + figure |
| dashboard/app.py | risk table + KPIs | Streamlit console (live) |

## Deployment
- **Console:** Streamlit Community Cloud — https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/
- **CI:** GitHub Actions: validate_risk_score.py -> model_comparison.py -> pytest

## Design rules
- Analysis scripts are importable modules (functions tested directly).
- Figures optional (matplotlib not required on slim deployments).
