# Final publication audit — Food-Delivery Refund Risk & Operations Analytics

Audit date: 2026-10-30. Scope: targeted publication repair, not a certification of literal perfection.
Baseline GitHub main: `e084babbf25492a418f565e6338a452bc15da6a1`. Recoverable branch: `audit/publication-review`.

## Execution and ownership
No autonomous subagents were available. One assistant performed sequential data/SQL, code, QA, security, browser and documentation workstreams. Tests and tool checks are evidence; there was no independent human or separately spawned QA agent.

## Changes and issue register
| Severity | File/screen | Evidence | Root cause | Repair | Verification |
|---|---|---|---|---|---|
| HIGH | dashboard/kpi_engine.py; dashboard/app.py | Live cards describe an 80% April decline although history stops on April 6. | Partial month compared with full prior month without coverage context. | Flag observed partial month boundaries, disclose unequal coverage, suppress partial-period order/exposure KPI deltas. | FIXED: arithmetic preserved; two new regression tests; full suite 139 passes. |
| MEDIUM | dashboard/kpi_engine.py | Below-P95 flags called likely false positives and automatically de-prioritized. | Baseline comparison overstated as an outcome finding. | Replace with human-review context and no automatic clearance. | FIXED; existing 113/279 metric retained. |
| LOW | dashboard/app.py; scripts/validate_risk_score.py | 17 pandas GroupBy.apply deprecation warnings. | Grouping columns implicitly passed to apply. | Select Refund_Reason explicitly before apply; compatible with the existing pandas>=2.0 minimum. | FIXED: 139 tests pass without those warnings. |
| LOW | dashboard/app.py | Monthly chart title says 2022–2024 although dataset spans February–April 2022. | Hardcoded date span. | Use observed-data title. | FIXED in source. |

## Data and metric verification
45,584 orders; 9,895 customers; refund amount 974,343.55; flagged exposure 377,891.92; 279 flagged; refund rate approximately 7.89%. Reconciliation script independently executed, zero discrepancies.

PASS for documented eight-KPI SQLite reconciliation (script exited 0). PARTIAL for the full PostgreSQL-oriented query library; no PostgreSQL server execution.

## Feature verification matrix
Production app woke successfully. Overview, Refund Patterns, Investigation and Delivery Context tabs clicked without displayed Streamlit exceptions. Four requested viewport screenshots captured. Local AppTest coverage passes. Every filter combination, download and external narration provider remains unverified.

- Production browser checks were separate from local tests.
- Initial Streamlit sleep screens were not counted as application success; apps were woken and actual embedded app frames inspected.
- Screenshot captures were genuine browser images, not generated mockups. Baseline production captures are retained in the external audit evidence pack, not represented as post-repair screenshots.
- No independent LLM provider test, exhaustive state-space check, accessibility-tool audit or production load test was completed.

## Source, structure and security checks
- 121 tracked files inventoried; 99 relevant text files pattern-scanned. This is not a claim of exhaustive semantic line-by-line review.
- Fatal syntax/undefined-name static check: `ruff check . --select E9,F63,F7,F82` passed. Broad style/type cleanup was not performed.
- README local link/image paths: no missing targets detected at baseline.
- Known GitHub token, Google-key and private-key signature scan over selected current text files and reachable historical text blobs: no matches. Heuristic only; screenshots/binary secrets and all possible credential formats are unverified.
- No tracked .env, credentials.json or secrets.toml found by the targeted filename check.
- pip-audit requirements resolution: no known vulnerabilities reported at scan time. This is not a guarantee of secure deployment or a replacement for a lockfile.
- The token supplied in chat is exposed and should be revoked/rotated. It must never enter repository content.

