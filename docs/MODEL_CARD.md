# FoodTrust — Model Card

**Model / system:** Weighted refund-review scoring + planted-label validation
**Owner:** FoodTrust portfolio project
**Status:** Rule-based primary engine; ML comparison only (no deployed classifier)

---

## 1. Intended use

- **Purpose:** Prioritise refund records for human analyst review in a food-delivery marketplace.
- **Users:** Risk/refund operations analysts. The score is an *input* to their queue, never an automated decision.
- **Out-of-scope:** Automated refund rejection, customer banning, or any irreversible action. The system is advisory.

## 2. System type

This is a **rule-based scoring engine**, not a trained classifier. A logistic-regression / tree comparison (`scripts/model_comparison.py`) is included to demonstrate that the hand-built score is competitive with a learned model on planted labels, and to show when each approach is appropriate.

## 3. Features (inputs)

| Feature | Source | Used in score |
|---|---|---|
| Customer refund rate | `Refund_Requested` rows / customer order rows | 40% |
| Reason repetition | max share of a single reason across the customer's claims | 30% |
| Refund frequency | count of refund-request rows | 20% |
| Reason breadth | distinct refund reasons used | 10% |
| Volume band | order count bucket (1-2 / 3-5 / 6-10 / 11-20 / 21+) | context (not scored) |
| Band P95 rate | 95th percentile rate within band | context (fairness) |
| Network components | shared rider / restaurant-cell / drop-cell excess rate | context (network check) |

## 4. Eligibility rule (must precede scoring)

A customer enters the review pool only if **orders ≥ 5 AND refund rate > 30%**. This is the 279-customer pool. The rule exists because short histories produce extreme rates and the score would otherwise be meaningless.

## 5. Score & bands

- Formula: `0.40·rate + 0.30·repetition + 0.20·frequency + 0.10·breadth`, scaled to 0–100.
- **Uncalibrated** — 70 ≠ 70% probability of anything. The score ranks the pool; it is not a probability.
- Bands: 0–39 Low Risk · 40–69 Review Recommended · 70–100 High Priority Review.
- Thresholds are documented in `dashboard/risk_rules.py` and `docs/risk_scoring_methodology.md`.

## 6. Labels / ground truth

- `ground_truth_customer_risk.csv`: 10,000 customers with planted Low / Medium / High labels (synthetic, seeded).
- Labels exist **only for validation**, are disclosed on the dashboard, and are never presented as real fraud outcomes.
- There are **no confirmed investigation outcomes** in any dataset — precision values measure agreement with planted labels only.

## 7. Evaluation

| Metric | Value | Caveat |
|---|---|---|
| Pool size | 279 | — |
| High-tier customers | 8 | — |
| High-tier precision vs planted labels | 100.0% | 8 reviews; small-n, agreement with planted labels only |
| High+Medium policy precision | 87.8% | 115 reviews |
| All-flagged policy precision | 46.9% | 279 reviews |
| Below-baseline flagged | 113 / 279 | Descriptive; eligibility applied before baseline |
| Network permutation test | p = 0.76 | No clustering evidence beyond chance — reported as null |
| KPI reconciliation | 0 mismatches (8 KPIs, pandas vs SQL) | — |

**Accuracy is not the primary metric** — the dataset is imbalanced and the labels are planted. Precision, false-positive exposure, and policy net value are the reported measures.

## 8. Business cost of errors (from alert economics)

- Assumed review cost: ₹250 / case
- Assumed false-positive friction: ₹100 / customer
- Assumed recovery: 50% of a planted High customer's exposure
- Break-even precision: 28.2%

These are explicit assumptions in `reports/alert_economics.md`, not realised costs.

## 9. Known limitations

1. Labels are planted, not verified — precision is agreement, not real-world detection rate.
2. Score is uncalibrated; cannot be read as a probability.
3. Short-history customers can show extreme rates; mitigated (not removed) by the 5-order floor.
4. No refund lifecycle timestamps → no operational-delay analysis.
5. No real merchant IDs → merchant analysis is by restaurant-cell, not by merchant.
6. No confirmed outcomes → no actual false-positive rate is measurable.
7. LLM narration path is not verified in CI (only deterministic path is).

## 10. Monitoring recommendations

- Weekly PSI on score inputs (`scripts/drift_monitor.py`).
- Re-run reconciliation after any change to `kpi_engine.py` or `sql/`.
- Re-validate thresholds on any new data source.
- Track below-baseline share as a proxy for false-positive exposure.
- Re-run the 12-case investigator benchmark (`scripts/investigator_eval.py`) after any change to `ai_investigator.py`.

## 11. Versioning

- Score version: tied to git commit; weights/eligibility in `dashboard/risk_rules.py` + `dashboard/kpi_engine.py`.
- Any change to weights or thresholds requires a methodology doc update and a test update.
