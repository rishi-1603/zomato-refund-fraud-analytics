"""
test_pareto_analysis.py — concentration results must be reproducible & consistent
================================================================================
Pins the Phase-1 upgrade. The dataset is seeded, so every cut is deterministic:
these tests fail if the data, the analysis, or the cross-checks drift apart.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pareto_analysis import compute_concentration  # noqa: E402

REPORT = ROOT / "reports" / "pareto_analysis.md"


def _load():
    return pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")


def test_script_runs_and_writes_report():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pareto_analysis.py")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, f"script failed:\n{result.stderr[-400:]}"
    assert REPORT.exists(), "reports/pareto_analysis.md not written"


def test_concentration_cuts_are_deterministic():
    c = compute_concentration(_load())
    # seeded data → exact, reproducible values (checked against audit run)
    assert c["n_customers"] == 9_895
    assert c["n_with_refund"] == 2_515
    assert abs(c["total_value"] - 974_344.0) < 1.0
    assert abs(c["top1"][1] - 26.9) < 0.2
    assert abs(c["top5"][1] - 60.6) < 0.2
    assert abs(c["top10"][1] - 75.6) < 0.2
    assert c["cover50"][0] == 292
    assert c["cover80"][0] == 1_165


def test_suspects_cross_check_matches_score_validation():
    """The 279 flagged suspects must hold exactly 38.78% of exposure — the same
    number reported in score_validation.md. Two independent analyses, one number."""
    df = _load()
    total = df["Refund_Amount"].sum()
    suspects = pd.read_csv(ROOT / "reports" / "fraud_suspects.csv")
    share = suspects["Total_Refund_Amount"].sum() / total * 100
    assert abs(share - 38.78) < 0.01, f"suspect share drifted: {share:.2f}%"
    assert len(suspects) == 279


def test_report_contains_findings_and_honest_framing():
    text = REPORT.read_text(encoding="utf-8")
    # findings
    assert "26.9" in text and "75.6" in text
    assert "292" in text
    # honest framing must survive future edits
    assert "not confirmed fraud loss" in text
    assert "synthetic" in text
    assert "Concentration ≠ guilt" in text or "Concentration != guilt" in text
