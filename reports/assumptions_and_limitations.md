# Assumptions & Limitations
### What this project can and cannot tell you

> An interviewer WILL probe these. Answering first is the skill.

---

## 1. The "fraud" is synthetic (read this before anything else)
- The refund columns are **generated**, not observed. The generator assigns
  3% of customers a "High" risk category and then makes them behave abusively
  (70% refund rate, repetitive "Item Not Received" reasons).
- Therefore: **no real fraud was detected, no real Zomato customers are
  implicated, and the found "patterns" are planted by construction.** The
  dataset's delivery/logistics columns are real; the fraud story is a
  simulation built to exercise the method.

## 2. The score has no independent ground truth
- "Fraud" here = planted category, recovered by replaying the seeded generator.
  In production there is no such label — validation comes only from
  investigator outcomes over time.
- The 100% High-tier precision is a property of clean synthetic separation.
  Real abuse is adversarial: abusers adapt once they sense detection.

## 3. Methodological limitations (documented, not hidden)
- **Circularity by design:** refund rate >30% *defines* the scored pool, and
  refund rate is 40% of the score. This is standard triage practice, but the
  score is a *prioritizer within a pre-filtered pool*, not an independent
  detector.
- **Coverage gap:** the ≥5-order rule excludes ~56% of planted abusers (avg
  4.6 orders/customer). End-to-end recall is 2.7% at the High tier — measured
  in `reports/score_validation.md`.
- **MinMax scaling is pool-relative:** scores re-normalize whenever the pool
  changes; a "70" today is not a "70" next quarter.
- **Reason length as a signal** is weak and dataset-specific (planted
  uniformity); at 10% weight it barely moves the score.
- **One row = one order, no temporal ordering of customer journeys** beyond
  dates; no features from order content, payment method, or device.

## 4. Correlation ≠ causation
Nothing here establishes that any behaviour *causes* fraud — the score
identifies statistical anomalies for human review. High refund rate can also
mean a genuinely unlucky customer or a genuinely bad restaurant.

## 5. What CANNOT be concluded
- That any real customer is fraudulent.
- That the score would generalize to real refund data (expect much lower
  precision and messy overlap).
- Any financial-loss figure for a real platform — the refund amounts are
  synthetic rupees.

## 6. Assumptions made explicitly
- The raw public dataset is immutable (CI-enforced).
- The seeded generator (seed=42) defines the single source of truth for the
  refund layer; recovered labels must match the committed data 100%.
- All thresholds (≥5 orders, >30%, >70) are analyst choices, documented with
  their tradeoffs, not derived from optimization.
