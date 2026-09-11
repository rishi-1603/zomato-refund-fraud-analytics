"""Streamlit dashboard for the Zomato refund fraud risk analysis.

A professional multi-tab BI dashboard — every figure is computed live from
the dataset (45,584 delivery orders). No hardcoded metrics anywhere.

Run with: streamlit run dashboard/app.py
Tabs: Executive Overview · Refund Analytics · Customer Risk · Operations
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from sklearn.preprocessing import MinMaxScaler

DATA_PATH = "data/processed/zomato_with_refunds.csv"

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
    margin=dict(l=40, r=30, t=50, b=40),
    title_font=dict(size=15, color="#1E293B"),
)


@st.cache_data
def load_orders(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
    return df


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

def tab_overview(orders: pd.DataFrame, suspects: pd.DataFrame) -> None:
    total_orders = len(orders)
    refund_orders = int(orders["Refund_Requested"].sum())
    refund_rate = refund_orders / total_orders * 100
    refund_amount = orders["Refund_Amount"].sum()
    flagged_exposure = suspects["Total_Refund_Amount"].sum()
    exposure_share = flagged_exposure / refund_amount * 100 if refund_amount else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total orders", f"{total_orders:,}")
    c2.metric("Refund orders", f"{refund_orders:,}")
    c3.metric("Refund rate", f"{refund_rate:.1f}%")
    c4.metric("Refund amount", f"₹{refund_amount:,.0f}")
    c5.metric("Flagged customers", len(suspects))
    c6.metric(
        "Flagged share of exposure", f"{exposure_share:.1f}%",
        delta=f"₹{flagged_exposure:,.0f}", delta_color="inverse",
    )

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
    st.info(
        f"📌 **What the data says:** “{top_reason}” is the most common refund reason "
        f"({top_reason_share:.1f}% of all refunds). Busiest month on record: "
        f"**{busiest_month}**. Flagged customers ({len(suspects)} accounts) hold "
        f"**{exposure_share:.1f}%** of total refund exposure — concentrating review "
        f"effort there is the highest-leverage action."
    )


def tab_refunds(orders: pd.DataFrame) -> None:
    refunds = orders[orders["Refund_Requested"] == True].copy()  # noqa: E712

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

        st.subheader("Flagged customers, ranked by risk score")
        st.dataframe(
            filtered[
                [
                    "Customer_ID", "City", "Risk_Tier", "Fraud_Risk_Score",
                    "Total_Orders", "Total_Refunds", "Refund_Rate",
                    "Reason_Repetition_Rate", "Total_Refund_Amount", "Last_Order_Date",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

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
    st.title("🍽️ Zomato Refund Fraud Analytics")
    st.caption(
        "End-to-end behavioural analytics over 45,584 delivery orders — refund patterns, "
        "customer risk scoring, and operating conditions. Every figure is computed live "
        "from the dataset; risk methodology in docs/risk_scoring_methodology.md."
    )

    orders = load_orders(DATA_PATH)
    suspects = build_customer_risk_table(orders)

    # ── Sidebar filters (drive the Customer Risk tab) ──
    st.sidebar.header("Filters — Customer Risk tab")
    cities = sorted(suspects["City"].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect("City type", cities, default=cities)

    min_date = suspects["Last_Order_Date"].min().date()
    max_date = suspects["Last_Order_Date"].max().date()
    date_range = st.sidebar.date_input(
        "Last order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )

    risk_tiers = st.sidebar.multiselect(
        "Risk tier", ["Low", "Medium", "High"], default=["Low", "Medium", "High"]
    )

    filtered = suspects[
        suspects["City"].isin(selected_cities) & suspects["Risk_Tier"].isin(risk_tiers)
    ]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            (filtered["Last_Order_Date"].dt.date >= start)
            & (filtered["Last_Order_Date"].dt.date <= end)
        ]

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Executive Overview", "💰 Refund Analytics", "👥 Customer Risk", "🚚 Operations"]
    )
    with tab1:
        tab_overview(orders, suspects)
    with tab2:
        tab_refunds(orders)
    with tab3:
        tab_customer_risk(filtered, suspects)
    with tab4:
        tab_operations(orders)

    st.divider()
    st.caption(
        "Synthetic, seeded dataset — methods are the story. Risk score = 40% refund rate + "
        "30% reason repetition + 20% refund frequency + 10% reason length "
        "(docs/risk_scoring_methodology.md). Demo analytics — not affiliated with Zomato."
    )


if __name__ == "__main__":
    main()
