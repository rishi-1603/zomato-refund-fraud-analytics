# FoodTrust — Problem Statement & Business Value

**Platform:** FoodTrust — Food Delivery Fraud, Trust & Marketplace Risk Intelligence Platform
**Positioning:** Independent portfolio platform inspired by food-delivery marketplace workflows. Not an official Zomato system; no access to internal Zomato data; results describe a public delivery dataset with a disclosed synthetic refund layer.

---

## 1. The business problem

A food-delivery marketplace refunds customers when orders go wrong. Refunds are a **service obligation, not an accusation** — but a small share of refund activity can be repeated, patterned, or disproportionate, and reviewing every claim is uneconomical. The real operational question is:

> **Which refund records deserve a human review first, what does that review policy cost, and how do we avoid harming legitimate customers while doing it?**

FoodTrust answers that question end-to-end: measure → compare fairly → rank for review → cost the policy → monitor drift → keep an audit trail. It deliberately distinguishes **confirmed fraud / suspicious behaviour / unusual activity / operational error / legitimate claim** — a flagged record is a *review candidate*, never a verdict.

## 2. Users and the questions each team asks

| Team | Question FoodTrust answers | Where |
|---|---|---|
| Fraud & Risk Operations | Who should we review first, and why exactly? | Risk Investigation, Investigation Workbench |
| Trust & Safety | Is flagged behaviour unusual for this customer's order volume, or just high-volume normality? | Volume-band baseline, Risk Investigation |
| Refund & Dispute Ops | Where does refund value concentrate, by reason and customer? | Refund Reasons (Pareto/Lorenz) |
| Marketplace Ops Managers | Which operating conditions (weather, traffic, riders) associate with refunds? | Operations Analysis |
| Restaurant/Merchant Quality | Do refund patterns cluster around shared restaurant locations or riders? | Network check |
| Finance / Revenue Assurance | What does each review policy net, and what precision does it need to break even? | Policy & Impact, alert economics |
| BI / Analytics | Are the KPIs reconcilable between pandas and SQL? Is anything drifting? | Data Quality, kpi_reconciliation, PSI monitor |
| Product / CX | What is the false-positive exposure — how many flagged customers look normal within their band? | Below-baseline analysis (113 of 279) |

## 3. The twelve problem areas — implemented / partial / gap

Honest mapping (details in `INITIAL_AUDIT.md` §4). Statuses: ✅ implemented · ⚠️ partial · ❌ gap.

| # | Problem | Status | Implementation & business value |
|---|---|---|---|
| 1 | Repeated refund abuse | ✅ | Refund frequency + reason repetition are 50% of the review score. Team action: prioritise repeat claimers for review. |
| 2 | Refund velocity / frequency anomalies | ⚠️ | Repeat-reason and velocity chips on the dashboard. **Limitation:** source data has order *dates*, not timestamps → 24h windows impossible without synthetic events (documented; optional Phase C extension). |
| 3 | Suspicious amount patterns | ⚠️ | Value concentration (38.78% in the review pool), Pareto/Lorenz views. Band-relative rates prevent "big spenders look risky" bias. |
| 4 | Refund reason abuse / repetition | ✅ | Reason repetition scoring; Wrong Item (862) and Item Not Received (594) dominate. No reason is treated as proof of fraud. |
| 5 | Eligibility & policy misuse | ✅ | Explicit, documented eligibility rule (≥5 orders, rate >30%) defines the 279-review pool; policy simulation costs three alternatives. |
| 6 | Merchant / restaurant quality risk | ⚠️ | Network analysis ranks shared restaurant-cell and rider components by excess refund rate. Merchant drill-down page is a Phase B upgrade. |
| 7 | Delivery fulfilment & disputes | ✅ | Operations tab uses **real** public-dataset fields: delivery time, rider ratings, weather, traffic, festival, vehicle condition. |
| 8 | Geographic & time hotspots | ⚠️ | City-type comparisons + monthly trends with partial-month suppression. Hour-of-day analysis blocked (no timestamps). |
| 9 | Repeat entities & connected behaviour | ✅ | Delivery-person permutation test (p = 0.76 → no clustering evidence) — an honest null result, ranked components by excess rate, not size. |
| 10 | Operational refund delays | ❌ | No refund lifecycle timestamps exist in the source. **Documented limitation.** Optional Phase C: disclosed synthetic event extension. |
| 11 | Financial leakage & exposure | ✅ | ₹974,344 exposure, pool holds ₹377,892 (38.78%), policy net-value modelled under labelled assumptions (never "realised savings"). |
| 12 | False positives & customer experience | ✅ | 113 of 279 flagged customers sit at/below their band's P95 — disclosed as descriptive, not a measured FPR. Friction cost in economics model. |

**Stretch capabilities (13–18 of the brief)** — merchant rate-change monitoring (PSI monitor partially covers input drift), approval/rejection consistency (no approval-status field → gap), complaint/support tickets (no field → gap), financial reconciliation (✅ pandas↔SQL, 8 KPIs, zero mismatch), model deterioration monitoring (⚠️ PSI runbook exists).

## 4. Data strategy — what is real, what is synthetic

| Layer | Provenance | Rows | Disclosure |
|---|---|---|---|
| Delivery attributes | Public dataset (`data/raw/`), unmodified | 45,584 | Real public data |
| Customer IDs | Seeded synthetic (seed 42) | 9,895 customers | Disclosed everywhere |
| Refund events/amounts | Seeded synthetic | 3,596 requests, ₹974,343.55 | Disclosed everywhere |
| Risk labels | Planted (Low/Medium/High) | 10,000 customers | Validation-only, disclosed on dashboard |

**Rule enforced:** original and synthetic records remain distinguishable (`DATA_DICTIONARY.md` documents every generated column). Null `Refund_Reason` = **no refund request** — a structural fact, not missing data, and never imputed as "No Refund" for claimants.

## 5. What the business gets (value framing, no inflated claims)

1. **A bounded, fair review queue** — 279 candidates from 45,584 orders, ranked by a transparent score with published weights and an eligibility rule.
2. **Costed policy choice** — High-tier (8 reviews, 100% planted-label precision, ₹8,274 modelled net) vs High+Medium (115 reviews, 87.8%, ₹92,125) vs all-flagged (279, 46.9%, ₹65,006); break-even precision 28.2%. *Modelled, assumption-labelled — not realised savings.*
3. **False-positive visibility** — the same policy view that catches repeat claimers also shows how many flagged customers look normal within their band.
4. **Reproducible governance** — every KPI reconciles pandas↔SQL; every report regenerates from `scripts/`; drift monitor watches the score inputs weekly (PSI).
5. **An evidence-grounded assistant** — the deterministic investigator answers from data and *refuses* unanswerable questions (12-case benchmark: 6/6 grounded, 6/6 refused).

## 6. Non-negotiables carried into the build

- No KPI is hardcoded; every dashboard number traces to `kpi_engine.py` and is pinned by tests.
- A flag is a **review priority**, not a guilt verdict — language and UI enforce this.
- Modelled values are labelled as modelled; planted-label precision is labelled as agreement-with-planted-labels.
- Gaps stay gaps until real data (or a clearly disclosed synthetic extension) fills them.
