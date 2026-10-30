# Publication verification — Food-Delivery Refund Risk & Operations Analytics

Audit date: 2026-10-30. This follow-up supersedes the earlier snapshot that treated PostgreSQL, fresh screenshots and accessibility tooling as wholly unperformed.

## What was executed

- Fresh-source branch with recoverable commits; no unrelated changes overwritten.
- Independent raw-data calculations and actual PostgreSQL execution, with dialect boundaries documented.
- Actual anonymous browser rendering, tab/navigation actions, representative filters, downloads and deterministic assistant workflows.
- Fresh screenshots stored in `docs/screenshots/publication_*.png` and referenced by the README.
- axe-core WCAG 2 A/AA and 2.1 AA checks at desktop/mobile, with measured defects repaired. Automated scans do not certify screen-reader usability.
- Direct deterministic AI benchmark execution, selected static checks and full regression: **141 tests**.
- Reviewed integration of the related publication-audit PR. The unrelated E-Commerce revenue PR remains outside this release.

## Evidence by area

| Area | Result and boundary |
|---|---|
| Structure/documentation | PASS for corrected links, fresh screenshot references and this separated audit set |
| Metrics/data quality | PASS for independently recomputed figures in [data validation](DATA_AND_METRIC_VALIDATION.md); not every future metric |
| SQL | PASS: all original PostgreSQL scripts executed |
| Code/static checks | PASS for Ruff E9/F63/F7/F82/F401/F541/F841; not an exhaustive proof of correctness |
| Regression | 141 tests pass; tests not weakened or skipped |
| Functionality | Representative workflows recorded in [feature matrix](FEATURE_VERIFICATION_MATRIX.md); combinatorial coverage remains partial |
| Accessibility | Automated tested scope repaired; incomplete axe checks and manual assistive-technology review remain PARTIAL |
| Security | [Security scope](SECURITY_AUDIT.md); no blanket security certification |
| Performance | Bounded local API concurrency and warm browser checks, not production capacity/stress certification |
| CI/release | Exact published commit and its Actions result must be checked at [GitHub Actions](https://github.com/rishi-1603/zomato-refund-fraud-analytics/actions) |
| Deployment identity | Changed behavior checked separately; no whole-commit Streamlit attestation without platform build metadata |

## Documents

[Issues](ISSUE_REGISTER.md) · [Data/SQL/statistics](DATA_AND_METRIC_VALIDATION.md) · [Features](FEATURE_VERIFICATION_MATRIX.md) · [Security](SECURITY_AUDIT.md) · [Release checklist](RELEASE_CHECKLIST.md)

## Verdict

**READY WITH DISCLOSED LIMITATIONS for the checked portfolio-demonstration scope**, contingent on the final pushed commit passing CI. Not a claim of clinical validity, real fraud detection, realized savings, exhaustive accessibility, or production-scale reliability.

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