## Release scorecard
| Area | Status | Evidence / boundary |
|---|---|---|
| Repository structure | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| Code quality | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| Data cleaning | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| Metric correctness | PARTIAL | Executed reconciliation/tests for covered metrics; not every displayed calculation independently re-derived. |
| SQL validation | PARTIAL | PASS for documented eight-KPI SQLite reconciliation (script exited 0). PARTIAL for the full PostgreSQL-oriented query library; no PostgreSQL server execution. |
| Feature functionality | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| UI/UX | PARTIAL | Four viewports captured; tab/navigation smoke checks only. |
| Accessibility | BLOCKED | No complete keyboard/screen-reader/contrast audit; viewport checks do not establish accessibility. |
| Security | PARTIAL | Requirements scan and selected secret signatures only. |
| Performance | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| Automated tests | PASS | 139 passed; see external final test log. |
| Build and CI | PARTIAL | Local checks recorded; pushed-commit CI is verified separately in the delivery report. |
| README and documentation | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| GitHub presentation | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |
| Live deployment | PARTIAL | Baseline production rendered; repaired-commit deployment must be confirmed separately. |
| Recruiter readiness | PARTIAL | Targeted evidence above; comprehensive requirement coverage not established. |

## Recruiter notes
### 15-second summary
Refund-risk review case study emphasizing SQL/Python KPI parity, customer-volume context and scenario-based alert policy economics—not confirmed fraud detection.

### One-minute technical overview
Refund-risk review case study emphasizing SQL/Python KPI parity, customer-volume context and scenario-based alert policy economics—not confirmed fraud detection. The workflow defines entities and denominators, validates selected calculations independently, and presents findings with reproducible Python/SQL evidence. Statistical results are framed as descriptive or scenario-based where causal evidence is absent. Review the limitations before interpreting any model, risk score or financial estimate. Tests support reproducibility but do not prove production performance.

### Three analytical achievements
- Eight headline KPIs reconciled by executing pandas and SQLite independently with no discrepancies.
- 113 of 279 flags fall at or below volume-band P95; a baseline signal is not a confirmed false-positive outcome.
- Policy economics and a permutation-test null result are published with synthetic-label and cost-assumption boundaries.

### Three technical challenges
- Comparing incomplete calendar periods without implying a real decline.
- Keeping customer-grain risk scores separate from order-grain exposure.
- Testing tool evidence and refusals without claiming unrestricted LLM reliability.

### Five interview questions
- What is synthetic versus public-source data?
- Why is a high refund rate not proof of abuse?
- Why do partial months distort volume comparisons?
- What changes the alert-policy recommendation?
- What does p=0.76 establish—and not establish?

## Release checklist
- [x] Fresh public clone; old workspaces left untouched.
- [x] Recoverable branch and scoped diff.
- [x] Targeted fixes tested; no test weakened or deleted.
- [x] Selected SQL/data, security and browser evidence recorded.
- [ ] Pushed commit CI and repaired deployment verified (see delivery report).
- [ ] Complete accessibility, filter/export/provider and performance coverage.

## Remaining verification
Recheck repaired partial-month messaging after Streamlit redeployment. Full PostgreSQL library, exhaustive filter/export/provider tests, accessibility and load/performance verification remain incomplete.

## Verdict
**NOT READY for an unconditional all-features final-release claim.** Targeted source repairs pass their local acceptance tests. Publication as an analytics demonstration must retain the listed limitations; release completion depends on the pushed-commit CI and deployment follow-up.

## Production follow-up

The first post-push check reproduced an outdated imported KPI schema in the running Streamlit process (KeyError after the application source refreshed). A fail-closed compatibility guard now shows a refresh/reboot notice rather than rendering stale comparison advice or crashing. A local AppTest simulates the prior schema. A clean Streamlit reboot is required if the deployed module remains stale; full repaired deployment is not yet certified.

The follow-up repair reloads the stateless analytics module only when its result schema is stale, then recomputes KPIs and narration together. The simulated previous-schema AppTest now requires the correct partial-period warning, not merely absence of exceptions. A fail-closed warning remains only if reloading cannot supply the current schema.
