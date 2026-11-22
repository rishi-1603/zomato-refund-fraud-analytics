# Data Quality Strategy & Missing Value Handling

**Source dataset:** `data/processed/zomato_with_refunds.csv` (45,584 rows × 24 columns)  
**Analysis period:** 11 Feb 2022 – 06 Apr 2022 (44 active days)  
**Last updated:** 22 Nov 2026

---

## Missing Value Summary

| Column | Null Count | % | Handling Strategy | Rationale |
|--------|------------|---|-------------------|-----------|
| `Delivery_person_Age` | 1,854 (4.1%) | **Dropped from delivery-person-level analyses** | Age not used in core refund KPIs or risk scoring. Dropping avoids imputation bias. |
| `Delivery_person_Ratings` | 1,908 (4.2%) | **Dropped from delivery-person-level analyses** | Ratings not used in refund risk model. Excluded to avoid imputation artifacts. |
| `City` | 1,200 (2.6%) | **Kept as "Unknown" category** | City used for geographic segmentation. Nulls grouped as "Unknown" in filters and charts. |
| `multiple_deliveries` | 993 (2.2%) | **Imputed as 1 (single delivery)** | Most orders are single deliveries. Conservative assumption; minimal impact on refund KPIs. |
| `Time_Orderd` | 1,731 (3.8%) | **Dropped from time-of-day analyses** | Not used in core refund KPIs. Excluded from temporal patterns. |
| `Weather_conditions` | 616 (1.4%) | **Kept as "Unknown" category** | Used in null-result delivery-condition analysis. Nulls grouped separately. |
| `Road_traffic_density` | 601 (1.3%) | **Kept as "Unknown" category** | Same as weather. |
| `Festival` | 228 (0.5%) | **Imputed as "No Festival"** | Conservative default; festival flag not a primary driver. |

---

## Data Quality Checks (Automated)

All checks run in `dashboard/app.py` → **Data & Methodology** page:

```python
# 1. Missing values in required columns
required = ["ID", "Customer_ID", "Order_Date", "Refund_Requested", "Refund_Amount", "City", "Refund_Reason"]
missing = {c: int(orders[c].isna().sum()) for c in required if c in orders.columns}

# 2. Duplicate order IDs
dup = int(orders["ID"].duplicated().sum())

# 3. Date range validity
dmin, dmax = orders["Order_Date"].min(), orders["Order_Date"].max()
active_days = orders["Order_Date"].dt.normalize().nunique()

# 4. Refund amounts non-negative
neg = int((orders["Refund_Amount"] < 0).sum())

# 5. Refund records have positive amount
rr = orders.loc[orders["Refund_Requested"] == True]
zero_amt = int((rr["Refund_Amount"] == 0).sum())

# 6. Flagged customers exist in orders
orphan = int((~suspects["Customer_ID"].isin(orders["Customer_ID"])).sum())
```

**All checks PASS** on current dataset.

---

## Refund Layer Specifics

| Aspect | Detail |
|--------|--------|
| **Source** | Synthetic (generated for portfolio case study) |
| **Generation** | `scripts/f9cab97` notebook (seeded, reproducible) |
| **Independence** | Generated independently of delivery conditions (weather, traffic, festival, vehicle, etc.) |
| **Validation** | Refund rate flat across weather/traffic/festival/vehicle (7.5–8.4% vs 7.9% overall) → confirms independence |
| **Disclosure** | Disclosed in README, dashboard header, every page footer, Data & Methodology page |

---

## Refund Amount Handling

| Scenario | Value | Used In |
|----------|-------|---------|
| Non-refunded orders | `0.0` | Order-level totals, exposure sums |
| Refunded orders | `> 0` (min ₹50.28, max ₹799.77) | Refund KPIs, customer exposure, Pareto |
| **Mean refund amount** | ₹270.95 | Computed **only on refunded orders** (3,596 rows) |

> **Note:** `Refund_Amount` = 0 for non-refunded orders by design. Mean/median refund metrics are computed on the refunded subset only (`Refund_Requested == True`).

---

## Customer-Level Aggregations

| Metric | Formula | Grain |
|--------|---------|-------|
| `Total_Orders` | `count(ID)` | Customer |
| `Total_Refunds` | `sum(Refund_Requested)` | Customer |
| `Total_Refund_Amount` | `sum(Refund_Amount)` | Customer |
| `Refund_Rate` | `Total_Refunds / Total_Orders × 100` | Customer |
| `Volume_Band` | `1-2 / 3-5 / 6-10 / 11-20 / 21+` | Customer (full history) |

**Volume bands assigned from full unfiltered history** — dashboard filters cannot move a customer between bands.

---

## Join Integrity

| Check | Result |
|-------|--------|
| Order ID uniqueness | PASS (0 duplicates) |
| Customer ID referential integrity (flagged ⊆ orders) | PASS (0 orphans) |
| Refund request grain | 3,596 requests across 2,515 customers (some customers have multiple requests) |
| One-to-many (order → refund) | Validated: each refund row maps to exactly one order |

---

## Partial Period Handling

| Period | Status | Handling |
|--------|--------|----------|
| Feb 2022 | Partial (starts 11 Feb) | MoM comparisons suppressed; coverage note displayed |
| Mar 2022 | Complete | Included in trends |
| Apr 2022 | Partial (ends 6 Apr) | MoM comparisons suppressed; coverage note displayed |

**Coverage note displayed on Executive Overview:**  
*"Observed monthly totals cover partial calendar periods; unequal coverage can explain the change. This is not a like-for-like business trend."*

---

## Reproducibility

| Artifact | Location | Regenerates |
|----------|----------|-------------|
| Synthetic refund layer | `scripts/f9cab97` (notebook) | ✅ Seeded |
| Baseline normalization | `scripts/baseline_normalization.py` | ✅ |
| Pareto analysis | `scripts/pareto_analysis.py` | ✅ |
| KPI reconciliation | `scripts/kpi_reconciliation.py` | ✅ |
| Drift monitoring | `scripts/drift_monitor.py` | ✅ |

All analytical scripts are pure Python, no external API dependencies (except optional AI narration).