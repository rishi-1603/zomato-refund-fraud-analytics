"""FoodTrust — Zomato Refund Risk & Operations Analytics
Professional dark-theme BI dashboard matching PDF mockups.

Four analytical pages:
1. Executive Overview    — Primary KPIs, trends, review queue snapshot
2. Refund Patterns       — Concentration, amounts, volume-band context
3. Risk Review           — Explain a flag, baselines, review list, AI investigation
4. Operations            — Review prioritization, capacity planning, analyst workflow

Run: streamlit run dashboard/app.py
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from sklearn.preprocessing import MinMaxScaler

_REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = str(_REPO_ROOT / "data" / "processed" / "zomato_with_refunds.csv")
TRUTH_PATH = str(_REPO_ROOT / "data" / "processed" / "ground_truth_customer_risk.csv")
METRICS_PATH = str(_REPO_ROOT / "data" / "metrics.json")

try:
    from kpi_engine import (
        BAND_LABELS,
        apply_global_filters,
        band_refund_rates,
        compute_kpis,
        load_metric_definitions,
        volume_band,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dashboard.kpi_engine import (
        BAND_LABELS,
        apply_global_filters,
        band_refund_rates,
        compute_kpis,
        load_metric_definitions,
        volume_band,
    )

try:
    from decision_history import render_history
except ImportError:
    from dashboard.decision_history import render_history

try:
    from decision_copilot import ask
except ImportError:
    from dashboard.decision_copilot import ask

RISK_WEIGHTS = {
    "Refund_Rate": 0.40,
    "Reason_Repetition_Rate": 0.30,
    "Refunds_Per_Day": 0.20,
    "Avg_Reason_Length": 0.10,
}

MIN_ORDERS_THRESHOLD = 5
MIN_REFUND_RATE_PCT = 30

# ─── Dark Console Palette ───
C_PRIMARY = "#58a6ff"   # blue
C_ACCENT = "#A78BFA"    # violet
C_GOOD = "#3fb950"      # green
C_WARN = "#d29922"      # amber
C_BAD = "#f85149"       # red
C_NEUTRAL = "#94A3B8"   # slate
C_ACCENT_2 = "#0D9488"    # teal
TIER_COLORS = {"Low": C_GOOD, "Medium": C_WARN, "High": C_BAD}

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    height=420,
    margin=dict(l=56, r=32, t=62, b=52),
    title_font=dict(size=15, color="#e6edf3", family="'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif"),
    font=dict(family="'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif", size=12, color="#c9d1d9"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    hoverlabel=dict(bgcolor="#161b22", font_size=12, font_color="#e6edf3", bordercolor="#30363d"),
    hovermode="closest",
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d", showgrid=True, title_font=dict(color="#c9d1d9"), tickfont=dict(color="#c9d1d9")),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d", showgrid=True, title_font=dict(color="#c9d1d9"), tickfont=dict(color="#c9d1d9")),
    legend=dict(bgcolor="rgba(22,27,34,0.9)", bordercolor="#30363d", borderwidth=1, font=dict(color="#c9d1d9")),
)


def _inr(value: float, decimals: int = 0) -> str:
    """Format currency with Indian digit grouping (₹9,74,344)."""
    negative = value < 0
    text = f"{abs(value):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    sign = "-" if negative else ""
    return f"{sign}₹{whole}" + (f".{frac}" if frac else "")


def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root{
  --bg:#0d1117;
  --bg-2:#161b22;
  --panel:#161b22;
  --panel-2:#1f2937;
  --panel-3:#263347;
  --border:#30363d;
  --border-light:#484f58;
  --text:#e6edf3;
  --text-2:#c9d1d9;
  --muted:#8b949e;
  --accent:#2f81f7;
  --accent-glow:rgba(47, 129, 247,.15);
  --accent-2:#58a6ff;
  --accent-3:#a371f7;
  --warn:#d29922;
  --danger:#f85149;
  --success:#3fb950;
  --gradient-1:linear-gradient(135deg,#0d1117 0%,#161b22 50%,#161b22 100%);
  --gradient-accent:linear-gradient(135deg,#2f81f7 0%,#58a6ff 100%);
  --shadow-sm:0 2px 8px rgba(0,0,0,.2);
  --shadow-md:0 8px 24px rgba(0,0,0,.3);
  --shadow-lg:0 16px 48px rgba(0,0,0,.4);
  --radius-sm:6px;
  --radius-md:10px;
  --radius-lg:16px;
  --radius-xl:24px;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

body{
  font:14px/1.65 'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  min-height:100vh;
}

body::before{
  content:'';
  position:fixed;
  top:0;left:0;right:0;bottom:0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%,rgba(47, 129, 247,.08),transparent),
    radial-gradient(ellipse 60% 40% at 80% 80%,rgba(88, 166, 255,.05),transparent);
  pointer-events:none;
  z-index:0;
}
a{color:var(--accent-2);text-decoration:none;transition:color .2s}
a:hover{color:var(--accent)}

/* ===== HEADER ===== */
header{
  position:relative;
  z-index:1;
  max-width:none;
  margin:0 auto;
  padding:48px 40px 32px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(47, 129, 247,.03) 0%,transparent 100%);
}

.eyebrow{
  font-size:10px;
  letter-spacing:.2em;
  text-transform:uppercase;
  color:var(--accent);
  font-weight:700;
  margin-bottom:12px;
  display:flex;
  align-items:center;
  gap:8px;
}
.eyebrow::before{
  content:'';
  width:24px;
  height:2px;
  background:var(--gradient-accent);
  border-radius:1px;
}

h1{
  font-size:clamp(28px,4vw,42px);
  line-height:1.15;
  margin:0 0 8px;
  font-weight:800;
  background:linear-gradient(135deg,#e6edf3 0%,#8b949e 100%);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  background-clip:text;
}

.sub{
  color:var(--muted);
  font-size:15px;
  max-width:760px;
  margin:0;
  line-height:1.6;
}

.notice{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:8px 14px;
  border:1px solid rgba(245,158,11,.2);
  background:rgba(245,158,11,.06);
  font-size:11px;
  color:var(--warn);
  margin:16px 0 0;
  border-radius:var(--radius-sm);
  font-weight:500;
}
.notice::before{content:'ℹ';font-size:12px}

/* ===== MAIN ===== */
main{
  position:relative;
  z-index:1;
  max-width:none;
  margin:0 auto;
  padding:0 40px 40px;
}
/* Streamlit's own block container caps content width; lift it so wide screens fill */
.stMainBlockContainer,
.block-container{
  max-width:none;
  padding-left:0;
  padding-right:0;
}

/* ===== FILTERS ===== */
.filters{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:16px;
  background:var(--panel);
  padding:20px 24px;
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  box-shadow:var(--shadow-md);
  margin-bottom:20px;
}
.filters label{
  display:flex;
  flex-direction:column;
  gap:6px;
  font-size:10px;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.08em;
  font-weight:700;
}
select,input[type=text],input[type=date],input[type=number]{
  min-width:0;
  max-width:100%;
  background:var(--bg-2);
  color:var(--text);
  border:1px solid var(--border);
  border-radius:var(--radius-sm);
  padding:9px 12px;
  transition:all .2s ease;
  font-size:13px;
}
select:hover,input:hover{border-color:var(--border-light)}
select:focus,input:focus{
  border-color:var(--accent);
  outline:none;
  box-shadow:0 0 0 3px var(--accent-glow);
}
input[type=checkbox]{accent-color:var(--accent);width:16px;height:16px;cursor:pointer}
input[type=range]{accent-color:var(--accent);cursor:pointer}

.scope{
  display:flex;
  align-items:center;
  gap:18px;
  flex-wrap:wrap;
  margin:16px 0 20px;
  color:var(--muted);
  font-size:13px;
  padding:12px 16px;
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius-md);
}
.scope strong{color:var(--text);font-weight:600}
.scope label{display:flex;align-items:center;gap:6px;cursor:pointer}
.scope input[type=date]{max-width:150px}

button{
  background:var(--panel-2);
  color:var(--text);
  border:1px solid var(--border);
  padding:9px 16px;
  border-radius:var(--radius-sm);
  cursor:pointer;
  transition:all .2s ease;
  font-weight:500;
  font-size:13px;
}
button:hover{
  background:var(--accent);
  color:#071a13;
  border-color:var(--accent);
  transform:translateY(-1px);
  box-shadow:0 4px 12px var(--accent-glow);
}
button:active{transform:translateY(0)}

/* ===== KPI CARDS ===== */
.kpis{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:16px;
  margin:20px 0;
}
.kpi{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:20px 22px;
  position:relative;
  overflow:hidden;
  transition:all .25s ease;
  box-shadow:var(--shadow-sm);
}
.kpi::before{
  content:'';
  position:absolute;
  top:0;left:0;right:0;
  height:3px;
  background:var(--gradient-accent);
  opacity:.7;
}
.kpi:hover{
  transform:translateY(-3px);
  box-shadow:var(--shadow-md);
  border-color:var(--border-light);
}
.kpi .label{
  font-size:10px;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.08em;
  font-weight:700;
  margin-bottom:6px;
}
.value{
  font-size:30px;
  line-height:1.1;
  font-weight:800;
  margin:8px 0 4px;
  color:#fff;
  letter-spacing:-.02em;
}
.kpi small{
  color:var(--muted);
  font-size:11px;
  display:block;
  margin-top:4px;
  line-height:1.4;
}

/* ===== CHARTS ===== */
.charts{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:18px;
  margin:20px 0;
}
.card{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:20px 22px;
  box-shadow:var(--shadow-sm);
  transition:box-shadow .2s ease;
}
.card:hover{box-shadow:var(--shadow-md)}
.card h3{
  font-size:14px;
  font-weight:600;
  color:var(--text-2);
  margin-bottom:12px;
  padding-bottom:10px;
  border-bottom:1px solid var(--border);
}
.plot{
  width:100%;
  height:360px;
  border-radius:var(--radius-sm);
}
.card p{
  font-size:13px;
  color:var(--muted);
  margin:10px 0 0;
  line-height:1.5;
}

/* ===== TABLE ===== */
.tablewrap{
  overflow:auto;
  max-height:500px;
  border:1px solid var(--border);
  border-radius:var(--radius-md);
  background:var(--panel);
}
.tablewrap table{
  border-collapse:collapse;
  width:100%;
  font-size:12px;
  text-align:left;
}
th{
  background:var(--panel-2);
  position:sticky;
  top:0;
  font-weight:600;
  padding:11px 14px;
  border-bottom:1px solid var(--border);
  color:var(--text-2);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.04em;
}
td{
  padding:10px 14px;
  border-bottom:1px solid var(--border);
  white-space:nowrap;
  color:var(--text);
}
tbody tr:hover{background:rgba(47, 129, 247,.04)}
tbody tr:last-child td{border-bottom:none}

/* ===== SUMMARY / INSIGHT ===== */
.summary{
  padding:18px 22px;
  border:1px solid rgba(47, 129, 247,.2);
  background:linear-gradient(135deg,rgba(47, 129, 247,.06) 0%,rgba(88, 166, 255,.04) 100%);
  border-radius:var(--radius-md);
  margin:20px 0;
  font-size:13px;
  color:var(--text);
  line-height:1.6;
  box-shadow:var(--shadow-sm);
}

.empty{
  padding:48px;
  border:1px dashed var(--border);
  text-align:center;
  color:var(--muted);
  border-radius:var(--radius-md);
  background:var(--panel);
}

[hidden]{display:none!important}

/* ===== VIDEO PLAYER ===== */
.player{
  width:100%;
  max-width:1100px;
  background:#000;
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  box-shadow:var(--shadow-lg);
  overflow:hidden;
}

/* ===== FOOTER ===== */
footer{
  font-size:12px;
  color:var(--muted);
  border-top:1px solid var(--border);
  padding-top:20px;
  margin-top:40px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  flex-wrap:wrap;
  gap:8px;
}
footer a{color:var(--muted);transition:color .2s}
footer a:hover{color:var(--accent)}

.error{color:var(--danger)}

.split{
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  flex-wrap:wrap;
  margin:16px 0
}

.muted{color:var(--muted);font-size:13px}
.scope label{max-width:100%;flex-wrap:wrap}

@keyframes fadeIn{
  from{opacity:0;transform:translateY(8px)}
  to{opacity:1;transform:translateY(0)}
}
main section,main .kpis,main .charts{animation:fadeIn .4s ease-out}

@media(max-width:1024px){
  header,main,footer{padding:20px 24px}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .charts{grid-template-columns:1fr}
  .value{font-size:26px}
}
@media(max-width:640px){
  header,main,footer{padding:16px 16px}
  .filters{grid-template-columns:1fr}
  .kpis{grid-template-columns:1fr 1fr}
  .value{font-size:22px}
  h1{font-size:24px}
  .plot{height:280px}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{transition:none!important;animation:none!important}
}
.charts>.card{min-width:0}
.plot{min-width:0;overflow:hidden}
.tablewrap{max-width:100%}
input[type=date]{max-width:160px}
#threshold{width:120px}
</style>
""", unsafe_allow_html=True)


