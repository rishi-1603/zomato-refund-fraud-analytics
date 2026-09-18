# Interview Preparation Pack
### Zomato Refund Fraud Analytics — questions and answers based ONLY on the actual project

---

## Resume Bullets (verified numbers only)

- **Engineered a 4-signal refund-abuse risk score** across 45,584 delivery orders, flagging 279 customers holding 38.78% of total refund exposure (₹3.78L) — validated against recovered ground truth at **100% top-tier precision and 0.94 in-pool AUC**.
- **Quantified a 56% coverage gap** in the eligibility funnel (the ≥5-order filter drops over half of planted abusers pre-scoring) and **identified 113 flagged customers (40.5%) as false-positive candidates** via volume-band baseline normalization — above-baseline customers have a 57.5% FP rate vs 4.8% below-baseline.
- **Reconciled all 8 headline KPIs across independent Python and SQL implementations** with zero discrepancies; stress-tested the 40/30/20/10 risk-score weights (all alternative configurations produce Spearman ρ > 0.95 — ranking is stable), and built a Pareto concentration analysis showing the top 10% of customers hold 75.6% of refund value.

## One-Line Description

End-to-end refund-fraud risk analytics: behavioral scoring over 45,584 real delivery orders, validated against recovered ground truth, with sensitivity testing, false-positive analysis, and full SQL/Python reconciliation.

## 5-Minute Presentation Script

**[30s] Business problem**
"Food-delivery platforms lose money to refund abuse — customers who repeatedly file false complaints. But you can't just block everyone who asks for a refund, because most refunds are legitimate. The question is: who should a fraud team investigate first?"

**[60s] Data & methodology**
"I used a real Kaggle dataset of 45,584 food-delivery orders with a transparent synthetic refund layer — the refunds are generated with seeded randomness, which means I can recover the ground-truth labels and actually measure how well the risk score works. The score uses four behavioral signals: refund rate at 40% weight, reason repetition at 30%, refund frequency at 20%, and reason length at 10%."

**[90s] Key findings**
"Three findings matter most. First, the ground-truth validation: the top risk tier is 100% precise — every customer in it is a planted abuser. But the funnel has a 56% coverage gap — the eligibility filter drops over half the abusers before scoring even starts. Second, the baseline normalization: 40.5% of flagged customers are within normal range for their order volume — they're not abnormal, just frequent users. Third, the false-positive analysis: below-baseline customers have a 57.5% FP rate versus 4.8% above-baseline, which means the volume-band normalization works as a screening tool."

**[60s] Root cause**
"The root cause of false positives is the flat 30% refund-rate threshold. It doesn't ask 'compared with WHAT?' A customer with 5 orders and 2 refunds hits 40% — that's small-sample variance, not abuse. A customer with 30 orders and 12 refunds at 40% is a different story. The volume-band baselines make that distinction quantitative."

**[60s] Recommendations**
"Three actions: score every customer with at least one refund instead of requiring five orders — that closes the coverage gap. Use volume-band P95 thresholds instead of a flat 30% — that reduces false positives by screening out below-baseline customers. And never auto-ban: the score is a review-prioritization tool, and every flag should route to human investigation."

**[30s] Limitations**
"The refund layer is synthetic and seeded — the methods are the story, not the numbers. On real data, ground truth would come from investigation outcomes. The 73 planted-Medium customers are a grey area. And concentration is a prioritization signal, never proof of fraud."

---

## 10 Business Questions

