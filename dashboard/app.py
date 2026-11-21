"""FoodTrust — Zomato Refund Risk & Operations Analytics
Professional minimalist BI dashboard (light theme).

Five analytical pages:
1. Executive Overview    — Primary KPIs, trends, business attention points
2. Refund Patterns       — Customer volume bands, city comparisons, trends
3. Risk Review           — Risk rules, investigation queue, account-level evidence
4. Operations            — Review prioritization, analyst workflow, reports
5. Data Quality          — Lineage, definitions, validation, limitations

Run: streamlit run dashboard/app.py
"""

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
        compute_kpis,
        load_metric_definitions,
        volume_band,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dashboard.kpi_engine import (
        BAND_LABELS,
        apply_global_filters,
        compute_kpis,
        load_metric_definitions,
        volume_band,
    )

try:
    from decision_history import render_history
except ImportError:
    from dashboard.decision_history import render_history

RISK_WEIGHTS = {
    "Refund_Rate": 0.40,
    "Reason_Repetition_Rate": 0.30,
    "Refunds_Per_Day": 0.20,
    "Avg_Reason_Length": 0.10,
}

MIN_ORDERS_THRESHOLD = 5
MIN_REFUND_RATE_PCT = 30

# ─── Dark Console Palette (original) ───
C_PRIMARY = "#3B82F6"   # blue
C_ACCENT = "#A78BFA"    # violet
C_GOOD = "#34D399"      # green
C_WARN = "#FBBF24"      # amber
C_BAD = "#F87171"       # red
C_NEUTRAL = "#94A3B8"   # slate
C_ACCENT_2 = "#0D9488"    # teal
TIER_COLORS = {"Low": C_GOOD, "Medium": C_WARN, "High": C_BAD}
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    height=380,
    margin=dict(l=40, r=30, t=56, b=40),
    title_font=dict(size=15, color="#F1F5F9"),
    font=dict(family="Inter, 'Segoe UI', system-ui, -apple-system, sans-serif",
              size=12.5, color="#CBD5E1"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    hoverlabel=dict(bgcolor="#141D31", font_size=12.5, font_color="#E8ECF4",
                    bordercolor="#26375C"),
    xaxis=dict(gridcolor="#1E293B", zerolinecolor="#334155"),
    yaxis=dict(gridcolor="#1E293B", zerolinecolor="#334155"),
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
  --bg:#0a0f1e;
  --bg-2:#0f1629;
  --panel:#131d33;
  --panel-2:#1a2744;
  --panel-3:#213052;
  --border:#1e3a5f;
  --border-light:#2a4a73;
  --text:#e8edf5;
  --text-2:#c5cdd9;
  --muted:#6b7a99;
  --accent:#10b981;
  --accent-glow:rgba(16,185,129,.15);
  --accent-2:#3b82f6;
  --accent-3:#8b5cf6;
  --warn:#f59e0b;
  --danger:#ef4444;
  --success:#10b981;
  --gradient-1:linear-gradient(135deg,#0a0f1e 0%,#131d33 50%,#0f1629 100%);
  --gradient-accent:linear-gradient(135deg,#10b981 0%,#3b82f6 100%);
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
    radial-gradient(ellipse 80% 50% at 50% -20%,rgba(16,185,129,.08),transparent),
    radial-gradient(ellipse 60% 40% at 80% 80%,rgba(59,130,246,.05),transparent);
  pointer-events:none;
  z-index:0;
}
a{color:var(--accent-2);text-decoration:none;transition:color .2s}
a:hover{color:var(--accent)}

/* ===== HEADER ===== */
header{
  position:relative;
  z-index:1;
  max-width:1400px;
  margin:0 auto;
  padding:48px 40px 32px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(16,185,129,.03) 0%,transparent 100%);
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
  background:linear-gradient(135deg,#fff 0%,#a0aec0 100%);
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
  max-width:1400px;
  margin:0 auto;
  padding:0 40px 40px;
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

/* ===== TABS ===== */
.tabs{
  display:flex;
  gap:4px;
  flex-wrap:wrap;
  margin:28px 0 20px;
  border-bottom:1px solid var(--border);
  padding-bottom:0;
}
.tabs button{
  background:transparent;
  color:var(--muted);
  border:none;
  border-bottom:2px solid transparent;
  padding:10px 18px;
  border-radius:0;
  cursor:pointer;
  font-weight:500;
  font-size:13px;
  transition:all .2s ease;
  margin-bottom:-1px;
}
.tabs button:hover{color:var(--text);background:rgba(255,255,255,.03)}
.tabs button[aria-selected=true]{
  color:var(--accent);
  border-bottom-color:var(--accent);
  font-weight:600;
  background:transparent;
}

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
tbody tr:hover{background:rgba(16,185,129,.04)}
tbody tr:last-child td{border-bottom:none}

/* ===== SUMMARY / INSIGHT ===== */
.summary{
  padding:18px 22px;
  border:1px solid rgba(16,185,129,.2);
  background:linear-gradient(135deg,rgba(16,185,129,.06) 0%,rgba(59,130,246,.04) 100%);
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
  margin:16px 0;
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
<div class="ft-header">
  <div class="ft-hleft">
    <div class="ft-hmark">RR</div>
    <div>
      <div class="ft-htitle">Zomato Refund Risk & Operations Analytics</div>
      <div class="ft-hsub">Refund patterns, customer comparisons and evidence for human review</div>
    </div>
  </div>
  <div class="ft-hright">
    <span class="ft-hchip"><span class="live">●</span>&nbsp; LIVE — COMPUTED FROM DATA</span>
    <span class="ft-hchip">{n:,} orders in scope · {period}</span>
    <span class="ft-hchip">Delivery data: public · Refund layer: synthetic</span>
    <span class="ft-hchip">Risk score ≠ proof of fraud</span>
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
<div class="ft-empty">
  <div class="ft-empty-icon">🔎</div>
  <div class="ft-empty-title">No records match the selected filters</div>
  <div class="ft-empty-sub">Reset the filters to bring the full dataset back into scope.</div>
</div>
""", unsafe_allow_html=True)


def ft_footer() -> None:
    st.markdown(
        f"""
<div class="ft-footer">
  <b>How to read this:</b> Refund rate = refunded orders ÷ total orders in the current view.
  A customer is flagged at ≥5 orders AND refund rate > 30% — a flag means <i>investigate</i>, never guilty.
  The score is a simple weighted formula (refund rate 40% · reason repetition 30% · refunds/day 20% · reason length 10%),
  checked against known test cases in this synthetic dataset.
  The data is seeded/synthetic — disclosed in the README and data dictionary.
  Changes are month-over-month on the filtered data.
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
def bar_chart(df, x, y, title, color=C_PRIMARY, horizontal=False, text_fmt=None):
    orientation = "h" if horizontal else "v"
    fig = px.bar(df, x=x, y=y, orientation=orientation, title=title)
    fig.update_traces(marker_color=color, marker_line_width=0)
    if text_fmt is not None:
        fig.update_traces(text=df[y].apply(text_fmt), textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def rate_by_column(orders: pd.DataFrame, col: str, title: str):
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

    # What changed?
    insights = engine.what_changed(orders, suspects, truth)
    if insights:
        st.subheader("What changed?")
        st.caption("This month vs last, on the data you're viewing. Each card shows where its number comes from.")
        cols = st.columns(min(3, len(insights)))
        for i, ins in enumerate(insights[:3]):
            with cols[i]:
                color = {"ok": C_GOOD, "info": C_PRIMARY, "watch": C_WARN, "alert": C_PRIMARY}.get(ins["level"], C_PRIMARY)
                st.markdown(
                    f'<div class="ft-insight" style="border-left-color:{color};">'
                    f'<div class="ft-ins-head">{ins["headline"]}</div>'
                    f'<div class="ft-ins-detail">{ins["detail"]}</div>'
                    f'<div class="ft-ins-ev">Evidence: {ins["evidence"]}</div></div>',
                    unsafe_allow_html=True)
        if len(insights) > 3:
            with st.expander(f"More signals ({len(insights) - 3})"):
                for ins in insights[3:]:
                    color = {"ok": C_GOOD, "info": C_PRIMARY, "watch": C_WARN, "alert": C_PRIMARY}.get(ins["level"], C_PRIMARY)
                    st.markdown(
                        f'<div class="ft-insight" style="border-left-color:{color};">'
                        f'<div class="ft-ins-head">{ins["headline"]}</div>'
                        f'<div class="ft-ins-detail">{ins["detail"]}</div>'
                        f'<div class="ft-ins-ev">Evidence: {ins["evidence"]}</div></div>',
                        unsafe_allow_html=True)

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
        ("blue", "🛒", "Delivery orders", f"{kpis['total_orders']:,}",
         _mom_chip(mom["orders_delta_pct"]), "Month-over-month on the current scope."),
        ("red", "↩", "Refund requests", f"{refund_orders:,}",
         f"{kpis['refund_rate_pct']:.1f}% of orders", "A refund request is not a confirmed refund."),
        ("amber", "₹", "Total refund amount", _inr(kpis["refund_exposure"]),
         _mom_chip(mom["exposure_delta_pct"], up_is_good=False),
         "Historical refund value — not a confirmed loss."),
        ("violet", "🛡", "High-risk accounts", f"{kpis['flagged_count']:,}",
         f"{refunders_share:.1f}% of refunders",
         "Eligibility: ≥5 orders AND refund rate >30%. A flag means investigate — never guilty."),
        ("teal", "⚠", "Potential exposure", _inr(kpis["flagged_exposure"]),
         f"{kpis['flagged_exposure_share_pct']:.1f}% of refunds",
         "Refund value held by the flagged pool."),
        ("rose", "₹", "Avg refund amount", _inr(avg_refund),
         "Per refund request", "Total refund amount ÷ refund requests."),
    ]
    st.markdown(
        '<div class="ft-kpi-row">' + "".join(
            f'<div class="ft-kpi-card"><div class="ft-kpi-head">'
            f'<div class="ft-kpi-icon {icon}">{emoji}</div>'
            f'<div class="ft-kpi-label">{label}</div></div>'
            f'<div class="ft-kpi-value">{value}</div>'
            f'<div class="ft-kpi-sub">{sub}</div>'
            f'<div class="ft-kpi-sub" style="color:var(--ft-text-muted)">{note}</div></div>'
            for icon, emoji, label, value, sub, note in kpi_cards
        ) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Changes are month-over-month on the filtered data. The precision figure is checked "
        "against known test cases (the data is synthetic — disclosed). A risk score is not proof of fraud."
    )

    # KPI definitions expander
    if metric_defs:
        with st.expander("📖 KPI definitions"):
            for _key, _m in metric_defs["metrics"].items():
                st.markdown(f"**{_key.replace('_', ' ').title()}** — {_m['definition']}")

    # Top suspects queue
    if len(suspects):
        top_n = min(8, len(suspects))
        rows = ""
        for _, r in suspects.head(top_n).iterrows():
            tier = str(r["Risk_Tier"])
            rows += (
                f'<div class="sus-row {tier.lower()}">'
                f'<span class="tier-pill {tier.lower()}">{tier.upper()}</span>'
                f'<span class="sus-id">#{r["Customer_ID"]}</span>'
                f'<span class="sus-metric"><b>{r["Fraud_Risk_Score"]:.1f}</b> risk score</span>'
                f'<span class="sus-metric">{r["Refund_Rate"]:.0f}% refund rate · {int(r["Total_Refunds"])}/{int(r["Total_Orders"])} orders</span>'
                f'<span class="sus-fill"></span>'
                f'<span class="sus-metric"><b>₹{r["Total_Refund_Amount"]:,.0f}</b> exposure</span>'
                f'</div>'
            )
        st.subheader("Top suspects — investigation queue")
        st.caption(
            "The highest risk scores in the current view. A flag means look closer — never guilty. "
            "The full list, baselines and per-customer details are in the Risk Review tab."
        )
        st.markdown(f'<div class="queue-card">{rows}</div>', unsafe_allow_html=True)

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
                marker_color="#7FB0F5", opacity=0.9)
    fig.add_scatter(x=m["Order_Date"], y=m["refund_rate"], name="Refund rate (%)",
                    mode="lines+markers", line=dict(color=C_PRIMARY, width=3), secondary_y=True)
    fig.update_layout(title="Monthly order volume vs refund rate (observed data)", **PLOTLY_LAYOUT)
    fig.update_yaxes(title_text="Orders", secondary_y=False)
    fig.update_yaxes(title_text="Refund rate (%)", secondary_y=True)
    st.plotly_chart(fig, width="stretch")

    # Bottom row: Reasons + City
    left, right = st.columns(2)
    with left:
        reasons = (
            orders[orders["Refund_Requested"] == True]["Refund_Reason"]
            .value_counts().rename_axis("Reason").reset_index(name="count")
        )
        fig = px.bar(reasons, y="Reason", x="count", orientation="h",
                     title="Refund reasons, ranked")
        fig.update_traces(marker_color="#7C3AED", text=reasons["count"], textposition="outside")
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
                     color_continuous_scale=["#1E3A8A", C_PRIMARY, "#FCA5A5"],
                     title="Orders by city type (colour = refund rate)",
                     hover_data=["refunds", "refund_rate"])
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="Orders")
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
                     color_discrete_map={"Low": C_GOOD, "Medium": C_WARN, "High": C_PRIMARY},
                     title="Flagged pool by risk tier", text="Flagged accounts")
        fig.update_layout(**PLOTLY_LAYOUT)
        fig.update_traces(textposition="outside")
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
            "Tiers come from the documented risk score on the flagged pool — not from the planted labels. "
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
                f'<div class="ft-claim-chip"><div class="cc-v">{v}</div>'
                f'<div class="cc-l">{l}</div></div>', unsafe_allow_html=True)
        st.caption("Behavioural patterns of refund requests in the current scope. Repeat claiming is an investigation signal, not proof of fraud.")

    # Key insight banner
    top_reason = reasons.iloc[0]["Reason"]
    top_reason_share = reasons.iloc[0]["count"] / reasons["count"].sum() * 100
    busiest_month = m.loc[m["orders"].idxmax(), "Order_Date"].strftime("%b %Y")
    n_high_tier = int((suspects["Risk_Tier"] == "High").sum()) if len(suspects) else 0
    st.markdown(
        f"""
<div class="ft-key-banner">
  <div class="ft-ki-eyebrow">Financial impact & actions — computed from the current scope</div>
  <div class="ft-ki-main">"{top_reason}" is the most common refund reason ({top_reason_share:.1f}% of all refunds).
  Busiest month on record: <b>{busiest_month}</b>. Flagged customers ({len(suspects):,} accounts) hold
  <b>{exposure_share:.1f}%</b> of total refund exposure.</div>
  <div class="ft-ki-why">Why it matters: exposure is concentrated, not uniform — review effort pointed at the
  flagged list covers the most refund value per account reviewed.</div>
  <div class="ft-ki-next"><b>Investigate next:</b> open the Risk Review tab and start with the High tier
  ({n_high_tier} accounts) — each carries the strongest evidence.</div>
</div>
""", unsafe_allow_html=True)


