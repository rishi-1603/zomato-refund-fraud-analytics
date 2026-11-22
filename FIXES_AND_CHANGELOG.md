# FIXES & CHANGELOG (final-audit-fixes branch)

## Changes since portfolio baseline (main)

### Dashboard theme (reverted to professional dark)
- Reverted a temporary light-theme experiment; kept dark theme (`#0D1117` bg, `#161B22` panels, `#2F81F7` blue accent) per product decision.
- Updated `.streamlit/config.toml` and `PLOTLY_LAYOUT` to dark slate palette with consistent chart styling (gridlines, hover labels, legend).

### Page structure (blueprint alignment)
- Renamed navigation/pages to the 5-page blueprint:
  1. Executive Overview
  2. Refund Analysis
  3. Customer Risk Review
  4. Review Operations
  5. Data & Methodology
- Removed all "tab" terminology; pages only.
- Renamed "Fraud Risk Score" → "Review Priority Score" throughout UI + tests (accurate: a review signal, not a fraud verdict).
- Changed "LIVE — COMPUTED FROM DATA" badge → "Historical dataset · Interactive analysis · Synthetic refund layer" (accurate for historical data).

### New Data & Methodology page
- Dataset overview table (public delivery data, synthetic refund layer, period, counts, project type).
- Computed (not assumed) data-quality checks: missing values, duplicate IDs, date validity, non-negative amounts, orphaned IDs, refund-request grain.
- KPI formula table (refund request rate, avg refund, customer refund rate, potential exposure, exposure share, P95 baseline, Review Priority Score).
- Risk methodology (eligibility, volume-band normalisation, tier thresholds, peer comparison, no confirmed labels).
- Limitations (synthetic layer, public data, partial April, rule-based heuristic).
- Technology stack.

### AI copilot hardening
- Added Gemini model fallback chain (3.6-flash → 3.5-flash → 3.8-flash) with retry on 503 rate-limit errors.
- Added rupee (₹) formatting rule and synthetic-data caveat to system prompt.
- `st.secrets` wiring in `main()` so API keys load from Streamlit secrets, never committed.
- Validation script `scripts/validate_ai.py` (loads key from env/secrets file, never hardcodes).

### Documentation alignment
- README updated to 5-page structure + project report PDF link.
- `docs/IMPLEMENTATION_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/INTERVIEW_PREPARATION.md`, `docs/METRIC_DICTIONARY.md`, `docs/PROBLEM_STATEMENT_AND_BUSINESS_VALUE.md` aligned to 5 pages / 214 tests.
- Empty 0-byte `reports/fraud_analysis_summary.pdf` removed; replaced by `reports/FoodTrust_Project_Report.pdf` + `scripts/build_report_pdf.py`.

### Audit package (new)
- `FINAL_AUDIT_REPORT.md`, `DATA_AND_KPI_VALIDATION.md`, `FILE_BY_FILE_AUDIT.md`, `QA_TEST_RESULTS.md`, `RECRUITER_ASSESSMENT.md`, `FIXES_AND_CHANGELOG.md`, `UI_UX_AUDIT.md`, `docs/AUDIT_FILE_INVENTORY.txt`

## Tests
- All 214 tests pass before and after changes.
- `tests/test_ai_investigation_ui.py` and `tests/test_business_decision_ui.py` page labels updated to match new 5-page names.

## No changes to
- Primary KPI definitions (all verified against source; no silent metric changes).
- Eligibility rule (≥5 orders, rate >30%).
- Risk score weights (40/30/20/10).
- Synthetic refund layer disclosure.
