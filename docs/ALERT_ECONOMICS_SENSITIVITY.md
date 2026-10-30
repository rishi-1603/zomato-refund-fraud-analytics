# Alert Economics & Sensitivity Analysis
**Objective:** Optimize the trade-off between manual investigation costs, customer friction, and fraud exposure recovery.

---

## 1. Cost & Value Parameters (Modeled Simulation)
- **Manual Review Cost per Ticket ($C_{review}$):** Rs. 200 (Investigator labor & tooling overhead)
- **False Positive Customer Insult Cost ($C_{insult}$):** Rs. 500 (Churn risk & support compensation)
- **Recovery / Prevention Rate ($lpha$):** 65% of flagged illegitimate refund value recovered
- **Weekly Investigation Capacity:** 120 Cases / Week

---

## 2. Sensitivity Matrix: Net Value by Cutoff Threshold

| Risk Score Cutoff | Weekly Alerts Generated | Flagged Exposure (Rs.) | Est. True Positive Rate | Review Cost (Rs.) | Friction Cost (Rs.) | Recovered Value (Rs.) | **Net Program Benefit (Rs.)** |
|---|---|---|---|---|---|---|---|
| Top 50 (Aggressive) | 50 | Rs. 1,42,000 | 88.0% | Rs. 10,000 | Rs. 3,000 | Rs. 81,224 | **+Rs. 68,224** |
| Top 115 (Recommended) | 115 | Rs. 2,12,400 | 78.5% | Rs. 23,000 | Rs. 12,360 | Rs. 1,08,380 | **+Rs. 73,020 (Optimal)** |
| Top 200 (Expanded) | 200 | Rs. 2,98,000 | 62.0% | Rs. 40,000 | Rs. 38,000 | Rs. 1,20,094 | **+Rs. 42,094** |
| All 279 (Unbounded) | 279 | Rs. 3,77,810 | 48.0% | Rs. 55,800 | Rs. 72,540 | Rs. 1,17,876 | **-Rs. 10,464 (Net Loss)** |

> **Key Finding:** Unbounded screening of all 279 initial flags results in a **net economic loss** (-Rs. 10.4K) due to excessive customer friction and review overhead. The **115-alert threshold** yields maximum net economic benefit (+Rs. 73.0K/week).
