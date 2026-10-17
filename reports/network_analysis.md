# Fraud-Ring Network Analysis

**9,895 customers · 1,320 delivery people · 45,584 orders · ₹974,344 in refunds**

## What the networks show

| Layer | Components | Rings (3+ customers) | Largest group | Refund ₹ inside rings | Share of all refunds |
|---|---|---|---|---|---|
| shared_delivery_person | 9,892 | 0 | 2 | ₹0 | 0.0% |
| shared_restaurant_cell | 8,959 | 27 | 788 | ₹113,156 | 11.6% |
| shared_drop_cell | 9,836 | 12 | 9 | ₹6,626 | 0.7% |

## Why component size alone is misleading (the density screen)

Raw connected components over-merge. One restaurant cell produced a 788-customer group that is simply a busy area, not a ring. A component only matters if its refund behaviour is **unusual for its size**, so every component is scored against the dataset baseline and ranked by excess refund rate — never by size.

| Layer | Components screened | Above baseline | 10pp+ above baseline | Max excess | ₹ in 10pp+ components |
|---|---|---|---|---|---|
| shared_restaurant_cell | 27 | 12 | 2 | +12.8 pp | ₹3,710 |
| shared_drop_cell | 12 | 5 | 1 | +14.3 pp | ₹814 |

### Top components by excess refund rate (all layers)

**shared_restaurant_cell**

| Ring | Customers | Refund rate | Baseline | Excess | ₹ exposure | High-risk members | High-risk lift |
|---|---|---|---|---|---|---|---|
| C0058 | 5 | 20.7% | 7.9% | +12.8 pp | ₹3,067 | 1 | 6.64x |
| C0178 | 3 | 18.8% | 7.9% | +10.9 pp | ₹643 | 0 | 0.0x |
| C5090 | 3 | 16.7% | 7.9% | +8.8 pp | ₹384 | 0 | 0.0x |
| C1092 | 11 | 15.1% | 7.9% | +7.2 pp | ₹2,659 | 0 | 0.0x |
| C0411 | 4 | 13.0% | 7.9% | +5.2 pp | ₹483 | 0 | 0.0x |

**shared_drop_cell**

| Ring | Customers | Refund rate | Baseline | Excess | ₹ exposure | High-risk members | High-risk lift |
|---|---|---|---|---|---|---|---|
| C0663 | 3 | 22.2% | 7.9% | +14.3 pp | ₹814 | 0 | 0.0x |
| C0739 | 5 | 16.7% | 7.9% | +8.8 pp | ₹704 | 0 | 0.0x |
| C0321 | 7 | 11.8% | 7.9% | +3.9 pp | ₹1,512 | 0 | 0.0x |
| C0473 | 8 | 10.5% | 7.9% | +2.6 pp | ₹1,534 | 0 | 0.0x |
| C0425 | 4 | 9.1% | 7.9% | +1.2 pp | ₹481 | 0 | 0.0x |


## The honest test: does risk actually cluster?

Any 300 customers out of 10,000 will share delivery people by chance — each driver handles ~34 orders. So the question is not *whether* high-risk customers share drivers, but how much **more** they share than random label assignment produces (200 shuffles).

| Measure | Value |
|---|---|
| High-risk customers | 298 |
| Observed clustering (share of high-risk pairs linked) | **2.0699%** |
| Chance clustering (null mean) | 2.1484% |
| 95th percentile of chance | 2.3754% |
| **p-value** | **0.76** |

**Verdict.** No evidence that High-risk customers cluster on shared delivery people beyond what chance produces — the refund signal is individual-level on this dataset, not network-level.

## Honesty notes

- Edges are shared-attribute associations, not evidence of collusion. Sharing a busy delivery person is normal behaviour.
- Delivery attributes are real (public Kaggle dataset); the refund layer is synthetic and labelled as such in the README.
- Connected components are a screening device for human review, never an accusation. A ring is a group worth looking at, not a group that is guilty.

## Reproduce

```bash
python scripts/network_analysis.py
```
