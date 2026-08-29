# Key Decisions Supported
### Decision log — evidence → action → owner → KPI

> Illustrative (synthetic fraud layer). The structure transfers to a real
> fraud-program engagement.

---

## Decision 1 — Investigate the High tier first
| Field | Detail |
|---|---|
| **Problem** | Fraud team can review only N accounts per week — which first? |
| **Evidence** | High tier (score >70) is 100% precise against planted labels (8/8 are planted abusers); AUC 0.942 in-pool |
| **Recommended decision** | Work the High tier top-down; batch-review the Medium watchlist weekly |
| **Owner** | Fraud investigations lead |
| **KPI** | Confirmed-abuse rate per investigation; review throughput |
| **Cost of inaction** | Review effort spread evenly; genuine abuse sits unreviewed |

## Decision 2 — Fix the coverage gap before production
| Field | Detail |
|---|---|
| **Problem** | The eligibility funnel drops most abusers before scoring |
| **Evidence** | Only 131/299 planted abusers (44%) reach the pool; end-to-end recall 2.7% |
| **Recommended decision** | Score every customer with ≥1 refund; keep the ≥5-order rule only for the *final tiering*, and report end-to-end recall in every review |
| **Owner** | Analytics |
| **KPI** | End-to-end recall at fixed review capacity |
| **Expected outcome** | Same review effort, materially more abuse caught |

## Decision 3 — Human review always in the loop
| Field | Detail |
|---|---|
| **Problem** | Automation tempting: auto-reject refunds for high scores |
| **Evidence** | MinMax score is pool-relative and uncalibrated; false positives punish genuine customers (whose refunds may be caused by restaurant failures, not abuse) |
| **Recommended decision** | Score queues work; only confirmed investigations change customer treatment |
| **Owner** | Ops + Fraud policy |
| **KPI** | False-positive complaint rate |
| **Cost of inaction** | Trust erosion; support costs; churn of good customers |

## Decision 4 — Track the score over time, not once
| Field | Detail |
|---|---|
| **Problem** | Scores re-normalize per pool; abusers adapt |
| **Evidence** | MinMax scaling makes cross-period comparison invalid by construction |
| **Recommended decision** | Freeze thresholds in absolute terms for ops; recalibrate quarterly; monitor tier-size drift as an abuse-pressure indicator |
| **Owner** | Analytics |
| **KPI** | Tier-size stability; confirmed-abuse rate trend |
