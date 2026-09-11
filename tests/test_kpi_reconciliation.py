"""test_kpi_reconciliation.py — Python and SQL must agree on every KPI."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "kpi_reconciliation.md"

def test_script_runs_and_writes_report():
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"kpi_reconciliation.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-300:]
    assert REPORT.exists()

def test_all_metrics_reconcile():
    text = REPORT.read_text()
    assert "ALL METRICS RECONCILE" in text
    assert "MISMATCH" not in text

def test_key_numbers_present():
    text = REPORT.read_text()
    for val in ["45,584", "3,596", "974,343", "9,895", "279", "377,891", "38.78"]:
        assert val in text, f"missing: {val}"
