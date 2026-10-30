# Population Stability Index (PSI) Drift Monitoring Runbook
**Target Model / Engine:** Food-Delivery Multi-Signal Refund Risk Scorer  
**Monitoring Frequency:** Weekly Scheduled Pipeline  
**Reference Distribution:** Weeks 1-4 Baseline Scoring Distribution

---

## 1. PSI Calculation Formula
$$\text{PSI} = \sum_{i=1}^{k} (A_i - E_i) \times \ln\left(\frac{A_i}{E_i}\right)$$
* Where $A_i$ = Actual proportion in score decile $i$ during monitoring week.
* Where $E_i$ = Expected proportion in score decile $i$ during baseline period (10% per decile).

---

## 2. Threshold Governance & Operating Protocol

| PSI Range | Drift Status | Operational Interpretation | Action Protocol |
|---|---|---|---|
| **PSI < 0.10** | **Green / Stable** | Negligible change in scoring distribution. | Continue standard automated queue processing. |
| **0.10 <= PSI < 0.25** | **Yellow / Moderate** | Noticeable shift in customer behavior or order profile. | Alert risk operations; investigate sub-signal contributions (e.g., weather spikes). |
| **PSI >= 0.25** | **Red / Critical Drift** | Significant distribution shift. High risk of queue saturation or missed fraud. | Freeze automated threshold adjustments; revert to fallback rules; initiate model recalibration. |

---

## 3. Incident Escalation Workflow
1. **Automated Alert Trigger:** GitHub Actions CI / Airflow job detects weekly PSI > 0.10.
2. **Root-Cause Diagnostic:** Execute `python -m src.psi_monitor --drilldown` to isolate which of the 4 signals drifted.
3. **Documentation:** Log incident in `reports/drift_log.json`.
