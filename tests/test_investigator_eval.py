"""
test_investigator_eval.py — the investigator must not fabricate, and must refuse
================================================================================
Day-2 upgrade pin. The eval harness recomputes every number the investigator
returns; these tests pin the harness results and the product properties:

Verified: answerable 6/6 grounded · unanswerable 6/6 refused · fabrications 0 ·
verdict PASS · schema clean (no verdict-like fields).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
sys.path.insert(0, str(ROOT / "scripts"))

REPORT = ROOT / "reports" / "investigator_eval.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_answerable_cases_all_grounded():
    r = _report()
    assert r["answerable"]["n"] == 6
    assert r["answerable"]["passed"] == 6
    assert r["answerable"]["accuracy"] == 1.0
    assert all(c["rubric_pass"] for c in r["answerable"]["cases"])


def test_unanswerable_cases_all_refused():
    r = _report()
    assert r["unanswerable"]["n"] == 6
    assert r["unanswerable"]["refused_correctly"] == 6
    assert r["unanswerable"]["refusal_accuracy"] == 1.0
    for c in r["unanswerable"]["cases"]:
        assert c["refused"] and not c["fabricated_score"]


def test_zero_fabrications_and_verdict_pass():
    r = _report()
    assert r["fabrications_total"] == 0
    assert r["mismatch_details"] == []
    assert r["verdict"] == "PASS"


def test_schema_has_no_verdict_fields():
    for c in _report()["answerable"]["cases"]:
        assert c["forbidden_schema_fields"] == []


def test_unknown_id_returns_error_not_a_score():
    import ai_investigator as inv
    e = inv.investigate("CUST99999")
    assert "error" in e["risk"]
    assert "risk_score" not in e["risk"]


def test_answerable_customer_returns_all_three_tools_and_verified_numbers():
    import ai_investigator as inv
    from investigator_eval import recompute_customer, audit_numbers
    import pandas as pd
    orders = pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)
    e = inv.investigate("CUST07704")
    assert set(e) == {"risk", "history", "baseline"}
    assert "error" not in e["risk"]
    assert audit_numbers(e, recompute_customer(orders, "CUST07704")) == []


def test_eval_is_deterministic():
    from investigator_eval import run
    a, b = run(), run()
    assert a["verdict"] == b["verdict"]
    assert a["fabrications_total"] == b["fabrications_total"]
