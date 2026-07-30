"""Streamlit dashboard for the Zomato refund fraud risk analysis.

Run with: streamlit run dashboard/app.py
"""

import pandas as pd
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


def main() -> None:
    st.set_page_config(page_title="Zomato Refund Fraud Risk", layout="wide")
    st.title("🍽️ Zomato Refund Fraud Risk Dashboard")
    st.caption(
        "Behavioral risk scoring over refund patterns — flags accounts worth manual review. "
        "Methodology: docs/risk_scoring_methodology.md"
    )

    orders = load_orders(DATA_PATH)
    suspects = build_customer_risk_table(orders)

    st.sidebar.header("Filters")
    cities = sorted(suspects["City"].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect("City", cities, default=cities)

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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Flagged accounts", len(filtered))
    col2.metric("Total refund exposure", f"₹{filtered['Total_Refund_Amount'].sum():,.0f}")
    col3.metric(
        "Avg risk score",
        f"{filtered['Fraud_Risk_Score'].mean():.1f}" if len(filtered) else "—",
    )
    col4.metric("High risk tier", int((filtered["Risk_Tier"] == "High").sum()))

    st.subheader("Flagged customers, ranked by risk score")
    st.dataframe(
        filtered[
            [
                "Customer_ID",
                "City",
                "Risk_Tier",
                "Fraud_Risk_Score",
                "Total_Orders",
                "Total_Refunds",
                "Refund_Rate",
                "Reason_Repetition_Rate",
                "Total_Refund_Amount",
                "Last_Order_Date",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top 20 by risk score")
    top20 = filtered.head(20).set_index("Customer_ID")
    st.bar_chart(top20["Fraud_Risk_Score"])

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
            "SHAP-based per-feature contribution for the trained ML model will replace this "
            "rule-based breakdown once the model layer ships."
        )
    else:
        st.info("No customers match the current filters.")


if __name__ == "__main__":
    main()
