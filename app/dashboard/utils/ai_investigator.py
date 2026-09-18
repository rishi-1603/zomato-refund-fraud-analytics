"""
ai_investigator.py — evidence-grounded AI investigation assistant
==================================================================
Tool-calling layer: the LLM can query the risk engine, refund history,
and baseline comparison for any customer. The LLM NEVER computes numbers —
every value comes from these deterministic tools.

GUARDRAILS (enforced in the system prompt):
    - Risk score ≠ proof of fraud
    - The AI explains EVIDENCE; it does not make fraud determinations
    - Every number in the response must come from a tool call
    - If information is missing, say so — never guess

LLM provider: any OpenAI-compatible API (set OPENAI_API_KEY) or
Google Gemini (set GOOGLE_API_KEY). Falls back to deterministic
tool-output display when no key is configured.
"""
import os
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
SUSPECTS = ROOT / "reports" / "fraud_suspects.csv"

# ── Load data once ──
_orders = pd.read_csv(DATA)
_orders["Order_Date"] = pd.to_datetime(_orders["Order_Date"], dayfirst=True)
_suspects = pd.read_csv(SUSPECTS)


# ════════════════════════════════════════════════════════════════════════════
# TOOL FUNCTIONS (deterministic — the LLM calls these, never computes)
# ════════════════════════════════════════════════════════════════════════════

def get_customer_risk(customer_id: str) -> dict:
    """Get risk score, tier, and signals for a flagged customer."""
    row = _suspects[_suspects["Customer_ID"] == customer_id]
    if row.empty:
        return {"error": f"Customer {customer_id} is not in the flagged suspects list."}
    r = row.iloc[0]
    score = float(r["Fraud_Risk_Score"])
    tier = "High" if score > 70 else "Medium" if score > 40 else "Low"
    return {
        "customer_id": customer_id,
        "risk_score": score,
        "risk_tier": tier,
        "total_orders": int(r["Total_Orders"]),
        "total_refunds": int(r["Total_Refunds"]),
        "refund_rate_pct": float(r["Refund_Rate"]),
        "reason_repetition_pct": float(r.get("Reason_Repetition_Rate", 0)),
        "refunds_per_day": float(r.get("Refunds_Per_Day", 0)),
        "total_refund_amount": float(r["Total_Refund_Amount"]),
    }


def get_refund_history(customer_id: str) -> dict:
    """Get refund records for a customer: reasons, amounts, dates."""
    refunds = _orders[
        (_orders["Customer_ID"] == customer_id) &
        (_orders["Refund_Requested"] == True)
    ].copy()
    if refunds.empty:
        return {"customer_id": customer_id, "refund_count": 0, "refunds": []}
    records = []
    for _, r in refunds.sort_values("Order_Date").iterrows():
        records.append({
            "date": str(r["Order_Date"].date()),
            "reason": r["Refund_Reason"],
            "amount": float(r["Refund_Amount"]),
        })
    # reason distribution
    reason_counts = refunds["Refund_Reason"].value_counts().to_dict()
    return {
        "customer_id": customer_id,
        "refund_count": len(refunds),
        "total_refund_amount": float(refunds["Refund_Amount"].sum()),
        "reason_distribution": reason_counts,
        "most_repeated_reason": refunds["Refund_Reason"].value_counts().index[0],
        "refunds": records[:20],  # cap at 20 for context window
    }


def get_baseline_comparison(customer_id: str) -> dict:
    """Compare customer's refund rate against their order-volume band's P95."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from baseline_normalization import build_baselines
    cust, bands = build_baselines(_orders)
    row = cust[cust["Customer_ID"] == customer_id]
    if row.empty:
        return {"error": f"Customer {customer_id} not found."}
    r = row.iloc[0]
    return {
        "customer_id": customer_id,
        "volume_band": r["volume_band"],
        "customer_refund_rate": float(r["refund_rate"]),
        "band_p95_threshold": float(r["band_p95"]),
        "above_baseline": bool(r["above_baseline"]),
        "interpretation": (
            "ABOVE baseline: refund rate is unusual for their order volume"
            if r["above_baseline"]
            else "WITHIN baseline: refund rate is high in absolute terms but "
                 "not unusual for their order volume (false-positive candidate)"
        ),
    }


# ── Tool registry (for LLM function calling) ──
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_risk",
            "description": "Get the risk score, tier, and behavioral signals for a flagged customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID e.g. CUST07704"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_refund_history",
            "description": "Get the refund history (reasons, amounts, dates) for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_baseline_comparison",
            "description": "Compare a customer's refund rate against their order-volume band's P95 baseline",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID"}
                },
                "required": ["customer_id"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "get_customer_risk": get_customer_risk,
    "get_refund_history": get_refund_history,
    "get_baseline_comparison": get_baseline_comparison,
}

# ── System prompt with guardrails ──
SYSTEM_PROMPT = """You are a fraud investigation assistant for a food-delivery platform.

