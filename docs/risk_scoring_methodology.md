# Risk Scoring Methodology
### How the refund-fraud risk score is computed (and why)

> This document is referenced by `dashboard/app.py` and defines the exact
> methodology used by the notebook, the dashboard, and
> `scripts/validate_risk_score.py` — all four stay in sync by design.

---

## 1. Objective

Prioritize *refund-abuse investigation effort*: rank customers whose refund
behaviour is statistically unusual, so a fraud team reviews the most suspicious
accounts first. The score is **triage support, not a fraud verdict** —
every flag requires human investigation before any action.

## 2. Eligibility (Stage 1 — the funnel)

A customer enters the scored pool only if:

| Rule | Rationale | Known cost |
|---|---|---|
| **≥ 5 total orders** | Enough history for a refund *rate* to mean anything | Excludes ~56% of planted high-risk customers in the synthetic data (see `reports/score_validation.md`) — a documented coverage limitation |
| **Refund rate > 30%** | Only customers whose refund rate is already anomalous | Pre-selects on refund rate, which also receives 40% weight in the score (partially circular by design — this is a triage score, not an independent detector) |

## 3. Signals (Stage 2 — the score)

| Signal | Definition | Weight | Intuition |
|---|---|---|---|
| **Refund rate** | refunds / orders × 100 | **40%** | The core abuse indicator |
| **Reason repetition** | share of refunds sharing the customer's most common reason | **30%** | Script-like behaviour: real complaints vary, scripts repeat |
| **Refund frequency** | refunds per day between first and last refund | **20%** | Burst behaviour: abuse is concentrated in time |
| **Reason length** | average characters of the refund reason | **10%** | Template/copy-paste complaints tend to be uniform |

Each signal is min–max scaled to 0–100 across the eligible pool, then combined
with the weights above into `Fraud_Risk_Score` (0–100).

## 4. Risk tiers

| Tier | Score | Operational meaning |
|---|---|---|
| **High** | > 70 | Investigate first |
| **Medium** | 40–70 | Watchlist |
| **Low** | ≤ 40 | Routine |

## 5. Validation

The refund data is synthetic and its generator *plants* each customer's risk
category (3% High / 7% Medium / 90% Low) before generating behaviour.
`scripts/validate_risk_score.py` recovers those planted labels (seeded,
verified 100% against the committed dataset) and measures the score:

| Metric | Value |
|---|---|
| Precision of the High tier | **100%** (all 8 are planted fraudsters) |
| End-to-end recall (all planted High) | **2.7%** |
| In-pool AUC | **0.942** |

**Honest reading:** the score ranks excellently *within the pool it scores*,
but the ≥5-order eligibility filter removes over half of the fraudsters before
scoring begins, and the conservative >70 tier threshold lets most of the rest
through. A production design would score all customers with ≥1 refund and
report end-to-end recall. Full details: `reports/score_validation.md`.

## 6. What this score is NOT

- Not a probability of fraud (uncalibrated, composite heuristic)
- Not evidence of wrongdoing — a flag means "investigate", never "guilty"
- Not validated on real refund data — the synthetic layer plants the signal
