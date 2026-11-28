> **Historical snapshot.** Numbers here reflect the build at the date recorded below. Current state (2026-11-28): 5-page Streamlit app, 222 passing tests, formula-driven Excel workbook, GitHub Actions CI. Treat README.md at the repo root as the source of truth.

# FoodTrust — Initial Repository Audit

**Date:** 2026-11-20
**Auditor scope:** Full repository inspection before the FoodTrust transformation (Phases A → B → C).
**Repo:** `rishi-1603/zomato-refund-fraud-analytics`

---

## 1. Headline verdict

The repository is **already substantially stronger than a beginner portfolio dashboard**. The transformation brief assumed a basic refund dashboard; the audit found a tested, reconciled, honestly-disclosed analytics product with 188 passing tests. The correct strategy is therefore **upgrade and extend**, not rebuild.

| Area | Finding | Severity |
|---|---|---|
| Test suite | 188 tests pass in CI (`pytest -q`) | Healthy |
| KPI integrity | Deterministic `kpi_engine.py`; no hardcoded dashboard numbers; numbers pinned by `tests/test_kpi_engine.py` | Healthy |
| Data honesty | Synthetic refund layer and planted labels are disclosed in README, data dictionary, and on the dashboard | Healthy |
| Pandas ↔ SQL reconciliation | 8 headline KPIs match, zero mismatches (`reports/kpi_reconciliation.md`) | Healthy |
| Risk language | "Flagged", "review", "risk band" — never "fraudster"; score explicitly labelled uncalibrated | Healthy |
| Branding | Project identity is generic ("Food-Delivery Refund Risk & Operations Analytics") — no FoodTrust identity | Medium |
| Database | SQL validated on **SQLite**; PostgreSQL is aspirational ("PostgreSQL-oriented files included") | High |
| Transformations | No dbt project; business logic lives in Python/pandas, not in versioned SQL models | High |
| Case management | Investigation queue + decision history exist; **no formal case lifecycle** (New → Under Review → Escalated → Cleared/Confirmed → Closed) with audit trail | High |
| Containerisation | `.devcontainer/` only; no Dockerfile / docker-compose | Medium |
| Schema validation | No Pandera (or equivalent) schema contracts | Medium |
| Problem mapping | Rich methodology docs, but no single document mapping the 12 FoodTrust problem areas → implemented / partial / gap | Medium |
| Metric dictionary | `data/metrics.json` semantic layer exists; not surfaced as `docs/METRIC_DICTIONARY.md` | Low |
| App monolith | `dashboard/app.py` is ~86 KB; core logic is extracted (kpi_engine, decision_engine, ai_investigator), so severity is Low | Low |

---

## 2. Dataset verification (recomputed from files, not from README)

| Claim (historical) | Recomputed | Verdict |
|---|---|---|
| 45,584 orders | `data/raw/Zomato Dataset.csv` → 45,584 rows × 20 cols | ✅ Exact |
| 3,596 refund requests | `Refund_Requested == True` → 3,596 | ✅ Exact |
| 41,988 null `Refund_Reason` | 41,988 rows have null reason | ✅ Exact — **and correctly interpreted**: null reason = **no refund request** (row has no claim). Not missing data. Not "No Refund" label fabrication. |
| ~₹9.74 lakh refunds | ₹974,343.55 | ✅ Exact |
| Wrong Item / Item Not Received leading reasons | 862 / 594 (top two of six reasons) | ✅ Exact |
| 279-customer review pool, 38.78% value | Pinned by tests | ✅ Verified by suite |

**Raw source note:** `data/raw/Zomato Dataset.csv` is the public **delivery** dataset (rider, weather, traffic, delivery time). Refund fields (`Refund_Requested`, `Refund_Reason`, `Refund_Amount`), customer IDs, and `ground_truth_customer_risk.csv` (10,000 customers, planted Low/Medium/High) are **synthetic, seeded extensions** — and the README says so explicitly. This matches the transformation brief's rule: *"Keep original and synthetic records distinguishable."* ✅

