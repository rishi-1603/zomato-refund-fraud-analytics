# UI redesign — baseline inventory (before any change)

Scope: presentation only. This file records what the existing Streamlit app shows **before** any redesign, so the redesign can be checked against it. No analytical logic was changed to write this file.

Measured on branch `arena/e5f9b9a3-zomato-refund-fraud-analytics` at `f1b1792`:
- Test suite: **186 passed** (`pytest`).
- App load (Streamlit `AppTest`, default filters): **0 exceptions, 0 errors**. Full captured state: `baseline_app_state.json`.

## 1. Pages (5 tabs, all in `dashboard/app.py`)

| # | Tab | Function | Purpose today |
|---|---|---|---|
| 1 | Overview | `tab_overview` | Headline KPIs, "What changed?" insights, top-suspects queue, KPI definitions |
| 2 | Refund Patterns | `tab_refunds` | Where refund money concentrates; reason patterns; refund rate by operating conditions |
| 3 | Investigation | `tab_customer_risk` | Volume-band baseline, flagged review list, AI investigation assistant, "Explain a flag" |
| 4 | Delivery Context | `tab_operations` | Delivery time, rider rating, operating-condition breakdowns |
| 5 | Decision & Value | `tab_decision_value` | Review-capacity scenarios, a deterministic queue question box, decision record, decision history |

Header band (`app_header`), footer (`app_footer`) and a methodology expander in the sidebar sit outside the tabs.

## 2. Filters and interactions

Sidebar, applied across tabs:
- City type (multiselect, default all).
- Customer volume band (multiselect, 5 bands).
- Last order date range (date input).
- Risk tier (multiselect, Low / Medium / High).
- "Reset all filters" button, and a reset button shown when filters remove all rows.

Other interactions: a customer selectbox in Investigation (review list and "Explain a flag"); a button that runs the AI investigation; text inputs and a status selectbox on Decision & Value; three download buttons (review list CSV, decision record JSON, queue CSV).

## 3. KPI cards (28 `st.metric` calls; values at default filters)

Overview:
- Delivery orders 45,584 · Refund rate 7.9% · Refund exposure ₹974,344 · Flagged customers 279 · High-tier flags 8 · Below-baseline flags 113.

Refund Patterns:
- Total refund exposure ₹974,344 · Customers 9,895 · Top 10% hold 75.6% of exposure · Half of exposure: top 292 customers · Avg refund ₹271 · Largest refund ₹800 · Refunds per month 100 · Repeat same reason (≥50%) 89.2% · Median reason repetition 60% · Median refund velocity 0.14/day.

Investigation:
- Flagged accounts 279 · **Total refund exposure ₹377,892** · Avg risk score 35.2 · High risk tier 8 · Flagged above band baseline 166 · Flagged but within band norms 113 · Above baseline (all customers) 400.

Delivery Context:
- Avg delivery time 26.3 min · Median 26 min · Avg rider rating 4.63 / 5 · 90th-percentile delivery time 40 min.

Decision & Value:
- Eligible customers in current queue 279.

**Issues found in this inventory (not fixed here):**
1. "Total refund exposure" is used twice with different meanings: ₹974,344 (all orders, Refund Patterns) and ₹377,892 (flagged accounts, Investigation). The label must change in the redesign. The values must not change.
2. "Flagged customers" (Overview) and "Flagged accounts" (Investigation) show the same 279 with different labels.
3. "Refund exposure" (Overview) and "Total refund exposure" (Refund Patterns) show the same ₹974,344 with different labels.

## 4. Charts (20 `plotly_chart` calls)

- Overview: top-suspects chart, headline comparisons.
- Refund Patterns: concentration (Lorenz-style) curve, reason and flagged-pattern charts, rate-by-conditions charts.
- Investigation: volume-band baseline chart, flagged-customer charts.
- Delivery Context: operating-condition charts.
- Decision & Value: scenario charts.

**Pie charts present (2):** `px.pie` at `app.py` lines ~884 and ~1111. The redesign brief asks to avoid pies. Replacing them is a presentation change, but it must keep the same data.

## 5. Tables and downloads

- `st.dataframe` ×3: flagged review list (styled), scenario table, decision queue.
- Download buttons ×3: review list CSV, decision record JSON, queue CSV.

## 6. Analytical results that must not change

Taken from the app state and README; these are the regression anchors.
- 45,584 orders · 3,596 refund requests · ₹974,343.55 refund value · 9,895 customers.
- Review pool 279 (≥5 orders and refund rate >30%).
- Risk tiers of the 279 review pool: High 8 · Medium 107 · Low 164 (checked by running `build_customer_risk_table` on this commit).
- Eligible review queue 279. Flagged above band P95: 166. Within band norms: 113.
- Committed model-comparison AUCs (rule 0.942, logistic 0.9606, gradient boosting 0.9774) live in `reports/model_comparison_metrics.json`, not on screen.

## 7. Optional AI feature (status)

`ai_investigator.py` calls an OpenAI-compatible API (`OPENAI_API_KEY`) or Gemini (`GOOGLE_API_KEY`). Without a key it falls back to a deterministic summary, and the app shows a notice saying so. The sandbox has no keys, so the live LLM path has **not** been run here. Only the deterministic path is verified.

## 8. Layout and UI problems observed

1. The theme is **dark** (`.streamlit/config.toml`, `base = "dark"`, background `#0A0F1E`). The redesign brief asks for a light workspace (`#F6F8FC`) with navy navigation. This is a design decision, not a bug. It needs your approval before anything changes.
2. Two pie charts (see §4).
3. Duplicate or ambiguous KPI labels (see §3).
4. `app.py` is 1,382 lines in one file. Styling, data, charts and page logic are mixed. The redesign can move presentation helpers into a separate module without changing logic.
5. Each tab has many KPI cards in a row (6 on Overview, 4 on Refund Patterns, 7 on Investigation across several rows). This works against the "too many KPI cards" guidance.

## 9. Functionality that must be preserved

- All five tabs and their content.
- All sidebar filters, the reset buttons and the empty-state handling.
- The flagged review list and its CSV download.
- The "Explain a flag" view and the AI assistant (with its deterministic fallback).
- The decision record and queue downloads and the decision history.
- The methodology expander and the disclosure that the data is synthetic.
