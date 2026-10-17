# Ascension Log — Zomato Refund & Fraud Analytics

## U1 — Fraud-ring network layer (real attributes, honest null result)

**Status:** done — 20 tests, 80 baseline + 20 = 100 passing

### What was built
`scripts/network_analysis.py` builds three bipartite networks from **real** dataset
attributes (no synthetic device layer was needed):

| Layer | Attribute | Components | Rings (3+) |
|---|---|---|---|
| shared_delivery_person | Delivery_person_ID | 9,892 | 0 |
| shared_restaurant_cell | restaurant geo (~1 km) | 8,959 | 27 |
| shared_drop_cell | drop-location geo (~1 km) | 9,836 | 12 |

Edges require **2+ shared orders** (one shared order is noise).

### The finding (published as-is)
**High-risk customers do NOT cluster on shared delivery people beyond chance.**
Permutation test, 200 label shuffles, seed 42:
- observed clustering: **2.0699%** of high-risk pairs linked
- chance: **2.1484%** (95th pct 2.3754%)
- **p = 0.76**

On this dataset refund abuse is an **individual-level** signal, not a network-level
one. That is the honest answer, and forcing a ring narrative would have been
manufacturing a story the data does not support.

### Why component size alone is misleading
The first run produced a **788-customer "ring"** on the restaurant layer. It is a
busy area, not a ring. Added a **density screen**: every component is scored by
excess refund rate over the dataset baseline (7.9%) and ranked by excess, never by
size. The 788-customer blob correctly drops out; the top candidate is **C0058**
(5 customers, 20.7% refund rate, **+12.8 pp**, 1 High-risk member = **6.64x** lift).

### Honesty notes carried into the report
- Edges are shared-attribute **associations**, never proof of collusion.
- Delivery attributes are real (public Kaggle); the refund layer is synthetic and
  disclosed. Ring structure is measured on real co-occurrence with synthetic labels.
- Components are a **screening device for human review**, not an accusation.

### Performance fix
The permutation test first took **160 s** in the test suite. Rewrote the statistic to
use adjacency sets (O(k²) per shuffle instead of O(all pairs)) and cached the pair
set — **8 s**, identical output.

---

## U2 — Alert Economics Engine (Day 2)

### The question
A fraud alert is not free. Every alert costs analyst review time; every false
positive costs customer goodwill. Finding fraud is a model question — **which
alerts to make is an economics question.**

### What was built
| File | Purpose |
|---|---|
| `scripts/alert_economics.py` | Prices every alert policy (tier thresholds + top-k% budgets) with an explicit cost model; computes break-even precision and a sensitivity grid |
| `tests/test_alert_economics.py` | 13 tests pinning every published number + economic identities |
| `reports/alert_economics.json/.md` | The decision artifact |

### Verified findings (pinned by tests)
- **Recommended policy: alert High + Medium tiers (115 alerts)** — net **₹92,125**, ROI 3.06
- Alerting everyone (279) nets less (**₹65,006**) — the extra 164 alerts destroy ₹27k of value
- High tier alone: 8 alerts, **100% precision**, net ₹8,274
- **Break-even precision = 28.2%** — the single number an ops team needs: below
  this hit rate the alert program loses money at base assumptions
- The engine reuses the dashboard's `build_risk_table`, so economics cannot
  drift from the product score

### Bugs caught during this work (disclosed)
1. A dead helper (`alert_budget_curve`) had an index bug (`reset_index` breaking
   mask alignment) — caught in self-review, deleted before first run. The
   inlined version in `run()` is covered by tests.

### Regression check
`pytest tests/` → **113 passed**. All 100 original tests untouched and green.
