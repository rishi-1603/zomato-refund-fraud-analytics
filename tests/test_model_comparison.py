"""
test_model_comparison.py — the rules-vs-ML comparison cannot drift.
===================================================================
Pins reports/model_comparison_metrics.json (written by
scripts/model_comparison.py) and locks the Day-4 verdict: head parity at
investigation cut sizes, ML's edge is funnel coverage only.

Run:  python -m pytest tests/test_model_comparison.py -v
"""
import json
import os
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

METRICS_PATH = os.path.join(BASE, "reports", "model_comparison_metrics.json")


@pytest.fixture(scope="module")
def metrics():
    assert os.path.exists(METRICS_PATH), \
        "reports/model_comparison_metrics.json missing — run scripts/model_comparison.py"
    with open(METRICS_PATH) as f:
        return json.load(f)


# ── Pinned values (Day-4 release, seeded synthetic data) ──────────────
def test_pinned_in_pool_aucs(metrics):
    ip = metrics["in_pool"]
    assert ip["rule_score"]["roc_auc"] == pytest.approx(0.942, abs=5e-3)
    assert ip["logistic_regression"]["roc_auc"] == pytest.approx(0.961, abs=5e-3)
    assert ip["gradient_boosting"]["roc_auc"] == pytest.approx(0.978, abs=5e-3)


def test_pinned_full_base(metrics):
    fb = metrics["full_base"]
    assert fb["n_planted_high"] == 298
    assert fb["funnel_visible_planted_high"] == 131
    assert fb["funnel_coverage_of_planted_high"] == pytest.approx(0.4396, abs=5e-3)
    assert fb["gradient_boosting"]["recall_at_40"] == pytest.approx(0.134, abs=5e-3)
    assert fb["gradient_boosting"]["precision_at_40"] == 1.0


def test_pinned_error_catalog(metrics):
    ec = metrics["error_catalog"]
    assert ec["missed_high_outside_funnel"] == 160
    assert ec["missed_high_in_funnel"] == 117


# ── The verdict is the finding — lock it ──────────────────────────────
def test_verdict_head_parity(metrics):
    assert metrics["verdict"]["head_parity_at_top20"] is True
    ip = metrics["in_pool"]
    for name in ip:
        assert ip[name]["precision_at_8"] == 1.0
        assert ip[name]["precision_at_20"] == 1.0


def test_verdict_recommends_hybrid_not_replacement(metrics):
    rec = metrics["verdict"]["recommendation"]
    assert "Do NOT swap" in rec
    assert "hybrid" in rec


# ── Statistical invariants ────────────────────────────────────────────
def test_ml_beats_rules_only_in_tail(metrics):
    ip = metrics["in_pool"]
    assert ip["gradient_boosting"]["roc_auc"] > ip["rule_score"]["roc_auc"]
    # ...yet head precision is identical
    assert ip["gradient_boosting"]["precision_at_20"] == ip["rule_score"]["precision_at_20"]


def test_simple_model_is_competitive(metrics):
    # logistic ≈ GBM on this data — the simpler model pays
    lr = metrics["full_base"]["logistic_regression"]["roc_auc"]
    gbm = metrics["full_base"]["gradient_boosting"]["roc_auc"]
    assert abs(lr - gbm) < 0.02


def test_tier_event_rates_are_monotone(metrics):
    tiers = {t["tier"]: t["planted_high_rate"] for t in metrics["rule_tier_event_rates"]}
    assert tiers["High"] >= tiers["Medium"] >= tiers["Low"]
    assert tiers["High"] == 1.0


def test_generator_caveat_is_documented(metrics):
    cav = metrics["generator_caveat"]
    assert "planted label" in cav and "not real-world superiority" in cav


def test_capacity_covers_all_systems(metrics):
    systems = {c["system"] for c in metrics["capacity"]}
    assert len(systems) == 4
    assert all(c["precision"] == 1.0 for c in metrics["capacity"])
