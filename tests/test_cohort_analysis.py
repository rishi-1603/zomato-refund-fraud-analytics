"""test_cohort_analysis.py — cohort results must be reproducible."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "cohort_analysis.md"

def test_script_runs_and_writes_report():
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"cohort_analysis.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-300:]
    assert REPORT.exists()

def test_cohorts_present():
    text = REPORT.read_text()
    for cohort in ["2022-02", "2022-03", "2022-04"]:
        assert cohort in text

def test_honest_framing():
    text = REPORT.read_text()
    assert "synthetic" in text.lower()
    assert "by construction" in text