def page_refund_patterns(orders: pd.DataFrame, suspects: pd.DataFrame):
    refunds = orders[orders["Refund_Requested"] == True].copy()

    # Pareto concentration
    x, cum, n_cust, total_val, k50, k80, top10_share = concentration_curve(orders)

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total refund exposure", f"₹{total_val:,.0f}")
    p2.metric("Refunding customers", f"{n_cust:,}")
    p3.metric("Top 10% hold", f"{top10_share:.1f}% of exposure")
    p4.metric("Half of exposure in", f"top {k50:,} customers")

    st.subheader("Where the refund money concentrates")
    st.caption(
        "How refund money is spread across customers — this tells you how big the review "
        "queue needs to be. Concentration is a reason to prioritize, never evidence "
        "that any individual customer is fraudulent. Full analysis: reports/pareto_analysis.md"
    )
    fig = go.Figure()
    fig.add_scatter(x=x, y=cum, mode="lines", name="Cumulative share of refund value",
                    line=dict(color=C_PRIMARY, width=3))
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Perfect equality (y = x)",
                    line=dict(color="#1e3a5f", dash="dash", width=1.5)))
    fig.add_hline(y=80, line_dash="dot", line_color=C_WARN, opacity=0.7)
    fig.add_vline(x=k80 / n_cust * 100, line_dash="dot", line_color=C_WARN, opacity=0.7)
    fig.update_layout(**PLOTLY_LAYOUT,
        xaxis_title="Customers (% — ranked by refund value, highest first)",
        yaxis_title="Cumulative share of refund value (%)")
    st.plotly_chart(fig, width="stretch")

    r1, r2, r3 = st.columns(3)
    r1.metric("Avg refund amount", f"₹{refunds['Refund_Amount'].mean():,.0f}")
    r2.metric("Largest refund", f"₹{refunds['Refund_Amount'].max():,.0f}")
    r3.metric("Refunds per month", f"{len(refunds) / 36:,.0f}")

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
                           title="Refund amount distribution", color_discrete_sequence=[C_PRIMARY])
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Refund amount (₹)")
        left.plotly_chart(fig, width="stretch")

    with right:
        avg_reason = (
            refunds.groupby("Refund_Reason")["Refund_Amount"].mean()
            .sort_values(ascending=False).round(0).rename_axis("Reason")
            .reset_index(name="avg_amount")
        )
        fig = bar_chart(avg_reason, x="Reason", y="avg_amount",
                        title="Avg refund amount by reason", color="#7C3AED",
                        text_fmt=lambda v: f"₹{v:,.0f}")
        right.plotly_chart(fig, width="stretch")

    # Refund rate by conditions
    st.subheader("Refund rate by operating conditions")
    st.caption(
        "Refund rates across delivery conditions — the first cut an ops analyst would run. "
        "(On this synthetic dataset rates are roughly flat by design: refunds were "
        "generated independently of conditions.)"
    )
    c1, c2 = st.columns(2)
    with c1:
        c1.plotly_chart(rate_by_column(orders, "Weather_conditions", "By weather condition"), width="stretch")
        c1.plotly_chart(rate_by_column(orders, "Type_of_order", "By order type"), width="stretch")
    with c2:
        c2.plotly_chart(rate_by_column(orders, "Road_traffic_density", "By road traffic density"), width="stretch")
        c2.plotly_chart(rate_by_column(orders, "Festival", "By festival period"), width="stretch")

    # Volume-band refund rates
    st.subheader("Refund rate by customer volume band")
    st.caption("Customers are compared with peers who order similar amounts — this prevents high-volume customers from being flagged purely for volume.")
    band_refunds = orders[orders["Refund_Requested"] == True].copy()
    band_refunds["Volume_Band"] = band_refunds["Customer_ID"].apply(
        lambda cid: volume_band(orders[orders["Customer_ID"] == cid].shape[0])
    )
    band_rates = (
        band_refunds.groupby("Volume_Band")
        .agg(refunds=("Refund_Requested", "sum"), orders=("ID", "count"))
        .reset_index()
    )
    band_rates["refund_rate"] = (band_rates["refunds"] / band_rates["orders"] * 100).round(2)
    band_rates = band_rates.set_index("Volume_Band").reindex(BAND_LABELS).reset_index()
    fig = px.bar(band_rates, x="Volume_Band", y="refund_rate", title="Refund rate by customer volume band",
                 color="refund_rate", color_continuous_scale=["#1E3A8A", C_PRIMARY, "#FCA5A5"],
                 text="refund_rate", hover_data=["orders", "refunds"])
    fig.update_traces(textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="Refund rate (%)")
    st.plotly_chart(fig, width="stretch")