---

## 3. Component-by-component audit

### 3.1 Data layer — `data/`
- `raw/Zomato Dataset.csv` — immutable public source. ✅ Keep unmodified.
- `processed/zomato_with_refunds.csv` — original 45,584 rows + 3 synthetic columns. ✅ Keep; provenance documented in `DATA_DICTIONARY.md`.
- `processed/ground_truth_customer_risk.csv` — planted labels, disclosed as validation-only. ✅ Keep.
- `claims.json` — verified-claims ledger with CI test counts. ✅ Keep; update test count if suite changes.
- `external/flights.csv` + `data/external/README.md` — used by external-validation script (analogy check). ✅ Keep.

### 3.2 Analytics core — `dashboard/kpi_engine.py`
Pure pandas, documented bands, MoM thresholds, and test-pinned numbers. The docstring itself pins: 45,584 orders / 9,895 customers / ₹974,344 exposure / 279 flagged / 38.78% / 8 high-tier at 100% precision / 113 below-baseline.
**Verdict:** Keep. This is the project's single source of truth and exactly what the master brief demands ("no hardcoded metrics").

### 3.3 Risk scoring
Weighted formula (refund rate 40%, reason repetition 30%, frequency 20%, reason length 10%), explicit eligibility rule (≥5 orders, refund rate >30%), uncalibrated-score disclosure, volume-band baseline comparison (P95 within band).
**Verdict:** Keep. Improve in Phase B by extracting the rule registry into a declarative structure (each rule: description, formula, threshold, rationale, test, limitation) — the methodology doc exists; the registry should live beside the code.

### 3.4 Decision / policy engine
`decision_engine.py`, `decision_copilot.py`, `decision_history.py` + alert-economics sensitivity grid (₹250 review cost, ₹100 friction, 50% recovery — all labelled assumptions; break-even precision 28.2%).
**Verdict:** Keep. Phase B upgrades this into the formal case lifecycle with statuses and an audit trail.

### 3.5 AI investigator
`ai_investigator.py` — **deterministic, no-LLM evidence tool**, benchmarked 6/6 answerable grounded + 6/6 refusals (`reports/investigator_eval.md`). Optional LLM narration path is disclosed as unverified.
**Verdict:** Keep. This already satisfies the master brief's safety philosophy ("never invent figures"). Phase B: keep deterministic core; document the LLM path's safeguards checklist without claiming it is verified.

### 3.6 SQL — `sql/`
3 files (fraud queries, cumulative Pareto, volume-band baselines), validated against pandas on **SQLite**.
**Verdict:** Keep + extend. Phase B adds PostgreSQL execution notes and dbt models. README already lists "Run a PostgreSQL pass" as next step.

### 3.7 Tests — `tests/` (17 files, 188 tests)
Cover KPIs, reconciliation, drift, network, cohorts, economics, decision engine/UI, investigator, data quality.
**Verdict:** Keep. Phase B adds tests for the case lifecycle; Phase C adds CI hardening.

### 3.8 CI — `.github/workflows/ci.yml`
Runs score validation, model comparison, then pytest. ✅ Working.
**Verdict:** Keep. Phase C adds lint/type/data-quality jobs.

### 3.9 Documentation — `docs/` (40+ files)
Unusually complete: release gates, security audits, methodology, PSI runbook, UI redesign records.
**Verdict:** Keep. Add the four missing FoodTrust docs (Problem Statement, Metric Dictionary, Architecture, Model Card) rather than duplicating.

### 3.10 Hygiene
- No credentials committed (checked: `.env.example` only, requirements clean). ✅
- No dead requirements (6 core deps, all used). ✅
- `.gitignore` present. ✅
- No fake screenshots — `docs/screenshots/` and `docs/chart_renders/` match implemented pages. ✅

---

## 4. Gap analysis against the FoodTrust master brief (12 problems)

