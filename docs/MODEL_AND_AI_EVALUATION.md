# MODEL & AI EVALUATION — Zomato

## Systems compared
1. **Rule score** (4 interpretable signals, weighted 0-1).
2. **Logistic regression** on the same signals.
3. **Gradient boosting** on the same signals.

## Evaluation chain
| Stage | Method | Finding |
|---|---|---|
| Discrimination | ROC-AUC + PR-AUC, 5-fold OOF | 0.942 / 0.961 / 0.978 |
| Operational head | precision@8 and @20 | 100% for ALL three — the AUC gap is in the ranking tail |
| Coverage | funnel audit | 43.96% of planted abusers covered; 160 invisible |
| Calibration | tier event rates | High 1.0 / Medium 0.87 / Low 0.18 |
| Errors | FP/FN catalogs by volume band | 1-order noise FPs; saturation ties at 1.000 |
| Robustness | weight sensitivity | Spearman rho > 0.95 — ranking is stable |

## Honest verdict (published)
Keep the rule-based triage (interpretability + proven head performance), fix the
eligibility funnel (the real coverage bug), ship the hybrid where ML adds
coverage. Do NOT market this as validated fraud detection.

## Limitations
Synthetic planted labels (behaviour drawn from the label); investigation capacity
modeled, not real; no live fraud ops feedback loop.

## Interview defense
"When is a rule-based score better than ML?" · "PR-AUC vs ROC-AUC?" · "What does
ML actually buy you here?" (reports/interview_prep.md, section 11)