1. **What % of customers request refunds?** 2,515 of 9,895 (25.4%) have at least one refund; 7,380 have none.
2. **What % of refund value comes from flagged customers?** 279 flagged customers (2.8% of all) hold 38.78% of total refund exposure.
3. **Which refund reasons are most associated with suspicious behavior?** "Item Not Received" is planted as the repetitive fraud reason; "Wrong Item" is the second.
4. **How concentrated are refund losses?** Top 1% of customers hold 26.9%; top 10% hold 75.6%; 292 customers (3%) cover 50%.
5. **Are high-risk customers also high-value?** Not necessarily — the top CLV tier and the top risk tier are different populations.
6. **What % of customers are in each risk tier?** Low: 164, Medium: 107, High: 8 (of 279 scored).
7. **What false-positive risks exist?** 73 of 279 flagged are planted Low-risk (26.2% FP rate). The biggest scenario: low-volume noise (5-6 orders, 2 refunds crossing 30% by chance).
8. **How could legitimate customers be protected?** Volume-band normalization (Phase 2) + minimum refund count ≥3 + reason-diversity check.
9. **How does refund behavior vary by city type?** Rates are roughly flat (~8%) across Metropolitian/Urban/Semi-Urban — refund behavior is generated independently of city type.
10. **What actions should management take?** Score all ≥1-refund customers, use band P95 thresholds, route flags to human review.

## 10 SQL Questions

1. **How did you calculate refund exposure in SQL?** Conditional aggregation: `SUM(CASE WHEN "Refund_Requested" = TRUE THEN "Refund_Amount" ELSE 0 END)`.
2. **How did you implement the Pareto concentration?** Window functions: `ROW_NUMBER() OVER (ORDER BY refund_value DESC)` for ranking, `SUM(...) OVER (ORDER BY ...)` for cumulative totals, then cuts at 1%/5%/10%/20%.
3. **What window functions did you use?** `ROW_NUMBER`, `SUM() OVER()` (running totals and grand totals), `NTILE` (not in this project but I know it).
4. **How does your SQL reconcile with Python?** `scripts/kpi_reconciliation.py` loads the CSV into SQLite, runs adapted SQL, and compares — all 8 KPIs match with zero discrepancy.
5. **What's the difference between RANK and DENSE_RANK?** RANK skips ties (1,1,3); DENSE_RANK doesn't (1,1,2). I used ROW_NUMBER for the Pareto because I needed a strict ordering.
6. **How would you find the top 10 customers by refund exposure?** `ORDER BY refund_value DESC LIMIT 10` or `ROW_NUMBER() OVER (ORDER BY refund_value DESC) <= 10` in a CTE.
7. **How do you calculate a running total?** `SUM(col) OVER (ORDER BY date)` — I used this for the cumulative concentration curve.
8. **What is conditional aggregation?** `SUM(CASE WHEN condition THEN value ELSE 0 END)` — I use it throughout for refund-flagged metrics.
9. **How would you detect duplicate customers?** `GROUP BY Customer_ID HAVING COUNT(*) > 1` — but at order grain, multiple orders per customer is correct; I check for duplicate order IDs instead.
10. **Why PostgreSQL?** It supports the window functions and analytics I need; the schema uses quoted identifiers for mixed-case column names.

## 10 Python Questions

1. **How did you recover the ground truth?** Replaying the seeded generator: `np.random.seed(42)`, regenerate customer assignments, recover the planted risk categories. Verified 100% match against committed data.
2. **Why MinMaxScaler?** The four signals have different scales (percentage, rate, chars); MinMax normalizes them to 0–100 so the weighted sum is meaningful.
3. **How did you validate the risk score?** Against recovered ground truth: 100% top-tier precision, 0.94 in-pool AUC, plus sensitivity analysis (signal removal, alternative weights, threshold shifts).
4. **How did you handle the pandas FutureWarning?** `groupby().apply()` deprecation — I documented it; the fix is `include_groups=False` in pandas 3.0.
5. **How did you build the baseline normalization?** Volume bands (1-2, 3-5, 6-10, 11-20 orders), per-band P95 of refund rate, then compare each customer against their band's P95.
6. **What's the difference between the risk score and the baseline?** The score is a weighted heuristic on four signals; the baseline is a population-norm comparison (are you abnormal for your volume?). They answer different questions.
7. **How did you test for false positives?** Cross-tab: flagged vs planted ground truth. 131 TP, 73 FP, 75 grey of 279.
8. **Why not use ML for fraud detection?** With seeded ground truth, a rule-based score + validation is more transparent and defensible than a black-box model. The coverage-gap finding shows the issue is funnel design, not model complexity.
9. **How did you ensure reproducibility?** Fixed seeds everywhere (42), all scripts deterministic, 37 CI tests, data committed to the repo.
10. **What would you do differently with real data?** Ground truth from investigation outcomes, temporal features (time between refunds), device/payment fingerprints, and a proper train/test split respecting time.