| # | Problem area | Status in repo | Phase |
|---|---|---|---|
| 1 | Repeated refund abuse | ✅ Implemented (frequency + repetition in score; repeat-reason chips) | — |
| 2 | Refund velocity anomalies | ⚠️ Partial (claim-behaviour velocity chips; no 24h/7d/30d windows — dataset has order dates only, no order timestamps) | B |
| 3 | Amount patterns vs peers | ⚠️ Partial (value concentration/Pareto; band-relative rates) | B |
| 4 | Reason abuse/repetition | ✅ Implemented (reason repetition 30% of score) | — |
| 5 | Eligibility & policy misuse | ✅ Implemented as explicit eligibility rule + policy simulation | — |
| 6 | Merchant/restaurant quality risk | ⚠️ Partial (restaurant-cell network component; no merchant drill-down page) | B |
| 7 | Delivery fulfilment disputes | ✅ Review Operations page (delivery time, riders, weather, traffic) — real columns from the public dataset | — |
| 8 | Geographic/time hotspots | ⚠️ Partial (city-type comparison; time analysis by order date; no hour-of-day — timestamps absent from source) | B |
| 9 | Connected entities | ✅ Network check (riders, restaurant cells, drop cells, permutation test) | — |
| 10 | Operational refund delays | ❌ Gap (no refund lifecycle timestamps in data) | C (documented limitation or synthetic extension) |
| 11 | Financial leakage & exposure | ✅ Implemented (exposure KPIs, policy net-value, reconciliation) | — |
| 12 | False positives & customer experience | ✅ Implemented (below-baseline analysis: 113/279; alert economics; friction assumption) | — |

**Honest scope statement:** Problems 10 (and the hour-of-day part of 8) are **blocked by source data** (no timestamps beyond dates; no refund processing events). Options: document as limitation (chosen for Phase A) or add a disclosed synthetic event extension (optional Phase C).

---

## 5. Data-leakage / integrity checks performed

1. **Train/test separation:** Model comparison script evaluates on held-out split; ground truth is planted per-customer, not per-row leakage of the target into features (features are refund-behaviour aggregates; the label is planted independently). Verified via `scripts/model_comparison.py` + `tests/test_model_comparison.py`.
2. **Eligibility before baseline:** The 279 pool is defined before band comparison; README explicitly notes the 113-below-baseline figure is descriptive, not a measured FPR. ✅ Correct framing.
3. **Partial-month handling:** Final month (to 6 Apr 2022) flagged; change badges suppressed. ✅
4. **No denominator games:** Refund request rate uses distinct orders; refund value uses transaction rows; reconciliation test pins this. ✅

---

## 6. Decision log for the transformation

| Existing element | Decision |
|---|---|
| kpi_engine, risk score, eligibility rule | **Keep** — already meets "no hardcoded KPIs" bar |
| Synthetic disclosures | **Keep and strengthen** in FoodTrust README |
| SQLite-based SQL validation | **Extend** to PostgreSQL pass in Phase B (documented, reproducible) |
| Investigation queue | **Upgrade** to formal case lifecycle in Phase B |
| app.py size | **Accept** for Phase A; core logic already extracted; splitting UI is Phase C optional |
| Missing hour-level / refund-lifecycle events | **Document as limitation** (Phase A); optional disclosed synthetic extension in Phase C |
| "Zomato" naming | **Rebrand to FoodTrust** positioning (independent portfolio platform; public delivery dataset + disclosed synthetic refund layer) |

---

## 7. Audit conclusion

- **Do not rebuild.** 188 green tests, pinned KPIs, honest disclosures, reconciled SQL — deleting this would destroy verified value (violates master rule 12).
- **Do upgrade:** identity (FoodTrust), problem-value mapping, metric dictionary, PostgreSQL/dbt, case lifecycle, Docker, hardened CI.
- **Do not fabricate:** no confirmed-fraud claims, no invented timestamps, no realised-savings language. The repo's existing honesty is its biggest asset — the transformation must raise the ceiling without lowering the floor.
