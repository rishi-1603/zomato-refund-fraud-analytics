# DEPLOYMENT VERIFICATION — Zomato
### Verified 2026-10-18

## Targets
| Component | Where | URL |
|---|---|---|
| Investigation console | Streamlit Community Cloud | https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/ |
| Repository + CI | GitHub Actions | rishi-1603/zomato-refund-fraud-analytics |

## Machine-verified (2026-10-18)
- HTTP check on the console URL: **303 (app reachable, Streamlit redirect)**.
- CI latest run: **success** (validate -> compare -> pytest, 139 tests).

## Manual click-through checklist (owner)
1. Open KPI page; compare 2 numbers to reports/kpi_reconciliation.md.
2. Open one suspect case; confirm the evidence view loads.
3. `python scripts/model_comparison.py && python -m pytest tests/` locally.

## Redeployment
Streamlit Community Cloud rebuilds on push to main (requirements.txt root file).
No manual secrets required (public app).

## Rollback
Git revert on main -> Streamlit rebuilds previous state. The console reads
precomputed risk tables; pipeline breakage cannot corrupt live session state.
