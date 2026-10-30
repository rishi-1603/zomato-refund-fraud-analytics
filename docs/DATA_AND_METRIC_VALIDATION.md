# Independent data, SQL and statistical validation

Audit date: 2026-10-30. Calculations below were rebuilt from CSVs without importing project metric functions, then compared with PostgreSQL execution. Reproduction scripts and detailed machine output are included in the external audit evidence pack.

## Independent calculations
```json
{
  "orders": 45584,
  "customers": 9895,
  "refund_requests": 3596,
  "refund_amount": 974343.55,
  "refund_rate_pct": 7.8887,
  "flagged": 279,
  "below_p95": 113,
  "missing_reasons_on_refunds": 0,
  "date_min": "2022-02-11",
  "date_max": "2022-04-06",
  "independent_permutation": {
    "observed": 0.020699,
    "null_mean": 0.021484,
    "empirical_p": 0.76,
    "plus_one_mc_p": 0.7612,
    "shuffles": 200,
    "interpretation": "No detected excess on this test; nonsignificance does not establish absence of organized activity."
  }
}
```

## Actual PostgreSQL execution
Original PostgreSQL query files, quoted source-column schema

| File | Executed statements | Failures |
|---|---:|---:|
| baseline_bands.sql | 2 | 0 |
| cumulative_pareto.sql | 2 | 0 |
| fraud_queries.sql | 6 | 0 |

## Permutation review
An independent adjacency-set implementation repeats the 200 shuffles: empirical p=.76; plus-one Monte Carlo correction gives .7612, the same rounded conclusion. This is not evidence that organized abuse is absent.
No missing refund reasons were found among actual refund requests. Missing reasons on non-refund orders are structurally expected. April ends on the sixth, so full-month growth claims are inappropriate.
