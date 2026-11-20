"""Risk rule registry — the declarative source of truth for the review score.
================================================================================
The weights and thresholds here MUST stay identical to dashboard/kpi_engine.py
and docs/risk_scoring_methodology.md. This registry exists so that every rule
carries its description, formula, threshold, rationale, limitation and test
reference beside the code — the structure the FoodTrust brief requires.

A score is a review PRIORITISATION. It is uncalibrated: 70 is not a 70%
probability of anything. A flag never implies guilt (language policy).
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCORE_MIN = 0.0
SCORE_MAX = 100.0

# Eligibility rule (identical to kpi_engine + methodology doc)
ELIGIBILITY_MIN_ORDERS = 5
ELIGIBILITY_MIN_RATE = 30.0  # percent

RISK_BANDS = ("Low Risk", "Review Recommended", "High Priority Review")


@dataclass(frozen=True)
class RiskRule:
    rule_id: str
    name: str
    weight: float                     # contribution weight in the score
    description: str
    formula: str
    threshold: str
    rationale: str
    limitation: str
    test: str
    tags: tuple = field(default_factory=tuple)


RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id="RR-01",
        name="Refund rate",
        weight=0.40,
        description="Share of a customer's orders carrying a refund request.",
        formula="refund_request_rows / customer_order_rows * 100",
        threshold="eligibility: rate > 30% and orders >= 5",
        rationale=(
            "Rate is the strongest single signal of claim-heavy behaviour, and the "
            "eligibility rule bounds it to customers with enough history for the rate to mean something."
        ),
        limitation=(
            "Short histories can show extreme rates; the 5-order floor mitigates but does not remove this. "
            "Rate alone cannot distinguish operational failures from abuse."
        ),
        test="tests/test_kpi_engine.py::test_score_components",
        tags=("eligibility", "score"),
    ),
    RiskRule(
        rule_id="RR-02",
        name="Reason repetition",
        weight=0.30,
        description="How often a customer repeats the same refund reason.",
        formula="max reason share across the customer's claim reasons",
        threshold="contributes via weighted score; no standalone flag",
        rationale=(
            "Genuine operational failures vary; identical repeated reasons on separate orders "
            "is the classic claim-pattern signal."
        ),
        limitation=(
            "A customer living in an area with a real recurring fulfilment problem can legitimately "
            "repeat one reason. Repetition is a review hint, never evidence of intent."
        ),
        test="tests/test_kpi_engine.py::test_score_components",
        tags=("score",),
    ),
    RiskRule(
        rule_id="RR-03",
        name="Refund frequency",
        weight=0.20,
        description="Count of refund-request rows for the customer.",
        formula="refund_request_rows",
        threshold="contributes via weighted score",
        rationale="Absolute claim volume drives review cost and potential exposure.",
        limitation=(
            "High-frequency customers may simply be high-volume customers; the volume-band baseline "
            "(RR-04) exists precisely to contextualise this rule."
        ),
        test="tests/test_kpi_engine.py::test_score_components",
        tags=("score",),
    ),
    RiskRule(
        rule_id="RR-04",
        name="Reason breadth (length of claim profile)",
        weight=0.10,
        description="Breadth of distinct reasons used by the customer.",
        formula="distinct refund reasons used (normalised)",
        threshold="contributes via weighted score",
        rationale="Claiming many different reason types can indicate opportunistic behaviour.",
        limitation="Weakest signal by design; broad reason use is also consistent with genuinely unlucky customers.",
        test="tests/test_kpi_engine.py::test_score_components",
        tags=("score",),
    ),
    RiskRule(
        rule_id="RR-05",
        name="Volume-band baseline comparison",
        weight=0.0,
        description=(
            "Context rule, not a score component: compare the customer's rate with the P95 rate "
            "of their order-volume band (1-2, 3-5, 6-10, 11-20, 21+)."
        ),
        formula="flag if customer rate > band P95",
        threshold="band P95",
        rationale=(
            "Protects legitimate high-volume customers from being flagged purely for having more orders. "
            "113 of the 279 flagged customers sit at or below their band's P95."
        ),
        limitation=(
            "Applied AFTER eligibility, so the below-baseline count is descriptive of the pool, "
            "not a measured false-positive rate."
        ),
        test="tests/test_baseline_normalization.py",
        tags=("context", "fairness"),
    ),
    RiskRule(
        rule_id="RR-06",
        name="Connected-entity network check",
        weight=0.0,
        description=(
            "Context check: shared delivery-person, restaurant-cell and drop-cell components "
            "scored against dataset baseline, with permutation testing."
        ),
        formula="component excess refund rate; permutation p-value",
        threshold="ranked by excess rate, not size",
        rationale="Clustered refunds across shared entities can reveal marketplace-side problems.",
        limitation=(
            "The delivery-person permutation test returned p = 0.76 — no clustering evidence beyond "
            "chance in this dataset. A null result is a valid result and is reported as such."
        ),
        test="tests/test_network_analysis.py",
        tags=("context", "network"),
    ),
)


def score_total_check() -> float:
    """Score weights must sum to 1.0. Raises if the registry drifts."""
    total = sum(r.weight for r in RULES)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Score weights sum to {total}, expected 1.0")
    return total


def rule_by_id(rule_id: str) -> RiskRule:
    for r in RULES:
        if r.rule_id == rule_id:
            return r
    raise KeyError(f"Unknown rule id {rule_id!r}")


def band_for_score(score: float) -> str:
    """Map a 0-100 score to a review-priority band (documented cut-points)."""
    if score < 0 or score > 100:
        raise ValueError("Score must be within 0-100.")
    if score >= 70:
        return "High Priority Review"
    if score >= 40:
        return "Review Recommended"
    return "Low Risk"
