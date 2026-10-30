# Operations Refund Risk Triage Funnel
**Audit Scope:** 45,584 Food Delivery Transactions | 9,895 Unique Customer Accounts  
**Financial Exposure:** Rs. 9.74L in Historical Requested Refunds

---

## 1. Multi-Stage Operational Funnel Diagram

```
[Stage 1: Ingestion]  9,895 Total Customers Observed
                             │
                             ▼ (Filter: Minimum 3 Orders in Window)
[Stage 2: Active Pool] 4,120 Active Customers (41.6% of Base)
                             │
                             ▼ (Multi-Signal Risk Heuristic: Refund Rate, Velocity, Reason Skew)
[Stage 3: Screened Pool] 279 Initial Anomaly Accounts
                             │ (Accounts represent Rs. 3.78L / 38.78% of Total Refund Value)
                             │
                             ├─────────────────────────────────────────────────┐
                             │                                                 │
                             ▼ (Volume-Band Normalization <= P95)              ▼ (Outliers > P95)
                    113 Normal Accounts (40.5%)                      166 High-Risk Outlier Accounts
               (High Order Volume Justifies Rate;               (Abnormal Refund Rates Independent 
                Cleared with Zero Customer Insult)               of Order Volume Frequency)
                                                                               │
                                                                               ▼ (Capacity Cutoff: 120 Cases/Wk)
                                                                      115 Prioritized Review Alerts
                                                                        ├── 48 High-Risk Escalations
                                                                        └── 67 Medium-Risk Verifications
```

---

## 2. Funnel Stage Definitions & Metrics

| Funnel Stage | Account Count | Refund Value (Rs.) | % of Total Exposure | Primary Operational Action |
|---|---|---|---|---|
| **1. Total Customer Base** | 9,895 | Rs. 9,74,250.00 | 100.0% | Baseline customer tracking |
| **2. Active Inpatient/Dining Base** | 4,120 | Rs. 8,62,400.00 | 88.5% | Feature generation window |
| **3. Multi-Signal Flagged Pool** | 279 | Rs. 3,77,810.00 | 38.78% | Candidate screening |
| **4. Volume-Band Cleared Normal** | 113 | Rs. 1,12,300.00 | 11.53% | **Whitelisted (Prevent False-Positive Friction)** |
| **5. Net Outlier Queue** | 166 | Rs. 2,65,510.00 | 27.25% | Ranked by risk severity |
| **6. Dispatched Review Alerts** | 115 | Rs. 2,12,400.00 | 21.80% | Assigned to human investigation queue |
