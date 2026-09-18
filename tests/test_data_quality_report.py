"""test_data_quality_report.py — DQ report must be reproducible & truthful."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "data_quality_report.md"

def test_script_runs_and_writes_report():
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"data_quality_report.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-300:]
    assert REPORT.exists()

def test_all_checks_present():
    text = REPORT.read_text()
    for family in ["Completeness", "Uniqueness", "Validity", "Consistency"]:
        assert family in text

def test_known_quirks_documented():
    text = REPORT.read_text()
    assert "six-star" in text or "6.0" in text  # the 53 ratings quirk
    assert "synthetic" in text.lower()
    assert "No records were dropped" in text
