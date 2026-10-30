# Issue register

2026-10-30 follow-up. All listed repairs require full regression; deployment checks are separate.

| Severity | Exact location | Evidence | Root cause | Repair | Verification |
|---|---|---|---|---|---|
| Medium | dashboard/app.py | 11 axe color-contrast nodes on selected filter tags. | White text on #3B82F6 had contrast 3.67:1. | Use darker #2563EB for selected tags. | Browser patch scan clears all detected WCAG-tag violations; source/render regression. |
| High | scripts/investigator_eval.py | Fresh CLI failed ModuleNotFoundError despite imported tests passing. | ai_investigator import ran before dashboard path setup. | Move import after path setup; add subprocess regression without PYTHONPATH. | Direct benchmark PASS and full suite pass. |
| Medium | dashboard/app.py | Filtered Metro KPI was 34,087, but header still said 45,584 in scope. | Header rendered the unfiltered table before filtering. | Render header using orders_f after global filters. | New AppTest asserts 34,087 header and absence of stale population. |
| Medium | scripts/network_analysis.py; sql/baseline_bands.sql | Ambiguous DD-MM parsing and language equating nonsignificance/baseline position with outcomes. | Implicit parsing and over-strong analytical wording. | Set dayfirst=True; disclose no detected network excess rather than absence; remove automatic-deprioritization advice. | Independent 200-shuffle result p=.76 and direct network regeneration. |
| Low | Selected Python/notebook code | 37 selected lint findings at baseline. | Unused imports/locals and unnecessary f prefixes. | Remove dead bindings without changing analytical assertions. | Selected Ruff rules clean; full suite pass. |

## Remaining boundaries
- No real parallel subagent facility was available; sequential specialist workstreams were used.
- Optional external LLM providers require separate credentials and evaluation; deterministic tests are not unrestricted narration tests.
- No complete manual screen-reader/contrast review or production stress certification.
- Revoke any credential exposed in chat or elsewhere. Repository cleanup cannot revoke that credential.
