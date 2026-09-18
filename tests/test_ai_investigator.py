"""
test_ai_investigator.py — the AI investigation layer must be evidence-grounded.
==============================================================================
Tests the tool functions (deterministic), the guardrails in the system prompt,
and the investigation pipeline.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.dashboard.utils.ai_investigator import (
    get_customer_risk, get_refund_history, get_baseline_comparison,
    investigate, SYSTEM_PROMPT, TOOLS, TOOL_FUNCTIONS
)


class TestToolFunctions:
    """Tool functions must return deterministic, correct data."""

    def test_get_customer_risk_known_customer(self):
        r = get_customer_risk("CUST07704")
        assert r["risk_score"] == 84.72
        assert r["risk_tier"] == "High"
        assert r["total_orders"] == 5
        assert r["total_refunds"] == 5

    def test_get_customer_risk_unknown(self):
        r = get_customer_risk("CUST99999")
        assert "error" in r

    def test_get_refund_history(self):
        h = get_refund_history("CUST07704")
        assert h["refund_count"] == 5
        assert h["total_refund_amount"] > 0
        assert "most_repeated_reason" in h
        assert len(h["refunds"]) == 5

    def test_get_baseline_comparison(self):
        b = get_baseline_comparison("CUST07704")
        assert b["above_baseline"] == True
        assert "volume_band" in b
        assert "interpretation" in b

    def test_investigate_returns_all_three(self):
        result = investigate("CUST07704")
        assert "risk" in result and "history" in result and "baseline" in result
        assert result["risk"]["risk_score"] == 84.72


class TestGuardrails:
    """The system prompt must enforce the non-negotiable rules."""

    def test_prompt_contains_fraud_disclaimer(self):
        assert "RISK SCORE ≠ PROOF OF FRAUD" in SYSTEM_PROMPT

    def test_prompt_requires_tool_data(self):
        assert "tool call" in SYSTEM_PROMPT.lower() or "tool function" in SYSTEM_PROMPT.lower()

    def test_prompt_requires_human_review(self):
        assert "human" in SYSTEM_PROMPT.lower()

    def test_prompt_prohibits_automated_action(self):
        assert "automated" in SYSTEM_PROMPT.lower()
        assert "ban" in SYSTEM_PROMPT.lower() or "block" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_synthetic_data(self):
        assert "synthetic" in SYSTEM_PROMPT.lower()

    def test_all_tools_registered(self):
        assert len(TOOLS) == 3
        assert set(TOOL_FUNCTIONS.keys()) == {
            "get_customer_risk", "get_refund_history", "get_baseline_comparison"
        }


class TestEvidenceConsistency:
    """Tool outputs must match the pipeline's known values."""

    def test_risk_matches_suspects_csv(self):
        sus = pd.read_csv(ROOT / "reports" / "fraud_suspects.csv")
        row = sus[sus["Customer_ID"] == "CUST07704"].iloc[0]
        r = get_customer_risk("CUST07704")
        assert r["risk_score"] == row["Fraud_Risk_Score"]
        assert r["total_orders"] == row["Total_Orders"]

    def test_refund_total_matches_data(self):
        df = pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")
        expected = df[
            (df["Customer_ID"] == "CUST07704") & (df["Refund_Requested"] == True)
        ]["Refund_Amount"].sum()
        h = get_refund_history("CUST07704")
        assert h["total_refund_amount"] == expected
