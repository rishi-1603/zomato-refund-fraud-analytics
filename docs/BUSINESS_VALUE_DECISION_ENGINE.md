# Business value & decision record — Refund review

## Business question

Given a limited investigation capacity, which flagged customers are selected under the existing score and what might a review policy cost under explicit assumptions?

The **Decision & Value** tab uses the current filtered eligible-customer queue. The existing eligibility rule is at least five orders and a refund rate above 30%; scores are computed on the full source population and are pool-relative, not calibrated fraud probabilities. City, volume band, risk tier and last-order-date filters select **customers**. Their order/refund totals and exposure remain full-history customer aggregates; the date control is not an order-transaction window.

## Scope, controls and calculations

The decision engine checks required columns, unique customer IDs, finite nonnegative exposure/score values, integer order/refund counts, score bounds and refunds not exceeding orders. It sorts by score descending and customer ID ascending for deterministic ties, then selects at most the specified capacity. It independently reconciles selected customer count, refund count and historical exposure with a fixed, query-only in-memory SQLite query. It does not execute generated SQL or check every possible data issue. Empty selection is allowed; break-even is unavailable if selected exposure is zero.

User-supplied values:

- capacity and cost per reviewed customer;
- assumed share of selected historical exposure that could be recovered;
- action, decision status, success KPI and validation plan.

For low/base/high recoverable shares of 0.5×/1×/1.5× the input (capped at 100%):

```
assumed recovery = selected historical exposure × assumed recoverable share
review cost = selected customers × assumed cost per review
modeled net = assumed recovery − review cost
break-even share = review cost / selected historical exposure
```

The share and review costs are assumptions. The model does **not** use planted labels, include all possible friction costs, estimate uncertainty, prove a flag is fraud or quantify realized recovery/savings. A break-even share above 100% is displayed as such rather than silently clamped. The review queue CSV contains synthetic customer IDs; the aggregate JSON does not include them.

## Decision record

A proposed/approved/deferred status, effective sidebar filter context, follow-up plan and optional user-entered outcome note can be downloaded as versioned JSON. Filter context is recorded from UI selections; it is not an independent reconstruction of all data transformations. `observed_outcome` is null unless the user enters a note, which is explicitly marked unverified. The app does not persist decisions on a server, validate follow-up evidence, assign cases or implement account actions; user-managed history files can be exported and re-imported. Changing the filtered queue clears the previous in-session snapshot. Do not include sensitive information in notes.

The existing AI investigator is separate from the calculator. Deterministic evidence remains available without credentials; optional provider prose is not validated and needs human review. Provider failures return a safe message rather than raw exception text. The existing authored benchmark is not a 30–50-question unrestricted-language or provider evaluation.

## Verify

```
python -m pytest tests/test_business_decision_engine.py tests/test_business_decision_ui.py -q
```

These tests check queue selection, ties, arithmetic, invalid/empty cases, source reconciliation and Streamlit scope changes. They do not establish real fraud detection, savings or full accessibility.

## Decision history and follow-up

The tab now supports adding multiple submitted snapshots to a session history, entering a manually observed metric, unit, optional baseline, date and evidence note, and downloading a bounded versioned JSON history. Re-import explicitly replaces the current session history. Imports and user-entered outcomes are unverified; the difference from a user-supplied baseline is arithmetic only, not a causal effect or verified saving. It is not a server-side, authenticated or multi-user approval system. Do not use real customer identifiers or sensitive notes in these files.

## Bounded deterministic question benchmark

The new **Ask the selected queue** control supports a small exact set of queue count/exposure and per-customer order/refund/rate/exposure/score questions. Questions naming customers outside the filtered queue, asking for unsupported causal claims, multiple metrics or fraud verdicts are refused. It uses deterministic computation and the scoped SQLite/pandas check, not an LLM or arbitrary SQL. The existing optional AI investigator narration is a separate, unvalidated provider path.

Run `python scripts/decision_copilot_eval.py` to evaluate 49 authored questions: five metric templates for each of five customers, four queue totals and 20 refusal cases. Expected counts/amounts are independently recomputed from raw order rows and scores are checked against the committed risk table. Per-query p50/p95 is measured after data load in the local process; there are no external provider calls or provider charges, while infrastructure cost is not measured. This is a narrow template benchmark, not a test of arbitrary language or provider hallucinations.
