"""
test_external_validation.py — provenance audit + real-drift tripwire validation
================================================================================
Day-2 upgrade pin. Verified:
20/24 columns real (83%) · traffic→time monotonic (20/27/27/31 min) ·
worst weather Cloudy (28 min) · ratings mean 4.634 ·
external airline drift PSI 11.8773 → significant → tripwire FIRED on real data.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "external_validation.json"
MD = ROOT / "reports" / "external_validation.md"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_provenance_is_complete_and_83pct_real():
    p = _report()["provenance"]
    assert p["provenance_complete"] is True
    assert len(p["real_columns"]) == 20
    assert len(p["synthetic_columns"]) == 4
    assert abs(p["real_share_of_columns"] - 20 / 24) < 1e-4


def test_real_findings_pin_traffic_effect():
    f = _report()["real_findings"]
    assert f["median_time_by_traffic_min"] == {"Low": 20.0, "High": 27.0, "Medium": 27.0, "Jam": 31.0}
    assert f["traffic_time_monotonic"] is True
    assert f["worst_weather"] == "Cloudy"
    assert f["ratings_mean"] == 4.634
    assert f["ratings_below_3_share"] == 0.0031
    assert f["orders"] == 45584


def test_external_drift_tripwire_fires_on_real_data():
    d = _report()["external_drift_validation"]
    assert d["reference_mean"] == 158.4
    assert d["current_mean"] == 413.5
    assert d["psi"] == 11.8773
    assert d["grade"] == "significant"
    assert d["tripwire_fired"] is True


def test_scope_of_validity_labels_both_worlds():
    worlds = {v["world"] for v in _report()["scope_of_validity"]}
    assert worlds == {"real-backed", "synthetic-layer"}
    synthetic = [v for v in _report()["scope_of_validity"] if v["world"] == "synthetic-layer"]
    assert any("economics" in v["claim"].lower() or "risk" in v["claim"].lower()
               for v in synthetic)


def test_report_discloses_the_split():
    md = MD.read_text(encoding="utf-8").lower()
    assert "synthetic" in md
    assert "real" in md
    assert "scope of validity" in md


def test_committed_external_copy_exists():
    fl = ROOT / "data" / "external" / "flights.csv"
    assert fl.exists()
    assert len(fl.read_text(encoding="utf-8").strip().splitlines()) == 145  # header + 144 months
