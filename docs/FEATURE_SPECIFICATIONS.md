# FEATURE SPECIFICATIONS — Zomato

| Feature | Input | Output | Acceptance (tested) |
|---|---|---|---|
| KPI engine (8 KPIs) | orders/refunds | headline metrics | Python vs SQL: 0 discrepancies |
| Risk score (refund rate, reason repetition, frequency, reason length) | customer behaviour | 0-1 score + tiers | weight sensitivity: Spearman rho > 0.95 |
| Ground-truth recovery | seeded corruption | planted labels | used as validation target (disclosed) |
| Score validation | risk table + labels | tier event rates | High 100% / Medium 86.9% / Low 18.3% |
| Rules-vs-ML comparison | 4 signals + labels | LR/GBM/rule metrics | AUC 0.942/0.961/0.978 pinned |
| Capacity curve | score ranking | captures vs reviews/day | precision@8, @20 pinned (1.0 all systems) |
| Baseline normalization | volume bands | flat-threshold failure map | 623 non-abusers over 30% rate documented |
| Error catalog | OOF predictions | 3 failure classes + fixes | reports/error_analysis.md |
| AI investigation console | case data | investigation view | covered by test_ai_investigator / test_ai_investigation_ui |
| Weight sensitivity | alternative weights | rank stability | sensitivity_analysis.py + tests |

**Explicit non-claim:** this is NOT validated real-world fraud detection. Labels
are planted; findings describe methods and this dataset only.