def page_risk_review(orders: pd.DataFrame, all_suspects: pd.DataFrame, filtered: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged customers", len(filtered))
    c2.metric("Refund exposure", f"₹{filtered['Total_Refund_Amount'].sum():,.0f}")
    c3.metric("Avg risk score", f"{filtered['Fraud_Risk_Score'].mean():.1f}" if len(filtered) else "—")
    c4.metric("High risk tier", int((filtered["Risk_Tier"] == "High").sum()))

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
                marker_color=C_PRIMARY, text=f"P95: {b['p95']:.1f}%",
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
        tier_counts = all_suspects["Risk_Tier"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
        tier_df = tier_counts.rename_axis("Tier").reset_index(name="count")
        fig = px.bar(tier_df, x="Tier", y="count", title="Risk tier distribution (all flagged)",
                     color="Tier", color_discrete_map={"Low": C_GOOD, "Medium": C_WARN, "High": C_PRIMARY},
                     text="count")
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        left.plotly_chart(fig, width="stretch")

        rep = filtered.groupby("City")["Customer_ID"].count().sort_values(ascending=False).rename_axis("City").reset_index(name="flagged")
        if len(rep):
            fig = px.bar(rep.iloc[::-1], x="flagged", y="City", orientation="h",
                         title="Flagged customers by city type",
                         color_discrete_sequence=[C_PRIMARY], text="flagged")
            fig.update_traces(textposition="outside", texttemplate="%{x:,.0f}", cliponaxis=False)
            fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="", xaxis_title="Flagged customers")
            left.plotly_chart(fig, width="stretch")

    with right:
        top20 = filtered.head(20).iloc[::-1]
        if len(top20):
            fig = px.bar(top20, y="Customer_ID", x="Fraud_Risk_Score",
                         orientation="h", title="Top 20 by fraud risk score",
                         color="Risk_Tier", color_discrete_map={"Low": C_GOOD, "Medium": C_WARN, "High": C_PRIMARY},
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
        ]].copy()
        _status_map = {"High": "Investigate first", "Medium": "Watchlist", "Low": "Routine review"}
        tbl["Status"] = tbl["Risk_Tier"].map(_status_map)

        def _tier_badge(val):
            if val in ("High", "Investigate first"):
                return f"background: rgba(248,113,113,0.13); color: #F87171; font-weight: 700"
            if val in ("Medium", "Watchlist"):
                return f"background: rgba(251,191,36,0.12); color: {C_WARN}; font-weight: 700"
            if val in ("Low", "Routine review"):
                return f"background: rgba(52,211,153,0.12); color: {C_GOOD}; font-weight: 700"
            return f"color: #6b7a99"

        styler = (
            tbl.style
            .map(_tier_badge, subset=["Risk_Tier"])
            .map(_tier_badge, subset=["Status"])
            .format({
                "Fraud_Risk_Score": "{:.1f}", "Refund_Rate": "{:.1f}%",
                "Reason_Repetition_Rate": "{:.0f}%", "Total_Refund_Amount": "₹{:,.0f}",
                "Last_Order_Date": lambda d: d.strftime("%d %b %Y"),
            })
        )
        st.dataframe(styler, width="stretch", hide_index=True)

        _csv = tbl.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download investigation list (CSV)", _csv,
                           file_name="zomato_flagged_investigation_list.csv",
                           mime="text/csv", help="The current filtered scope — ready for the review workflow.")

    # Explain a flag
    st.subheader("Explain a flag")
    customer_options = filtered["Customer_ID"].tolist()
    if customer_options:
        chosen = st.selectbox("Select a customer", customer_options, key="inv_customer")
        row = filtered[filtered["Customer_ID"] == chosen].iloc[0]
        st.write(f"**{chosen}** — Risk score **{row['Fraud_Risk_Score']}** ({row['Risk_Tier']})")
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
                f'<div class="ft-meter-row">'
                f'<div class="ft-meter-head"><span>{name} <span style="color:var(--ft-text-muted);">· weight {weight:.0%}</span></span>'
                f'<b>{text}</b></div>'
                f'<div class="ft-meter-track"><div class="ft-meter-fill {fill}" style="width:{pct:.0f}%"></div></div>'
                f'<div class="ft-meter-note">{note}</div></div>'
            )
        st.markdown(f'<div class="ft-meter-card">{meters}</div>', unsafe_allow_html=True)
        st.caption(
            "Each bar shows how extreme one score factor is, compared to the 95th percentile "
            "of flagged customers in the current view. The score is a simple weighted formula — "
            "full details in docs/risk_scoring_methodology.md."
        )
    else:
        st.info("No customers match the current filters.")

    # ─── AI Investigation (deterministic evidence + optional LLM narration) ───
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
        if inv_customer and st.button("Run AI Investigation", key="ai_inv_run"):
            try:
                try:
                    from ai_investigator import investigate_with_llm
                except ImportError:
                    from dashboard.ai_investigator import investigate_with_llm
                with st.spinner("Pulling the customer's numbers..."):
                    result = investigate_with_llm(inv_customer)
                if not result.get("ok"):
                    st.error(result.get("error", "Investigation failed."))
                else:
                    ev = result["evidence"]
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


