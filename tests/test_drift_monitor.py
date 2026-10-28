"""
test_drift_monitor.py — the drift console must reproduce verified numbers AND
detect drift when it exists
================================================================================
Day-2 upgrade pin. Two kinds of pins here:

A. The console's output on the real stream is deterministic and verified:
   reference 7,242 orders @ 7.29% refund rate · 6 monitoring weeks, all
   STABLE (max PSI 0.0129) · overall verdict STABLE.

B. The TRIPWIRE must fire on injected drift. A monitor that only ever prints
   STABLE is decoration; these tests shift a distribution deliberately and
   require the PSI grade to go significant.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drift_monitor import (  # noqa: E402
    grade,
    psi,
    psi_categorical,
    run,
)

REPORT = ROOT / "reports" / "drift_monitor.json"
MD = ROOT / "reports" / "drift_monitor.md"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


# ── A. real-stream pins ──────────────────────────────────────────────────────

def test_reference_window_pins():
    ref = _report()["reference_window"]
    assert ref["orders"] == 7242
    assert ref["refund_rate"] == 0.0729
    assert ref["weeks"] == ["2022-02-07/2022-02-13", "2022-02-14/2022-02-20"]


def test_all_monitoring_weeks_stable_and_pinned():
    r = _report()
    weeks = r["monitoring_weeks"]
    assert len(weeks) == 6
    for w in weeks:
        assert w["verdict"] == "STABLE"
        assert w["n_significant"] == 0
        assert w["worst_psi"] < 0.10
    assert max(w["worst_psi"] for w in weeks) == 0.0129


def test_overall_verdict_is_stable_with_no_drift_week():
    r = _report()
    assert r["overall_verdict"] == "STABLE"
    assert r["first_drift_week"] is None
    assert r["first_watch_week"] is None


def test_refund_rate_moves_less_than_2pp_all_weeks():
    for w in _report()["monitoring_weeks"]:
        assert abs(w["refund_rate_delta_pp"]) < 2.0


# ── B. tripwire: injected drift MUST fire ────────────────────────────────────

def test_psi_detects_shifted_numeric_distribution():
    rng = np.random.default_rng(42)
    ref = rng.normal(30, 5, 5000)
    cur = rng.normal(36, 5, 5000)   # one SD shift
    p = psi(ref, cur)
    assert p > 0.25, f"PSI {p:.3f} missed a 1-SD shift"
    assert grade(p) == "significant"


def test_psi_is_low_for_same_distribution():
    rng = np.random.default_rng(7)
    ref = rng.normal(30, 5, 5000)
    cur = rng.normal(30, 5, 5000)
    p = psi(ref, cur)
    assert p < 0.10, f"PSI {p:.3f} false-alarmed on an identical distribution"
    assert grade(p) == "stable"


def test_psi_categorical_detects_new_dominant_category():
    ref = pd.Series(["A"] * 80 + ["B"] * 20)
    cur = pd.Series(["A"] * 20 + ["C"] * 80)   # population replaced
    p = psi_categorical(ref, cur)
    assert p > 0.25
    assert grade(p) == "significant"


def test_grade_boundaries():
    assert grade(0.09) == "stable"
    assert grade(0.10) == "moderate"
    assert grade(0.24) == "moderate"
    assert grade(0.25) == "significant"


# ── determinism & honest reporting ──────────────────────────────────────────

def test_run_is_deterministic():
    a = run()
    b = run()
    assert a["overall_verdict"] == b["overall_verdict"]
    assert [w["worst_psi"] for w in a["monitoring_weeks"]] == \
           [w["worst_psi"] for w in b["monitoring_weeks"]]


def test_report_discloses_synthetic_nature():
    md = MD.read_text(encoding="utf-8")
    assert "synthetic" in md.lower()
    assert "retrain" in md.lower()
    r = _report()
    assert "synthetic" in r["honesty"].lower()
