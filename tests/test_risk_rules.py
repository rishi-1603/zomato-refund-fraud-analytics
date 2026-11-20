"""Tests for the FoodTrust risk rule registry."""
import pytest

from dashboard import risk_rules as rr


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
        assert rule.description.strip(), rule.rule_id
        assert rule.formula.strip(), rule.rule_id


def test_band_cut_points():
    assert rr.band_for_score(0) == "Low Risk"
    assert rr.band_for_score(39.9) == "Low Risk"
    assert rr.band_for_score(40) == "Review Recommended"
    assert rr.band_for_score(69.9) == "Review Recommended"
    assert rr.band_for_score(70) == "High Priority Review"
    assert rr.band_for_score(100) == "High Priority Review"
    with pytest.raises(ValueError):
        rr.band_for_score(101)
    with pytest.raises(ValueError):
        rr.band_for_score(-1)


def test_rule_lookup():
    r = rr.rule_by_id("RR-01")
    assert r.name == "Refund rate"
    with pytest.raises(KeyError):
        rr.rule_by_id("RR-999")


def test_risk_bands_tuple():
    assert rr.RISK_BANDS == ("Low Risk", "Review Recommended", "High Priority Review")
    assert rr.ELIGIBILITY_MIN_ORDERS == 5
    assert rr.ELIGIBILITY_MIN_RATE == 30.0