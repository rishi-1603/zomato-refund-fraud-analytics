# FoodTrust — Final Project Audit (internal rubric)

**Scorecard** (internal project-quality rubric; not a recruiter score or a top-5% guarantee):

| Evaluation area | Weight | Score | Reason |
|---|---:|---:|---|
| Business problem relevance | 10 | 9 | Real marketplace refund-risk question, clearly framed; 12 problem areas mapped, 2 blocked by data (documented). |
| Data architecture and data quality | 10 | 8 | Immutable raw source, synthetic layer with provenance, DQ report, reconciliation. Missing: PostgreSQL runtime, Pandera contracts. |
| SQL and analytics engineering | 15 | 7 | 3 business queries, pandas↔SQL reconciliation (0 mismatches). SQLite-validated; PostgreSQL pass not yet run. |
| Python and statistical analysis | 10 | 8 | Deterministic pandas KPIs, volume-band baseline, permutation test, PSI, sensitivity grid. |
| Fraud and risk methodology | 15 | 9 | Transparent weighted score, eligibility rule, uncalibrated disclosure, context rules, null-result reporting. |
| Dashboard and data storytelling | 10 | 8 | 8 tabs, one filter set, live DQ, downloads, screenshots. `app.py` is large (~86 KB) but core logic extracted. |
| ML and explainability | 10 | 7 | Model comparison (rules vs ML) on planted labels; SHAP not justified (no deployed classifier). Correctly scoped. |
| AI assistant quality and safety | 5 | 8 | Deterministic evidence tool, 12-case benchmark (6/6 grounded, 6/6 refused). LLM path disclosed as unverified. |
| Software engineering and testing | 10 | 9 | 206 tests pass; case lifecycle + risk registry + CI; no hardcoded KPIs; no credentials committed. |
| Documentation and presentation | 5 | 9 | 40+ docs, README, metric dictionary, architecture, model card, audit trail. |
| **Total** | **100** | **82** | |

## Areas below 8/10 — required corrections

- **SQL and analytics engineering (7):** run the SQL pass against PostgreSQL and add dbt models. Until then, SQL claims are SQLite-validated only.
- **ML and explainability (7):** SHAP is not implemented (correctly, since there is no deployed classifier). If ML is to be shown, add a clearly-labelled synthetic-label demonstration with leakage-free evaluation, or keep rule-based and document why.
- **Data architecture (8):** add Pandera contracts and Docker Compose (Phase C).
- **Dashboard (8):** optional further splitting of `app.py`; not blocking.

## Final audit questions — answered

- **Every KPI mathematically correct?** Yes — verified by `tests/test_kpi_engine.py` and `scripts/kpi_reconciliation.py` (8 KPIs, zero mismatches).
- **All chart values connected to validated data?** Yes — `kpi_engine.py` is the single source of truth; no hardcoded values.
- **All financial values reconciled?** Yes — ₹974,343.55 exposure, ₹377,892 pool (38.78%), all cross-checked.
- **Null values interpreted correctly?** Yes — `Refund_Reason` null = no refund request (structural), never imputed.
- **Data leakage?** No — eligibility applied before baseline; ground truth planted per customer, not leaked into features.
- **ML labels defensible?** Planted labels only, disclosed as validation-only; no real fraud claimed.
- **Risk scores explainable?** Yes — weights published, components shown, methodology doc exists.
- **Can legitimate customers be distinguished from confirmed abuse?** The score separates volume from pattern; 113/279 flagged customers sit at/below their band's P95. But there are **no confirmed outcomes** in the data, so no real FPR is measurable — documented.
- **Dashboard tells a coherent business story?** Yes — 8 tabs from overview → reasons → risk → ops → policy → AI → DQ → reports.
- **AI assistant uses real query results?** Deterministic path: yes (12-case benchmark 6/6 grounded, 6/6 refused). LLM path: disclosed as unverified.
- **Can the project run from a fresh clone?** Yes — `requirements.txt`, venv, `streamlit run dashboard/app.py`, `pytest -q`. Docker optional (Phase C).
- **Tests passing?** 206/206 (was 188 + 18 new case-management/risk-rule tests).
- **Deployment claims verified?** Streamlit Cloud app is live at the documented URL; local Docker not yet tested (Phase C).
- **Can another analyst reproduce the findings?** Yes — scripts regenerate reports; reconciliation report documents mismatches (zero).
- **Can I explain every major technology and decision?** Yes — see `docs/INTERVIEW_PREPARATION.md` (30+ questions with honest answers).

## Known limitations (full list)

1. Refund layer is synthetic; risk labels planted. Results describe the simulation.
2. No confirmed investigation outcomes → no measurable real FPR.
3. Scores are uncalibrated.
4. Short-history customers can show extreme rates (mitigated, not removed).
5. No refund lifecycle timestamps → no operational-delay analysis.
6. No real merchant IDs → merchant analysis is by restaurant-cell.
7. SQL validated on SQLite; PostgreSQL pass pending.
8. LLM narration path not verified in CI.
9. Hour-of-day analysis blocked (no timestamps in source).
10. `app.py` is large (~86 KB); core logic is extracted.

## Evidence-backed final score: **82 / 100**
