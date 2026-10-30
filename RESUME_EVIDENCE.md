# Food-Delivery Refund Risk Intelligence & Operations Analytics — Resume Evidence Index
**Repository:** https://github.com/rishi-1603/zomato-refund-fraud-analytics  
**Live Application:** https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/  
**Verification Date:** 2026-10-30  
**CI Test Status:** 136 Passing Tests (100% Passing)

---

## 1. Resume Claim Verification Matrix

| # | Resume Claim | Canonical Metric Value | Target Population / Grain | Source File / Implementation | Reproduction Command | Automated Test File | Documented Limitation |
|---|---|---|---|---|---|---|---|
| 1 | **Total Delivery Orders** | 45,584 Orders | Complete raw transaction log | data/raw_orders.csv, src/eda.py | python -m src.eda --orders | tests/test_data_integrity.py | Real public delivery order log enriched with synthetic refund behavioral attributes. |
| 2 | **Customer Population** | 9,895 Observed Customers | Unique customer entities | src/feature_engineering.py | python -m src.feature_engineering --customers | tests/test_data_integrity.py | Real customer ID space from food delivery records. |
| 3 | **Historical Refund Exposure** | ₹9.74L (₹9,74,250.00) | Cumulative refund amounts requested | src/exposure_analysis.py | python -m src.exposure_analysis | tests/test_risk_scoring.py | Exposure represents requested refund value, not confirmed financial loss. |
| 4 | **Flagged Account Triage** | 279 Accounts (38.78% refund value) | High multi-signal anomaly pool | src/risk_engine.py | python -m src.risk_engine --triage | tests/test_triage_queue.py | Heuristic prioritization score; flagged does not equal confirmed fraud. |
| 5 | **Volume-Band Normalization** | 113 of 279 accounts (40.5%) cleared | Accounts with refund rate <= P95 of order volume decile | src/volume_bands.py | python -m src.volume_bands --normalize | tests/test_volume_normalization.py | High order frequency naturally accumulates more refunds; baseline normalization prevents customer insult. |
| 6 | **Prioritized Review Alerts** | 115 High + Medium Action Alerts | Thresholded review capacity | src/alert_policy.py | python -m src.alert_policy --capacity | tests/test_alert_economics.py | Selected based on human investigator review capacity of 120 cases/week. |
| 7 | **Alert Economics Model** | 70%+ recoverable risk captured | Trade-off: ₹200 review cost vs fraud prevention | src/alert_economics.py | python -m src.alert_economics --simulate | tests/test_alert_economics.py | Model is an economic simulation, not actual company audited P&L. |
| 8 | **Drift Monitoring (PSI)** | Weekly Population Stability Index | Feature distributions across 12 weeks | src/psi_monitor.py | python -m src.psi_monitor --weekly | tests/test_drift_monitoring.py | PSI threshold < 0.10 indicates stable scoring distribution. |
| 9 | **Automated CI Footprint** | 136 Passing Tests | Unit, regression, & property-based tests | tests/ directory | python -m pytest | GitHub Actions workflow .github/workflows/ci.yml | Full test execution covers edge cases, boundary conditions, and schema sanity. |

---

## 2. Unambiguous Operations Funnel

`
Observed Customer Population: 9,895 Customers (100.0%)
 └── Filtered by Minimum Activity (>= 3 Orders): 4,120 Active Customers (41.6%)
      └── Multi-Signal Anomaly Scoring (Refund Rate, Velocity, Reason Skew):
           └── Eligible Anomaly Pool: 279 Accounts (Driving ₹3.78L / 38.78% of Total Refund Value)
                ├── Volume-Band Normalization (<= P95 within order-frequency tier):
                │    └── 113 Accounts (40.5%) -> Cleared as High-Volume Normal Customers (Zero Friction)
                └── Net True Anomaly Queue: 166 Genuine Outlier Accounts
                     └── Operational Capacity Cutoff (Top Risk Scores):
                          ├── High Priority Alerts:    48 Accounts (Immediate Human Review)
                          ├── Medium Priority Alerts:  67 Accounts (Secondary Verification)
                          └── Total Actionable Alerts: 115 High/Med Alerts (Capturing 74.2% of Recoverable Risk)
`

---

## 3. Standardized Terminology Guide
- **Eligible Anomaly Account:** An account exhibiting multi-signal behavioral risk score above baseline screening threshold (279 accounts).
- **Volume-Band Normalized Account:** An account whose refund volume is statistically expected given its high order volume (113 accounts cleared).
- **Prioritized Review Alert:** An account selected for human investigator action within operational workload constraints (115 accounts).
- **Simulated Risk Outcome:** A probabilistic assessment based on synthetic behavioral attributes—**never referred to as confirmed fraud**.