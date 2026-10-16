# Error Analysis — Refund-Fraud Detection
### Who the systems miss, who they wrongly flag, and what would fix it

> Failure cases extracted from the rules-vs-ML comparison
> (`scripts/model_comparison.py`, OOF predictions) and the false-positive
> analysis (`scripts/false_positive_analysis.py`). Customer IDs and behaviour
> are real rows from the seeded dataset.

## 1. Where the misses live (planted-High below the top-20 cut)

| Orders | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Missed abusers | 13 | 27 | **60** | **58** | 36 | 30 | 34 | 14 | 4 | 1 | 1 |

**118 of 278 below-the-cut abusers have 3–5 orders** — exactly the zone the
≥5-order eligibility filter and small-sample discounting drop.

## 2. Case type A — abusers invisible to the rule funnel (the structural miss)

| Customer | Orders | Refunds | Refund rate | Reason repetition | Refund amount | Planted |
|---|---|---|---|---|---|---|
| CUST05940 | 4 | 3 | 75% | 100% | ₹1,892 | High |
| CUST04042 | 4 | 4 | **100%** | 75% | ₹2,015 | High |
| CUST00273 | 4 | 4 | **100%** | 75% | ₹2,224 | High |
| CUST04484 | 3 | 3 | **100%** | 67% | ₹1,528 | High |

**Why they are missed:** the ≥5-order eligibility rule never scores them. A
customer who refunds **every one of their first 3–4 orders** is as suspicious as
it gets — and the funnel cannot see them by construction.

**What would fix it:** score every customer with ≥1 refund (the documented
recommendation), with volume-band baselines so 1-of-1 refunds are not treated
the same as 4-of-4.

## 3. Case type B — abusers inside the funnel but ranked below the head

| Customer | Orders | Refunds | Refund rate | Reason repetition | Refund amount | Planted |
|---|---|---|---|---|---|---|
| CUST08630 | 7 | 5 | 71% | 60% | ₹2,804 | High |
| CUST09128 | 11 | 8 | 73% | 50% | ₹4,648 | High |
| CUST05191 | 8 | 6 | 75% | 100% | ₹3,882 | High |
| CUST08010 | 7 | 4 | 57% | 50% | ₹2,082 | High |

**Why they rank low:** on this synthetic data, model scores **saturate at 1.0**
for obvious abusers (the label is near-deterministic) — among ties, ranking is
arbitrary. Capacity numbers at k > 20 *understate* what a model could find:
any tie-breaking rule (e.g., refund amount desc) recovers them.

**What would fix it:** secondary sort key (exposure amount) in the review queue —
a product fix, not a modeling fix.

## 4. Case type C — false-positive drivers (flagged, actually Low)

623 non-abusers have a refund rate above 30%. The extreme cases:

| Customer | Orders | Refunds | Refund rate | Refund amount | Planted |
|---|---|---|---|---|---|
| CUST04978 | 1 | 1 | 100% | ₹103 | Low |
| CUST04405 | 1 | 1 | 100% | ₹155 | Low |
| CUST04392 | 1 | 1 | 100% | ₹212 | Low |
| CUST05196 | 1 | 1 | 100% | ₹139 | Low |

**Why they get flagged (or would be):** 1 refund in 1 order = 100% refund rate —
pure small-sample noise. This is the same failure mode quantified in
`reports/false_positive_analysis.md` (below-baseline customers have a 57.5% FP
rate vs 4.8% above-baseline) and echoed by the churn model's new-customer
blindness: **rates computed on tiny denominators are not evidence**.

**What would fix it:** volume-band P95 thresholds (already specified), minimum
refund count ≥ 3 before the rate is trusted, and never auto-flag on rate alone.

## 5. What this analysis changes

1. **Funnel first, model second.** The single highest-value fix is eligibility
   (score everyone with ≥1 refund) — it recovers case type A, which no model
   can recover while the funnel hides the customers.
2. **Tie-break by exposure** in the review queue (case type B) — free wins.
3. **Band-normalize rates** (case type C) — already the documented
   recommendation; this analysis adds the concrete cases that make the argument
   in a review meeting.

## 6. Limitations

1. Synthetic refund layer; behaviour is generated from the planted label — case
   types reflect generator structure as much as real fraud behaviour.
2. Score saturation at 1.0 makes tail ranking on this data arbitrary; real
   scores would spread and the comparison would be sharper.
3. "Missed" here means "below the chosen cut" — at higher review capacity most
   of these customers surface eventually.
