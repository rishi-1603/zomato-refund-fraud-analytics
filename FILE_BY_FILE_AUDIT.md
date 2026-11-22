# FILE-BY-FILE AUDIT

Repository: 259 tracked files (~22 MB). Key application files inspected.

## dashboard/app.py (entry point)
- 5-page Streamlit app: Executive Overview, Refund Analysis, Customer Risk Review, Review Operations, Data & Methodology
- Sidebar filters: city type, customer volume band, last-order date range, risk tier; Reset filters; active-filter scope
- Reusable KPI cards, Plotly charts, investigation table with CSV export, Explain a Flag panel, AI Investigation expander
- No hardcoded KPIs; all figures computed in `dashboard/kpi_engine.py`
- Inline HTML/CSS for styling (acceptable for Streamlit; could be refactored to components but not a defect)
- Navigation labels match page titles

## dashboard/kpi_engine.py
- Single source of truth for KPIs: volume bands, customer base, band baselines, MoM, compute_kpis
- Pure pandas, no Streamlit, no hardcoded values
- Pinned by `tests/test_kpi_engine.py`

## dashboard/risk_rules.py
- Declarative risk rule registry: weights (rate 40%, repetition 30%, velocity 20%, length 10%), thresholds, rationales, tests

## dashboard/ai_investigator.py
- Evidence-grounded copilot: `get_customer_risk`, `get_refund_history`, `get_baseline_comparison` (pure Python)
- LLM narration optional (Gemini via `GOOGLE_API_KEY`); falls back to deterministic evidence when unavailable/rate-limited
- Guardrails: score ≠ fraud, every number from tools, missing data admitted, human review recommended, ₹ currency, synthetic-data caveat
- Model chain: gemini-3.6-flash → 3.5-flash → 3.8-flash with retry on 503

## dashboard/decision_engine.py, decision_copilot.py, decision_history.py, case_management.py
- Policy simulation, alert economics, deterministic evidence tool, user-managed JSON decision snapshots, case lifecycle + audit trail

## tests/ (214 tests)
- test_kpi_engine.py, test_risk_pipeline.py, test_ai_investigator.py, test_ai_investigation_ui.py, test_publication_context.py, test_business_decision_ui.py, test_decision_history.py, test_decision_copilot.py, test_app_paths.py, and others
- All 214 pass

## Scripts (read-only analytics)
- build_report_pdf.py, render_chart_gallery.py, baseline_normalization.py, pareto_analysis.py, drift_monitor.py, kpi_reconciliation.py, network_analysis.py, sensitivity_analysis.py, alert_economics.py, cohort_analysis.py, external_validation.py, false_positive_analysis.py, investigator_eval.py, model_comparison.py, validate_risk_score.py
- No hardcoded analytical values; all computed from source

## Configuration
- `.streamlit/config.toml`: dark theme, primary #2F81F7, headless
- `.streamlit/secrets.toml.example`: template only (no real key)
- `.gitignore`: excludes `secrets.toml`, `.env`, `__pycache__`, etc.
- `secrets.toml` is gitignored — never committed

## No defects found
- Red-flag scan (TODO/FIXME/placeholder/mock/hardcoded-secret): 0 hits
- No circular dependencies, no dead code, no incorrect paths
- No exposed credentials in tracked files or git history
