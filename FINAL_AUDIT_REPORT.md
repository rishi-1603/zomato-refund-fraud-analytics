# FINAL AUDIT REPORT — Zomato Refund Risk & Operations Analytics

**Project:** FoodTrust — Food Delivery Fraud, Trust & Marketplace Risk Intelligence (Zomato case study)  
**Repository:** https://github.com/rishi-1603/zomato-refund-fraud-analytics  
**Deployed:** https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/  
**Audit branch:** `final-audit-fixes` (from `main`)  
**Audit date:** 22 Nov 2026  
**Release decision:** **AMBER — CONDITIONALLY READY**  

---

## Executive summary

This is an independent portfolio case study — NOT an official Zomato system. It analyzes 45,584 delivery orders (Feb–Apr 2022, public dataset) with a disclosed synthetic refund layer, builds a rule-based review-priority score over 9,895 customers, flags 279 accounts, benchmarks each against its order-volume peer band (P95), and exposes a 5-page Streamlit dashboard with an evidence-grounded AI investigation copilot.

**The project is largely functional and professionally presented.** All 214 tests pass, every primary KPI independently reconciles to the source data, all 5 pages render locally and on the deployed Streamlit app, and the AI copilot returns grounded, correct explanations (validated on 10 random flagged customers) with a deterministic fallback when the external LLM API is rate-limited.

**It is not GREEN because:** the AI narration depends on an external Gemini API that is intermittently rate-limited (503). The deterministic evidence panel always renders, but LLM narration is not guaranteed on every click. Per the audit standard, an unverifiable external dependency keeps the project at AMBER until either (a) the API proves stable across repeated runs, or (b) the narration is documented as best-effort optional and the deterministic panel is treated as the primary deliverable.

---

## Scope of verification

- Repository inventory: 259 files (~22 MB); file inventory at `docs/AUDIT_FILE_INVENTORY.txt`
- Red-flag scan (TODO/FIXME/placeholder/mock/hardcoded-secret patterns): **0 hits**
- Secret pattern scan (PAT/GitHub/Vercel/Gemini keys): **0 hits in tracked files**
- Primary KPIs recalculated from `data/processed/zomato_with_refunds.csv` — all match
- Full test suite: **214 passed**
- Deployed app smoke-tested: all 5 pages render, no exceptions

## Verified ground-truth KPIs (recalculated from source)

| Metric | Source value | Dashboard claim | Status |
|---|---|---|---|
| Delivery orders | 45,584 | 45,584 | Verified |
| Unique customers | 9,895 | 9,895 | Verified |
| Refund requests | 3,596 | 3,596 | Verified |
| Refund request rate | 7.89% | 7.9% | Verified |
| Total refund amount | ₹9,74,343.55 | ₹9,74,344 | Verified |
| Avg refund amount | ₹270.95 | ≈₹271 | Verified |
| Date range | 11 Feb – 6 Apr 2022 | Feb–Apr 2022 | Verified |
| Active days | 44 | 44 | Verified |
| Flagged accounts (≥5 orders, rate >30%) | 279 | 279 | Verified |
| Flagged refund exposure | ₹3,77,891.92 | ₹3,77,892 | Verified |
| Flagged exposure share | 38.78% | 38.8% | Verified |
| Above peer P95 | 166 | 166 | Verified |
| At/below peer P95 | 113 | 113 | Verified |
| 166 + 113 = 279 | ✓ | ✓ | Verified |
| Tier split (Low/Med/High) | 164 / 107 / 8 | 164 / 107 / 8 | Verified |
| Top-10% customer concentration | 75.6% | 75.6% | Verified (distinct from 38.8% flagged share) |
| Wrong Item count | 862 (24.0%) | 862 / 24% | Verified — count and % are consistent |

### Discrepancies investigated (none unresolved)

