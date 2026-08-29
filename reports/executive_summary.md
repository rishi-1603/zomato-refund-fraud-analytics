# Executive Summary
### Zomato Refund Fraud Risk Analytics — Fraud-Team Brief
*Dataset: 45,584 real delivery orders + synthetic refund layer · 10,000 customers*

> **Read me first:** One page, non-technical. Methodology: `reports/methodology.md`.
> **Critical caveat:** the refund behaviour (and therefore the "fraud") is
> **synthetic**, planted by the data generator. The delivery data is real
> (public Kaggle Zomato dataset); the refund columns are generated on top of it.

---

## 1. What was the problem?
Platforms refunding abusive claims lose money twice — the refund itself and the
margin on the order. Reviewing every refund manually doesn't scale, and blocking
customers without evidence destroys trust. The fraud team needs a **ranked,
explainable watchlist**: who to investigate first, and why.

## 2. What was built?
An end-to-end pipeline: refund-layer generation (seeded) → EDA → customer-level
risk scoring (4 behavioural signals) → SQL validation queries → interactive
dashboard (Streamlit + Power BI) → **validation of the score against the planted
ground truth** (the step most projects skip).

## 3. What the score achieves (validated, not assumed)
| Metric | Value |
|---|---|
| High-tier precision | **100%** — every customer in the top tier is a planted abuser |
| In-pool ranking (AUC) | **0.942** |
| **End-to-end recall** | **2.7%** — the funnel catches only 8 of 299 planted abusers |

**The honest headline:** the score is excellent at *ranking within the pool it
scores*, but the ≥5-order eligibility filter drops **56% of planted abusers
before scoring begins** (the data averages ~4.6 orders/customer). A production
design must score every customer with ≥1 refund and report end-to-end recall —
this is the project's most important lesson, and it's quantified in
`reports/score_validation.md`.

## 4. Top insights
1. **Refund abuse is concentrated**: 279 customers (2.8% of all) exceed 30%
   refund rate — and 131 of them are planted "high-risk" (47% of the pool).
2. **Repetition is the tell**: planted abusers reuse "Item Not Received" /
   "Wrong Item" (planted by design — in real data, reason-repetition is a
   classic script signal).
3. **Thresholds are decisions**: every cutoff (≥5 orders, >30% rate, >70 score)
   trades coverage against precision — and each tradeoff is now measured.

## 5. Recommended actions (on real data)
| Action | Owner | KPI |
|---|---|---|
| Investigate the High tier first (100% precision in this data) | Fraud team | Confirmed-abuse rate per investigation |
| Lower the eligibility filter to ≥1 refund; re-score everyone | Analytics | End-to-end recall |
| Require manual review above a refund-rate threshold instead of auto-approving | Ops | Refund loss rate |

## 6. What must NOT be done
No automated customer bans from this score. A flag means *investigate*, never
*guilty*. The score is uncalibrated, the refund layer is synthetic, and
false-positive cost (angry genuine customers) is as real as fraud loss.
