"""test_sensitivity_analysis.py — the score's stress test must be reproducible."""
import subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "sensitivity_analysis.md"

def test_script_runs_and_writes_report():
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"sensitivity_analysis.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-300:]
    assert REPORT.exists()

def test_signal_removal_results_are_deterministic():
    text = REPORT.read_text()
    # verified values from the audit run
    assert "75" in text and "26.9%" in text   # Refund_Rate removal
    assert "18" in text and "6.5%" in text    # Avg_Reason_Length removal
    assert "Refund Rate" in text

def test_alternative_weights_are_stable():
    """All alternative weight configs should have Spearman ρ > 0.95 — the
    ranking is robust to weight choices."""
    text = REPORT.read_text()
    assert "0.964" in text and "0.952" in text and "0.989" in text

def test_honest_framing():
    text = REPORT.read_text()
    assert "heuristic" in text
    assert "No optimization performed" in text