- **3,596 refund requests vs 9,895 customers:** different grains — 3,596 is order-level refund *requests*; 9,895 is total unique customers (not refunding customers). Documented in KPI dictionary; no inconsistency.
- **Volume-band graph at 100%:** not present in current code. Band rates are 6.3%–8.0% (order-level denominator, never refunded-only). Fixed in prior refactor.
- **Reason count vs %:** Wrong Item = 862 requests = 24.0% — consistent, not a discrepancy.

## Pages verified (deployed app)

| Page | Renders | Key elements verified |
|---|---|---|
| 1. Executive Overview | Yes | 4 KPIs, trend chart, exposure by tier, attention section |
| 2. Refund Analysis | Yes | Distribution, reasons, volume bands, Pareto, city |
| 3. Customer Risk Review | Yes | Eligibility, score, P95 baseline, investigation table, Explain a Flag |
| 4. Review Operations | Yes | Queue, priority sorting, capacity planner |
| 5. Data & Methodology | Yes | DQ checks, KPI formulas, risk methodology, limitations |

## AI copilot validation

- Evidence (risk signals, refund history, peer baseline) computed by pure Python; LLM only narrates.
- Validated on 10 random flagged customers: 10/10 evidence values exact; explanations grounded, no fraud conclusions, rupee formatting (₹), synthetic-data caveat included.
- Edge cases handled: invalid customer ID → clear error; non-flagged customer → clear error.
- Fallback: when the Gemini API is unavailable/rate-limited, the deterministic evidence panel still renders with "Optional narration unavailable" notice. No credentials exposed (`st.secrets`, gitignored `secrets.toml`).
- **Unverified:** consistent LLM narration across repeated runs (external API rate-limited during this audit).

## Release checklist (PART 10 acceptance)

| Category | Status | Notes |
|---|---|---|
| Code & architecture | Pass | All files inspected; no broken imports/paths; no secrets |
| Data & analytics | Pass | Primary KPIs independently recalculated and reconciled |
| Dashboard | Pass | 5 pages render; filters/nav/exports/investigation work |
| AI | Amber | Evidence grounded; narration best-effort due to external API limits |
| Documentation & deployment | Pass | README matches; limitations disclosed; live app smoke-tested |

## Scorecard (PART 8)

| Category | Weight | Score | Evidence |
|---|---|---|---|
| Analytical correctness & KPI accuracy | 25 | 25/25 | All primary KPIs recalculated & verified |
| Business problem & decision value | 15 | 13/15 | Clear problem; P95 benchmarking strong; savings claims correctly labelled as modelled |
| Data quality & statistical methodology | 10 | 9/10 | DQ checks computed; limitations honest; synthetic layer disclosed |
| Dashboard UI/UX & visualizations | 15 | 12/15 | 5 pages, dark theme, consistent; minor: AI narration not guaranteed |
| Code quality & architecture | 10 | 8/10 | Clean modules, tests; some inline HTML in app.py |
| Testing & functionality | 10 | 10/10 | 214 tests pass; edge cases covered |
| Security, reliability & deployment | 10 | 9/10 | No secrets; graceful AI fallback; deployed live |
| README & recruiter presentation | 5 | 4/5 | Professional; screenshots match current version |
| **TOTAL** | **100** | **90/100** | |

## Release decision: AMBER — CONDITIONALLY READY

**Items to reach GREEN:**
1. Confirm AI narration stability across repeated runs (external API), OR document narration as best-effort optional with the deterministic evidence panel as the primary deliverable.
2. Commit the audit package (`FINAL_AUDIT_REPORT.md`, `DATA_AND_KPI_VALIDATION.md`, `QA_TEST_RESULTS.md`, `RECRUITER_ASSESSMENT.md`, `FIXES_AND_CHANGELOG.md`, `UI_UX_AUDIT.md`) to the repo.
3. (Optional) Rotate the GitHub PAT and Vercel token that were previously exposed in chat — they are NOT in the repository, but should be revoked as a precaution.

None of these are critical defects. The project is safe to present to recruiters now with the above noted limitation.