def page_operations(orders: pd.DataFrame, filtered: pd.DataFrame, city_subset=None, band_subset=None, risk_tiers=None):
    avg_time = orders["Time_taken (min)"].mean()
    avg_rating = orders["Delivery_person_Ratings"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg delivery time", f"{avg_time:.1f} min")
    c2.metric("Median delivery time", f"{orders['Time_taken (min)'].median():.0f} min")
    c3.metric("Avg rider rating", f"{avg_rating:.2f} / 5")
    c4.metric("Slowest (90th pct)", f"{orders['Time_taken (min)'].quantile(0.9):.0f} min")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(orders, x="Time_taken (min)", nbins=45, title="Delivery time distribution",
                           color_discrete_sequence=[C_PRIMARY])
        fig.add_vline(x=avg_time, line_dash="dash", line_color=C_PRIMARY,
                      annotation_text=f"mean {avg_time:.1f} min")
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Minutes")
        left.plotly_chart(fig, width="stretch")

    with right:
        fig = px.box(orders, x="Road_traffic_density", y="Time_taken (min)",
                     title="Delivery time by traffic density", points=False,
                     color="Road_traffic_density",
                     color_discrete_sequence=["#93C5FD", "#60A5FA", "#3B82F6", "#2563EB"])
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        right.plotly_chart(fig, width="stretch")

    c3_, c4_ = st.columns(2)
    with c3_:
        fig = px.box(orders, x="Weather_conditions", y="Time_taken (min)",
                     title="Delivery time by weather", points=False,
                     color="Weather_conditions",
                     color_discrete_sequence=["#DDD6FE", "#C4B5FD", "#A78BFA", "#8B5CF6", "#7C3AED", "#6D28D9", "#5B21B6"])
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        c3_.plotly_chart(fig, width="stretch")

    with c4_:
        type_counts = orders["Type_of_order"].value_counts().rename_axis("Type").reset_index(name="count")
        fig = px.bar(type_counts.iloc[::-1], x="count", y="Type", orientation="h",
                     title="Order mix by type (orders)", color_discrete_sequence=[C_PRIMARY], text="count")
        fig.update_traces(textposition="outside", texttemplate="%{x:,.0f}", cliponaxis=False)
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="", xaxis_title="Orders")
        c4_.plotly_chart(fig, width="stretch")

    # Rider view
    riders = orders.groupby("Delivery_person_ID").agg(
        orders=("ID", "count"), avg_rating=("Delivery_person_Ratings", "mean"),
        avg_time=("Time_taken (min)", "mean")).reset_index()
    r1, r2 = st.columns(2)
    with r1:
        fig = px.histogram(riders, x="avg_rating", nbins=25,
                           title="Rider ratings — distribution of rider averages",
                           color_discrete_sequence=[C_GOOD])
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Average rating (per rider)")
        r1.plotly_chart(fig, width="stretch")
    with r2:
        top_riders = riders.nlargest(10, "orders").iloc[::-1]
        fig = px.bar(top_riders, y="Delivery_person_ID", x="orders", orientation="h",
                     title="Top 10 riders by order volume", hover_data=["avg_rating", "avg_time"])
        fig.update_traces(marker_color="#6b7a99")
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_title="")
        r2.plotly_chart(fig, width="stretch")

    # Decision & value
    st.divider()
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

    # ─── Deterministic Copilot (no LLM) ───
    # Track filter context to clear copilot answer when scope changes
    filter_context = {"city_types": city_subset or None, "customer_volume_bands": band_subset or None,
                      "risk_tiers": risk_tiers, "last_order_date_range": None}
    scope_id = str(hash(str(filter_context)))
    if st.session_state.get("refund_copilot_scope") != scope_id:
        st.session_state["refund_copilot_scope"] = scope_id
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

    # ─── Decision History ───
    render_history("refund_risk", record, "refund")


