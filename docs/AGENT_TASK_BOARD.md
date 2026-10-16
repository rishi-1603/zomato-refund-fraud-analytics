# AGENT TASK BOARD — Zomato
### Completed work items. Every item shipped with script + pinned test + limitations.

| # | Task | Output | State |
|---|---|---|---|
| 1 | KPI engine + Python/SQL reconciliation | kpi_engine.py, reports/kpi_reconciliation.md (8 KPIs, 0 discrepancies) | Done |
| 2 | Risk score (4 signals) + weight sensitivity | validate_risk_score.py (Spearman rho > 0.95 across weightings) | Done |
| 3 | Ground-truth recovery + score validation | reports/score_validation.md (100% top-tier precision) | Done |
| 4 | Rules-vs-ML comparison (LR, GBM, OOF) | scripts/model_comparison.py + reports/model_comparison.md | Done |
| 5 | Capacity curve + false-positive analysis | reports/false_positive_analysis.md + baseline_normalization.md | Done |
| 6 | Error catalog (3 failure classes) | reports/error_analysis.md | Done |
| 7 | Metric registry | data/metrics.json | Done |
| 8 | CI pins model_comparison before tests | .github/workflows/ci.yml | Done |
| 9 | AI investigation console + tests | dashboard/app.py, test_ai_investigator.py, test_ai_investigation_ui.py | Done |
| 10 | Release gates A-E | docs/RELEASE_GATES.md | Done |
