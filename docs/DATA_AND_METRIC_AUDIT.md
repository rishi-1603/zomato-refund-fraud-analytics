# DATA & METRIC AUDIT — Zomato

## Data provenance
- **Synthetic refund layer** over 45,584 seeded delivery orders; corruption draws
  behaviour FROM the planted label (disclosed in every report). Fraud labels are
  recovered via `recover_ground_truth`, not externally verified.
- Implication stated in reports: measured gaps = method + coverage on this data,
  not real-world superiority of one detector.

## Metric registry (data/metrics.json — canonical)
| Metric | Definition | Pinned value |
|---|---|---|
| ROC-AUC (in-pool) | 5-fold OOF, planted-High labels | rule 0.9422 / LR 0.9611 / GBM 0.9782 |
| PR-AUC | reported for the imbalanced (≈3%) base rate | see reports/model_comparison.md |
| Precision@k | planted-High precision in top-k | P@8 = P@20 = 1.00 (all three systems) |
| Funnel coverage | share of planted abusers inside eligibility funnel | 131/299 = 43.96% |
| Tier event rate | P(planted-High \| tier) | High 1.0 / Medium 0.8692 / Low 0.1829 |

## Audit findings (published)
1. Head parity: at investigation cut sizes all systems tie at 100% precision.
2. 160 planted abusers sit OUTSIDE the funnel — invisible to the rule score.
3. Flat 30% refund-rate threshold fails: 623 non-abusers cross it on volume noise.

## Reproducibility
Seeded generation, importable script functions, CI regenerates the comparison
before tests, exact behavior pinned by tests/test_model_comparison.py.
