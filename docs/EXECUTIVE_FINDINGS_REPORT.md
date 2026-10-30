# Executive Findings & Risk Operations Brief
**Subject:** Delivery Refund Risk Intelligence & Queue Sizing  
**Dataset Scope:** 45,584 Orders | 9,895 Customers | Rs. 9.74L Historical Refund Exposure  
**Author:** Rishi Dappu, Data Analyst

---

## 1. Context & Business Challenge
Food delivery platforms balance two competing priorities: preventing exploitative refund requests while preserving frictionless customer experiences for loyal, high-frequency diners. Naive outlier detection flags high-volume customers simply because their raw refund count is high, damaging relationship with top spenders.

---

## 2. Key Analytical Insights
1. **Pareto Concentration:** Sizing revealed that **279 accounts** accounted for **38.78% (Rs. 3.78L)** of total historical refund exposure.
2. **False-Positive Volume Trap:** Volume-band analysis proved that **113 of these 279 flagged accounts (40.5%)** exhibited refund rates consistent with normal baseline behavior for their order volume decile.
3. **Queue Optimization:** Limiting human investigator triage to the top **115 High/Med alerts** captures 74.2% of recoverable exposure while reducing operational review costs by 58.8%.

---

## 3. Recommendations
1. Deploy baseline volume-band normalization in production to whitelist loyal high-frequency accounts.
2. Institute automated OTP verification for high-risk accounts rather than immediate account suspension.
