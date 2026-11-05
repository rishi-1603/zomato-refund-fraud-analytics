# Bounded decision-copilot evaluation

**Local snapshot, 5 November 2026:** `python scripts/decision_copilot_eval.py` on Linux x86_64, Python 3.13.16, pandas 2.3.3, NumPy 2.5.4 and scikit-learn 1.9.1, in a shared sandbox reporting Intel Xeon 2.60 GHz. Data loading and queue construction occur before per-question timing. The measured local run returned:

| Measure | Result |
|---|---:|
| Authored cases | 49 |
| Supported numerical answers | 29/29 |
| Expected refusals | 20/20 |
| Local in-process p50 | 5.95 ms |
| Local in-process p95 | 6.71 ms |
| External provider calls | 0 |

The case set comprises the same five supported metric templates for five synthetic customers, four queue-total phrasings and 20 unsupported/ambiguous/out-of-scope requests. Expected customer order counts, refund counts, rates and exposure are recomputed from raw order rows; expected scores are compared with the committed score table. Successful answers must contain formula, source columns and scope identity. The fixed SQLite/pandas selected-queue reconciliation runs on each request.

This measures the deterministic `decision_copilot.ask` path only. It does **not** test the separate optional provider-generated investigator narration, arbitrary natural-language understanding, network latency or real fraud decisions. Provider usage cost for these calls is zero because no provider is contacted; CPU/infrastructure cost is not measured. Timing varies with machine load, data and versions and is not a service-level promise. CI runs the same authored cases; recompute timings on the target environment.
