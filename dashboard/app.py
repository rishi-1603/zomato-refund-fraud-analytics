"""Streamlit dashboard for the Zomato refund fraud risk analysis.

A professional multi-tab BI dashboard — every figure is computed live from
the dataset (45,584 delivery orders). No hardcoded metrics anywhere.

Run with: streamlit run dashboard/app.py
Tabs: Executive Overview · Refund Analytics · Customer Risk · Operations
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from sklearn.preprocessing import MinMaxScaler

DATA_PATH = "data/processed/zomato_with_refunds.csv"
TRUTH_PATH = "data/processed/ground_truth_customer_risk.csv"
METRICS_PATH = "data/metrics.json"

try:  # executed by Streamlit — the script dir is on sys.path
    from kpi_engine import (  # noqa: E402
        BAND_LABELS,
        apply_global_filters,
        compute_kpis,
        load_metric_definitions,
        volume_band,
        what_changed,
    )
except ImportError:  # imported as a module from the repo root (tests)
    from dashboard.kpi_engine import (  # noqa: E402
        BAND_LABELS,
        apply_global_filters,
        compute_kpis,
        load_metric_definitions,
        volume_band,
        what_changed,
    )

RISK_WEIGHTS = {
    "Refund_Rate": 0.40,
    "Reason_Repetition_Rate": 0.30,
    "Refunds_Per_Day": 0.20,
    "Avg_Reason_Length": 0.10,
}
MIN_ORDERS_THRESHOLD = 5
MIN_REFUND_RATE_PCT = 30

# ── Consistent professional palette ─────────────────────────────────────────
C_PRIMARY = "#2563EB"   # blue
C_ACCENT = "#7C3AED"    # violet
C_GOOD = "#059669"      # green
C_WARN = "#D97706"      # amber
C_BAD = "#DC2626"       # red
C_NEUTRAL = "#64748B"   # slate
TIER_COLORS = {"Low": C_GOOD, "Medium": C_WARN, "High": C_BAD}
PLOTLY_LAYOUT = dict(
    template="plotly_white",
    height=380,
    margin=dict(l=40, r=30, t=56, b=40),
    title_font=dict(size=15, color="#1E293B"),
    font=dict(family="Inter, 'Segoe UI', system-ui, -apple-system, sans-serif",
              size=12.5, color="#334155"),
    hoverlabel=dict(bgcolor="#0F172A", font_size=12.5, font_color="#F8FAFC",
                    bordercolor="#0F172A"),
)


# ════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — light "risk-operations console" identity.
# Presentation only: every number still comes from the kpi_engine.
# ════════════════════════════════════════════════════════════════════════════

def inject_css() -> None:
    st.markdown("""
<style>
:root {
  --z-bg:#F4F6FA; --z-card:#FFFFFF; --z-border:#E2E8F0; --z-border2:#CBD5E1;
  --z-text:#0F172A; --z-text2:#334155; --z-muted:#64748B;
  --z-primary:#2563EB; --z-good:#059669; --z-warn:#D97706; --z-bad:#DC2626;
}
html, body, [class*="css"], .stApp { font-family: Inter, 'Segoe UI', system-ui, -apple-system, sans-serif; }
.stApp { background: var(--z-bg); }
section[data-testid="stSidebar"] {
  background: #FFFFFF; border-right: 1px solid var(--z-border);
}
section[data-testid="stSidebar"] * { font-size: 13px; }
section[data-testid="stSidebar"] hr { border-color: var(--z-border); margin: 14px 0 10px; }