def page_data_quality(orders: pd.DataFrame):
    st.subheader("Data Quality")
    st.caption(
        "Computed live from `data/processed/zomato_with_refunds.csv` (45,584 orders). "
        "The fuller audit — pandas↔SQL reconciliation, drift monitor, sensitivity — lives in "
        "reports/data_quality_report.md and is pinned by CI."
    )

    req = orders["Refund_Requested"].astype(bool)
    missing = orders.isna().sum()
    n = len(orders)
    dup_ids = int(orders["ID"].duplicated().sum())
    span_min, span_max = orders["Order_Date"].min(), orders["Order_Date"].max()

    checks = [
        ("Order ID uniqueness", f"{dup_ids} duplicate ID(s) across {n:,} rows", "pass" if dup_ids == 0 else "review"),
        ("Refund amount consistency", f"{int((req & (orders['Refund_Amount'] <= 0)).sum())} refund request(s) with amount ≤ 0",
         "pass" if int((req & (orders["Refund_Amount"] <= 0)).sum()) == 0 else "review"),
        ("Refund reason coverage", f"{int((req & orders['Refund_Reason'].isna()).sum())} refund request(s) missing a reason",
         "pass" if int((req & orders["Refund_Reason"].isna()).sum()) == 0 else "review"),
        ("No amount without a request", f"{int((~req & (orders['Refund_Amount'] > 0)).sum())} rows carry refund value without a request",
         "pass" if int((~req & (orders["Refund_Amount"] > 0)).sum()) == 0 else "review"),
        ("Date window sanity", f"All orders inside {span_min:%d %b %Y} → {span_max:%d %b %Y}", "pass"),
        ("City coverage", f"{int(missing['City']):,} orders ({missing['City'] / n * 100:.1f}%) have no City value — kept in scope by default filters (NaN-safe)", "gap"),
        ("Delivery-person fields",
         f"Age missing on {int(missing['Delivery_person_Age']):,} ({missing['Delivery_person_Age'] / n * 100:.1f}%) · "
         f"ratings missing on {int(missing['Delivery_person_Ratings']):,} ({missing['Delivery_person_Ratings'] / n * 100:.1f}%) — retained, never imputed", "gap"),
        ("Refund layer provenance", "Customer IDs, refund events, amounts and ground-truth labels are synthetic and seeded (seed 42) — disclosed; Refund_Reason is populated only for refund rows by design", "disclosed"),
    ]
    pill_label = {"pass": "PASS", "review": "REVIEW", "gap": "KNOWN GAP", "disclosed": "DISCLOSED"}
    rows = "".join(
        f'<div class="ft-dq-row"><div class="ft-dq-check">{name}</div>'
        f'<div class="ft-dq-result">{result}</div>'
        f'<span class="ft-dq-pill {status}">{pill_label[status]}</span></div>'
        for name, result, status in checks
    )
    st.markdown(f'<div class="ft-dq-card">{rows}</div>', unsafe_allow_html=True)

    st.markdown("**Column completeness**")
    comp = (pd.DataFrame({"Column": orders.columns, "Missing": missing.values})
            .assign(**{"Complete %": lambda d: ((n - d["Missing"]) / n * 100).round(1)})
            .sort_values("Complete %"))
    st.dataframe(comp, use_container_width=True, hide_index=True)
    st.caption(
        "Completeness is a property of the source delivery dataset (public) plus the disclosed "
        "synthetic refund layer. Missing delivery fields are expected in the public data and are "
        "documented, not imputed."
    )

    st.divider()
    st.subheader("KPI Definitions & Provenance")
    st.caption("Every KPI on this dashboard traces to `data/metrics.json` and is validated by pandas↔SQL reconciliation (0 mismatches, 8 KPIs).")
    try:
        with open(METRICS_PATH) as f:
            metrics = __import__('json').load(f)
        for _key, _m in metrics["metrics"].items():
            with st.expander(f"{_key.replace('_', ' ').title()}"):
                st.markdown(f"**Definition:** {_m['definition']}")
                st.markdown(f"**Basis:** {_m['basis']}")
    except Exception:
        st.info("Metric definitions file not found in this deployment.")


