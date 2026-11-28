# Food-Delivery Refund Risk & Operations Analytics — Resume Evidence Index
**Repository:** https://github.com/rishi-1603/zomato-refund-fraud-analytics  
**Live Application:** https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/  
**Verification Date:** 2026-11-28  
**CI Test Status:** 222 Passing Tests (100% Passing)

---

## 1. Resume Claim Verification Matrix

| # | Resume Claim | Canonical Metric Value | Target Population / Grain | Source File / Implementation | Reproduction Command | Automated Test File | Documented Limitation |
|---|---|---|---|---|---|---|---|
| 1 | **Total Delivery Orders** | 45,584 Orders | Complete raw transaction log | data/processed/zomato_with_refunds.csv, dashboard/kpi_engine.py | pytest tests/test_kpi_engine.py | tests/test_kpi_engine.py | Real public delivery order log enriched with synthetic refund behavioral attributes. |
| 2 | **Customer Population** | 9,895 Observed Customers | Unique customer entities | dashboard/kpi_engine.py | pytest tests/test_kpi_engine.py | tests/test_kpi_engine.py | Real customer ID space from food delivery records. |
| 3 | **Historical Refund Exposure** | ₹974,343.55 (₹9.74L) | Cumulative refund amounts requested | scripts/build_excel_workbook.py, dashboard/kpi_engine.py | python scripts/build_excel_workbook.py | tests/test_excel_workbook.py | Exposure represents requested refund value, not confirmed financial loss. |
| 4 | **Flagged Account Triage** | 279 Accounts (38.78% refund value) | High multi-signal anomaly pool | dashboard/app.py (build_customer_risk_table) | pytest tests/test_kpi_engine.py | tests/test_kpi_engine.py | Heuristic prioritization score; flagged does not equal confirmed fraud. |
| 5 | **Volume-Band Normalization** | 113 of 279 cleared | Accounts with refund rate <= P95 of order-frequency tier | dashboard/app.py (band_refund_rates) | pytest tests/test_kpi_engine.py | tests/test_kpi_engine.py | High order frequency naturally accumulates more refunds; baseline normalization prevents customer insult. |
| 6 | **Prioritized Review Alerts** | 115 High/Med Action Alerts | Thresholded review capacity | scripts/alert_economics.py | python scripts/alert_economics.py | tests/ | Selected based on human investigator review capacity. |
| 7 | **Alert Economics Model** | 115 High/Med reviews, ₹92,125 modelled net value | Trade-off: assumed review cost vs fraud prevention | scripts/alert_economics.py | python scripts/alert_economics.py | tests/ | Model is an economic simulation, not realised savings. |
| 8 | **Drift Monitoring (PSI)** | Weekly Population Stability Index | Feature distributions across 12 weeks | scripts/drift_monitor.py | python scripts/drift_monitor.py | tests/ | PSI threshold < 0.10 indicates stable scoring distribution. |
| 9 | **Automated CI Footprint** | 222 Passing Tests | Unit, regression, & property-based tests | tests/ directory | python -m pytest | GitHub Actions workflow .github/workflows/ci.yml | Full test execution covers edge cases, boundary conditions, and schema sanity. |

---

## 2. Unambiguous Operations Funnel

```
Observed Customer Population: 9,895 Customers (100.0%)
 └── Filtered by Eligibility (>= 5 Orders): 4,734 Eligible Customers (47.8%)
      └── Multi-Signal Anomaly Scoring (Refund Rate, Velocity, Reason Skew):
           └── Eligible Anomaly Pool: 279 Accounts (Driving ₹377,891.92 / 38.78% of Total Refund Value)
                ├── Volume-Band Normalization (<= P95 within order-frequency tier):
                │    └── 113 Accounts (40.5%) -> Cleared as High-Volume Normal Customers (Zero Friction)
                └── Net True Anomaly Queue: 166 Genuine Outlier Accounts
                     └── Operational Capacity Cutoff (Top Risk Scores):
                          ├── High Priority Alerts:    8 Accounts (Immediate Human Review)
                          ├── Medium Priority Alerts:  107 Accounts (Secondary Verification)
                          └── Total Actionable Alerts: 115 High/Med Alerts (8 High + 107 Medium)
```

---

## 3. Standardized Terminology Guide
- **Eligible Anomaly Account:** An account exhibiting multi-signal behavioral risk score above baseline screening threshold (279 accounts).
- **Volume-Band Normalized Account:** An account whose refund volume is statistically expected given its high order volume (113 accounts cleared).
- **Prioritized Review Alert:** An account selected for human investigator action within operational workload constraints (115 accounts).
- **Simulated Risk Outcome:** A probabilistic assessment based on synthetic behavioral attributes—**never referred to as confirmed fraud**.