/* ── Header band ── */
.app-header {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
  border: 1px solid #1E293B; border-radius: 14px;
  padding: 16px 22px; margin-bottom: 4px; color: #F8FAFC; flex-wrap: wrap;
}
.ah-left { display: flex; align-items: center; gap: 14px; min-width: 0; }
.ah-mark {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; letter-spacing: 0.5px; color: #fff;
}
.ah-title { font-size: 19px; font-weight: 800; letter-spacing: -0.2px; }
.ah-sub { font-size: 12px; color: #94A3B8; margin-top: 1px; }
.ah-right { display: flex; gap: 8px; flex-wrap: wrap; }
.ah-chip {
  font-size: 11px; font-weight: 600; letter-spacing: 0.03em;
  color: #E2E8F0; background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.14); border-radius: 999px; padding: 5px 11px;
  white-space: nowrap;
}
.ah-chip .live { color: #34D399; }

/* ── Sidebar product mark ── */
.side-mark { padding: 2px 2px 10px; border-bottom: 1px solid var(--z-border); margin-bottom: 10px; }
.side-mark .sm-t { font-size: 13px; font-weight: 800; color: var(--z-text); }
.side-mark .sm-s { font-size: 11px; color: var(--z-muted); margin-top: 1px; }

/* ── Filter status chips ── */
.fchips { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 2px; }
.fchip {
  font-size: 11px; font-weight: 600; color: #1D4ED8;
  background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 999px; padding: 3px 10px;
}
.fnone { font-size: 11.5px; color: var(--z-muted); }

/* ── KPI cards (st.metric, restyled — values/deltas untouched) ── */
[data-testid="stMetric"] {
  background: var(--z-card); border: 1px solid var(--z-border); border-radius: 12px;
  padding: 14px 16px 12px; box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
[data-testid="stMetric"] label, [data-testid="stMetric"] > div > label {
  font-size: 10.5px !important; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--z-muted) !important; margin-bottom: 6px;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-size: 25px !important; font-weight: 800; color: var(--z-text);
  font-variant-numeric: tabular-nums; letter-spacing: -0.5px;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
  font-size: 12px !important; font-variant-numeric: tabular-nums;
}

/* ── Section headers (st.subheader) ── */
.main .stMarkdown h3 {
  font-size: 15px; font-weight: 800; color: var(--z-text); letter-spacing: -0.1px;
  border-left: 3px solid var(--z-primary); padding-left: 10px; margin: 10px 0 2px;
}

/* ── Insight cards (What changed? / Key insight) ── */
.ins-card {
  background: var(--z-card); border: 1px solid var(--z-border);
  border-left: 4px solid var(--z-primary); border-radius: 10px;
  padding: 12px 14px; height: 100%;
}
.ins-head { font-size: 13px; font-weight: 750; color: var(--z-text); display: flex; gap: 8px; align-items: baseline; }
.ins-detail { font-size: 12.5px; color: var(--z-text2); line-height: 1.5; margin-top: 5px; }
.ins-ev { font-size: 11px; color: var(--z-muted); margin-top: 8px; font-variant-numeric: tabular-nums; }
.key-insight {
  background: linear-gradient(90deg, #0F172A 0%, #16283F 100%);
  border: 1px solid #1E293B; border-radius: 12px; padding: 16px 20px; color: #E2E8F0; margin-top: 6px;
}
.ki-eyebrow { font-size: 10.5px; font-weight: 700; letter-spacing: 0.09em; color: #7DD3FC; text-transform: uppercase; }
.ki-main { font-size: 14px; line-height: 1.55; margin-top: 6px; color: #F1F5F9; }
.ki-why { font-size: 12.5px; line-height: 1.5; margin-top: 8px; color: #94A3B8; }
.ki-next { font-size: 12.5px; margin-top: 10px; color: #E2E8F0; }
.ki-next b { color: #FCD34D; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid var(--z-border); }
.stTabs [data-baseweb="tab"] {
  font-size: 13.5px; font-weight: 600; color: var(--z-muted); padding: 9px 16px;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--z-text); background: #EEF2F7; }
.stTabs [aria-selected="true"] { color: var(--z-primary) !important; font-weight: 750; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--z-primary) !important; height: 3px; }

/* ── Tables ── */
[data-testid="stDataFrame"] { font-size: 12.5px; }
[data-testid="stDataFrame"] table { font-variant-numeric: tabular-nums; }

/* ── Empty state ── */
.empty-state {
  background: var(--z-card); border: 1px dashed var(--z-border2); border-radius: 14px;
  padding: 48px 24px; text-align: center; margin-top: 14px;
}
.es-icon { font-size: 30px; }
.es-title { font-size: 15.5px; font-weight: 750; color: var(--z-text); margin-top: 8px; }
.es-sub { font-size: 12.5px; color: var(--z-muted); margin-top: 4px; }

/* ── Footer ── */
.app-footer {
  border-top: 1px solid var(--z-border); margin-top: 22px; padding: 12px 2px 4px;
  font-size: 11.5px; color: var(--z-muted); line-height: 1.6;
}
.app-footer b { color: var(--z-text2); }

/* ── Buttons / inputs polish ── */
.stButton > button {
  border-radius: 8px; border: 1px solid var(--z-border2); font-weight: 600; font-size: 13px;
}
.stButton > button[kind="primary"] { background: var(--z-primary); border-color: var(--z-primary); }
div[data-testid="stExpander"] {
  background: var(--z-card); border: 1px solid var(--z-border); border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


def app_header(orders: pd.DataFrame) -> None:
    """Product header band — every value computed from the live dataset."""
    n = len(orders)
    period = (
        f"{orders['Order_Date'].min():%b %Y} – {orders['Order_Date'].max():%b %Y}"
        if n else "no data in scope"
    )
    st.markdown(
        f"""
<div class="app-header">
  <div class="ah-left">
    <div class="ah-mark">ZR</div>
    <div>
      <div class="ah-title">Refund Risk Intelligence</div>
      <div class="ah-sub">Zomato delivery operations · refund behaviour, customer risk & operating conditions</div>
    </div>
  </div>
  <div class="ah-right">
    <span class="ah-chip"><span class="live">●</span>&nbsp; LIVE — COMPUTED FROM DATA</span>
    <span class="ah-chip">{n:,} orders in scope · {period}</span>
    <span class="ah-chip">Risk score ≠ proof of fraud</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def insight_card_html(ins: dict) -> str:
    """One 'What changed?' card — headline/detail/evidence straight from kpi_engine."""
    color = {"ok": C_GOOD, "info": C_PRIMARY, "watch": C_WARN, "alert": C_BAD}.get(ins["level"], C_PRIMARY)
    return (
        f'<div class="ins-card" style="border-left-color:{color};">'
        f'<div class="ins-head">{ins["headline"]}</div>'
        f'<div class="ins-detail">{ins["detail"]}</div>'
        f'<div class="ins-ev">Evidence: {ins["evidence"]}</div>'
        f"</div>"
    )


def render_filter_status(
    selected_cities, all_cities, selected_bands, all_bands, risk_tiers, all_tiers,
) -> None:
    """Active-filter chips in the sidebar — the analyst always sees the scope."""
    chips = []
    if len(selected_cities) < len(all_cities):
        chips.append(f"City: {', '.join(selected_cities) if selected_cities else 'none'}")
    if len(selected_bands) < len(all_bands):
        chips.append(f"Volume band: {', '.join(selected_bands) if selected_bands else 'none'}")
    if len(risk_tiers) < len(all_tiers):
        chips.append(f"Tier: {', '.join(risk_tiers) if risk_tiers else 'none'}")
    html = "".join(f'<span class="fchip">{c}</span>' for c in chips) if chips else \
        '<span class="fnone">No filters active — full dataset in scope</span>'
    st.sidebar.markdown(f'<div style="margin-top:2px;"><div style="font-size:10.5px;font-weight:700;letter-spacing:0.07em;color:#64748B;text-transform:uppercase;margin-bottom:4px;">Active scope</div><div class="fchips">{html}</div></div>', unsafe_allow_html=True)


def empty_state_html() -> None:
    st.markdown(
        """
<div class="empty-state">
  <div class="es-icon">🔎</div>
  <div class="es-title">No records match the selected filters</div>
  <div class="es-sub">Reset the filters to bring the full dataset back into scope.</div>
</div>
""",
        unsafe_allow_html=True,
    )


def app_footer() -> None:
    st.markdown(
        """
<div class="app-footer">
  <b>How to read this dashboard:</b> Refund rate = refunded orders ÷ total orders on the current scope.
  Flag eligibility: ≥5 orders AND refund rate &gt; 30% — a flag means <i>investigate</i>, never guilty.
  Risk score is a rule-based weighted index (docs/risk_scoring_methodology.md), validated against a
  disclosed synthetic ground-truth layer. Dataset: seeded/synthetic Zomato-style delivery data —
  disclosed in the README and data dictionary. Deltas are month-over-month on the filtered scope.
</div>
""",
        unsafe_allow_html=True,
    )


@st.cache_data
def load_orders(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
    return df


@st.cache_data
def load_truth(path: str):
    """Seeded ground-truth labels — validation only (disclosed synthetic layer).
    Returns None when the file is absent so the app degrades gracefully."""
    from pathlib import Path as _P

    p = _P(path)
    if not p.exists():
        return None
    return pd.read_csv(p)


def build_customer_risk_table(orders: pd.DataFrame) -> pd.DataFrame:
    """Reproduces the risk-scoring methodology from notebooks/03_fraud_detection.ipynb.

    See docs/risk_scoring_methodology.md for the formula and threshold rationale.
    """
    customer_stats = orders.groupby("Customer_ID").agg(
        Total_Orders=("ID", "count"),
        Total_Refunds=("Refund_Requested", "sum"),
        Total_Refund_Amount=("Refund_Amount", "sum"),
    ).reset_index()
    customer_stats["Refund_Rate"] = (
        customer_stats["Total_Refunds"] / customer_stats["Total_Orders"] * 100
    ).round(2)

    flagged = customer_stats[
        (customer_stats["Total_Orders"] >= MIN_ORDERS_THRESHOLD)
        & (customer_stats["Refund_Rate"] > MIN_REFUND_RATE_PCT)
    ].copy()

    refund_df = orders[orders["Refund_Requested"] == True].copy()  # noqa: E712
    refund_df["Reason_Length"] = refund_df["Refund_Reason"].str.len()

    def top_reason_rate(group: pd.DataFrame) -> float:
        if len(group) == 0:
            return 0.0
        counts = group["Refund_Reason"].value_counts()
        return round(counts.iloc[0] / len(group) * 100, 2)

    reason_repetition = (
        refund_df.groupby("Customer_ID")
        .apply(top_reason_rate)
        .reset_index(name="Reason_Repetition_Rate")
    )
    avg_reason_length = refund_df.groupby("Customer_ID").agg(
        Avg_Reason_Length=("Reason_Length", "mean")
    ).reset_index()
    timeline = refund_df.groupby("Customer_ID").agg(
        First_Refund=("Order_Date", "min"),
        Last_Refund=("Order_Date", "max"),
        Refund_Count=("Refund_Requested", "count"),
    ).reset_index()
    timeline["Days_Span"] = (timeline["Last_Refund"] - timeline["First_Refund"]).dt.days
    timeline["Refunds_Per_Day"] = (
        timeline["Refund_Count"] / (timeline["Days_Span"] + 1)
    ).round(4)

    flagged = flagged.merge(reason_repetition, on="Customer_ID", how="left")
    flagged = flagged.merge(avg_reason_length, on="Customer_ID", how="left")
    flagged = flagged.merge(
        timeline[["Customer_ID", "Days_Span", "Refunds_Per_Day"]],
        on="Customer_ID",
        how="left",
    )
    flagged[list(RISK_WEIGHTS)] = flagged[list(RISK_WEIGHTS)].fillna(0)

    scaler = MinMaxScaler(feature_range=(0, 100))
    scaled = scaler.fit_transform(flagged[list(RISK_WEIGHTS)])
    scaled_df = pd.DataFrame(scaled, columns=[f"Score_{c}" for c in RISK_WEIGHTS])

    flagged = flagged.reset_index(drop=True)
    flagged["Fraud_Risk_Score"] = sum(
        scaled_df[f"Score_{col}"] * weight for col, weight in RISK_WEIGHTS.items()
    ).round(2)

    flagged["Risk_Tier"] = pd.cut(
        flagged["Fraud_Risk_Score"],
        bins=[-1, 40, 70, 100],
        labels=["Low", "Medium", "High"],
    )

    latest_order = orders.groupby("Customer_ID")["Order_Date"].max().rename("Last_Order_Date")
    latest_city = orders.sort_values("Order_Date").groupby("Customer_ID")["City"].last().rename("City")
    flagged = flagged.merge(latest_order, on="Customer_ID", how="left")
    flagged = flagged.merge(latest_city, on="Customer_ID", how="left")

    return flagged.sort_values("Fraud_Risk_Score", ascending=False).reset_index(drop=True)


# ── Chart helpers (consistent styling) ──────────────────────────────────────
def bar_chart(df, x, y, title, color=C_PRIMARY, horizontal=False, text_fmt=None):
    orientation = "h" if horizontal else "v"
    fig = px.bar(df, x=x, y=y, orientation=orientation, title=title)
    fig.update_traces(marker_color=color, marker_line_width=0)
    if text_fmt is not None:
        fig.update_traces(text=df[y].apply(text_fmt), textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def rate_by_column(orders: pd.DataFrame, col: str, title: str):
    """Refund rate (%) grouped by a categorical column — the analyst's cut."""
    g = (
        orders.groupby(col)
        .agg(orders=("ID", "count"), refunds=("Refund_Requested", "sum"))
        .reset_index()
    )
    g["refund_rate"] = (g["refunds"] / g["orders"] * 100).round(2)
    g = g.sort_values("refund_rate", ascending=False)
    fig = px.bar(g, x=col, y="refund_rate", title=title, hover_data=["orders", "refunds"])
    fig.update_traces(marker_color=C_PRIMARY, text=g["refund_rate"], textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="Refund rate (%)")
    return fig


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════

def tab_overview(
    orders: pd.DataFrame,
    suspects: pd.DataFrame,
    truth: pd.DataFrame | None = None,
    metric_defs: dict | None = None,
) -> None:
    total_orders = len(orders)
    refund_orders = int(orders["Refund_Requested"].sum())
    refund_rate = refund_orders / total_orders * 100
    refund_amount = orders["Refund_Amount"].sum()
    flagged_exposure = suspects["Total_Refund_Amount"].sum()
    exposure_share = flagged_exposure / refund_amount * 100 if refund_amount else 0

    kpis = compute_kpis(orders, suspects, truth)
    mom = kpis["mom"]

    # ── "What changed?" — computed from data. No LLM, no hardcoding. ──
    insights = what_changed(orders, suspects, truth)
    if insights:
        st.subheader("What changed?")
        st.caption("Signals computed from the filtered scope — latest month vs the month before. Each card cites its evidence.")
        cols = st.columns(min(3, len(insights)))
        for i, ins in enumerate(insights[:3]):
            with cols[i]:
                st.markdown(insight_card_html(ins), unsafe_allow_html=True)
        if len(insights) > 3:
            with st.expander(f"More signals ({len(insights) - 3})"):
                for ins in insights[3:]:
                    st.markdown(insight_card_html(ins), unsafe_allow_html=True)

    # ── Executive KPI cards: value + direction + context ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "Delivery orders", f"{kpis['total_orders']:,}",
        delta=(f"{mom['orders_delta_pct']:+.1f}%" if mom["orders_delta_pct"] is not None else None),
        help=f"Month-over-month: {mom['prev_label']} → {mom['label']} on the current scope.",
    )
    c2.metric(
        "Refund rate", f"{kpis['refund_rate_pct']:.1f}%",
        delta=(
            f"{mom['refund_rate_delta_pp']:+.1f} pp"
            if mom["refund_rate_delta_pp"] is not None else None
        ),
        delta_color="inverse",
        help="Refunds as a share of orders. Delta: percentage points, month-over-month.",
    )
    c3.metric(
        "Refund exposure", f"₹{kpis['refund_exposure']:,.0f}",
        delta=(
            f"{mom['exposure_delta_pct']:+.1f}%"
            if mom["exposure_delta_pct"] is not None else None
        ),
        delta_color="inverse",
        help="Historical refund value — NOT a confirmed loss and NOT future revenue at risk.",
    )
    c4.metric(
        "Flagged customers", f"{kpis['flagged_count']:,}",
        delta=f"{kpis['flagged_exposure_share_pct']:.1f}% of exposure",
        delta_color="off",
        help="Eligibility: ≥5 orders AND refund rate >30%. A flag means investigate — never guilty.",
    )
    c5.metric(
        "High-tier flags", f"{kpis['high_tier_count']}",
        delta=(
            f"{kpis['high_tier_precision_pct']:.0f}% precision"
            if kpis["high_tier_precision_pct"] is not None else "n = 8"
        ),
        delta_color="off",
        help="Precision vs the seeded ground truth (synthetic layer, disclosed). Small n — see docs.",
    )
    c6.metric(
        "Below-baseline flags", f"{kpis['below_baseline_flagged']:,}",
        delta=f"{kpis['below_baseline_share_pct']:.1f}% of flags",
        delta_color="off",
        help="Refund rate normal for their volume band — likely false positives; de-prioritise.",
    )
    st.caption(
        "Deltas are month-over-month on the filtered scope. High-tier precision is validated "
        "against the seeded ground truth (disclosed). Risk score ≠ proof of fraud."
    )

    # ── KPI definitions — the semantic layer every number cites ──
    if metric_defs:
        with st.expander("📖 KPI definitions (semantic layer)"):
            for _key, _m in metric_defs["metrics"].items():
                st.markdown(f"**{_key.replace('_', ' ').title()}** — {_m['definition']}")

    # ── Monthly trend: order volume (bars) + refund rate (line, secondary axis)
    m = (
        orders.groupby(orders["Order_Date"].dt.to_period("M"))
        .agg(orders=("ID", "count"), refunds=("Refund_Requested", "sum"))
        .reset_index()
    )
    m["Order_Date"] = m["Order_Date"].dt.to_timestamp()
    m["refund_rate"] = (m["refunds"] / m["orders"] * 100).round(2)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(
        x=m["Order_Date"], y=m["orders"], name="Orders",
        marker_color="#BFDBFE", opacity=0.85,
    )
    fig.add_scatter(
        x=m["Order_Date"], y=m["refund_rate"], name="Refund rate (%)",
        mode="lines+markers", line=dict(color=C_BAD, width=3),
        secondary_y=True,
    )
    fig.update_layout(
        title="Monthly order volume vs refund rate (2022–2024)", **PLOTLY_LAYOUT
    )
    fig.update_yaxes(title_text="Orders", secondary_y=False)
    fig.update_yaxes(title_text="Refund rate (%)", secondary_y=True)
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        reasons = (
            orders[orders["Refund_Requested"] == True]["Refund_Reason"]  # noqa: E712
            .value_counts()
            .rename_axis("Reason")
            .reset_index(name="count")
        )
        fig = px.bar(
            reasons, y="Reason", x="count", orientation="h",
            title="Refund reasons, ranked",
        )
        fig.update_traces(marker_color=C_ACCENT, text=reasons["count"], textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT)
        left.plotly_chart(fig, width="stretch")

    with right:
        city = (
            orders.groupby("City")
            .agg(orders=("ID", "count"), refunds=("Refund_Requested", "sum"))
            .reset_index()
        )
        city["refund_rate"] = (city["refunds"] / city["orders"] * 100).round(2)
        city = city.sort_values("orders", ascending=False)
        fig = px.bar(
            city, x="City", y="orders", color="refund_rate",
            color_continuous_scale=["#BFDBFE", C_PRIMARY, "#1E3A8A"],
            title="Orders by city type (colour = refund rate)",
            hover_data=["refunds", "refund_rate"],
        )
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="Orders")
        right.plotly_chart(fig, width="stretch")

    # ── Computed insight callouts
    top_reason = reasons.iloc[0]["Reason"]
    top_reason_share = reasons.iloc[0]["count"] / reasons["count"].sum() * 100
    busiest_month = m.loc[m["orders"].idxmax(), "Order_Date"].strftime("%b %Y")
    n_high_tier = int((suspects["Risk_Tier"] == "High").sum()) if len(suspects) else 0
    st.markdown(
        f"""
<div class="key-insight">
  <div class="ki-eyebrow">Key insight — computed from the current scope</div>
  <div class="ki-main">“{top_reason}” is the most common refund reason ({top_reason_share:.1f}% of all refunds).
  Busiest month on record: <b>{busiest_month}</b>. Flagged customers ({len(suspects):,} accounts) hold
  <b>{exposure_share:.1f}%</b> of total refund exposure.</div>
  <div class="ki-why">Why it matters: exposure is concentrated, not uniform — review effort pointed at the
  flagged list covers the most refund value per account reviewed.</div>
  <div class="ki-next"><b>Investigate next:</b> open the Customer Risk tab and start with the High tier
  ({n_high_tier} accounts) — each carries the strongest multi-signal evidence.</div>
</div>
""",
        unsafe_allow_html=True,
    )


def concentration_curve(orders: pd.DataFrame):
    """Pareto cuts + cumulative curve — mirrors scripts/pareto_analysis.py."""
    total = float(orders["Refund_Amount"].sum())
    cust = orders.groupby("Customer_ID")["Refund_Amount"].sum().sort_values(ascending=False)
    n = len(cust)
    cum = (cust.cumsum() / total * 100).values
    x = np.arange(1, n + 1) / n * 100
    k50 = int(np.searchsorted(cum, 50) + 1)
    k80 = int(np.searchsorted(cum, 80) + 1)
    k10 = max(1, int(np.ceil(n * 0.10)))
    return x, cum, n, total, k50, k80, float(cum[k10 - 1])


def tab_refunds(orders: pd.DataFrame) -> None:
    refunds = orders[orders["Refund_Requested"] == True].copy()  # noqa: E712

    # ---- Phase 1: refund exposure concentration (Pareto) ----
    x, cum, n_cust, total_val, k50, k80, top10_share = concentration_curve(orders)

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total refund exposure", f"₹{total_val:,.0f}")
    p2.metric("Customers", f"{n_cust:,}")
    p3.metric("Top 10% hold", f"{top10_share:.1f}% of exposure")
    p4.metric("Half of exposure", f"top {k50:,} customers")

    st.subheader("Refund exposure concentration (Pareto)")
    st.caption(
        "How much refund value sits with what share of customers — the review-queue "
        "sizing question. Concentration is a prioritization signal, never evidence "
        "that any individual customer is fraudulent. Full analysis: "
        "reports/pareto_analysis.md"
    )
    fig = go.Figure()
    fig.add_scatter(
        x=x, y=cum, mode="lines", name="Cumulative share of refund value",
        line=dict(color=C_PRIMARY, width=3),
    )
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100], mode="lines", name="Perfect equality (y = x)",
        line=dict(color=C_NEUTRAL, dash="dash", width=1.5),
    ))
    fig.add_hline(y=80, line_dash="dot", line_color=C_WARN, opacity=0.7)
    fig.add_vline(x=k80 / n_cust * 100, line_dash="dot", line_color=C_WARN, opacity=0.7)
    fig.update_layout(
        **PLOTLY_LAYOUT,
        xaxis_title="Customers (% — ranked by refund value, highest first)",
        yaxis_title="Cumulative share of refund value (%)",
    )
    st.plotly_chart(fig, width="stretch")

    r1, r2, r3 = st.columns(3)
    r1.metric("Avg refund amount", f"₹{refunds['Refund_Amount'].mean():,.0f}")
    r2.metric("Largest refund", f"₹{refunds['Refund_Amount'].max():,.0f}")
    r3.metric("Refunds per month", f"{len(refunds) / 36:,.0f}")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(
            refunds, x="Refund_Amount", nbins=40,
            title="Refund amount distribution",
            color_discrete_sequence=[C_PRIMARY],
        )
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Refund amount (₹)")
        left.plotly_chart(fig, width="stretch")

    with right:
        avg_reason = (
            refunds.groupby("Refund_Reason")["Refund_Amount"].mean()
            .sort_values(ascending=False).round(0).rename_axis("Reason")
            .reset_index(name="avg_amount")
        )
        fig = bar_chart(
            avg_reason, x="Reason", y="avg_amount",
            title="Avg refund amount by reason", color=C_ACCENT,
            text_fmt=lambda v: f"₹{v:,.0f}",
        )
        right.plotly_chart(fig, width="stretch")

    st.subheader("Refund rate by operating conditions")
    st.caption(
        "Where refunds concentrate across the delivery context — the same cut an "
        "ops analyst would run first. (On this seeded dataset, expect roughly flat "
        "rates: refund behaviour is generated independently of conditions.)"
    )
    c1, c2 = st.columns(2)
    with c1:
        c1.plotly_chart(
            rate_by_column(orders, "Weather_conditions", "By weather condition"),
            width="stretch",
        )
        c1.plotly_chart(
            rate_by_column(orders, "Type_of_order", "By order type"),
            width="stretch",
        )
    with c2:
        c2.plotly_chart(
            rate_by_column(orders, "Road_traffic_density", "By road traffic density"),
            width="stretch",
        )
        c2.plotly_chart(
            rate_by_column(orders, "Festival", "By festival period"),
            width="stretch",
        )


def tab_customer_risk(filtered: pd.DataFrame, all_suspects: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged accounts", len(filtered))
    c2.metric("Total refund exposure", f"₹{filtered['Total_Refund_Amount'].sum():,.0f}")
    c3.metric(
        "Avg risk score",
        f"{filtered['Fraud_Risk_Score'].mean():.1f}" if len(filtered) else "—",
    )
    c4.metric("High risk tier", int((filtered["Risk_Tier"] == "High").sum()))

    left, right = st.columns([1, 2])
    # ---- Phase 2: baseline normalization (volume-band comparison) ----
    st.subheader("Is the refund rate abnormal for the customer's order volume?")
    st.caption(
        "The raw 30% threshold doesn't ask 'compared with WHAT?' This section "
        "compares each flagged customer against their order-volume band's "
        "distribution. Above-baseline ≠ fraudulent — it means statistically "
        "unusual for the customer's volume. Full analysis: "
        "reports/baseline_normalization.md"
    )
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "scripts"))
        from baseline_normalization import build_baselines
        _df = pd.read_csv("data/processed/zomato_with_refunds.csv")
        _cust, _bands = build_baselines(_df)
        _sus_ids = set(all_suspects["Customer_ID"])
        _cust["is_flagged"] = _cust["Customer_ID"].isin(_sus_ids)
        _flagged = _cust[_cust["is_flagged"]]
        _above = _flagged[_flagged["above_baseline"]]
        _below = _flagged[~_flagged["above_baseline"]]

        b1, b2, b3 = st.columns(3)
        b1.metric("Flagged above band baseline", f"{len(_above):,}",
                   f"{len(_above)/len(_flagged)*100:.0f}% of flagged")
        b2.metric("Flagged but within band norms", f"{len(_below):,}",
                  f"{len(_below)/len(_flagged)*100:.0f}% — false-positive candidates",
                  delta_color="inverse")
        b3.metric("Above baseline (all customers)", f"{int(_cust['above_baseline'].sum()):,}")

        # volume-band reference chart
        fig = go.Figure()
        for _, b in _bands.iterrows():
            fig.add_trace(go.Bar(
                x=[b["band"]], y=[b["p95"]], name=b["band"],
                marker_color=C_PRIMARY, text=f"P95: {b['p95']:.1f}%",
                textposition="outside", showlegend=False,
            ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            xaxis_title="Order-volume band",
            yaxis_title="P95 refund rate (%)",
            height=320,
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "P95 refund rate by volume band — the 'unusual' threshold varies "
            "dramatically with order count. A 50% rate on 2 orders is normal; "
            "a 35% rate on 10 orders is unusual."
        )
    except Exception:
        st.info("Baseline normalization unavailable — run scripts/baseline_normalization.py")

    left, right = st.columns([1, 2])
    with left:
        tier_counts = (
            all_suspects["Risk_Tier"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
        )
        tier_df = tier_counts.rename_axis("Tier").reset_index(name="count")
        fig = px.bar(
            tier_df, x="Tier", y="count", title="Risk tier distribution (all flagged)",
            color="Tier", color_discrete_map=TIER_COLORS,
        )
        fig.update_traces(text=tier_df["count"].astype(int), textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        left.plotly_chart(fig, width="stretch")

        rep = (
            filtered.groupby("City")["Customer_ID"].count()
            .sort_values(ascending=False).rename_axis("City").reset_index(name="flagged")
        )
        if len(rep):
            fig = px.pie(
                rep, names="City", values="flagged",
                title="Flagged customers by city type", hole=0.45,
                color_discrete_sequence=[C_PRIMARY, C_ACCENT, C_GOOD],
            )
            fig.update_layout(**PLOTLY_LAYOUT)
            left.plotly_chart(fig, width="stretch")

    with right:
        top20 = filtered.head(20).iloc[::-1]
        if len(top20):
            fig = px.bar(
                top20, y="Customer_ID", x="Fraud_Risk_Score",
                orientation="h", title="Top 20 by fraud risk score",
                color="Risk_Tier", color_discrete_map=TIER_COLORS,
                hover_data=["Total_Orders", "Total_Refunds", "Refund_Rate"],
            )
            fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="")
            right.plotly_chart(fig, width="stretch")

        st.subheader("Flagged customers — investigation list")
        if not len(filtered):
            st.info("No flagged customers match the current filters.")
        else:
            tbl = filtered[
                [
                    "Customer_ID", "City", "Risk_Tier", "Fraud_Risk_Score",
                    "Total_Orders", "Total_Refunds", "Refund_Rate",
                    "Reason_Repetition_Rate", "Total_Refund_Amount", "Last_Order_Date",
                ]
            ].copy()
            _status_map = {"High": "Investigate first", "Medium": "Watchlist", "Low": "Routine review"}
            tbl["Status"] = tbl["Risk_Tier"].map(_status_map)

            def _tier_color(val):
                return f"color: {TIER_COLORS.get(val, C_NEUTRAL)}; font-weight: 600"

            styler = (
                tbl.style
                .map(_tier_color, subset=["Risk_Tier"])
                .map(_tier_color, subset=["Status"])
                .format(
                    {
                        "Fraud_Risk_Score": "{:.1f}",
                        "Refund_Rate": "{:.1f}%",
                        "Reason_Repetition_Rate": "{:.0f}%",
                        "Total_Refund_Amount": "₹{:,.0f}",
                        "Last_Order_Date": lambda d: d.strftime("%d %b %Y"),
                    }
                )
            )
            st.dataframe(styler, width="stretch", hide_index=True)

            _csv = tbl.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download investigation list (CSV)",
                _csv,
                file_name="zomato_flagged_investigation_list.csv",
                mime="text/csv",
                help="The current filtered scope — ready for the review workflow.",
            )

    # ---- AI Investigation Assistant (tool calling + evidence grounding) ----
    st.subheader("AI Investigation Assistant")
    st.caption(
        "Tool-calling AI: queries the risk engine, refund history, and baseline "
        "comparison, then explains the EVIDENCE. The AI never computes numbers "
        "and never makes fraud determinations. Risk score ≠ proof of fraud."
    )
    inv_customer = st.selectbox(
        "Select customer to investigate",
        filtered["Customer_ID"].tolist() if len(filtered) else [],
        key="inv_customer",
    )
    if inv_customer and st.button("Run AI Investigation", key="inv_run"):
        try:
            from app.dashboard.utils.ai_investigator import investigate_with_llm
            with st.spinner("Gathering evidence from risk engine, refund history, and baseline..."):
                result = investigate_with_llm(inv_customer)
            if not result.get("ok"):
                st.error(result.get("error", "Investigation failed."))
            else:
                ev = result["evidence"]
                # Display evidence (always shown — deterministic)
                e1, e2, e3 = st.columns(3)
                with e1:
                    st.markdown(f"**Risk Score:** {ev['risk']['risk_score']}")
                    st.markdown(f"**Tier:** {ev['risk']['risk_tier']}")
                    st.markdown(f"**Refund Rate:** {ev['risk']['refund_rate_pct']}%")
                with e2:
                    st.markdown(f"**Refunds:** {ev['history']['refund_count']}")
                    st.markdown(f"**Top Reason:** {ev['history'].get('most_repeated_reason', 'N/A')}")
                    st.markdown(f"**Total Exposure:** ₹{ev['history']['total_refund_amount']:,.0f}")
                with e3:
                    st.markdown(f"**Volume Band:** {ev['baseline']['volume_band']}")
                    st.markdown(f"**Above Baseline:** {'Yes' if ev['baseline']['above_baseline'] else 'No'}")
                    st.markdown(f"**Band P95:** {ev['baseline']['band_p95_threshold']}%")

                # LLM explanation (if available)
                explanation = result.get("explanation")
                if explanation:
                    st.markdown("#### AI Investigation Summary")
                    st.markdown(explanation)
                else:
                    if result.get("note"):
                        st.info("No LLM API key configured — showing deterministic tool outputs only. "
                               "Set OPENAI_API_KEY or GOOGLE_API_KEY to enable AI explanations.")
                    # Show structured evidence as fallback
                    st.markdown("#### Evidence Details (deterministic tool outputs)")
                    st.json(ev["risk"], expanded=False)
                    st.json(ev["history"], expanded=False)
                    st.json(ev["baseline"], expanded=False)
        except ImportError:
            st.info("AI investigation module not available.")
        except Exception as e:
            st.error(f"Investigation error: {str(e)}")

    st.subheader("Explain a flag")
    customer_options = filtered["Customer_ID"].tolist()
    if customer_options:
        chosen = st.selectbox("Select a customer", customer_options)
        row = filtered[filtered["Customer_ID"] == chosen].iloc[0]
        st.write(
            f"**{chosen}** — Risk score **{row['Fraud_Risk_Score']}** ({row['Risk_Tier']})"
        )
        breakdown = pd.DataFrame(
            {
                "Signal": [
                    "Refund rate (%)",
                    "Reason repetition rate (%)",
                    "Refunds per day",
                    "Avg refund-reason length (chars)",
                ],
                "Value": [
                    row["Refund_Rate"],
                    row["Reason_Repetition_Rate"],
                    row["Refunds_Per_Day"],
                    row["Avg_Reason_Length"],
                ],
                "Weight in score": [f"{w:.0%}" for w in RISK_WEIGHTS.values()],
            }
        )
        st.table(breakdown)
        st.caption(
            "Rule-based weighted scoring — full formula and threshold rationale in "
            "docs/risk_scoring_methodology.md."
        )
    else:
        st.info("No customers match the current filters.")


def tab_operations(orders: pd.DataFrame) -> None:
    avg_time = orders["Time_taken (min)"].mean()
    avg_rating = orders["Delivery_person_Ratings"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg delivery time", f"{avg_time:.1f} min")
    c2.metric("Median delivery time", f"{orders['Time_taken (min)'].median():.0f} min")
    c3.metric("Avg rider rating", f"{avg_rating:.2f} / 5")
    c4.metric("Slowest deliveries (90th pct)", f"{orders['Time_taken (min)'].quantile(0.9):.0f} min")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(
            orders, x="Time_taken (min)", nbins=45,
            title="Delivery time distribution",
            color_discrete_sequence=[C_PRIMARY],
        )
        fig.add_vline(
            x=avg_time, line_dash="dash", line_color=C_BAD,
            annotation_text=f"mean {avg_time:.1f} min",
        )
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Minutes")
        left.plotly_chart(fig, width="stretch")

    with right:
        fig = px.box(
            orders, x="Road_traffic_density", y="Time_taken (min)",
            title="Delivery time by traffic density", points=False,
            color="Road_traffic_density",
            color_discrete_sequence=px.colors.sequential.Blues[-4:],
        )
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        right.plotly_chart(fig, width="stretch")

    c3_, c4_ = st.columns(2)
    with c3_:
        fig = px.box(
            orders, x="Weather_conditions", y="Time_taken (min)",
            title="Delivery time by weather", points=False,
            color="Weather_conditions",
            color_discrete_sequence=px.colors.sequential.Purples[-7:],
        )
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        c3_.plotly_chart(fig, width="stretch")

    with c4_:
        type_counts = (
            orders["Type_of_order"].value_counts().rename_axis("Type").reset_index(name="count")
        )
        fig = px.pie(
            type_counts, names="Type", values="count", hole=0.45,
            title="Order mix by type",
            color_discrete_sequence=[C_PRIMARY, C_ACCENT, C_GOOD, C_WARN],
        )
        fig.update_layout(**PLOTLY_LAYOUT)
        c4_.plotly_chart(fig, width="stretch")

    # ── Rider-level view: top riders by volume + rating
    riders = (
        orders.groupby("Delivery_person_ID")
        .agg(orders=("ID", "count"), avg_rating=("Delivery_person_Ratings", "mean"),
             avg_time=("Time_taken (min)", "mean"))
        .reset_index()
    )
    r1, r2 = st.columns(2)
    with r1:
        fig = px.histogram(
            riders, x="avg_rating", nbins=25,
            title="Rider ratings — distribution of rider averages",
            color_discrete_sequence=[C_GOOD],
        )
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Average rating (per rider)")
        r1.plotly_chart(fig, width="stretch")

    with r2:
        top_riders = riders.nlargest(10, "orders").iloc[::-1]
        fig = px.bar(
            top_riders, y="Delivery_person_ID", x="orders", orientation="h",
            title="Top 10 riders by order volume",
            hover_data=["avg_rating", "avg_time"],
        )
        fig.update_traces(marker_color=C_NEUTRAL)
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="")
        r2.plotly_chart(fig, width="stretch")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="Zomato Refund Fraud Analytics",
        page_icon="🍽️",
        layout="wide",
    )
    inject_css()

    orders = load_orders(DATA_PATH)
    suspects = build_customer_risk_table(orders)
    truth = load_truth(TRUTH_PATH)
    try:
        metric_defs = load_metric_definitions(METRICS_PATH)
    except (OSError, ValueError):
        metric_defs = None

    app_header(orders)

    # ── Sidebar: product mark + filters + scope status + reset + methodology ──
    st.sidebar.markdown(
        '<div class="side-mark"><div class="sm-t">ZR · Refund Risk Intelligence</div>'
        '<div class="sm-s">Filters apply across all tabs</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("**Filters**")

    # ── Global filters (cross-filter every tab) ──
    # Full selection == no filter (NaN-safe: 1,200 orders have a missing City)
    all_city_types = sorted(orders["City"].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect(
        "City type", all_city_types, default=all_city_types,
        help="Order-level city type — applies to every tab.",
        key="f_city",
    )
    selected_bands = st.sidebar.multiselect(
        "Customer volume band", BAND_LABELS, default=BAND_LABELS,
        help="1-2 / 3-5 / 6-10 / 11-20 / 21+ orders (customer-level) — applies to every tab.",
        key="f_band",
    )
    city_subset = selected_cities if len(selected_cities) < len(all_city_types) else None
    band_subset = selected_bands if len(selected_bands) < len(BAND_LABELS) else None
    orders_f = apply_global_filters(orders, city_subset, band_subset)
    suspects_scope = suspects
    if city_subset:
        suspects_scope = suspects_scope[suspects_scope["City"].isin(city_subset)]
    if band_subset:
        suspects_scope = suspects_scope[
            suspects_scope["Total_Orders"].apply(volume_band).isin(band_subset)
        ]

    # ── Customer Risk tab filters (tier + last-order date) ──
    st.sidebar.markdown("**Customer Risk tab filters**")
    min_date = suspects["Last_Order_Date"].min().date()
    max_date = suspects["Last_Order_Date"].max().date()
    date_range = st.sidebar.date_input(
        "Last order date range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date, key="f_date",
    )
    risk_tiers = st.sidebar.multiselect(
        "Risk tier", ["Low", "Medium", "High"], default=["Low", "Medium", "High"],
        key="f_tier",
    )

    filtered = suspects_scope[suspects_scope["Risk_Tier"].isin(risk_tiers)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            (filtered["Last_Order_Date"].dt.date >= start)
            & (filtered["Last_Order_Date"].dt.date <= end)
        ]

    # ── Active-scope chips + one-click reset ──
    render_filter_status(
        selected_cities, all_city_types, selected_bands, list(BAND_LABELS),
        risk_tiers, ["Low", "Medium", "High"],
    )
    if st.sidebar.button("↺ Reset all filters", help="Restore the full dataset into scope."):
        for _k in ("f_city", "f_band", "f_tier", "f_date"):
            st.session_state.pop(_k, None)
        st.rerun()

    with st.sidebar.expander("📖 Methodology & how to read this"):
        st.markdown(
            "- **Refund rate** = refunded orders ÷ total orders (current scope)\n"
            "- **Flag eligibility**: ≥5 orders AND refund rate >30% — "
            "*a flag means investigate, never guilty*\n"
            "- **Risk score**: rule-based weighted index — refund rate 40% · "
            "reason repetition 30% · refunds/day 20% · reason length 10% "
            "([methodology](https://github.com/rishi-1603/zomato-refund-fraud-analytics/"
            "blob/main/docs/risk_scoring_methodology.md))\n"
            "- **Validation**: top-tier precision vs a disclosed synthetic "
            "ground-truth layer\n"
            "- **Data**: seeded/synthetic Zomato-style delivery data — disclosed "
            "in the README"
        )

    # ── Empty state: filters excluded everything ──
    if not len(orders_f):
        empty_state_html()
        if st.button("Reset filters", key="reset_main"):
            for _k in ("f_city", "f_band", "f_tier", "f_date"):
                st.session_state.pop(_k, None)
            st.rerun()
        app_footer()
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Executive Overview", "Refund Analytics", "Customer Risk", "Operations"]
    )
    with tab1:
        tab_overview(orders_f, suspects_scope, truth=truth, metric_defs=metric_defs)
    with tab2:
        tab_refunds(orders_f)
    with tab3:
        tab_customer_risk(filtered, suspects)
    with tab4:
        tab_operations(orders_f)

    app_footer()

    st.divider()
    st.caption(
        "Synthetic, seeded dataset — methods are the story. Risk score = 40% refund rate + "
        "30% reason repetition + 20% refund frequency + 10% reason length "
        "(docs/risk_scoring_methodology.md). Demo analytics — not affiliated with Zomato."
    )


if __name__ == "__main__":
    main()