## 10 Fraud/Risk Questions

1. **Why these risk signals?** Refund rate (40%) is the core abuse indicator; reason repetition (30%) detects scripted claims; frequency (20%) captures burst behavior; reason length (10%) is a weak template signal.
2. **Why these weights?** They're documented analyst choices, not optimized. Sensitivity analysis shows all alternatives produce Spearman ρ > 0.95 — the ranking is stable regardless.
3. **How did you validate the score?** Ground-truth recovery + measurement: 100% top-tier precision, 0.94 AUC, 56% coverage gap quantified.
4. **What if a legitimate customer gets flagged?** That's the false-positive analysis: 73 of 279 flagged are planted Low-risk. The biggest scenario is low-volume noise. Recommendations: volume-band thresholds, minimum refund count, reason-diversity check.
5. **Why not use ML?** Transparency and defensibility. A rule-based score with documented weights is auditable; a black-box model is not. On real data, I'd benchmark both.
6. **How would you reduce false positives?** Volume-band normalization (Phase 2) is validated: below-baseline customers have 57.5% FP vs 4.8% above. Also: minimum 3 refunds before scoring, reason-diversity flag.
7. **How would this work in production?** Batch scoring nightly, flag queue for investigators, monthly recalibration of baselines, monitoring for drift in refund-rate distributions.
8. **How would you monitor rule drift?** Track the refund-rate distribution per volume band monthly; alert when P95 shifts by more than a threshold; log FP feedback from investigators.
9. **How would you measure fraud reduction?** Compare refund exposure before/after intervention, using a holdout control group — the same methodology recommended in the decision log.
10. **What would you do with real-time data?** Score at refund-request time, not batch; add device fingerprints, payment velocity, and geo-velocity signals; escalate to real-time review queues.

## 10 Project Deep-Dive Questions

1. **What was your biggest data-quality issue?** The 53 six-star ratings in the source Kaggle data. I documented them and pinned them with a test so any change to the raw data is caught.
2. **What is the most important insight?** The coverage gap: the eligibility filter (≥5 orders) drops 56% of planted abusers before scoring even starts. This is a design flaw, not a model issue.
3. **What would you do if management disagreed with your recommendation?** Show the data: the coverage-gap numbers and the FP-rate-by-baseline table are objective. If they disagree on prioritization, that's a business call — my job is to quantify the tradeoffs.
4. **What assumptions did you make?** That refund behavior is the primary abuse signal (no device/payment data); that the seeded ground truth is a reasonable proxy for real labels; that concentration implies reviewability.
5. **What is the biggest limitation?** The synthetic refund layer — the methods transfer, but the numbers don't. On real data, ground truth comes from months of investigations.
6. **What would you improve with more data?** Real ground-truth labels, temporal features, device fingerprints, payment-method analysis, merchant-level signals.
7. **What would you do differently in production?** Real-time scoring, proper database (not CSV), API-based investigator workflow, model monitoring, feedback loops from investigation outcomes.
8. **Why did you choose this project structure?** Separation of concerns: SQL for warehouse-style queries, Python for analysis and validation, Streamlit for the dashboard, pytest for data quality, CI for reproducibility.
9. **How long did this take?** The core pipeline took ~2 weeks; the professionalization (tests, reports, validation, sensitivity, false-positive analysis, reconciliation) took another ~2 weeks.
10. **What did you learn?** That a perfect metric (AUC 1.0) is a debugging signal, not a win. That validation against ground truth is the most valuable thing you can do. That false-positive analysis is what separates fraud analytics from dashboard building.
