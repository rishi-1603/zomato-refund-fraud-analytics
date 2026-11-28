# RECRUITER & SENIOR DATA ANALYST ASSESSMENT

## Overall impression
A credible, polished, fully working Data Analyst portfolio project. It solves a clear real-world problem (refund-review prioritization) with appropriate complexity for a fresher: rule-based scoring, peer-band benchmarking, an explainable investigation workflow, and an evidence-grounded AI copilot. No fake KPIs, no unverified savings claims, synthetic layer disclosed throughout.

## Strengths (differentiators)
1. **Peer-band P95 benchmarking** — compares customers against similar-volume peers, not the whole population. Strong statistical thinking.
2. **Explainable investigation** — "Explain a Flag" + AI copilot show why each account was flagged, with peer comparison and next-step checks.
3. **Investigation queue** — turnkey review workflow with CSV export and capacity planner.
4. **Analytical honesty** — synthetic data disclosed, limitations documented, no fraud conclusions, "review priority ≠ guilt" messaging throughout.
5. **Verified metrics** — every primary KPI independently recalculated and reconciled; 222 tests pass.

## Interview questions a recruiter may ask (and the project can defend)
1. Why ≥5 orders and >30% refund rate as the eligibility rule? → Documented in `docs/risk_scoring_methodology.md`; it's a review gate, not a probability.
2. Why P95 for peer benchmarking? → Flags what's unusual for a given volume; avoids penalizing high-frequency legitimate customers.
3. How do you handle partial April coverage? → MoM comparisons suppressed; coverage note displayed.
4. What's the difference between potential exposure and confirmed fraud loss? → Explicitly distinguished; flagged value is "associated exposure," not realized loss.
5. How does the AI assistant get its evidence? → Python computes facts; LLM only narrates the evidence package; no arbitrary SQL execution.
6. How do you validate AI answers? → 10-customer validation with exact value checks; deterministic fallback when API unavailable.

## Risks / weaknesses
- AI narration depends on an external Gemini API that is intermittently rate-limited. Deterministic evidence panel always works; narration is best-effort. Document this in demos.
- Some inline HTML/CSS in `app.py` — functional but not componentized. Not a defect, but worth refactoring if the project grows.
- No verified "money saved" figures — correctly avoided; all savings are explicitly modelled under stated assumptions.

## Presentation risks
- Generic/AI-generated feel: Low. The project has a specific domain story, verified numbers, and documented limitations.
- ATS/portfolio: GitHub repo, README, deployed Streamlit app, and project report PDF are consistent.

## Verdict
Safe to present to recruiters. Strongest demonstration: open the dashboard, walk through Executive Overview → pick a flagged customer → run Explain a Flag + AI copilot → show the investigation queue and CSV export.
