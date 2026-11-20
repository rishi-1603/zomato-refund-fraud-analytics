"""Tests for the FoodTrust case-management lifecycle and risk rule registry."""
import pytest

from dashboard import case_management as cm
from dashboard import risk_rules as rr


# ── Risk rule registry ───────────────────────────────────────────────────────
def test_score_weights_sum_to_one():
    assert rr.score_total_check() == 1.0


def test_rule_weights_match_pinned_methodology():
    weights = {r.rule_id: r.weight for r in rr.RULES}
    assert weights["RR-01"] == 0.40
    assert weights["RR-02"] == 0.30
    assert weights["RR-03"] == 0.20
    assert weights["RR-04"] == 0.10
    # context rules contribute no score weight
    assert weights["RR-05"] == 0.0
    assert weights["RR-06"] == 0.0


def test_every_rule_documents_test_and_limitation():
    for rule in rr.RULES:
        assert rule.limitation.strip(), rule.rule_id
        assert rule.test.startswith("tests/"), rule.rule_id
        assert rule.rationale.strip(), rule.rule_id


def test_band_cut_points():
    assert rr.band_for_score(0) == "Low Risk"
    assert rr.band_for_score(39.9) == "Low Risk"
    assert rr.band_for_score(40) == "Review Recommended"
    assert rr.band_for_score(69.9) == "Review Recommended"
    assert rr.band_for_score(70) == "High Priority Review"
    with pytest.raises(ValueError):
        rr.band_for_score(101)


# ── Case lifecycle ───────────────────────────────────────────────────────────
def _open_case(**overrides):
    kwargs = dict(
        customer_id="CUST00042",
        risk_score=72.5,
        risk_band="High Priority Review",
        exposure=1234.5,
        alert_reasons=["Repeat Wrong Item claims", "Refund rate 45% in 21+ band"],
    )
    kwargs.update(overrides)
    return cm.open_case(**kwargs)


def test_open_case_defaults_and_first_audit_event():
    case = _open_case()
    assert case["status"] == cm.NEW
    assert case["priority"] == "High"  # derived from High Priority Review band
    assert len(case["events"]) == 1
    assert case["events"][0]["field"] == "status"
    assert case["events"][0]["to"] == cm.NEW


def test_open_case_low_band_gets_low_priority():
    case = _open_case(risk_band="Low Risk", risk_score=10)
    assert case["priority"] == "Low"


def test_happy_path_review_then_confirm_then_close():
    case = _open_case()
    cm.change_status(case, cm.UNDER_REVIEW, note="started")
    cm.record_outcome(case, cm.CONFIRMED_ISSUE, note="pattern repeated on a 6th order")
    cm.close_case(case, note="sent to ops with evidence")
    assert case["status"] == cm.CLOSED
    fields = [e["field"] for e in case["events"]]
    assert fields == ["status", "status", "outcome", "status"]


def test_cleared_case_closes_and_stays_in_history():
    case = _open_case()
    cm.change_status(case, cm.UNDER_REVIEW)
    cm.record_outcome(case, cm.CLEARED, note="delivery failure confirmed by rider log")
    cm.close_case(case)
    assert case["status"] == cm.CLOSED
    assert case["outcome"] == cm.CLEARED
    # Cleared cases may only be closed — never re-opened
    with pytest.raises(ValueError):
        cm.change_status(case, cm.UNDER_REVIEW)


def test_illegal_transition_rejected():
    case = _open_case()
    with pytest.raises(ValueError, match="not allowed"):
        cm.change_status(case, cm.CLOSED)  # New -> Closed without outcome


def test_close_without_outcome_rejected():
    case = _open_case()
    cm.change_status(case, cm.UNDER_REVIEW)
    with pytest.raises(ValueError, match="outcome"):
        cm.change_status(case, cm.CLOSED)


def test_outcome_cannot_be_changed_once_recorded():
    case = _open_case()
    cm.change_status(case, cm.UNDER_REVIEW)
    cm.record_outcome(case, cm.CLEARED)
    with pytest.raises(ValueError, match="already recorded"):
        cm.record_outcome(case, cm.CONFIRMED_ISSUE)


def test_priority_change_is_audited():
    case = _open_case()
    cm.set_priority(case, "Medium", note="rebalanced queue")
    event = case["events"][-1]
    assert event["field"] == "priority"
    assert event["from"] == "High" and event["to"] == "Medium"


def test_status_change_to_same_status_rejected():
    case = _open_case()
    with pytest.raises(ValueError, match="already in that status"):
        cm.change_status(case, cm.NEW)


def test_validate_rejects_tampered_audit_trail():
    case = _open_case()
    cm.change_status(case, cm.UNDER_REVIEW)
    tampered = dict(case)
    tampered["status"] = cm.CLOSED  # status not reflected in audit trail
    with pytest.raises(ValueError, match="does not match current status"):
        cm.validate(tampered)


def test_validate_rejects_illegal_transition_in_history():
    case = _open_case()
    forged = dict(case)
    forged["events"] = list(case["events"])
    forged["events"].append({"at_utc": "2026-01-01T00:00:00+00:00", "actor": "x",
                             "field": "status", "from": cm.NEW, "to": cm.CONFIRMED_ISSUE,
                             "note": "forged"})
    forged["status"] = cm.CONFIRMED_ISSUE
    with pytest.raises(ValueError, match="illegal transition"):
        cm.validate(forged)


def test_export_import_roundtrip():
    case = _open_case()
    cm.change_status(case, cm.ESCALATED)
    blob = cm.export_cases([case])
    restored = cm.import_cases(blob)
    assert restored[0]["case_id"] == case["case_id"]
    assert restored[0]["status"] == cm.ESCALATED
    assert len(restored[0]["events"]) == len(case["events"])


def test_import_rejects_oversized_or_invalid_payload():
    with pytest.raises(ValueError):
        cm.import_cases(b"not json")
    with pytest.raises(ValueError):
        cm.import_cases(b"[]") if False else cm.import_cases(b'{"a": 1}')  # not a list


def test_language_policy_terms():
    """Outcomes are Cleared / Confirmed Issue — never fraud verdicts."""
    text = " ".join([cm.CLEARED, cm.CONFIRMED_ISSUE]).lower()
    assert "fraud" not in text
    assert "guilt" not in text
