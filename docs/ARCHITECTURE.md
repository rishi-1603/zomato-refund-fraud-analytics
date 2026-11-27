# FoodTrust — Architecture

**Platform:** FoodTrust — Food Delivery Fraud, Trust & Marketplace Risk Intelligence Platform
**Style:** Modular, deterministic, evidence-first. No hardcoded KPIs, no unverified LLM claims.

---

## 1. System shape

```
data/raw/ (immutable public delivery dataset)
   │
   ▼
dashboard/kpi_engine.py  ←── pandas, single source of truth (deterministic)
   │
   ├── sql/fraud_queries.sql  ←── same KPIs in SQL, validated against pandas (SQLite)
   │
   ▼
dashboard/app.py  (Streamlit, 5 pages)  ←── sidebar filters (city type, volume band, date, tier)
   │
   ├── dashboard/decision_engine.py     (policy simulation, alert economics)
   ├── dashboard/decision_copilot.py    (deterministic evidence tool)
   ├── dashboard/decision_history.py    (user-managed JSON snapshots)
   ├── dashboard/ai_investigator.py     (AI narrative, optional LLM)
   ├── dashboard/case_management.py     (case lifecycle + audit trail)
   └── dashboard/risk_rules.py          (declarative risk rule registry)

reports/  ←── generated artefacts (reconciliation, drift, sensitivity, external validation, Excel workbook)
tests/    ←── 222 pytest (KPIs, SQL, drift, network, economics, UI, AI, workbook)
docs/     ←── methodology, audits, dictionaries
```

## 2. Data flow

1. **Source** — `data/raw/Zomato Dataset.csv` (45,584 rows, 20 columns, public delivery dataset, immutable).
2. **Synthetic extension** — `data/processed/zomato_with_refunds.csv` (same 45,584 rows + 3 synthetic columns: `Refund_Requested`, `Refund_Reason`, `Refund_Amount`), seed 42. `ground_truth_customer_risk.csv` (10,000 planted labels) for validation only.
3. **KPI layer** — `kpi_engine.py` computes every headline number in pure pandas; `sql/` mirrors the same definitions.
4. **Reconciliation** — `scripts/kpi_reconciliation.py` compares pandas vs SQL across 8 headline KPIs → zero mismatches (verified).
5. **Risk score** — weighted formula (rate 40%, repetition 30%, frequency 20%, reason length 10%), eligibility rule ≥5 orders & rate >30%, uncalibrated, with volume-band baseline context.
6. **Dashboard** — Streamlit, 5 pages, one filter set; every figure traces to `kpi_engine.py`.
7. **Monitoring** — PSI on score inputs (weekly), partial-month suppression, data-quality report.

## 3. Layer responsibilities

| Layer | Responsibility | Key files |
|---|---|---|
| `data/raw/` | Immutable public source | `Zomato Dataset.csv` |
| `data/processed/` | Synthetic extension + ground truth | `zomato_with_refunds.csv`, `ground_truth_customer_risk.csv` |
| `dashboard/kpi_engine.py` | Single source of truth for KPIs | pure pandas, documented bands |
| `dashboard/risk_rules.py` | Declarative risk rule registry | weights, thresholds, rationales, tests |
| `dashboard/case_management.py` | Case lifecycle state machine + audit trail | statuses, transitions, export/import |
| `dashboard/decision_engine.py` | Policy simulation, alert economics | costed review policies |
| `dashboard/decision_copilot.py` | Deterministic evidence tool | 12-case benchmark |
| `dashboard/ai_investigator.py` | Optional LLM narration | disclosed as unverified |
| `sql/` | Business queries mirroring pandas | validated on SQLite |
| `scripts/` | Reproduction, validation, analysis, workbook generation | 19 scripts |
| `tests/` | Unit + integration + data quality | 222 tests |
| `docs/` | Methodology, audits, dictionaries | 40+ files |

## 4. Database posture (Phase A → Phase B)

- **Phase A (current):** SQLite-validated SQL; PostgreSQL-oriented files included. `requirements.txt` lists psycopg2-binary as local-only.
- **Phase B (planned):** PostgreSQL as the runtime database; dbt models under `dbt/models/{staging,intermediate,marts}`; Pandera schema contracts in `src/foodtrust/data/`.
- **Phase C (planned):** Docker Compose orchestrating Postgres + app; CI adds sqlfluff + docker build.

## 5. AI assistant safeguards (already in place)

- Deterministic core answers only from data; optional LLM narration path disclosed as unverified.
- `ai_investigator.py` refuses unanswerable questions (6/6 on benchmark).
- Phase B: read-only DB role, SQL validation (SQLGlot), allow-listed tables, query timeouts, row limits, PII masking.

## 6. Security & privacy

- No credentials committed; `.env.example` only.
- Synthetic data in public demos; no real customer implicated.
- Read-only analytics posture documented in `SECURITY_AUDIT.md` and `SECURITY_AND_DEPENDENCY_AUDIT.md`.

## 7. Known gaps (honest)

1. No PostgreSQL runtime (SQLite only) — Phase B.
2. No dbt project yet — Phase B.
3. No Dockerfile/docker-compose — Phase C.
4. No Pandera contracts — Phase B.
5. No hour-of-day / refund-lifecycle analysis — blocked by source data (order dates only); documented as limitation, optional disclosed synthetic extension in Phase C.
6. `dashboard/app.py` is ~86 KB — core logic is extracted; further splitting is optional Phase C.
7. LLM narration path is not verified in CI — documented as unverified.
