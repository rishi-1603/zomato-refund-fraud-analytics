# Fraud & Operations Investigator Case Workflow
**Role:** Senior Risk Operations Specialist / Fraud Triage Investigator  
**Interface:** Streamlit Triage Console & Case Management System

---

## 1. Case Header & Profile Snapshot
- **Case ID:** `CASE-2026-0942`
- **Customer ID:** `CUST_7841`
- **Account Age:** 142 Days
- **Total Orders Placed:** 54 Orders (Top 5% Order Volume Decile)
- **Refunds Requested:** 16 Orders (29.6% Refund Rate)
- **Total Refund Exposure:** Rs. 4,820.00

---

## 2. Multi-Signal Evidence Summary
1. **Volume-Band Benchmark:** For customer volume band (50-60 orders), 95th percentile refund rate is **12.5%**. Customer's rate (29.6%) exceeds baseline by **2.37x**.
2. **Refund Reason Distribution:**
   - "Missing Item": 11 claims (68.8%)
   - "Quality / Cold Food": 4 claims (25.0%)
   - "Late Delivery": 1 claim (6.2%)
3. **Restaurant Diversity:** Refunds requested across 9 distinct restaurant partners (rules out single-vendor packaging issue).
4. **Delivery Partner Verification:** 14 of 16 delivery trips confirmed on-time GPS arrival.

---

## 3. Human Review Decision Workflow

```
                        [Investigator Review]
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
  [Approve Claims]        [Require OTP Verification] [Account Restrictions]
- Verified vendor issue  - Two-factor photo/OTP     - Freeze refund claims
- Clear account flag     - Monitor next 5 orders     - Escalate to legal/risk
```

---

## 4. Case Audit Fields
- **Review Decision:** `REQUIRE_OTP_VERIFICATION`
- **Confidence Rating:** 4 / 5 (High)
- **Investigator Notes:** Frequent "missing item" claims concentrated on high-value side dishes across multiple reliable restaurants. Require customer photo confirmation upon delivery.
