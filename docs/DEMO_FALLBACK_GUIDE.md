# Live Demo & Offline Fallback Guide — Refund Risk Intelligence
**Primary Live Streamlit App:** https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/  

---

## 1. What to Do If Streamlit Community Cloud is Asleep
Streamlit free-tier apps enter sleep mode after a period of inactivity. If the app displays a "Waking up" screen:

### Option A: Local Instant Execution
```bash
# Clone and enter directory
git clone https://github.com/rishi-1603/zomato-refund-fraud-analytics.git
cd zomato-refund-fraud-analytics

# Install requirements
pip install -r requirements.txt

# Launch Streamlit local console
streamlit run streamlit_app.py
```
The interactive operations triage console will immediately launch on `http://localhost:8501`.

### Option B: Quick CLI Operations Sizing
```bash
python -m src.risk_engine --summary
```

### Option C: Inspect Key Methodology Documentation
- **Triage Funnel:** See `docs/REFUND_RISK_FUNNEL.md`
- **Case Review Workflow:** See `docs/INVESTIGATOR_CASE_WORKFLOW.md`
- **Alert Economics:** See `docs/ALERT_ECONOMICS_SENSITIVITY.md`
- **Drift Monitoring:** See `docs/PSI_MONITORING_RUNBOOK.md`
