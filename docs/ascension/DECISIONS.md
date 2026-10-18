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

---

## U3 — Drift / Monitoring Console (Day 2)

### The question
The alert policy's economics assume the score's inputs hold still. What watches
that assumption?

### What was built
| File | Purpose |
|---|---|
| `scripts/drift_monitor.py` | Weekly PSI (numeric + categorical) vs a reference window, refund-rate deltas, per-week verdicts, explicit retrain trigger |
| `tests/test_drift_monitor.py` | 10 tests: real-stream pins + **injected-drift tripwire tests** |
| `reports/drift_monitor.json/.md` | The monitoring artifact |

### Verified findings (pinned by tests)
- Reference window: 7,242 orders (2022-02-07→02-20), refund rate 7.29%
- 6 monitoring weeks: **all STABLE**, max PSI 0.0129 (thresholds: <0.10 stable, >0.25 significant)
- Refund rate moves <2pp in every week
- **Honest result: the seeded generator is stationary.** A console that prints
  STABLE on stable data proves nothing by itself — so the test suite injects a
  1-SD distribution shift and a category replacement and **requires the PSI
  grade to go significant**. The tripwire is proven, not assumed.
- Explicit retrain rule printed in the report: 2 consecutive weeks of any
  feature PSI > 0.25 → rebuild the score before trusting precision again.

### Bugs caught during this work (disclosed)
1. `psi_categorical` crashed on NaN + mixed str/float categories
   (`TypeError: '<' not supported between str and float`). Fixed by coercing
   NaN to a `"missing"` bucket — which is also the correct drift semantics.
2. `psi` now drops NaNs before binning (the `multiple_deliveries` column has
   missing values); histogram edges on NaN input are undefined.

### Regression check
`pytest tests/` → **123 passed**. All previous tests untouched and green.

---

## U4 — Investigator Eval + External Real-Data Validation (Day 2 final)

### What was built
| File | Purpose |
|---|---|
| `evals/investigator_benchmark.json` | 6 answerable + 6 unanswerable cases (real suspect IDs verified against fraud_suspects.csv) |
| `scripts/investigator_eval.py` | Hallucination audit: every returned number RECOMPUTED from raw CSV; refusal correctness; schema guardrail (no verdict fields) |
| `scripts/external_validation.py` | Provenance audit (real vs synthetic columns), real-column findings re-check, real external drift validation |
| `data/external/flights.csv` | Committed real dataset (seaborn-data, BSD-3): 144 months of airline passengers |
| tests | 13 pins across both engines |

### Verified findings (pinned by tests)
- **Investigator: 6/6 grounded · 6/6 refused · 0 fabrications · schema clean → PASS**
  (unknown IDs and unflagged customers refuse with errors — never a score from thin air)
- **Provenance: 20/24 columns (83%) are the REAL public dataset**; only the 4
  refund-layer columns are synthetic — the "how much is real?" question gets a table
- Real-column findings hold without the synthetic layer: traffic→time monotonic
  (20/27/27/31 min), worst weather Cloudy (28 min), ratings mean 4.634
- **Real external drift validation: PSI 11.88 on airline passengers 1949–60 →
  tripwire FIRES on real drift** — the monitoring method validated where the
  stationary synthetic stream could not

### Bugs caught during this work (disclosed)
1. The eval's first draft guessed suspect IDs (CUST00170 etc.) — 0/6 "failures"
   were the benchmark's fault, not the investigator's. Fixed by using real rows
   of fraud_suspects.csv. Lesson: an eval that guesses its fixtures tests nothing.
2. `psi_categorical` crashed on NaN/mixed types (fixed in U3, re-confirmed here).
3. External dataset fetch #1 (plotly heart.csv) 404'd — the mirror moved. Switched
   to stable sources and committed copies so tests never depend on the network.

### Regression check
`pytest tests/` → **136 passed**.

---

## U5 — README & Presentation Polish (top-5% pass)

### The question
The repo's engineering was top-tier; its FIRST IMPRESSION was not. A recruiter
decides in 3 seconds. What does the page show in those 3 seconds?

### What was built/changed
| Item | Purpose |
|---|---|
| README rebuilt to the 10-section target architecture | Hero strip → 5 numbers → questions → decision-layer results → provenance → dashboard → DS layer → verification → reproduce → evidence → limitations |
| `docs/screenshots/alert_policy_net_value.png` | Chart generated from reports/alert_economics.json: alerting more is worth less |
| `docs/screenshots/weekly_psi_strip.png` | Chart generated from reports/drift_monitor.json: weekly PSI vs thresholds |
| Evidence section | 8 flagship reports pinned, each with the question it answers |
| Verification section | 136 tests, tripwire proofs, split scoring, bugs-found pointer (DECISIONS.md) |
| Test count corrected | README claimed 80 tests (stale) → 136 |

### Design decisions
1. The 5-numbers block goes ABOVE the fold: ₹92,125 · 28.2% · p=0.76 · 0 fabrications · 83% real.
2. The scope-of-validity table moved from a report into the README itself —
   the trust differentiator should not require a click.
3. Charts are generated FROM the committed JSON artifacts, so they can never
   drift from the tested numbers.
4. The critical data notice (synthetic layer disclaimer) stays prominent.

### Regression check
Docs + assets only; `pytest tests/` → 136 passed unchanged.
