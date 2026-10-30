# Feature verification matrix

2026-10-30. PASS applies to the stated workflow, not every combination of inputs. Fresh production screenshots are genuine browser captures.

| Feature | Check | Status / boundary |
|---|---|---|
| Four tabs | Overview, Refund Patterns, Investigation, Delivery Context | PASS in browser |
| City filter | Metro-only KPI=34,087; stale header found and corrected | PASS in regression and live browser: header and KPI both 34,087 |
| Reset | Restored 45,584-order scope | PASS in browser |
| Investigation export | Downloaded and parsed CSV with 279 rows | PASS in browser |
| Investigation evidence | Ran selected customer investigation and observed evidence panel | PASS; narration separately unverified |
| Benchmark CLI | Fresh subprocess without PYTHONPATH | PASS; repaired path-order bug |

## Accessibility
axe scans use WCAG2A/AA and WCAG2.1AA tags. Measured patch verification has zero detected violations at 1440×900 and 390×844, with 2 incomplete rule groups still requiring manual review. Live post-push scans also reported zero detected violations in the tested desktop/mobile states; incomplete rules remain manual-review items.
Keyboard focus smoke checks are not a screen-reader walkthrough. Not all chart semantics, every hidden state or assistive-technology behavior is certified.

## Performance
Warm browser rendering was observed; fixed waits used for UI screenshots are not latency measurements. A local API test used 50 read-only requests at concurrency 5: 0 errors, median 54.295 ms, p95 103.5 ms in this sandbox. This does not establish Streamlit session capacity, production cold-start bounds or real-user service levels.

## Not tested exhaustively
Every filter permutation, provider outage/rate-limit scenario and arbitrary question; unrestricted LLM narration; sustained production stress and real screen-reader behavior.
