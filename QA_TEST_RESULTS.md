# QA TEST RESULTS

## Execution
- Command: `python -m pytest -q` from repository root
- Result: **222 passed, 0 failed** in ~4:41
- Warning: Streamlit "missing ScriptRunContext" in bare mode — expected, not a defect

## Test categories covered
1. Unit tests — kpi_engine, risk rules, risk score bounds, tier boundaries
2. Data validation — path absolutism, no relative data reads, join integrity
3. KPI reconciliation — pandas vs SQL, 8 headline KPIs, zero mismatches
4. Risk rule tests — eligibility (≥5 orders, rate >30%), tier split (164/107/8), 166+113=279
5. P95 benchmarking tests — per-band P95, above/below baseline counts
6. Integration tests — decision engine, copilot, case management, history
7. UI interaction tests — Streamlit AppTest: all 5 pages render, filters work, AI investigation button works, no exceptions
8. Deployment smoke tests — `py_compile` clean; deployed app smoke-tested via browser (all 5 pages render)

## Edge cases verified (via ai_investigator + decision engine)
- Invalid customer ID → clear error, no crash
- Non-flagged customer → clear error
- Empty filtered result → "No customers match the current filters" / info states
- Missing data handled by AI with explicit "missing information" statements

## AI validation (10 random flagged customers)
- 10/10 evidence values exact (risk score, tier, refund rate, refunds, exposure, volume band)
- Explanations grounded, rupee-formatted (₹), no fraud conclusions, synthetic-data caveat
- External Gemini API intermittently rate-limited (503); deterministic evidence panel always renders as fallback

## Unresolved
- AI narration consistency across repeated runs depends on external API availability (best-effort; graceful fallback implemented)
