# FoodTrust — Interview Preparation

30+ project-specific questions with honest, fresher-level answers. Use these as starting points and adapt to your own words.

---

## A. Dataset and data design

**1. What is your dataset?**
A public food-delivery delivery dataset (45,584 order lines, 20 columns: rider, weather, traffic, delivery time, city, order type). Customer IDs, refund events, amounts and risk labels are synthetic, seeded with seed 42. No real customer is implicated.

**2. Why add synthetic refund data on top of a real delivery dataset?**
The public dataset has no refund fields. To demonstrate refund analytics without claiming access to a company's confidential data, I extended it with a disclosed, internally consistent synthetic refund layer. The README and data dictionary state this explicitly.

**3. How do you interpret null `Refund_Reason`?**
Null means **no refund was requested** on that order — a structural fact, not missing data. I never impute it as "No Refund" for claimants, and the claim count (3,596) comes from `Refund_Requested == True`.

**4. How do you keep original and synthetic data distinguishable?**
Three added columns (`Refund_Requested`, `Refund_Reason`, `Refund_Amount`) are documented in the data dictionary; `ground_truth_customer_risk.csv` is separate; provenance is in the README table.

## B. SQL and analytics engineering

**5. How do you make sure pandas and SQL agree?**
`scripts/kpi_reconciliation.py` compares 8 headline KPIs between pandas and SQL on SQLite; the report shows zero mismatches. Both use the same definitions from `data/metrics.json`.

**6. Why SQLite and not PostgreSQL?**
The verification runs on SQLite for reproducibility without credentials. PostgreSQL-oriented SQL is included; a Postgres pass is a documented Phase B item. I do not claim Postgres is currently in production.

**7. What SQL techniques do you use?**
Complex joins, CTEs, window functions (ranking, rolling), conditional aggregation, date analysis, deduplication, reconciliation. See `sql/fraud_queries.sql`, `sql/cumulative_pareto.sql`, `sql/baseline_bands.sql`.

## C. KPIs and metrics

**8. Define refund request rate.**
Distinct eligible orders with at least one refund request / distinct eligible orders. Row-based (order-line grain), 7.89% (3,596 / 45,584).

**9. Define refund value share of the pool.**
Pool refund value / total refund value = ₹377,892 / ₹974,343.55 = 38.78%. Descriptive concentration, not fraud loss.

**10. Why not just use refund count as a KPI?**
Because one customer can have many requests. I distinguish request-row counts from distinct-order counts and state the basis per metric.

## D. Fraud and risk methodology

**11. How is the risk score calculated?**
0.40·refund rate + 0.30·reason repetition + 0.20·frequency + 0.10·reason breadth, scaled 0–100. Weights documented in `risk_rules.py` and the methodology doc.

**12. Is the score a probability?**
No. It is explicitly **uncalibrated** — 70 is not a 70% probability. It ranks the review pool.

**13. Who enters the review pool?**
Eligibility: ≥5 orders AND refund rate > 30%. 279 customers. The rule is applied before any baseline comparison.

**14. How do you avoid flagging high-volume customers unfairly?**
Volume-band baseline: each customer is compared with customers in the same order-volume band (1–2, 3–5, 6–10, 11–20, 21+) using the band's P95 rate. 113 of 279 flagged customers sit at or below their band's P95.

**15. Is that 113/279 a false-positive rate?**
No — it is descriptive. Eligibility is applied *before* the baseline comparison, so it describes the pool, not a measured FPR. There are no confirmed investigation outcomes to measure a true FPR.

**16. Why report a null result (p = 0.76)?**
The delivery-person permutation test found no clustering evidence beyond chance. Reporting nulls honestly is part of credible analysis; hiding them would be worse.

## E. Machine learning

**17. Did you train a fraud classifier?**
No. There are no confirmed fraud labels, so I did not invent them. I ran a rules-vs-ML comparison (`scripts/model_comparison.py`) on planted labels to show when each approach is appropriate, and documented why a deployed classifier is not justified here.

**18. Why not use SHAP?**
SHAP needs a fitted model. There is no deployed classifier in this project, so adding SHAP would be decorative. It is listed as a future capability with its prerequisite stated.

**19. How do you prevent data leakage?**
Eligibility applied before baseline; features are behaviour aggregates; labels (planted) are per-customer and not leaked into feature construction. Evaluation is on a held-out split.

## F. Dashboard and product

**20. How many tabs and what does each answer?**
8 tabs: Executive Overview, Refund Reasons, Risk Investigation, Operations Analysis, Policy & Impact, AI Refund Analyst, Data Quality, Reports. Each has a one-line "what it answers" in the README.

**21. Why Streamlit?**
Fast to build, supports interactivity, deployable to Streamlit Cloud. Chosen for portfolio reproducibility, not because it is the only option.

**22. Why no pie charts everywhere?**
Chart type is chosen by analytical question: trends → line, categories → sorted bar, distributions → histogram, relationships → scatter, time-by-day → heatmap, prioritisation → ranked table.

## G. AI assistant

**23. Does the AI assistant call an LLM?**
There is an optional LLM narration path, but it is disclosed as unverified. The core is a **deterministic evidence tool** that answers bounded questions from data and refuses unanswerable ones.

**24. How do you prevent hallucinations?**
The tool only answers from pre-computed, data-backed facts; it refuses unknown IDs and unanswerable questions. Benchmark: 6/6 answerable grounded, 6/6 refused (`reports/investigator_eval.md`).

## H. Testing and engineering

**25. How many tests?**
206, all passing (`pytest -q`). Cover KPIs, reconciliation, drift, network, cohort, economics, decision engine/UI, investigator, data quality, case management, risk rules.

**26. What is the CI pipeline?**
GitHub Actions: install deps → validate risk score → run model comparison → run all tests. No private API keys required.

**27. Are there credentials in the repo?**
No — `.env.example` only, no real credentials committed (verified in security audit).

## I. Business and positioning

**28. What is the one-line value proposition?**
"Which refund records deserve human review first, what does that review policy cost, and how do we avoid harming legitimate customers while doing it?"

**29. What are the three policies compared?**
High tier (8 reviews, 100% planted precision, ₹8,274 modelled net), High+Medium (115, 87.8%, ₹92,125), All flagged (279, 46.9%, ₹65,006). Break-even precision 28.2%.

**30. What is the biggest limitation you would state in an interview?**
No confirmed investigation outcomes exist, so the precision values measure agreement with planted labels — not real-world fraud detection. I would never present them as realised performance.

## J. Known limitations (state these proactively)

1. Refund layer is synthetic; labels planted.
2. No confirmed outcomes → no real FPR.
3. Score uncalibrated.
4. No refund lifecycle timestamps (no operational-delay analysis).
5. No real merchant IDs (restaurant-cell only).
6. SQL on SQLite (Postgres pass pending).
7. LLM narration unverified.
8. Hour-of-day analysis blocked (no timestamps).
9. `app.py` is large; core logic extracted.
10. Docker scaffolded, not yet tested.
