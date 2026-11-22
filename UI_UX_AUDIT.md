# UI/UX AUDIT

## Theme & layout (verified on deployed app)
- Dark theme: bg `#0D1117`, panels `#161B22`/`#1F2937`, borders `#30363D`, text `#E6EDF3`, accent blue `#2F81F7`
- Consistent palette across all pages and charts (Plotly dark template)
- Sidebar ~220px equivalent with branding, date coverage, data-source disclosure, compact filters, Reset control, active-filter scope
- Main content wide layout; charts stretch to container width
- KPI cards: metric name, big number, short explanation/formula; no icons on every metric, no fake growth indicators
- Typography: one font family, consistent heading sizes, readable body text

## Page-by-page findings

| Page | Status | Notes |
|---|---|---|
| 1. Executive Overview | Pass | 4 KPIs, monthly trend with peak annotation, exposure by tier, attention section with 166/113 split, partial-month caveat |
| 2. Refund Analysis | Pass | Refund distribution histogram, reasons horizontal bar, volume-band bar (6–8% rates, no 100%), Pareto curve, city-type comparison |
| 3. Customer Risk Review | Pass | Tier distribution (bar, High→Medium→Low), P95 peer comparison, searchable/sortable investigation table, CSV export, Explain a Flag, AI copilot |
| 4. Review Operations | Pass | Queue by tier, priority sorting, capacity planner (assumptions labelled as planning, not results), no delivery-performance charts |
| 5. Data & Methodology | Pass | DQ checks, KPI formulas, risk methodology, limitations, technology |

## UX requirements check
1. Professional dark theme — Pass
2. Restrained accent color — Pass (blue primary, red/amber/green semantic only)
3. Readable typography — Pass
4. No excessive gradients — Pass
5. No unnecessary decorative icons — Pass (icons only on KPI cards and tier badges)
6. No crowded sidebar — Pass (compact filters, collapsible methodology)
7. No oversized filters — Pass
8. Consistent page header — Pass
9. Consistent card spacing — Pass
10. Charts use available width — Pass (`width="stretch"`)
11. No truncated KPI values — Pass
12. No cropped chart legends — Pass
13. No unreadable axes — Pass
14. No excessive scrolling — Pass
15. No redundant duplicate charts — Pass

## Minor recommendations (P3, optional)
- Componentize inline HTML/CSS in `app.py` into reusable render functions for maintainability
- Add a theme toggle (dark/light) only if user research demands it; dark is currently consistent and professional
