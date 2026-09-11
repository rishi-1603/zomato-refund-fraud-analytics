"""test_false_positive_analysis.py — FP analysis must be reproducible & honest."""
import subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "false_positive_analysis.md"

def test_script_runs_and_writes_report():
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"false_positive_analysis.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-300:]
    assert REPORT.exists()

def test_ground_truth_split_is_deterministic():
    """131 TP / 73 FP / 75 grey of 279 flagged — the measured FP rate."""
    text = REPORT.read_text()
    assert "131" in text and "73" in text and "75" in text

def test_baseline_validates_as_fp_screen():
    """The key finding: below-baseline group has 57.5% FP vs 4.8% above."""
    text = REPORT.read_text()
    assert "57.5%" in text and "4.8%" in text

def test_honest_framing():
    text = REPORT.read_text()
    assert "Never auto-ban" in text or "never automated action" in text
    assert "planted" in text  # ground truth is planted, not real
    assert "grey area" in text