def ft_header(orders: pd.DataFrame, export_df: pd.DataFrame | None = None) -> None:
    n = len(orders)
    period = (
        f"{orders['Order_Date'].min():%b %Y} – {orders['Order_Date'].max():%b %Y}"
        if n else "no data in scope"
    )
    head_col, act_col = st.columns([0.85, 0.15])
    with head_col:
        st.markdown(
            f"""
<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;
  background:var(--panel);border:1px solid var(--border);
  border-radius:12px;padding:16px 20px;margin-bottom:16px;flex-wrap:wrap;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:14px;min-width:0;">
    <div style="width:38px;height:38px;border-radius:10px;flex-shrink:0;
      background:linear-gradient(135deg,#58a6ff,#7C3AED);
      display:flex;align-items:center;justify-content:center;
      font-weight:800;font-size:15px;letter-spacing:.5px;color:#fff;">FT</div>
    <div>
      <div style="font-size:18px;font-weight:800;letter-spacing:-0.2px;color:var(--text);">FoodTrust — Refund Risk & Marketplace Intelligence</div>
      <div style="font-size:11.5px;color:var(--muted);margin-top:1px;">Zomato case study — refund patterns, customer comparisons and evidence for human review</div>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="font-size:10.5px;font-weight:600;letter-spacing:.03em;
      color:var(--muted);background:var(--bg);border:1px solid var(--border);
      border-radius:999px;padding:5px 11px;white-space:nowrap;"><span style="color:#2f81f7;margin-right:4px;">●</span>&nbsp; Historical dataset · Interactive analysis · Synthetic refund layer</span>
    <span style="font-size:10.5px;font-weight:600;letter-spacing:.03em;
      color:var(--muted);background:var(--bg);border:1px solid var(--border);
      border-radius:999px;padding:5px 11px;white-space:nowrap;">{n:,} orders in scope · {period}</span>
    <span style="font-size:10.5px;font-weight:600;letter-spacing:.03em;
      color:var(--muted);background:var(--bg);border:1px solid var(--border);
      border-radius:999px;padding:5px 11px;white-space:nowrap;">Delivery data: public · Refund layer: synthetic</span>
    <span style="font-size:10.5px;font-weight:600;letter-spacing:.03em;
      color:var(--muted);background:var(--bg);border:1px solid var(--border);
      border-radius:999px;padding:5px 11px;white-space:nowrap;">Review priority score ≠ proof of fraud</span>
  </div>
</div>
""", unsafe_allow_html=True)
    with act_col:
        if export_df is not None and len(export_df):
            st.download_button(
                "⬇ Export queue", data=export_df.to_csv(index=False).encode("utf-8"),
                file_name="flagged_queue_current_scope.csv", mime="text/csv",
                help="Download the flagged investigation queue for the current filter scope.",
                use_container_width=True,
            )


def ft_empty_state() -> None:
    st.markdown(
        """
<div style="background:var(--panel);border:1px dashed var(--border);
  border-radius:12px;padding:40px 20px;text-align:center;margin-top:16px;">
  <div style="font-size:28px;">🔎</div>
  <div style="font-size:14px;font-weight:700;color:var(--text);margin-top:8px;">No records match the selected filters</div>
  <div style="font-size:12px;color:var(--muted);margin-top:4px;">Reset the filters to bring the full dataset back into scope.</div>
</div>
""", unsafe_allow_html=True)


def ft_footer() -> None:
    st.markdown(
        """
<div style="border-top:1px solid var(--border);margin-top:40px;padding-top:20px;
  font-size:12px;color:var(--muted);line-height:1.6;">
  <b>How to read this:</b> Refund rate = refunded orders ÷ total orders in the current view.
  A customer is flagged at ≥5 orders AND refund rate > 30% — a flag means <i>investigate</i>, never guilty.
  The score is a simple weighted formula (refund rate 40% · reason repetition 30% · refunds/day 20% · reason length 10%),
  checked against known test cases in this synthetic dataset.
  The data is seeded/synthetic — disclosed in the README and data dictionary.
  KPI chips compare with the previous month only where data coverage allows.
</div>
""", unsafe_allow_html=True)


