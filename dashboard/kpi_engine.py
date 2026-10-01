"""
kpi_engine.py — deterministic KPI layer for the Zomato refund-risk dashboard.
================================================================================
Every number shown in the executive KPI header and the "What changed?" strip
is computed HERE with pure pandas — no Streamlit, no LLM, no hardcoded values.
tests/test_kpi_engine.py pins the verified numbers (45,584 orders / 9,895
customers / ₹974,344 exposure / 279 flagged / 38.78% / 8 high-tier at 100%
precision / 113 below-baseline).

KPI definitions live in data/metrics.json (the semantic layer the dashboard
and the AI assistant both cite). Risk score ≠ proof of fraud — see
docs/risk_scoring_methodology.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# ── Volume bands (must stay identical to scripts/baseline_normalization.py) ──
BANDS = [(1, 2), (3, 5), (6, 10), (11, 20), (21, 10**9)]
BAND_LABELS = ["1-2 orders", "3-5 orders", "6-10 orders", "11-20 orders", "21+ orders"]

# Relative MoM change (in %) that triggers an "alert" in the What-changed strip
MOM_ALERT_THRESHOLD_PCT = 10.0
# Absolute MoM refund-rate change (percentage points) that triggers an alert
MOM_RATE_ALERT_PP = 2.0


def volume_band(order_count: int) -> str:
    """Map an order count to its volume band label."""
    for (lo, hi), label in zip(BANDS, BAND_LABELS):
        if lo <= order_count <= hi:
            return label
    return BAND_LABELS[-1]


def customer_base(orders: pd.DataFrame) -> pd.DataFrame:
    """Per-customer aggregates over ALL customers (not just flagged)."""
    cust = (
        orders.groupby("Customer_ID")
        .agg(
            Total_Orders=("ID", "count"),
            Total_Refunds=("Refund_Requested", "sum"),
            Total_Refund_Amount=("Refund_Amount", "sum"),
        )
        .reset_index()
    )
    cust["Refund_Rate"] = (cust["Total_Refunds"] / cust["Total_Orders"] * 100).round(2)
    cust["Volume_Band"] = cust["Total_Orders"].apply(volume_band)
    return cust


def band_baselines(customers: pd.DataFrame) -> pd.DataFrame:
    """Per-band refund-rate P95 — the 'normal for their volume' threshold."""
    return (
        customers.groupby("Volume_Band")["Refund_Rate"]
        .quantile(0.95)
        .rename("Band_P95_Refund_Rate")
        .reset_index()
    )


def _mom(orders: pd.DataFrame) -> dict:
    """Latest month vs previous month, computed from Order_Date (datetime)."""
    out = {
        "label": None, "prev_label": None,
        "orders_delta_pct": None, "exposure_delta_pct": None,
        "refund_rate_delta_pp": None,
    }
    if "Order_Date" not in orders.columns or orders.empty:
        return out
    dates = pd.to_datetime(orders["Order_Date"], dayfirst=True, errors="coerce")
    m = (
        orders.assign(_m=dates.dt.to_period("M"))
        .groupby("_m")
        .agg(orders=("ID", "count"), refunds=("Refund_Requested", "sum"),
             amount=("Refund_Amount", "sum"))
        .sort_index()
    )
    if len(m) < 2:
        return out
    cur, prev = m.iloc[-1], m.iloc[-2]
    out["label"] = str(m.index[-1])
    out["prev_label"] = str(m.index[-2])
    out["orders_delta_pct"] = (cur["orders"] - prev["orders"]) / prev["orders"] * 100 if prev["orders"] else None
    out["exposure_delta_pct"] = (
        (cur["amount"] - prev["amount"]) / prev["amount"] * 100 if prev["amount"] else None
    )
    cur_rate = cur["refunds"] / cur["orders"] * 100 if cur["orders"] else 0
    prev_rate = prev["refunds"] / prev["orders"] * 100 if prev["orders"] else 0
    out["refund_rate_delta_pp"] = cur_rate - prev_rate
    return out


def compute_kpis(orders: pd.DataFrame, suspects: pd.DataFrame, truth: pd.DataFrame | None = None) -> dict:
    """All executive KPIs for the current scope. `suspects` is the flagged
    table produced by dashboard/app.build_customer_risk_table (279 rows on the
    full dataset). `truth` (optional) = planted labels for validation."""
    kpis = {
        "total_orders": int(len(orders)),
        "refund_orders": int(orders["Refund_Requested"].sum()),
        "refund_rate_pct": float(orders["Refund_Requested"].mean() * 100),
        "refund_exposure": float(orders["Refund_Amount"].sum()),
        "customers": int(orders["Customer_ID"].nunique()),
        "flagged_count": int(len(suspects)),
        "flagged_exposure": float(suspects["Total_Refund_Amount"].sum()),
        "high_tier_count": int((suspects["Risk_Tier"] == "High").sum()) if len(suspects) else 0,
        "high_tier_precision_pct": None,
        "below_baseline_flagged": 0,
        "below_baseline_share_pct": 0.0,
    }
    if kpis["refund_exposure"]:
        kpis["flagged_exposure_share_pct"] = kpis["flagged_exposure"] / kpis["refund_exposure"] * 100
    else:
        kpis["flagged_exposure_share_pct"] = 0.0

    # High-tier precision vs seeded ground truth (disclosed synthetic layer)
    if truth is not None and kpis["high_tier_count"]:
        high = suspects[suspects["Risk_Tier"] == "High"][["Customer_ID"]]
        merged = high.merge(truth, on="Customer_ID", how="left")
        planted_high = int((merged["Planted_Risk"] == "High").sum())
        kpis["high_tier_precision_pct"] = planted_high / kpis["high_tier_count"] * 100

    # Below-baseline false-positive candidates (volume-band P95 rule)
    if len(suspects):
        base = customer_base(orders)
        baselines = band_baselines(base)
        flagged_base = suspects[["Customer_ID", "Refund_Rate"]].merge(
            base[["Customer_ID", "Volume_Band"]], on="Customer_ID", how="left"
        ).merge(baselines, on="Volume_Band", how="left")
        below = flagged_base[flagged_base["Refund_Rate"] <= flagged_base["Band_P95_Refund_Rate"]]
        kpis["below_baseline_flagged"] = int(len(below))
        kpis["below_baseline_share_pct"] = len(below) / len(suspects) * 100

    kpis["mom"] = _mom(orders)
    return kpis


def what_changed(orders: pd.DataFrame, suspects: pd.DataFrame, truth: pd.DataFrame | None = None) -> list[dict]:
    """Rule-based 'What changed?' insights. Detection is arithmetic on computed
    KPIs; narration is templated text around those numbers. No LLM, ever."""
    kpis = compute_kpis(orders, suspects, truth)
    mom = kpis["mom"]
    insights: list[dict] = []

    if mom["orders_delta_pct"] is not None:
        d = mom["orders_delta_pct"]
        level = "alert" if abs(d) >= MOM_ALERT_THRESHOLD_PCT else "ok"
        direction = "rose" if d >= 0 else "fell"
        insights.append({
            "headline": f"Orders {direction} {abs(d):.1f}% in {mom['label']}",
            "detail": f"{mom['prev_label']} → {mom['label']}, month-over-month.",
            "level": level,
            "evidence": "Order volume by month, computed from Order_Date.",
        })
    if mom["exposure_delta_pct"] is not None:
        d = mom["exposure_delta_pct"]
        level = "alert" if abs(d) >= MOM_ALERT_THRESHOLD_PCT else "ok"
        direction = "rose" if d >= 0 else "fell"
        insights.append({
            "headline": f"Refund exposure {direction} {abs(d):.1f}% in {mom['label']}",
            "detail": "Refund amount, month-over-month — the exposure KPI's trend.",
            "level": level,
            "evidence": "Refund_Amount summed by month.",
        })
    if mom["refund_rate_delta_pp"] is not None:
        d = mom["refund_rate_delta_pp"]
        if abs(d) >= MOM_RATE_ALERT_PP:
            insights.append({
                "headline": f"Refund rate moved {d:+.1f} pp in {mom['label']}",
                "detail": "Refunds as a share of orders changed by more than 2 pp.",
                "level": "alert",
                "evidence": "Refund rate by month (refunds / orders).",
            })

    if kpis["flagged_count"]:
        if kpis["below_baseline_flagged"]:
            insights.append({
                "headline": f"{kpis['below_baseline_flagged']} of {kpis['flagged_count']} flags sit below their volume-band baseline",
                "detail": (
                    f"{kpis['below_baseline_share_pct']:.1f}% of flagged customers refund at a rate "
                    "normal for their order volume — likely false positives, de-prioritise."
                ),
                "level": "watch",
                "evidence": "Refund rate vs volume-band P95 (baseline rule).",
            })
        if kpis["high_tier_precision_pct"] is not None:
            insights.append({
                "headline": f"High tier: {kpis['high_tier_count']} customers, {kpis['high_tier_precision_pct']:.0f}% precision",
                "detail": "Validated against the seeded ground truth (synthetic layer, disclosed).",
                "level": "info",
                "evidence": "High-tier flags vs planted labels.",
            })
    return insights


def apply_global_filters(
    orders: pd.DataFrame, city_types: list[str] | None = None, bands: list[str] | None = None
) -> pd.DataFrame:
    """Global cross-filtering: city type (order level) + customer volume band."""
    out = orders
    if city_types:
        out = out[out["City"].isin(city_types)]
    if bands:
        base = customer_base(orders)
        keep = base[base["Volume_Band"].isin(bands)]["Customer_ID"]
        out = out[out["Customer_ID"].isin(keep)]
    return out


def load_metric_definitions(path: str | Path) -> dict:
    """Load the semantic layer (data/metrics.json). Raises if invalid."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
