"""
test_kpi_engine.py — the executive KPI layer must reproduce verified numbers
================================================================================
Day-1 upgrade pin. The dataset is seeded and deterministic, so every executive
KPI is a known value. These tests fail if the KPI engine, the risk pipeline,
or the semantic layer (data/metrics.json) drift apart.

Verified values (reconciled with reports/ and scripts/):
45,584 orders · 9,895 customers · ₹974,344 exposure · 279 flagged ·
38.78% flagged exposure share · 8 high-tier at 100% precision ·
113 below-baseline flags (40.5%).
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import importlib.util  # noqa: E402

# The repo also has an app/ namespace package (app/dashboard/utils/...), which
# other tests import first — so `import app` may resolve to that package.
# Load dashboard/app.py directly by path to avoid the name collision.
_spec = importlib.util.spec_from_file_location(
    "zomato_dashboard_app", str(ROOT / "dashboard" / "app.py")
)
app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app)

from kpi_engine import (  # noqa: E402
    BAND_LABELS,
    apply_global_filters,
    band_baselines,
    compute_kpis,
    customer_base,
    load_metric_definitions,
    volume_band,
    what_changed,
)

DATA = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
TRUTH = ROOT / "data" / "processed" / "ground_truth_customer_risk.csv"
METRICS = ROOT / "data" / "metrics.json"


def _setup():
    orders = pd.read_csv(DATA)
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)
    suspects = app.build_customer_risk_table(orders)
    truth = pd.read_csv(TRUTH) if TRUTH.exists() else None
    return orders, suspects, truth


def test_volume_bands():
    assert volume_band(1) == "1-2 orders"
    assert volume_band(2) == "1-2 orders"
    assert volume_band(3) == "3-5 orders"
    assert volume_band(5) == "3-5 orders"
    assert volume_band(6) == "6-10 orders"
    assert volume_band(20) == "11-20 orders"
    assert volume_band(21) == "21+ orders"
    assert volume_band(99999) == "21+ orders"
    assert len(BAND_LABELS) == 5


def test_core_kpis_match_verified_values():
    orders, suspects, truth = _setup()
    k = compute_kpis(orders, suspects, truth)
    assert k["total_orders"] == 45_584
    assert k["customers"] == 9_895
    assert round(k["refund_exposure"]) == 974_344
    assert k["flagged_count"] == 279
    assert abs(k["flagged_exposure_share_pct"] - 38.78) < 0.05
    assert k["high_tier_count"] == 8
    assert k["high_tier_precision_pct"] == 100.0


def test_below_baseline_false_positives():
    orders, suspects, truth = _setup()
    k = compute_kpis(orders, suspects, truth)
    assert k["below_baseline_flagged"] == 113
    assert abs(k["below_baseline_share_pct"] - 40.5) < 0.1


def test_no_truth_graceful():
    orders, suspects, _ = _setup()
    k = compute_kpis(orders, suspects, truth=None)
    assert k["high_tier_count"] == 8
    assert k["high_tier_precision_pct"] is None  # precision simply not claimed


def test_customer_base_and_baselines():
    orders, _, _ = _setup()
    base = customer_base(orders)
    assert len(base) == 9_895
    assert set(base["Volume_Band"]).issubset(set(BAND_LABELS))
    bl = band_baselines(base)
    # baselines exist for exactly the bands present in the data
    # (verified: customers have 1-14 orders, so '21+ orders' is empty here)
    assert set(bl["Volume_Band"]) == set(base["Volume_Band"].unique())
    assert (bl["Band_P95_Refund_Rate"] >= 0).all()


def test_mom_deltas_present():
    orders, suspects, _ = _setup()
    k = compute_kpis(orders, suspects)
    mom = k["mom"]
    assert mom["label"] is not None and mom["prev_label"] is not None
    # deterministic dataset → deltas are stable and non-trivial
    assert mom["orders_delta_pct"] is not None


def test_what_changed_structure_and_honesty():
    orders, suspects, truth = _setup()
    insights = what_changed(orders, suspects, truth)
    assert len(insights) >= 3
    for ins in insights:
        assert set(ins) == {"headline", "detail", "level", "evidence"}
        assert ins["level"] in {"ok", "watch", "alert", "info"}
        assert ins["headline"] and ins["evidence"]
    # the false-positive insight must carry the verified 113/279 numbers
    fp = [i for i in insights if "below their volume-band baseline" in i["headline"]]
    assert fp and "113" in fp[0]["headline"]


def test_global_filters():
    orders, suspects, _ = _setup()
    full = compute_kpis(orders, suspects)
    # city filter shrinks scope consistently
    cities = sorted(orders["City"].dropna().unique())
    orders_city = apply_global_filters(orders, city_types=[cities[0]])
    assert len(orders_city) < full["total_orders"]
    assert len(orders_city) > 0
    # band filter keeps only customers in that band
    orders_band = apply_global_filters(orders, bands=["1-2 orders"])
    base = customer_base(orders_band)
    assert set(base["Volume_Band"]) == {"1-2 orders"}
    # no filters → unchanged
    assert len(apply_global_filters(orders)) == len(orders)


def test_metrics_json_semantic_layer():
    defs = load_metric_definitions(METRICS)
    assert defs["meta"]["methodology_doc"] == "docs/risk_scoring_methodology.md"
    m = defs["metrics"]
    for key in [
        "total_orders", "customers", "refund_exposure", "refund_rate",
        "flagged_customers", "flagged_exposure_share", "fraud_risk_score",
        "high_tier_precision", "volume_band_baseline", "below_baseline_flags",
        "pareto_concentration", "mom_delta",
    ]:
        assert key in m and "definition" in m[key], f"missing metric or definition: {key}"
    # pinned values in the semantic layer must match the verified numbers
    assert m["total_orders"]["full_dataset_value"] == 45_584
    assert m["flagged_customers"]["full_dataset_value"] == 279
    assert m["below_baseline_flags"]["full_dataset_value"] == 113
    # JSON must be valid and parseable
    json.loads(METRICS.read_text(encoding="utf-8"))


def test_dashboard_app_runs_end_to_end():
    """AppTest smoke: the upgraded dashboard must render without exceptions."""
    import os

    from streamlit.testing.v1 import AppTest

    cwd = os.getcwd()
    os.chdir(ROOT)  # DATA_PATH is repo-root-relative
    try:
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=240)
        at.run()
        assert not at.exception, f"dashboard raised: {at.exception}"
    finally:
        os.chdir(cwd)


def test_default_scope_equals_full_dataset_regression():
    """Regression (found in the 2026-10-02 KPI reconciliation): with ALL filters at
    their default selection, the rendered executive KPI header must equal the FULL
    dataset. 1,200 orders carry a missing City value — selecting every city type
    must NOT silently drop them (it previously did, showing 44,384 / Rs944,983
    instead of 45,584 / Rs974,344)."""
    import os

    from streamlit.testing.v1 import AppTest

    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=240)
        at.run()
        assert not at.exception, at.exception
        labels = [m.label for m in at.metric]
        orders_m = at.metric[labels.index("Delivery orders")]
        assert orders_m.value == "45,584", (
            f"default scope dropped data: rendered {orders_m.value}")
        exposure_m = at.metric[labels.index("Refund exposure")]
        assert "974,344" in exposure_m.value, f"exposure mismatch: {exposure_m.value}"
    finally:
        os.chdir(cwd)


def test_apply_global_filters_full_selection_is_noop():
    """Full city selection must be a no-op even with NaN City rows present."""
    orders = pd.read_csv(DATA)
    full = list(orders["City"].dropna().unique())
    out = apply_global_filters(orders, city_types=full, bands=BAND_LABELS)
    assert len(out) == len(orders), "full selection silently dropped rows"
    assert out["Refund_Amount"].sum() == orders["Refund_Amount"].sum()
    # a genuine subset still filters (and may exclude NaN-City rows, as intended)
    subset = apply_global_filters(orders, city_types=[full[0]])
    assert len(subset) < len(orders)