@st.cache_data
def load_orders(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
    return df


@st.cache_data
def load_truth(path: str):
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return None
    return pd.read_csv(p)


def build_customer_risk_table(orders: pd.DataFrame) -> pd.DataFrame:
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

    refund_df = orders[orders["Refund_Requested"] == True].copy()
    refund_df["Reason_Length"] = refund_df["Refund_Reason"].str.len()

    def top_reason_rate(group: pd.DataFrame) -> float:
        if len(group) == 0:
            return 0.0
        counts = group["Refund_Reason"].value_counts()
        return round(counts.iloc[0] / len(group) * 100, 2)

    reason_repetition = (
        refund_df.groupby("Customer_ID")[["Refund_Reason"]]
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
        on="Customer_ID", how="left",
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


# ─── Chart helpers ───
def bar_chart(df, x, y, title, color="#58a6ff", horizontal=False, text_fmt=None):
    orientation = "h" if horizontal else "v"
    fig = px.bar(df, x=x, y=y, orientation=orientation, title=title)
    fig.update_traces(marker_color=color, marker_line_width=0)
    if text_fmt is not None:
        fig.update_traces(text=df[y].apply(text_fmt), textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def concentration_curve(orders: pd.DataFrame):
    total = float(orders["Refund_Amount"].sum())
    cust = orders.groupby("Customer_ID")["Refund_Amount"].sum().sort_values(ascending=False)
    n = len(cust)
    cum = (cust.cumsum() / total * 100).values
    x = np.arange(1, n + 1) / n * 100
    k50 = int(np.searchsorted(cum, 50) + 1)
    k80 = int(np.searchsorted(cum, 80) + 1)
    k10 = max(1, int(np.ceil(n * 0.10)))
    return x, cum, n, total, k50, k80, float(cum[k10 - 1])


# ─── Pages ───

def page_executive(orders: pd.DataFrame, suspects: pd.DataFrame, truth: pd.DataFrame | None, metric_defs: dict | None):
    refund_amount = orders["Refund_Amount"].sum()
    flagged_exposure = suspects["Total_Refund_Amount"].sum()
    exposure_share = flagged_exposure / refund_amount * 100 if refund_amount else 0

    kpis = compute_kpis(orders, suspects, truth)
    mom = kpis["mom"]
    import importlib, sys
    engine = sys.modules[compute_kpis.__module__]
    if "partial_periods" not in mom:
        engine = importlib.reload(engine)
        kpis = engine.compute_kpis(orders, suspects, truth)
        mom = kpis["mom"]
    if "partial_periods" not in mom:
        st.warning("Analytics modules are refreshing. Please reload this page.")
        return
    if mom.get("partial_periods"):
        st.warning(mom["coverage_note"])

    # Hero KPI row
    refund_orders = kpis["refund_orders"]
    refunders = int(orders.loc[orders["Refund_Requested"] == True, "Customer_ID"].nunique())
    avg_refund = kpis["refund_exposure"] / refund_orders if refund_orders else 0.0
    refunders_share = kpis["flagged_count"] / refunders * 100 if refunders else 0.0

    def _mom_chip(delta, suffix="%", up_is_good=True):
        if delta is None or mom.get("partial_periods"):
            return ""
        cls = "up" if (delta >= 0) == up_is_good else "down"
        arrow = "▲" if delta >= 0 else "▼"
        return f'<span class="{cls}">{arrow} {delta:+.1f}{suffix}</span> vs {mom["prev_label"]}'

    kpi_cards = [
        ("#58a6ff", "🛒", "Delivery orders", f"{kpis['total_orders']:,}",
         _mom_chip(mom["orders_delta_pct"]), "Observed orders in the current scope."),
        ("#f85149", "↩", "Refund requests", f"{refund_orders:,}",
         f"{kpis['refund_rate_pct']:.1f}% of orders", "A refund request is not a confirmed refund."),
        ("#d29922", "₹", "Total refund amount", _inr(kpis["refund_exposure"]),
         _mom_chip(mom["exposure_delta_pct"], up_is_good=False),
         "Historical refund value — not a confirmed loss."),
        ("#a371f7", "🛡", "Accounts flagged for review", f"{kpis['flagged_count']:,}",
         f"{refunders_share:.1f}% of refunders",
         "Eligibility: ≥5 orders AND refund rate >30%. A flag means review — never a guilt verdict."),
        ("#2f81f7", "⚠", "Potential exposure", _inr(kpis["flagged_exposure"]),
         f"{kpis['flagged_exposure_share_pct']:.1f}% of refunds",
         "Refund value held by the flagged pool."),
        ("#EC4899", "₹", "Avg refund amount", _inr(avg_refund),
         "Per refund request", "Total refund amount ÷ refund requests."),
    ]
    st.markdown(
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:8px 0 4px;">' + "".join(
            f'<div style="background:#161b22;border:1px solid #30363d;border-left:3px solid {color};border-radius:12px;padding:14px 14px 12px;min-width:0;box-shadow:0 1px 4px rgba(0,0,0,.06);">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="width:28px;height:28px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:13px;background:rgba(88, 166, 255,.15);color:{color};">{emoji}</div>'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#8b949e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;">{label}</div></div>'
            f'<div style="font-size:22px;font-weight:800;color:#fff;font-variant-numeric:tabular-nums;letter-spacing:-.4px;white-space:nowrap;line-height:1.2;">{value}</div>'
            f'<div style="font-size:11px;color:#8b949e;margin-top:3px;font-variant-numeric:tabular-nums;line-height:1.4;">{sub}</div>'
            f'<div style="font-size:11px;color:#8b949e;margin-top:2px;font-variant-numeric:tabular-nums;line-height:1.4;">{note}</div></div>'
            for color, emoji, label, value, sub, note in kpi_cards
        ) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "A refund request is not a confirmed refund, and a flag is a review priority — "
        "not proof of fraud. The refund layer is synthetic and disclosed in the README."
    )

    # KPI definitions expander
    if metric_defs:
        with st.expander("📖 KPI definitions"):
            for _key, _m in metric_defs["metrics"].items():
                st.markdown(f"**{_key.replace('_', ' ').title()}** — {_m['definition']}")

    # Review queue snapshot
    if len(suspects):
        top_n = min(8, len(suspects))
        rows = ""
        for _, r in suspects.head(top_n).iterrows():
            tier = str(r["Risk_Tier"])
            rows += (
                f'<div style="display:flex;align-items:center;gap:12px;padding:8px 4px;'
                f'border-bottom:1px solid rgba(38,55,92,.5);font-size:12.5px;'
                f'background:#161b22;border:1px solid #30363d;border-radius:12px;padding:6px 14px;margin-top:6px;">'
                f'<span style="font-size:10px;font-weight:800;letter-spacing:.07em;border-radius:999px;'
                f'padding:2px 9px;flex-shrink:0;'
                f'{"color:#f85149;background:rgba(248, 81, 73,.13);border:1px solid rgba(248, 81, 73,.4);" if tier=="High" else "color:#d29922;background:rgba(210, 153, 34,.12);border:1px solid rgba(210, 153, 34,.4);" if tier=="Medium" else "color:#3fb950;background:rgba(63, 185, 80,.12);border:1px solid rgba(63, 185, 80,.4);"}">{tier.upper()}</span>'
                f'<span style="color:#e6edf3;font-weight:700;font-variant-numeric:tabular-nums;width:92px;">#{r["Customer_ID"]}</span>'
                f'<span style="color:#c9d1d9;font-variant-numeric:tabular-nums;white-space:nowrap;"><b>{r["Fraud_Risk_Score"]:.1f}</b> risk score</span>'
                f'<span style="color:#c9d1d9;font-variant-numeric:tabular-nums;white-space:nowrap;">{r["Refund_Rate"]:.0f}% refund rate · {int(r["Total_Refunds"])}/{int(r["Total_Orders"])} orders</span>'
                f'<span style="flex:1;"></span>'
                f'<span style="color:#c9d1d9;font-variant-numeric:tabular-nums;"><b>₹{r["Total_Refund_Amount"]:,.0f}</b> exposure</span>'
                f'</div>'
            )
        st.subheader("Review queue — highest priority first")
        st.caption(
            "The highest review priority scores in the current view. A flag means look closer — never a guilt verdict. "
            "The full list, baselines and per-customer details are on the Customer Risk Review page."
        )
        st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:6px 14px;margin-top:6px;">{rows}</div>', unsafe_allow_html=True)

    # Monthly trend: dual-axis
    m = (
        orders.groupby(orders["Order_Date"].dt.to_period("M"))
        .agg(orders=("ID", "count"), refunds=("Refund_Requested", "sum"))
        .reset_index()
    )
    m["Order_Date"] = m["Order_Date"].dt.to_timestamp()
    m["refund_rate"] = (m["refunds"] / m["orders"] * 100).round(2)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=m["Order_Date"], y=m["orders"], name="Orders",
                marker_color="#58a6ff", opacity=0.65,
                text=m["orders"], textposition="outside", textfont=dict(size=10))
    fig.add_scatter(x=m["Order_Date"], y=m["refund_rate"], name="Refund rate (%)",
                    mode="lines+markers", line=dict(color="#f85149", width=3),
                    marker=dict(size=8, color="#f85149", line=dict(color="#0d1117", width=1)),
                    secondary_y=True)
    # Annotate the month with the highest refund rate
    if len(m):
        peak_idx = m["refund_rate"].idxmax()
        fig.add_annotation(x=m.loc[peak_idx, "Order_Date"], y=m.loc[peak_idx, "refund_rate"],
                           text=f"Peak {m.loc[peak_idx, 'refund_rate']:.1f}%",
                           showarrow=True, arrowhead=2, ax=0, ay=-30,
                           font=dict(color="#d29922", size=11), secondary_y=True)
    fig.update_layout(title="Monthly order volume vs refund rate (observed data)", **PLOTLY_LAYOUT,
                      bargap=0.25)
    fig.update_yaxes(title_text="Orders", secondary_y=False)
    fig.update_yaxes(title_text="Refund rate (%)", secondary_y=True)
    st.plotly_chart(fig, width="stretch")
    st.caption("February starts on the 11th and April ends on the 6th, so the first and last bars cover "
               "partial months. The line shows observed refund rate, not a trend forecast.")

    # Bottom row: Reasons + City
    left, right = st.columns(2)
    with left:
        reasons = (
            orders[orders["Refund_Requested"] == True]["Refund_Reason"]
            .value_counts().rename_axis("Reason").reset_index(name="count")
        )
        fig = px.bar(reasons, y="Reason", x="count", orientation="h",
                     title="Refund reasons, ranked")
        fig.update_traces(marker_color="#a371f7", text=reasons["count"],
                          textposition="inside", insidetextanchor="end",
                          textfont=dict(color="white", size=12))
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
        fig = px.bar(city, x="City", y="orders", color="refund_rate",
                     color_continuous_scale=["#1E3A8A", "#58a6ff", "#FCA5A5"],
                     title="Orders by city type (colour = refund rate)",
                     text="orders", hover_data=["refunds", "refund_rate"])
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="Orders")
        fig.update_coloraxes(colorbar_title="Refund rate (%)")
        right.plotly_chart(fig, width="stretch")

    # Risk tier distribution + Claim behaviour
    tier_left, tier_right = st.columns(2)
    with tier_left:
        tier_counts = (
            suspects["Risk_Tier"].value_counts()
            .reindex(["Low", "Medium", "High"]).fillna(0).astype(int)
        )
        tdf = tier_counts.rename_axis("Tier").reset_index(name="Flagged accounts")
        fig = px.bar(tdf, x="Tier", y="Flagged accounts", color="Tier",
                     category_orders={"Tier": ["Low", "Medium", "High"]},
                     color_discrete_map={"Low": "#3fb950", "Medium": "#d29922", "High": "#f85149"},
                     title="Flagged pool by risk tier", text="Flagged accounts")
        fig.update_layout(**PLOTLY_LAYOUT)
        fig.update_traces(textposition="outside", marker_line_width=0)
        tier_left.plotly_chart(fig, width="stretch")
        gt_note = ""
        if truth is not None and truth["Planted_Risk"].notna().any():
            gt_mix = truth["Planted_Risk"].value_counts(normalize=True) * 100
            gt_note = (
                f"Planted ground-truth mix across all {truth['Customer_ID'].nunique():,} customers "
                f"(validation only, disclosed): Low {gt_mix.get('Low', 0):.0f}% · "
                f"Medium {gt_mix.get('Medium', 0):.0f}% · High {gt_mix.get('High', 0):.0f}%."
            )
        st.caption(
            "Tiers come from the documented review priority score on the flagged pool — not from the planted labels. "
            + gt_note
        )

    with tier_right:
        refund_rows = orders[orders["Refund_Requested"] == True]
        claims_per_refunder = refund_orders / refunders if refunders else 0.0
        refunds_by_cust = refund_rows.groupby("Customer_ID").size()
        repeat_claim_rate = (refunds_by_cust >= 2).mean() * 100 if len(refunds_by_cust) else 0.0
        reason_words = refund_rows["Refund_Reason"].dropna().str.split().str.len().mean()
        top_reason_share_val = (
            refund_rows["Refund_Reason"].value_counts(normalize=True).iloc[0] * 100
            if len(refund_rows) else 0.0
        )
        chips = [
            (f"{claims_per_refunder:.1f}", "Avg. refund requests per refunding customer"),
            (f"{repeat_claim_rate:.1f}%", "Refunding customers with repeat claims"),
            (f"{reason_words:.1f}", "Avg. reason length (words)"),
            (f"{top_reason_share_val:.1f}%", "Top reason's share of all refunds"),
        ]
        st.markdown("**Claim behaviour**")
        cc1, cc2, cc3, cc4 = st.columns(4)
        for col, (v, l) in zip((cc1, cc2, cc3, cc4), chips):
            col.markdown(
                f'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px 12px;text-align:left;height:100%;">'
                f'<div style="font-size:19px;font-weight:800;color:#e6edf3;font-variant-numeric:tabular-nums;">{v}</div>'
                f'<div style="font-size:10px;font-weight:600;color:#8b949e;margin-top:2px;line-height:1.35;">{l}</div></div>',
                unsafe_allow_html=True)
        st.caption("Behavioural patterns of refund requests in the current scope. Repeat claiming is an investigation signal, not proof of fraud.")

    # Key insight banner
    top_reason = reasons.iloc[0]["Reason"]
    top_reason_share = reasons.iloc[0]["count"] / reasons["count"].sum() * 100
    busiest_month = m.loc[m["orders"].idxmax(), "Order_Date"].strftime("%b %Y")
    n_high_tier = int((suspects["Risk_Tier"] == "High").sum()) if len(suspects) else 0
    st.markdown(
        f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px 20px;margin-top:8px;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="font-size:10px;font-weight:700;letter-spacing:.09em;color:#60a5fa;text-transform:uppercase;">Financial impact & actions — computed from the current scope</div>
  <div style="font-size:13.5px;line-height:1.55;margin-top:6px;color:#e6edf3;">"{top_reason}" is the most common refund reason ({top_reason_share:.1f}% of all refunds).
  Busiest month on record: <b>{busiest_month}</b>. Flagged customers ({len(suspects):,} accounts) hold
  <b>{exposure_share:.1f}%</b> of total refund exposure.</div>
  <div style="font-size:12px;line-height:1.5;margin-top:8px;color:#9ca3af;">Why it matters: exposure is concentrated, not uniform — review effort pointed at the
  flagged list covers the most refund value per account reviewed.</div>
  <div style="font-size:12px;margin-top:10px;color:#e6edf3;"><b>Investigate next:</b> open the Customer Risk Review page and start with the High tier
  ({n_high_tier} accounts) — each carries the strongest evidence.</div>
</div>
""", unsafe_allow_html=True)


def page_refund_patterns(orders: pd.DataFrame, suspects: pd.DataFrame, all_orders: pd.DataFrame | None = None):
    refunds = orders[orders["Refund_Requested"] == True].copy()

    # Pareto concentration
    x, cum, n_cust, total_val, k50, k80, top10_share = concentration_curve(orders)

    p1, p2, p3, p4 = st.columns(4)
    n_refunders = int(refunds["Customer_ID"].nunique())
    p1.metric("Total refund exposure", f"₹{total_val:,.0f}")
    p2.metric("Customers with a refund", f"{n_refunders:,}",
              help=f"{n_refunders:,} of {n_cust:,} customers ({n_refunders / n_cust * 100:.1f}%) "
                   f"have at least one refund. The concentration curve ranks all {n_cust:,} customers.")
    p3.metric("Top 10% hold", f"{top10_share:.1f}% of exposure")
    p4.metric("Half of exposure in", f"top {k50:,} customers")

    st.subheader("Where the refund money concentrates")
    st.caption(
        f"How refund money is spread across customers — this tells you how big the review "
        f"queue needs to be. The curve ranks all {n_cust:,} customers; {n_refunders:,} have "
        f"at least one refund. Concentration is a reason to prioritize, never evidence "
        f"that any individual customer is fraudulent. Full analysis: reports/pareto_analysis.md"
    )
    fig = go.Figure()
    fig.add_scatter(x=x, y=cum, mode="lines", name="Cumulative share of refund value",
                    line=dict(color="#58a6ff", width=3), fill="tozeroy",
                    fillcolor="rgba(88, 166, 255,0.12)")
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Perfect equality (y = x)",
                    line=dict(color="#475569", dash="dash", width=1.5)))
    fig.add_hline(y=80, line_dash="dot", line_color="#d29922", opacity=0.7,
                  annotation_text="80% of value", annotation_position="right")
    fig.add_vline(x=k80 / n_cust * 100, line_dash="dot", line_color="#d29922", opacity=0.7,
                  annotation_text=f"top {k80} customers", annotation_position="top right")
    fig.update_layout(**PLOTLY_LAYOUT,
        xaxis_title="Customers (% — ranked by refund value, highest first)",
        yaxis_title="Cumulative share of refund value (%)")
    st.plotly_chart(fig, width="stretch")

    r1, r2, r3 = st.columns(3)
    active_days = int(orders["Order_Date"].dt.normalize().nunique())
    r1.metric("Avg refund amount", f"₹{refunds['Refund_Amount'].mean():,.0f}")
    r2.metric("Largest refund", f"₹{refunds['Refund_Amount'].max():,.0f}")
    r3.metric("Avg refunds per active day", f"{len(refunds) / active_days:,.1f}",
              help=f"{len(refunds):,} refunds across {active_days} observed order dates "
                   f"({orders['Order_Date'].min():%d %b} – {orders['Order_Date'].max():%d %b %Y}). "
                   f"No partial-month extrapolation.")

    # Flagged behaviour patterns
    if len(suspects):
        reps = suspects["Reason_Repetition_Rate"].dropna()
        vel = suspects["Refunds_Per_Day"].dropna()
        st.subheader("Patterns among flagged customers")
        st.caption("What flagged customers have in common in the current view: repeating the same refund reason, and refunding faster than normal ordering would explain.")
        s1, s2, s3 = st.columns(3)
        s1.metric("Repeat same reason (≥50%)", f"{(reps >= 50).mean() * 100:.1f}%",
                  delta=f"{int((reps >= 50).sum())} of {len(reps)} flagged", delta_color="off",
                  help="Share of flagged customers whose most common refund reason covers at least half of their refunds.")
        s2.metric("Median reason-repetition", f"{reps.median():.0f}%",
                  help="Median share of refunds going to each flagged customer's top reason.")
        s3.metric("Median refund velocity", f"{vel.median():.2f}/day",
                  help="Median refunds per day across the flagged customers' refund window.")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(refunds, x="Refund_Amount", nbins=40,
                           title="Refund amount distribution", color_discrete_sequence=["#58a6ff"])
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Refund amount (₹)")
        left.plotly_chart(fig, width="stretch")

    with right:
        avg_reason = (
            refunds.groupby("Refund_Reason")["Refund_Amount"].mean()
            .sort_values(ascending=False).round(0).rename_axis("Reason")
            .reset_index(name="avg_amount")
        )
        fig = bar_chart(avg_reason, x="Reason", y="avg_amount",
                        title="Avg refund amount by reason", color="#a371f7",
                        text_fmt=lambda v: f"₹{v:,.0f}")
        right.plotly_chart(fig, width="stretch")

    # Delivery conditions — a null result worth stating once, not four flat charts
    st.subheader("Delivery conditions do not explain refunds")
    st.caption(
        "Refund rate stays between 7.5% and 8.4% across every weather, traffic, order-type "
        "and festival segment (overall 7.9%) — conditions don't separate refunders from "
        "non-refunders here. The synthetic refund layer was generated independently of "
        "delivery conditions, so this is the expected result, not a failed analysis."
    )

    # Volume-band refund rates
    band_rates = band_refund_rates(orders, band_source=all_orders if all_orders is not None else orders)
    lo, hi = band_rates["refund_rate"].min(), band_rates["refund_rate"].max()
    st.subheader("Refund rate by customer volume band")
    st.caption(
        f"Aggregate refund rate by each customer's full order history: {lo:.1f}–{hi:.1f}% across "
        f"bands. Order volume alone does not explain refunds; what changes with volume is the "
        f"per-customer P95 threshold used to flag unusual accounts (see Customer Risk Review). "
        f"No customer in this dataset exceeds 20 orders, so the 21+ band is empty and omitted."
    )
    band_rates = band_rates.sort_values("refund_rate", ascending=True)
    fig = px.bar(band_rates, x="refund_rate", y="Volume_Band", orientation="h",
                 title="Refund rate by customer volume band",
                 color="refund_rate", color_continuous_scale=["#1E3A8A", "#58a6ff", "#FCA5A5"],
                 text="refund_rate", hover_data=["customers", "orders", "refunds"])
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.add_vline(x=float(orders["Refund_Requested"].mean() * 100), line_dash="dash",
                  line_color="#94A3B8", opacity=0.7,
                  annotation_text="overall 7.9%", annotation_position="top right")
    fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Refund rate (%)", yaxis_title="Volume band")
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, width="stretch")


def page_risk_review(all_suspects: pd.DataFrame, filtered: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged customers", len(filtered))
    c2.metric("Refund exposure", f"₹{filtered['Total_Refund_Amount'].sum():,.0f}")
    c3.metric("Avg review priority score", f"{filtered['Fraud_Risk_Score'].mean():.1f}" if len(filtered) else "—")
    c4.metric("High risk tier", int((filtered["Risk_Tier"] == "High").sum()))

    # Explain a flag — first thing a reviewer needs: why this customer?
    st.subheader("Explain a flag")
    customer_options = filtered["Customer_ID"].tolist()
    if customer_options:
        chosen = st.selectbox("Select a customer", customer_options, key="inv_customer")
        row = filtered[filtered["Customer_ID"] == chosen].iloc[0]
        st.write(f"**{chosen}** — Review Priority Score **{row['Fraud_Risk_Score']}** ({row['Risk_Tier']})")
        signals = [
            ("Refund rate", row["Refund_Rate"], f"{row['Refund_Rate']:.1f}%", 0.40),
            ("Reason repetition", row["Reason_Repetition_Rate"], f"{row['Reason_Repetition_Rate']:.0f}% same reason", 0.30),
            ("Refund velocity", row["Refunds_Per_Day"], f"{row['Refunds_Per_Day']:.2f} refunds/day", 0.20),
            ("Reason length", row["Avg_Reason_Length"], f"{row['Avg_Reason_Length']:.0f} chars avg", 0.10),
        ]
        pop = all_suspects
        meters = ""
        for name, value, text, weight in signals:
            col_name = {"Refund rate": "Refund_Rate", "Reason repetition": "Reason_Repetition_Rate",
                        "Refund velocity": "Refunds_Per_Day", "Reason length": "Avg_Reason_Length"}[name]
            p95 = float(pop[col_name].quantile(0.95)) if len(pop) else 0.0
            pct = min(100.0, (value / p95 * 100)) if p95 > 0 else 0.0
            over = value >= p95 and p95 > 0
            fill = "over" if over else ""
            note = (f"≥ P95 of flagged ({p95:.1f}) — extreme" if over else f"P95 of flagged: {p95:.1f}")
            meters += (
                f'<div style="margin:10px 0;">'
                f'<div style="display:flex;justify-content:space-between;font-size:11.5px;color:#9ca3af;margin-bottom:4px;">'
                f'<span>{name} <span style="color:#8b949e;">· weight {weight:.0%}</span></span>'
                f'<b>{text}</b></div>'
                f'<div style="height:7px;border-radius:999px;background:#30363d;overflow:hidden;">'
                f'<div class="meter-fill {fill}" style="height:100%;border-radius:999px;background:#58a6ff;'
                f'{"background:linear-gradient(90deg,#d29922,#f85149);" if over else ""} width:{pct:.0f}%"></div></div>'
                f'<div style="font-size:10px;color:#8b949e;margin-top:3px;font-variant-numeric:tabular-nums;">{note}</div>'
                f'</div>'
            )
        st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 16px;">{meters}</div>', unsafe_allow_html=True)
        st.caption(
            "Each bar shows how extreme one score factor is, compared to the 95th percentile "
            "of flagged customers in the current view (0% = at peer P95, 100% = at or above P95). "
            "The score is a simple weighted formula — full details in docs/risk_scoring_methodology.md."
        )
    else:
        st.info("No customers match the current filters.")

    st.subheader("Is the refund rate abnormal for the customer's order volume?")
    st.caption(
        "A flat 30% cutoff doesn't ask 'compared to what?' This section compares each "
        "flagged customer with others who order similar amounts. Above the normal range "
        "≠ fraudulent — it means unusual for their volume. Full analysis: reports/baseline_normalization.md"
    )
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "scripts"))
        from baseline_normalization import build_baselines
        _df = pd.read_csv(DATA_PATH)
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
                  f"{len(_below)/len(_flagged)*100:.0f}% — review context, not an error label", delta_color="inverse")
        b3.metric("Above baseline (all customers)", f"{int(_cust['above_baseline'].sum()):,}")

        fig = go.Figure()
        for _, b in _bands.iterrows():
            fig.add_trace(go.Bar(x=[b["band"]], y=[b["p95"]], name=b["band"],
                marker_color="#58a6ff", text=f"P95: {b['p95']:.1f}%",
                textposition="outside", showlegend=False))
        fig.update_layout(**{**PLOTLY_LAYOUT, "height": 320},
            xaxis_title="Order-volume band", yaxis_title="P95 refund rate (%)")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Normal refund rate (95th percentile) by order volume — what counts as "
            "'unusual' changes a lot with order count. A 50% rate on 2 orders is normal; "
            "a 35% rate on 10 orders is unusual."
        )
    except Exception:
        st.info("Baseline normalization unavailable — run scripts/baseline_normalization.py")

    left, right = st.columns([1, 2])
    with left:
        rep = filtered.groupby("City")["Customer_ID"].count().sort_values(ascending=False).rename_axis("City").reset_index(name="flagged")
        if len(rep):
            fig = px.bar(rep.iloc[::-1], x="flagged", y="City", orientation="h",
                         title="Flagged customers by city type",
                         color_discrete_sequence=["#58a6ff"], text="flagged")
            fig.update_traces(textposition="outside", texttemplate="%{x:,.0f}", cliponaxis=False)
            fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="", xaxis_title="Flagged customers")
            left.plotly_chart(fig, width="stretch")

    with right:
        top20 = filtered.head(20).iloc[::-1]
        if len(top20):
            fig = px.bar(top20, y="Customer_ID", x="Fraud_Risk_Score",
                         orientation="h", title="Top 20 by review priority score",
                         color="Risk_Tier", color_discrete_map={"Low": "#3fb950", "Medium": "#d29922", "High": "#f85149"},
                         hover_data=["Total_Orders", "Total_Refunds", "Refund_Rate"])
            fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="")
            right.plotly_chart(fig, width="stretch")

    # Investigation table
    st.subheader("Flagged customers — review list")
    if not len(filtered):
        st.info("No flagged customers match the current filters.")
    else:
        tbl = filtered[[
            "Customer_ID", "City", "Risk_Tier", "Fraud_Risk_Score",
            "Total_Orders", "Total_Refunds", "Refund_Rate",
            "Reason_Repetition_Rate", "Total_Refund_Amount", "Last_Order_Date",
        ]].copy().rename(columns={"Fraud_Risk_Score": "Review Priority Score"})
        _status_map = {"High": "Investigate first", "Medium": "Watchlist", "Low": "Routine review"}
        tbl["Status"] = tbl["Risk_Tier"].map(_status_map)

        def _tier_badge(val):
            # Colorblind-safe: icon + text, not just color
            if val == "High":
                return "background: rgba(248, 81, 73,0.13); color: #f85149; font-weight: 700"
            if val == "Medium":
                return "background: rgba(210, 153, 34,0.12); color: #d29922; font-weight: 700"
            if val == "Low":
                return "background: rgba(63, 185, 80,0.12); color: #3fb950; font-weight: 700"
            if val == "Investigate first":
                return "background: rgba(248, 81, 73,0.13); color: #f85149; font-weight: 700"
            if val == "Watchlist":
                return "background: rgba(210, 153, 34,0.12); color: #d29922; font-weight: 700"
            if val == "Routine review":
                return "background: rgba(63, 185, 80,0.12); color: #3fb950; font-weight: 700"
            return "color: #9ca3af"

        styler = (
            tbl.style
            .map(_tier_badge, subset=["Risk_Tier"])
            .map(_tier_badge, subset=["Status"])
            .format({
                "Review Priority Score": "{:.1f}", "Refund_Rate": "{:.1f}%",
                "Reason_Repetition_Rate": "{:.0f}%", "Total_Refund_Amount": "₹{:,.0f}",
                "Last_Order_Date": lambda d: d.strftime("%d %b %Y"),
            })
        )
        st.dataframe(styler, width="stretch", hide_index=True)

        _csv = tbl.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download investigation list (CSV)", _csv,
                           file_name="zomato_flagged_investigation_list.csv",
                           mime="text/csv", help="The current filtered scope — ready for the review workflow.")

    # AI Investigation
    with st.expander("🤖 AI Investigation — evidence-grounded customer analysis", expanded=False):
        st.caption(
            "Retrieve a customer's risk signals, refund history and volume-band comparison. "
            "The numeric evidence is computed by the tools; optional AI narration is not validated and needs human review. "
            "A flag is not a fraud determination."
        )
        inv_customer = st.selectbox(
            "Select customer to investigate",
            filtered["Customer_ID"].tolist() if len(filtered) else [],
            key="ai_inv_customer",
        )
        # Cooldown to prevent API hammering
        cooldown_key = "ai_inv_cooldown"
        cooldown_seconds = 3
        last_run = st.session_state.get(cooldown_key, 0)
        import time as _time
        can_run = (_time.time() - last_run) >= cooldown_seconds
        btn_disabled = not can_run or not inv_customer
        if st.button("Run AI Investigation", key="ai_inv_run", disabled=btn_disabled):
            st.session_state[cooldown_key] = _time.time()
            try:
                try:
                    from ai_investigator import investigate_with_llm
                except ImportError:
                    from dashboard.ai_investigator import investigate_with_llm
                with st.spinner("Analyzing customer evidence..."):
                    result = investigate_with_llm(inv_customer)
                if not result.get("ok"):
                    st.error(result.get("error", "Investigation failed."))
                else:
                    ev = result["evidence"]
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        st.markdown(f"**Review Priority Score:** {ev['risk']['risk_score']}")
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

                    explanation = result.get("explanation")
                    if explanation:
                        st.markdown("#### AI Investigation Summary")
                        st.markdown(explanation)
                    else:
                        if result.get("llm_error"):
                            st.warning("Optional AI narration unavailable; deterministic evidence remains available.")
                        if result.get("note"):
                            st.info("No AI key set — showing the raw numbers only. "
                                   "Set OPENAI_API_KEY or GOOGLE_API_KEY to get the AI-written summary.")
                        st.markdown("#### The raw numbers behind this")
                        st.json(ev["risk"], expanded=False)
                        st.json(ev["history"], expanded=False)
                        st.json(ev["baseline"], expanded=False)
            except ImportError:
                st.info("AI investigation module not available.")
            except Exception:
                st.error("Investigation could not complete. Review the data and try again.")


def page_operations(filtered: pd.DataFrame, city_subset=None, band_subset=None, risk_tiers=None):
    # Delivery-condition charts were removed: refunds in this dataset are generated
    # independently of delivery conditions, so those charts carried no signal here.
    st.subheader("Review queue & capacity")
    st.caption("Select cases from the filtered eligible queue. Customer scores and exposures use full source history; date filtering is on last order.")

    try:
        import json
        from decision_engine import plan_reviews
    except ImportError:
        from dashboard.decision_engine import plan_reviews

    filter_context = {"city_types": city_subset or None, "customer_volume_bands": band_subset or None,
                      "risk_tiers": risk_tiers, "last_order_date_range": None}
    scope_id = str(hash(str(filter_context)))
    if st.session_state.get("refund_decision_scope") != scope_id:
        st.session_state["refund_decision_scope"] = scope_id
        st.session_state.pop("refund_decision_record", None)
        st.session_state.pop("refund_decision_queue", None)

    try:
        scope, _ = plan_reviews(filtered, capacity=0, review_cost=0, recoverable_fraction=0, filter_context=filter_context)
    except ValueError as error:
        st.warning("Decision planning is blocked: " + str(error))
        return

    st.metric("Eligible customers in queue", len(filtered))

    with st.form("refund_decision_form"):
        c1, c2, c3 = st.columns(3)
        capacity = c1.number_input("Investigation capacity (customers)", min_value=0, max_value=1000000, value=50, step=1, key="dec_capacity")
        review_cost = c2.number_input("Assumed review cost per customer (₹)", min_value=0.0, max_value=10000000.0, value=250.0, step=50.0, key="dec_cost")
        recovery_pct = c3.number_input("Assumed recoverable exposure (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0, key="dec_recovery")
        action = st.text_input("Proposed action", value="Review cases with human oversight", max_chars=500, key="dec_action")
        metric = st.text_input("Follow-up KPI", value="Verified review outcomes and customer friction", max_chars=500, key="dec_metric")
        follow_up = st.text_input("Validation plan", value="Compare reviewed outcomes with a documented baseline", max_chars=500, key="dec_follow")
        status = st.selectbox("Decision status", ["proposed", "approved", "deferred"], key="dec_status")
        observed = st.text_input("Optional observed follow-up note (user-entered, unverified)", max_chars=500, key="dec_observed")
        submit = st.form_submit_button("Build review decision", type="primary")

    if submit:
        try:
            record, queue = plan_reviews(filtered, capacity, review_cost, recovery_pct / 100,
                                          action=action, success_metric=metric, follow_up=follow_up,
                                          observed_note=observed, status=status, filter_context=filter_context)
            st.session_state["refund_decision_record"] = record
            st.session_state["refund_decision_queue"] = queue
        except ValueError as error:
            st.session_state.pop("refund_decision_record", None)
            st.session_state.pop("refund_decision_queue", None)
            st.error(str(error))

    record = st.session_state.get("refund_decision_record")
    if record:
        st.caption("Snapshot reflects the submitted assumptions. Changing the filtered queue clears it. User-entered follow-up is unverified.")
        c1, c2 = st.columns(2)
        c1.metric("Selected for review", record['scope']['selected_customers'])
        c2.metric("Selected exposure", f"₹{record['evidence']['selected_historical_exposure_inr']:,.2f}")
        st.caption("Selected queue count, refund count and historical exposure: SQLite/pandas reconciliation PASS. Assumed recovery and costs are not validated by that check.")
        scenarios = pd.DataFrame([{'scenario': name, **record['scenarios'][name]} for name in ('low', 'base', 'high')])
        st.dataframe(scenarios, hide_index=True, width="stretch")
        threshold = record['scenarios']['break_even_recovery_fraction']
        st.caption("Break-even assumed recoverable share: " + (f"{threshold:.1%}" if threshold is not None else "not available: selected exposure is zero"))
        st.dataframe(st.session_state["refund_decision_queue"], hide_index=True, width="stretch")
        b1, b2 = st.columns(2)
        b1.download_button("⬇ Download decision record (JSON)", json.dumps(record, indent=2, allow_nan=False).encode('utf-8'),
                           f"refund_decision_{record['scope']['scope_id'][:8]}.json", "application/json", key="dec_download_record")
        b2.download_button("⬇ Download review queue (CSV)", st.session_state["refund_decision_queue"].to_csv(index=False).encode('utf-8'),
                           f"refund_queue_{record['scope']['scope_id'][:8]}.csv", "text/csv", key="dec_download_queue")
        st.caption("The JSON is an aggregate snapshot; the queue CSV includes synthetic customer IDs. Use no sensitive notes. Neither file is server-side case management.")

        # Decision History
        render_history("refund_risk", record, "refund")

    # Deterministic Copilot
    filter_context_copilot = {"city_types": city_subset or None, "customer_volume_bands": band_subset or None,
                      "risk_tiers": risk_tiers, "last_order_date_range": None}
    scope_id_copilot = str(hash(str(filter_context_copilot)))
    if st.session_state.get("refund_copilot_scope") != scope_id_copilot:
        st.session_state["refund_copilot_scope"] = scope_id_copilot
        st.session_state.pop("refund_copilot_answer", None)

    with st.expander("🤖 Ask the queue (deterministic)", expanded=False):
        st.caption("Try: 'How many flagged customers?' or 'What is the refund rate for CUST07704?' One supported metric at a time; no LLM or external provider is used.")
        with st.form("refund_copilot_form"):
            question = st.text_input("Queue question", max_chars=300, key="refund_copilot_question")
            asked = st.form_submit_button("Calculate queue answer")
        if asked:
            try:
                try:
                    from decision_copilot import ask
                except ImportError:
                    from dashboard.decision_copilot import ask
                st.session_state["refund_copilot_answer"] = ask(filtered, question)
            except Exception:
                st.session_state["refund_copilot_answer"] = {"ok": False, "text": "Could not answer. Try a simpler question."}
        answer = st.session_state.get("refund_copilot_answer")
        if answer:
            if answer['ok']:
                st.success(f"{answer['value']:,.2f} {answer['unit']}")
                st.caption(f"Formula: {answer['formula']} · Scope: {answer['scope_customers']} customers · Sources: {', '.join(answer['source_columns'])} · SQLite/pandas queue check: {answer['reconciliation']}.")
                st.caption(answer['warnings'][0])
            else:
                st.info(answer['text'])

    # Decision History (use unique prefix per scope to avoid duplicate keys on rerun)
    if record:
        scope_id = record['scope']['scope_id'][:8]
        render_history("refund_risk", record, f"refund_{scope_id}")


# ─── Main ───
def page_methodology(orders: pd.DataFrame, suspects: pd.DataFrame):
    st.subheader("Data, validation and methodology")
    st.caption(
        "Where the data comes from, how every KPI is calculated, and the limits of "
        "what this dashboard can claim. The refund layer is synthetic and disclosed."
    )

    st.subheader("Dataset overview")
    overview = pd.DataFrame([
        ("Delivery source", "Public delivery dataset (Zomato-style)"),
        ("Refund layer", "Synthetic — generated for this portfolio case study"),
        ("Analysis period", f"{orders['Order_Date'].min():%d %b %Y} – {orders['Order_Date'].max():%d %b %Y}"),
        ("Delivery orders", f"{len(orders):,}"),
        ("Refund requests", f"{int(orders['Refund_Requested'].sum()):,}"),
        ("Unique customers", f"{orders['Customer_ID'].nunique():,}"),
        ("Customers with at least one refund", f"{int(orders.loc[orders['Refund_Requested'] == True, 'Customer_ID'].nunique()):,}"),
        ("Flagged accounts", f"{len(suspects):,}"),
        ("Project type", "Independent portfolio project — not affiliated with Zomato"),
    ], columns=["Item", "Information"])
    st.dataframe(overview, width="stretch", hide_index=True)

    st.subheader("Data quality checks (computed, not assumed)")
    checks = []
    required = ["ID", "Customer_ID", "Order_Date", "Refund_Requested", "Refund_Amount", "City", "Refund_Reason"]
    missing = {c: int(orders[c].isna().sum()) for c in required if c in orders.columns}
    total_missing = sum(missing.values())
    checks.append(("Missing values in required columns", "PASS" if total_missing == 0 else "WARN",
                   f"{total_missing} nulls across {len(required)} columns"))
    dup = int(orders["ID"].duplicated().sum()) if "ID" in orders.columns else 0
    checks.append(("Duplicate order IDs", "PASS" if dup == 0 else "WARN", f"{dup} duplicate IDs"))
    dmin, dmax = orders["Order_Date"].min(), orders["Order_Date"].max()
    checks.append(("Date range validity", "PASS", f"{dmin:%d %b %Y} – {dmax:%d %b %Y} ({orders['Order_Date'].dt.normalize().nunique()} active days)"))
    neg = int((orders["Refund_Amount"] < 0).sum())
    checks.append(("Refund amounts non-negative", "PASS" if neg == 0 else "WARN", f"{neg} negative amounts"))
    rr = orders.loc[orders["Refund_Requested"] == True]
    zero_amt = int((rr["Refund_Amount"] == 0).sum())
    checks.append(("Refund records have positive amount", "PASS" if zero_amt == 0 else "WARN", f"{zero_amt} refund requests with zero amount"))
    orphan = int((~suspects["Customer_ID"].isin(orders["Customer_ID"])).sum()) if len(suspects) else 0
    checks.append(("Flagged customers exist in orders", "PASS" if orphan == 0 else "WARN", f"{orphan} orphaned flagged IDs"))
    checks.append(("Refund request grain", "INFO",
                   f"{int(orders['Refund_Requested'].sum()):,} refund requests across {orders.loc[orders['Refund_Requested']==True,'Customer_ID'].nunique():,} customers"))
    dq = pd.DataFrame(checks, columns=["Check", "Status", "Detail"])
    st.dataframe(dq, width="stretch", hide_index=True)

    st.subheader("KPI definitions")
    formulas = pd.DataFrame([
        ("Refund request rate", "Refund requests ÷ eligible delivery orders × 100"),
        ("Average refund amount", "Total refund value ÷ refund requests"),
        ("Customer refund rate", "Customer refund requests ÷ customer eligible orders × 100"),
        ("Potential exposure", "Refund value associated with flagged accounts"),
        ("Refund exposure share", "Flagged refund value ÷ total refund value × 100"),
        ("P95 baseline", "95th percentile of peer-group (volume band) refund rates"),
        ("Review Priority Score", "0.40·refund rate + 0.30·reason repetition + 0.20·refund velocity + 0.10·reason length, scaled 0–100"),
    ], columns=["Metric", "Definition"])
    st.dataframe(formulas, width="stretch", hide_index=True)

    st.subheader("Risk methodology")
    st.markdown(
        "- **Eligibility:** ≥5 orders AND refund rate > 30% — a flag means review, never a guilt verdict.\n"
        "- **Volume-band normalisation:** customers are compared with others who order similar amounts; "
        "P95 is computed per band, not over the whole population.\n"
        "- **Risk tiers:** Low (≤40), Medium (41–70), High (>70) on the review priority score.\n"
        "- **Peer comparison:** above P95 = unusual for that volume; at/below P95 = within normal range for that volume.\n"
        "- **No confirmed fraud labels exist** in this dataset; the score is a review-prioritisation signal."
    )

    st.subheader("Limitations")
    st.markdown(
        "- The refund layer is **synthetic** (generated for this case study) — disclosed throughout.\n"
        "- The delivery dataset is **public**; this is an independent portfolio project, not an internal Zomato system.\n"
        "- April is a **partial calendar period**; month-over-month comparisons are suppressed.\n"
        "- **No confirmed fraud labels** — risk flags are review priorities, not verdicts.\n"
        "- The score is a **rule-based heuristic**, not a validated predictive model.\n"
        "- Weather/traffic/festival segments were removed from the core story because refunds were generated independently of delivery conditions."
    )

    st.subheader("Technology")
    st.markdown(
        "Python · Pandas · NumPy · Streamlit · Plotly · (optional) Gemini/OpenAI for the investigation copilot."
    )


def main():
    st.set_page_config(
        page_title="FoodTrust — Refund Risk & Marketplace Intelligence",
        page_icon="🍽️",
        layout="wide",
    )
    inject_css()

    # Wire API keys from Streamlit secrets (never commit keys)
    try:
        if "GOOGLE_API_KEY" in st.secrets and not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
        if "OPENAI_API_KEY" in st.secrets and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    orders = load_orders(DATA_PATH)
    suspects = build_customer_risk_table(orders)
    truth = load_truth(TRUTH_PATH)
    try:
        metric_defs = load_metric_definitions(METRICS_PATH)
    except (OSError, ValueError):
        metric_defs = None

    # ── Sidebar ───
    period_label = f"{orders['Order_Date'].min().strftime('%b %Y')} – {orders['Order_Date'].max().strftime('%d %b %Y')}"
    n_refunds = int(orders["Refund_Requested"].sum())
    st.sidebar.markdown(
        """
<div style="display:flex;gap:10px;align-items:center;padding:4px 4px 12px;border-bottom:1px solid #30363d;margin-bottom:12px;">
  <div style="width:40px;height:40px;border-radius:10px;flex-shrink:0;
    background:linear-gradient(135deg,#E23744,#B91C1C);
    display:flex;align-items:center;justify-content:center;
    font-weight:900;font-size:18px;color:#fff;
    box-shadow:0 0 16px rgba(226,55,68,.35);">FT</div>
  <div>
    <div style="font-size:14px;font-weight:800;color:#e6edf3;line-height:1.2;">FoodTrust</div>
    <div style="font-size:11px;color:#8b949e;margin-top:2px;">Refund & Trust Intelligence</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.sidebar.markdown(
        f"""
<div style="font-size:11px;color:#8b949e;background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 10px;margin-bottom:12px;line-height:1.5;">
  📅 <b>{period_label}</b><br>
  {len(orders):,} orders · {n_refunds:,} refunds<br>
  <span style="color:#8b949e">Synthetic refund layer — disclosed</span></div>
""", unsafe_allow_html=True)

    st.sidebar.markdown("**Filters**")

    # Global filters
    all_city_types = sorted(orders["City"].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect(
        "City type", all_city_types, default=all_city_types,
        help="Order-level city type — applies to every page.", key="f_city")
    selected_bands = st.sidebar.multiselect(
        "Customer volume band", BAND_LABELS, default=BAND_LABELS,
        help="1-2 / 3-5 / 6-10 / 11-20 / 21+ orders (customer-level) — applies to every page.", key="f_band")
    city_subset = selected_cities if len(selected_cities) < len(all_city_types) else None
    band_subset = selected_bands if len(selected_bands) < len(BAND_LABELS) else None
    orders_f = apply_global_filters(orders, city_subset, band_subset)
    suspects_scope = suspects
    if city_subset:
        suspects_scope = suspects_scope[suspects_scope["City"].isin(city_subset)]
    if band_subset:
        suspects_scope = suspects_scope[suspects_scope["Total_Orders"].apply(volume_band).isin(band_subset)]

    # Investigation filters
    st.sidebar.markdown("**Investigation filters**")
    min_date = suspects["Last_Order_Date"].min().date()
    max_date = suspects["Last_Order_Date"].max().date()
    date_range = st.sidebar.date_input("Last order date range", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date, key="f_date")
    risk_tiers = st.sidebar.multiselect("Risk tier", ["Low", "Medium", "High"],
                                        default=["Low", "Medium", "High"], key="f_tier")

    filtered = suspects_scope[suspects_scope["Risk_Tier"].isin(risk_tiers)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[(filtered["Last_Order_Date"].dt.date >= start) & (filtered["Last_Order_Date"].dt.date <= end)]

    # Active filter chips
    chips = []
    if len(selected_cities) < len(all_city_types):
        chips.append(f"City: {', '.join(selected_cities) if selected_cities else 'none'}")
    if len(selected_bands) < len(BAND_LABELS):
        chips.append(f"Volume band: {', '.join(selected_bands) if selected_bands else 'none'}")
    if len(risk_tiers) < 3:
        chips.append(f"Tier: {', '.join(risk_tiers) if risk_tiers else 'none'}")
    html = "".join(f'<span style="font-size:11px;font-weight:600;color:#58a6ff;background:rgba(88, 166, 255,.12);border:1px solid rgba(88, 166, 255,.3);border-radius:999px;padding:3px 10px;">{c}</span>' for c in chips) if chips else \
        '<span style="font-size:11px;color:#8b949e;">No filters active — full dataset in scope</span>'
    st.sidebar.markdown(f'<div style="margin-top:2px;"><div style="font-size:10px;font-weight:700;letter-spacing:.07em;color:#8b949e;text-transform:uppercase;margin-bottom:4px;">Active scope</div><div style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 4px;">{html}</div></div>', unsafe_allow_html=True)

    if st.sidebar.button("↺ Reset all filters", help="Restore the full dataset into scope.", use_container_width=True):
        for _k in ("f_city", "f_band", "f_tier", "f_date"):
            st.session_state.pop(_k, None)
        st.rerun()

    with st.sidebar.expander("📖 Methodology & how to read this"):
        st.markdown(
            "- **Refund rate** = refunded orders ÷ total orders (current scope)\n"
            "- **Flag eligibility**: ≥5 orders AND refund rate >30% — "
            "*a flag means review, never a guilt verdict*\n"
            "- **Risk score**: a simple weighted formula — refund rate 40% · "
            "reason repetition 30% · refunds/day 20% · reason length 10% "
            "([methodology](https://github.com/rishi-1603/zomato-refund-fraud-analytics/"
            "blob/main/docs/risk_scoring_methodology.md))\n"
            "- **Validation**: the score is checked against known test cases "
            "(the data is synthetic, disclosed)\n"
            "- **Data**: seeded/synthetic Zomato-style delivery data — disclosed "
            "in the README"
        )

    ft_header(orders_f, export_df=filtered)

    if not len(orders_f):
        ft_empty_state()
        if st.button("Reset filters", key="reset_main"):
            for _k in ("f_city", "f_band", "f_tier", "f_date"):
                st.session_state.pop(_k, None)
            st.rerun()
        ft_footer()
        return

    # Navigation
    # Use selectbox for reliable navigation on Streamlit Cloud (radio+horizontal has rerender bugs)
    page = st.selectbox(
        "Navigation",
        ["1. Executive Overview", "2. Refund Analysis", "3. Customer Risk Review", "4. Review Operations", "5. Data & Methodology"],
        index=0,
        label_visibility="collapsed",
        key="Navigation",
        help="Select a dashboard page to view",
    )

    if page == "1. Executive Overview":
        page_executive(orders_f, suspects_scope, truth, metric_defs)
    elif page == "2. Refund Analysis":
        page_refund_patterns(orders_f, suspects_scope, orders)
    elif page == "3. Customer Risk Review":
        page_risk_review(suspects_scope, filtered)
    elif page == "4. Review Operations":
        page_operations(filtered, city_subset, band_subset, risk_tiers)
    elif page == "5. Data & Methodology":
        page_methodology(orders_f, suspects_scope)

    ft_footer()
    st.caption(
        "Synthetic, seeded dataset — the method is the point. "
        "Risk score = 40% refund rate + 30% reason repetition + 20% refund frequency + 10% reason length "
        "(docs/risk_scoring_methodology.md). Demo project — not affiliated with Zomato."
    )


if __name__ == "__main__":
    main()