CRITICAL RULES (violating any of these is a system failure):
1. RISK SCORE ≠ PROOF OF FRAUD. Never state or imply that a customer is "fraudulent" or "guilty." The risk score is a review-prioritization signal only.
2. EVERY NUMBER must come from a tool call result. Never calculate, estimate, or invent any figure.
3. If a tool returns an error or missing data, say so explicitly. Never guess.
4. Distinguish clearly between: DATA (from tools), MODEL OUTPUT (risk score), and YOUR INTERPRETATION (what the evidence suggests).
5. Always include: (a) what the evidence shows, (b) what information is missing, (c) what should be investigated next.
6. Recommend HUMAN REVIEW for every conclusion. Never recommend automated action (bans, blocks, account restrictions).
7. The dataset is synthetic (seeded). Mention this caveat when presenting findings.

STRUCTURE your response as:
## Risk Assessment
[Score, tier, key signals — from tool calls]

## Evidence Summary
[Refund history, reasons, amounts — from tool calls]

## Baseline Context
[How this customer compares to similar-volume customers — from tool calls]

## What to Investigate Next
[Specific questions a human investigator should answer]

## Important Caveats
[Risk score ≠ fraud, synthetic data, missing information]

Use these tool functions to get the data before answering. Call ALL three tools for a complete picture."""


def investigate(customer_id: str) -> dict:
    """Run the full investigation: call all 3 tools, return the evidence."""
    risk = get_customer_risk(customer_id)
    history = get_refund_history(customer_id)
    baseline = get_baseline_comparison(customer_id)
    return {"risk": risk, "history": history, "baseline": baseline}


def investigate_with_llm(customer_id: str) -> dict:
    """Full investigation with LLM explanation layer (if API key available)."""
    evidence = investigate(customer_id)
    if "error" in evidence["risk"]:
        return {"ok": False, "error": evidence["risk"]["error"]}

    # Try LLM providers
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            try:
                return _investigate_with_gemini(customer_id, evidence, google_key)
            except Exception as e:
                return {"ok": True, "evidence": evidence,
                        "explanation": None, "llm_error": str(e)}

    if not api_key:
        return {"ok": True, "evidence": evidence, "explanation": None,
                "note": "No LLM API key configured. Displaying tool outputs only."}

    try:
        return _investigate_with_openai(customer_id, evidence, api_key)
    except Exception as e:
        return {"ok": True, "evidence": evidence, "explanation": None,
                "llm_error": str(e)}


def _investigate_with_openai(customer_id, evidence, api_key):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    evidence_json = json.dumps(evidence, indent=2, default=str)
    resp = client.chat.completions.create(
        model=os.environ.get("BRIEF_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Investigate customer {customer_id}. Here is the evidence from all three tools:\n```json\n{evidence_json}\n```\n\nWrite the investigation summary."}
        ],
        temperature=0.1,
    )
    return {"ok": True, "evidence": evidence,
            "explanation": resp.choices[0].message.content}


def _investigate_with_gemini(customer_id, evidence, api_key):
    import google.genai as genai
    client = genai.Client(api_key=api_key)
    evidence_json = json.dumps(evidence, indent=2, default=str)
    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{SYSTEM_PROMPT}\n\nInvestigate customer {customer_id}. Evidence:\n```json\n{evidence_json}\n```\n\nWrite the investigation summary."
    )
    return {"ok": True, "evidence": evidence,
            "explanation": resp.text}