# ─── Main ───
def main():
    st.set_page_config(
        page_title="Zomato Refund Risk & Operations Analytics",
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

    # ── Sidebar ───
    period_label = f"{orders['Order_Date'].min().strftime('%b %Y')} – {orders['Order_Date'].max().strftime('%d %b %Y')}"
    n_refunds = int(orders["Refund_Requested"].sum())
    st.sidebar.markdown(
        f'<div class="ft-brand"><div class="ft-mark">Z</div><div>'
        f'<div class="ft-title">Zomato Analytics</div>'
        f'<div class="ft-sub">Refund & Trust Intelligence</div></div></div>',
        unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div class="ft-period">📅 <b>{period_label}</b><br>'
        f'{len(orders):,} orders · {n_refunds:,} refunds<br>'
        f'<span style="color:var(--ft-text-muted)">Synthetic refund layer — disclosed</span></div>',
        unsafe_allow_html=True)

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
    html = "".join(f'<span class="ft-chip">{c}</span>' for c in chips) if chips else \
        '<span class="ft-chip-none">No filters active — full dataset in scope</span>'
    st.sidebar.markdown(f'<div style="margin-top:2px;"><div style="font-size:10px;font-weight:700;letter-spacing:0.07em;color:var(--ft-text-muted);text-transform:uppercase;margin-bottom:4px;">Active scope</div><div class="ft-filter-chips">{html}</div></div>', unsafe_allow_html=True)

    if st.sidebar.button("↺ Reset all filters", help="Restore the full dataset into scope.", use_container_width=True):
        for _k in ("f_city", "f_band", "f_tier", "f_date"):
            st.session_state.pop(_k, None)
        st.rerun()

    with st.sidebar.expander("📖 Methodology & how to read this"):
        st.markdown(
            "- **Refund rate** = refunded orders ÷ total orders (current scope)\n"
            "- **Flag eligibility**: ≥5 orders AND refund rate >30% — "
            "*a flag means investigate, never guilty*\n"
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

    # ─── Navigation ───
    page = st.radio(
        "Navigation",
        ["1. Executive Overview", "2. Refund Patterns", "3. Risk Review", "4. Operations", "5. Data Quality"],
        horizontal=True, label_visibility="collapsed",
        key="Navigation",
    )

    if page == "1. Executive Overview":
        page_executive(orders_f, suspects_scope, truth, metric_defs)
    elif page == "2. Refund Patterns":
        page_refund_patterns(orders_f, suspects_scope)
    elif page == "3. Risk Review":
        page_risk_review(orders_f, suspects_scope, filtered)
    elif page == "4. Operations":
        page_operations(orders_f, filtered, city_subset, band_subset, risk_tiers)
    elif page == "5. Data Quality":
        page_data_quality(orders_f)

    ft_footer()
    st.caption(
        "Synthetic, seeded dataset — the method is the point. "
        "Risk score = 40% refund rate + 30% reason repetition + 20% refund frequency + 10% reason length "
        "(docs/risk_scoring_methodology.md). Demo project — not affiliated with Zomato."
    )


if __name__ == "__main__":
    main()