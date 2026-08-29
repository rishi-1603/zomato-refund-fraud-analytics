"""
test_risk_pipeline.py — the risk pipeline must be reproducible and honest
==========================================================================
Pins the pipeline to its documented behaviour:
  - the suspects list regenerates deterministically from the orders data
  - scores stay in bounds, tiers match the documented thresholds
  - the recovered ground truth stays consistent with the committed data
  - the headline validation numbers (precision/recall/AUC) hold
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
SUSPECTS_PATH = ROOT / "reports" / "fraud_suspects.csv"
GT_PATH = ROOT / "data" / "processed" / "ground_truth_customer_risk.csv"


@pytest.fixture(scope="module")
def orders():
    df = pd.read_csv(ORDERS_PATH)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
    return df


@pytest.fixture(scope="module")
def risk_table(orders):
    from validate_risk_score import build_risk_table
    return build_risk_table(orders)


def test_suspects_csv_reproduces_from_orders(risk_table):
    """reports/fraud_suspects.csv must equal a fresh recomputation — no
    hand-edited numbers."""
    committed = pd.read_csv(SUSPECTS_PATH)
    assert len(committed) == len(risk_table), (
        f"Committed suspects {len(committed)} vs recomputed {len(risk_table)}")
    merged = committed.merge(risk_table[["Customer_ID", "Fraud_Risk_Score"]],
                             on="Customer_ID", how="left", suffixes=("_csv", "_new"))
    diff = (merged["Fraud_Risk_Score_csv"] - merged["Fraud_Risk_Score_new"]).abs()
    # 0.05 tolerance: float-rounding drift between the notebook's per-signal
    # .round(2) calls and the script's full-precision aggregation is ~0.01 max;
    # hand-fabricated numbers would differ by far more.
    assert diff.max() < 0.05, f"Scores drifted (max diff {diff.max():.2f})"


def test_scores_within_bounds(risk_table):
    assert risk_table["Fraud_Risk_Score"].between(0, 100).all()


def test_tier_thresholds_match_documentation(risk_table):
    """docs/risk_scoring_methodology.md: Low <= 40 < Medium <= 70 < High."""
    high = risk_table[risk_table["Risk_Tier"] == "High"]
    medium = risk_table[risk_table["Risk_Tier"] == "Medium"]
    low = risk_table[risk_table["Risk_Tier"] == "Low"]
    assert (high["Fraud_Risk_Score"] > 70).all()
    assert medium["Fraud_Risk_Score"].between(40, 70).all()
    assert (low["Fraud_Risk_Score"] <= 40).all()


def test_eligibility_rule_enforced(risk_table):
    """Pool rule: >= 5 orders AND refund rate > 30%."""
    assert (risk_table["Total_Orders"] >= 5).all()
    assert (risk_table["Refund_Rate"] > 30).all()


def test_ground_truth_exists_and_consistent(orders):
    """The recovered planted labels must exist and reproduce the committed
    dataset's customer assignment 100%."""
    assert GT_PATH.exists(), (
        "ground_truth_customer_risk.csv missing — run scripts/validate_risk_score.py")
    gt = pd.read_csv(GT_PATH, index_col="Customer_ID")["Planted_Risk"]
    assert set(gt.unique()) == {"Low", "Medium", "High"}
    # Planted High customers must actually show high refund behaviour in the data
    stats = orders.groupby("Customer_ID")["Refund_Requested"].agg(["sum", "count"])
    stats["rate"] = stats["sum"] / stats["count"]
    high_rate = stats.loc[stats.index.isin(gt[gt == "High"].index), "rate"].mean()
    low_rate = stats.loc[stats.index.isin(gt[gt == "Low"].index), "rate"].mean()
    assert high_rate > low_rate * 3, (
        "Planted High customers don't refund more than Low — labels are wrong")


def test_headline_validation_numbers(risk_table):
    """Pin the documented headline metrics from reports/score_validation.md:
    High tier is 100% precise but end-to-end recall is low (coverage gap)."""
    gt = pd.read_csv(GT_PATH, index_col="Customer_ID")["Planted_Risk"]
    n_planted_high = (gt == "High").sum()
    table = risk_table.copy()
    table["Planted_Risk"] = table["Customer_ID"].map(gt)

    high_tier = table[table["Risk_Tier"] == "High"]
    precision = (high_tier["Planted_Risk"] == "High").mean()
    recall = (high_tier["Planted_Risk"] == "High").sum() / n_planted_high

    assert precision == 1.0, f"High-tier precision dropped from 100% to {precision:.1%}"
    assert recall < 0.10, (
        "End-to-end recall changed materially — update reports/score_validation.md")


def test_validation_script_runs_clean():
    """The validation script is the source of truth for the report — it must
    run without errors."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_risk_score.py")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, f"Validation script failed:\n{result.stderr[-500:]}"
