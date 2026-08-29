# Data Dictionary
### `data/raw/Zomato Dataset.csv` (real) + `data/processed/zomato_with_refunds.csv` (real + generated)
> 45,584 orders · 10,000 synthetic customers · refund layer generated with seed 42

## Real columns (public Kaggle Zomato delivery dataset — unmodified)

| Column | Type | Notes |
|---|---|---|
| `ID` | string (hex) | Order ID — primary key, unique |
| `Delivery_person_ID` | string | e.g. `DEHRES17DEL01` |
| `Delivery_person_Age` | int | rider age |
| `Delivery_person_Ratings` | float 1–6 | ⚠️ 53 rows rated 6.0 (out-of-scale quirk in the public data; pinned by tests), ~1.9k NaN |
| `Restaurant_latitude/longitude` | float | pickup coordinates |
| `Delivery_location_latitude/longitude` | float | dropoff coordinates |
| `Order_Date` | date (DD-MM-YYYY) | 2022 |
| `Time_Orderd` / `Time_Order_picked` | time | |
| `Weather_conditions` | string | Fog / Stormy / Sandstorms / … |
| `Road_traffic_density` | string | Jam / High / Medium / Low |
| `Vehicle_condition` | int | |
| `Type_of_order` | string | Meal / Snack / Drinks / Buffet |
| `Type_of_vehicle` | string | motorcycle / scooter / … |
| `multiple_deliveries` | int | |
| `Festival` | Yes/No | |
| `City` | string | Metropolitian / Urban / Semi-Urban (as in source data) |
| `Time_taken (min)` | int | delivery duration |

## Generated columns (notebook 01, seed 42 — synthetic)

| Column | Type | Generation logic |
|---|---|---|
| `Customer_ID` | string `CUST#####` | Random assignment of 10,000 customers to orders |
| `Refund_Requested` | bool | Drawn from the customer's planted risk: High 70% / Medium 20% / Low 5% |
| `Refund_Reason` | string | High → repetitive fraud reasons; others → normal reasons |
| `Refund_Amount` | float ₹ | High ₹200–800 / Medium ₹100–400 / Low ₹50–200 |

## Planted ground truth (recovered)

| File | Content |
|---|---|
| `data/processed/ground_truth_customer_risk.csv` | Customer_ID → Planted_Risk (High 299 / Medium 711 / Low 8,990), recovered by replaying the seeded generator; verified 100% against the committed Customer_ID assignment |

## Refund reasons

Normal: Late Delivery · Wrong Item · Missing Item · Poor Quality · Damaged Packaging
Planted-fraud: Item Not Received · Wrong Item (repetitive by design)

## Key outputs

| File | Grain | Content |
|---|---|---|
| `reports/fraud_suspects.csv` | customer (279 rows) | eligible pool + signals + Fraud_Risk_Score |
| `reports/score_validation.md` | — | score vs planted truth: precision/recall/AUC/coverage |
