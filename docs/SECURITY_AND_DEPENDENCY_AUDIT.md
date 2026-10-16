# SECURITY & DEPENDENCY AUDIT — Zomato
### Audit date: 2026-10-17

## Dependencies (requirements.txt)
Deployment set (6): streamlit>=1.35,<2 · pandas>=2,<3 · numpy>=1.24,<3 ·
scikit-learn>=1.3,<2 · pytest>=8,<10 · plotly>=5.20,<6
- Wide bounds for Streamlit Cloud resolution; matplotlib deliberately optional
  (figures degrade gracefully on slim envs).
- Local-only extras documented in requirements.txt comments, not installed in CI.

## Secrets
- Token-pattern scan of all tracked files: **CLEAN** (2026-10-17).
- Maintainer PAT: environment variable only; rotation scheduled. Never in repo,
  history, reports, or logs.

## Supply chain / CI
GitHub-hosted runners; official actions only (checkout, setup-python). Streamlit
Community Cloud hosts the console; no database, no auth surface in-app.

## Data ethics
Synthetic data with planted labels; the repo refuses real-world fraud claims in
README, model comparison, and error catalog.

## Residual risks
Broad dependency bounds can drift on fresh resolves (mitigated by CI running on
each push); account security (2FA, PAT rotation) is the owner's responsibility.
