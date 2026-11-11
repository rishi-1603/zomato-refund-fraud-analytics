# UI implementation and regression report

Scope: presentation only. No analytical logic, filter behaviour, data or calculation was changed. Baseline: `BASELINE_INVENTORY.md` and `baseline_app_state.json` (commit `b87f789`).

## 1. Changes made

| # | Change | Where | Effect on numbers |
|---|---|---|---|
| 1 | Header chip: "Delivery data: public · Refund layer: synthetic" | `dashboard/app.py`, header | None |
| 2 | Refund Patterns KPI label "Total refund exposure" → "Refund exposure, all customers" | Refund Patterns tab | None (₹974,344) |
| 3 | Investigation KPI label "Flagged accounts" → "Flagged customers" | Investigation tab | None (279) |
| 4 | Investigation KPI label "Total refund exposure" → "Refund exposure, flagged customers" | Investigation tab | None (₹377,892) |
| 5 | Pie chart "Flagged customers by city type" → horizontal bar, same aggregated counts | Investigation tab | None |
| 6 | Pie chart "Order mix by type" → horizontal bar "Order mix by type (orders)", same counts | Delivery Context tab | None |
| 7 | README rewritten to the brief's structure, with verified figures only | `README.md` | Documentation only |

The Overview KPI "Refund exposure" was kept unchanged because an existing test (`tests/test_kpi_engine.py`) depends on that label.

## 2. Regression checks

| Check | Result |
|---|---|
| App loads with default filters | 0 exceptions, 0 errors |
| Tabs | Same five tabs, same order |
| KPI cards | 28 before, 28 after. Every value identical, in the same order |
| Label changes | Exactly three, as listed in §1 |
| Buttons and subheadings | Identical |
| Test suite (`pytest`) | 186 passed |
| Analytical code and data | Not modified |

## 3. Not verified in this environment

- **Visual rendering.** The sandbox cannot run a browser, so no screenshot was captured. The layout and colours of the new bar charts have not been seen by a person. Check them on your machine before publishing.
- **Hosted app.** The Streamlit Cloud link could not be reached from the sandbox.
- **Filter behaviour in the browser.** Filters were not clicked through. The AppTest check covers load and state only.
- **Optional LLM narration.** Not run (no API key).

## 4. Known issues intentionally not changed

1. The Overview "Refund exposure" (₹974,344) and the Refund Patterns "Refund exposure, all customers" (₹974,344) are the same figure under two labels. This is consistent, but worth merging into one card in a later pass.
2. Reports use "Rs." and the app uses "₹". The app is consistent. Harmonising the report text is a documentation task.
3. The dark theme (`.streamlit/config.toml`) was kept as chosen. Spacing and typography were not otherwise refined.
4. `dashboard/app.py` is still one large file (about 1,400 lines). Moving presentation helpers into their own module is a refactor, not a presentation change.
5. The `Time_taken` and weather charts are unchanged.

## 5. Before and after

- Before: 2 pie charts; two different cards labelled "Total refund exposure" on different tabs; "Flagged accounts" on one tab and "Flagged customers" on another.
- After: 2 horizontal bar charts with the same data; each exposure card names its scope; one name for the flagged count.

Screenshots were not regenerated (see §3). The screenshots in `docs/screenshots/` predate these changes.
