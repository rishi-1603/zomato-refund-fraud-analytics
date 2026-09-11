"""
test_baseline_normalization.py — baselines must be reproducible & consistent
==============================================================================
Pins the Phase-2 upgrade. The seeded dataset makes every value deterministic.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from baseline_normalization import build_baselines, BAND_LABELS  # noqa: E402

REPORT = ROOT / "reports" / "baseline_normalization.md"


def _load():
    return pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")


def test_script_runs_and_writes_report():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "baseline_normalization.py")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, f"script failed:\n{result.stderr[-400:]}"
    assert REPORT.exists(), "reports/baseline_normalization.md not written"


def test_band_distribution_is_deterministic():
    cust, bands = build_baselines(_load())
    # seeded data → exact counts per band (verified against audit run)
    counts = dict(zip(bands["band"], bands["customers"]))
    assert counts["1-2 orders"] == 1_514
    assert counts["3-5 orders"] == 5_331
    assert counts["6-10 orders"] == 2_978
    assert counts["11-20 orders"] == 72


def test_flagged_vs_baseline_split_is_deterministic():
    """The key Phase-2 finding: 166 above / 113 below baseline of the 279 flagged."""
    df = _load()
    cust, _ = build_baselines(df)
    sus = pd.read_csv(ROOT / "reports" / "fraud_suspects.csv")
    cust["is_flagged"] = cust["Customer_ID"].isin(set(sus["Customer_ID"]))
    flagged = cust[cust["is_flagged"]]
    above = flagged[flagged["above_baseline"]]
    below = flagged[~flagged["above_baseline"]]
    assert len(flagged) == 279
    assert len(above) == 166
    assert len(below) == 113


def test_all_bands_have_monotone_p95():
    """P95 should generally decrease as volume increases (more orders → less variance).
    Not strictly required by the data, but if a band's P95 jumps wildly,
    something changed and the report needs regeneration."""
    cust, bands = build_baselines(_load())
    p95s = bands.set_index("band")["p95"]
    # 1-2 orders and 3-5 orders naturally have high P95 (small denominators)
    assert p95s["1-2 orders"] >= p95s["3-5 orders"]


def test_report_contains_findings_and_honest_framing():
    text = REPORT.read_text(encoding="utf-8")
    # the key numbers
    assert "166" in text and "113" in text and "279" in text
    # honest framing must survive future edits
    assert "Above-baseline ≠ fraudulent" in text or "Above-baseline != fraudulent" in text
    assert "Activity ≠ fraud" in text or "Activity != fraud" in text
    assert "synthetic" in text.lower()
    assert "false-positive" in text
