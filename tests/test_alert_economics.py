"""
test_alert_economics.py — the alert economics engine must reproduce verified numbers
================================================================================
Day-2 upgrade pin. The dataset is seeded and deterministic, so every economic
quantity is a known value. These tests fail if the alert economics engine, the
risk score (build_risk_table), or the cost model drift apart.

Verified values (recomputed from data/ + reports/alert_economics.json):
279 flagged · 131 planted High · tier_high 8 alerts @ 100% precision net ₹8,273.51 ·
tier_high_plus_medium 115 alerts @ 87.83% precision net ₹92,125.11 (recommended) ·
all_flagged 279 @ 46.95% precision net ₹65,005.58 · break-even precision 28.19%.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from alert_economics import (  # noqa: E402
    break_even_precision,
    load_pool,
    run,
)

REPORT = ROOT / "reports" / "alert_economics.json"
MD = ROOT / "reports" / "alert_economics.md"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _policy(report, name):
    return next(p for p in report["policies"] if p["policy"] == name)


# ── pool pins ────────────────────────────────────────────────────────────────

def test_pool_pins_verified_counts():
    r = _report()
    assert r["pool"]["flagged_customers"] == 279
    assert r["pool"]["planted_high_in_pool"] == 131
    assert abs(r["pool"]["exposure_in_pool"] - 377891.92) < 0.01


def test_pool_exposure_matches_orders_file():
    pool = load_pool()
    orders = pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")
    total_refunds = float(orders["Refund_Amount"].sum())
    assert pool["Exposure"].sum() <= total_refunds
    assert int(pool["Is_True_High"].sum()) == 131


# ── policy pins ──────────────────────────────────────────────────────────────

def test_tier_high_policy_pins():
    p = _policy(_report(), "tier_high")
    assert p["alerts"] == 8
    assert p["true_high"] == 8
    assert p["false_positives"] == 0
    assert p["precision"] == 1.0
    assert abs(p["net_value"] - 8273.51) < 0.01


def test_tier_high_plus_medium_policy_pins_and_is_recommended():
    r = _report()
    p = _policy(r, "tier_high_plus_medium")
    assert p["alerts"] == 115
    assert p["precision"] == 0.8783
    assert p["recall"] == 0.771
    assert abs(p["net_value"] - 92125.11) < 0.01
    assert r["recommended_policy"] == "tier_high_plus_medium"
    assert abs(r["recommended_net_value"] - 92125.11) < 0.01


def test_all_flagged_policy_pins():
    p = _policy(_report(), "all_flagged")
    assert p["alerts"] == 279
    assert p["recall"] == 1.0
    assert p["precision"] == 0.4695
    assert abs(p["net_value"] - 65005.58) < 0.01


def test_med_plus_beats_alerting_everyone():
    r = _report()
    assert _policy(r, "tier_high_plus_medium")["net_value"] > _policy(r, "all_flagged")["net_value"]


# ── economic identities (must hold for any policy) ──────────────────────────

def test_net_is_recovered_minus_cost():
    for p in _report()["policies"]:
        assert abs(p["recovered_exposure"] - p["total_cost"] - p["net_value"]) < 0.02
        assert abs(p["review_cost"] + p["friction_cost"] - p["total_cost"]) < 0.02


def test_precision_recall_formulas():
    r = _report()
    for p in r["policies"]:
        assert abs(p["true_high"] / p["alerts"] - p["precision"]) < 1e-3
        assert abs(p["true_high"] / 131 - p["recall"]) < 1e-3


def test_break_even_precision_pins_and_satisfies_identity():
    r = _report()
    assert abs(r["break_even_precision"] - 0.2819) < 0.0001
    cm = r["cost_model"]
    recomputed = break_even_precision(cm["mean_recovery_per_true_high"])
    assert abs(recomputed - r["break_even_precision"]) < 1e-4


# ── budget curve & sensitivity ───────────────────────────────────────────────

def test_budget_curve_top10_is_perfect_precision():
    curve = {b["policy"]: b for b in _report()["alert_budget_curve"]}
    top10 = curve["top_10pct"]
    assert top10["alerts"] == 28
    assert top10["precision"] == 1.0
    assert abs(top10["net_value"] - 31978.68) < 0.01


def test_sensitivity_grid_is_9_scenarios_and_structural():
    r = _report()
    assert len(r["sensitivity_grid"]) == 9
    # At the harshest scenario (25% recovery, ₹400 review) the best policy
    # must still be a real policy name with a computed net.
    harshest = next(g for g in r["sensitivity_grid"]
                    if g["recovery_rate"] == 0.25 and g["review_cost"] == 400.0)
    assert harshest["best_policy"] in {"tier_high", "tier_high_plus_medium", "all_flagged"}
    assert isinstance(harshest["best_net_value"], (int, float))


# ── honest reporting ─────────────────────────────────────────────────────────

def test_report_discloses_synthetic_nature():
    md = MD.read_text(encoding="utf-8")
    assert "synthetic" in md.lower()
    assert "not a real P&L" in md
    r = _report()
    assert "planted" in r["honesty"].lower()


def test_run_is_deterministic():
    a = run()
    b = run()
    assert a["recommended_net_value"] == b["recommended_net_value"]
    assert a["break_even_precision"] == b["break_even_precision"]
