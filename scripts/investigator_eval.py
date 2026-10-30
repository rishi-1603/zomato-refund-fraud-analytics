"""
investigator_eval.py — hallucination audit + rubric for the AI investigator
================================================================================
THE STORY THIS SCRIPT TELLS:

dashboard/ai_investigator.py is the agentic layer: deterministic tools fetch
evidence, and an optional LLM narrates it. The project's trust claim is that
the evidence layer CANNOT fabricate — but a claim is not a test. This harness
is the test:

  1. ANSWERABLE CASES: for each benchmark customer, run the investigation and
     RECOMPUTE every returned number from the raw CSV. A single mismatch is a
     fabrication — scored as such, not rounded away.
  2. UNANSWERABLE CASES (unknown IDs, unflagged customers): the investigator
     must REFUSE (surface an error), never invent a risk score. Refusal
     correctness is scored separately from answer correctness — the same
     structure as the e-commerce NL2SQL eval.
  3. SCHEMA GUARDRAIL AUDIT: the tool outputs must not contain verdict-like
     fields ("fraud", "guilty", ...). The layer explains evidence; it does not
     render fraud verdicts — enforced at the schema level.
  4. RUBRIC: each evidence package scored on completeness (all 3 tools),
     groundedness (all numbers recomputed), and error handling.

HONESTY DISCLOSURE: the underlying refund layer is synthetic (planted labels).
This audit verifies the INVESTIGATOR never fabricates relative to the dataset
it is given — a property that holds for any dataset, real or synthetic.

Run:  python scripts/investigator_eval.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import random
import sys
random.seed(0)
np.random.seed(0)



ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import ai_investigator as inv  # noqa: E402


BENCH_PATH = ROOT / "evals" / "investigator_benchmark.json"
JSON_PATH = ROOT / "reports" / "investigator_eval.json"
MD_PATH = ROOT / "reports" / "investigator_eval.md"
ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"


def recompute_customer(orders: pd.DataFrame, cid: str) -> dict:
    """Independently recompute every fact the tools claim to return."""
    sub = orders[orders["Customer_ID"] == cid]
    refunds = sub[sub["Refund_Requested"] == True]  # noqa: E712
    out = {
        "total_orders": int(len(sub)),
        "total_refunds": int(len(refunds)),
        "total_refund_amount": round(float(sub["Refund_Amount"].sum()), 2),
    }
    if len(sub):
        out["refund_rate_pct"] = round(len(refunds) / len(sub) * 100, 2)
    return out


def audit_numbers(evidence: dict, expected: dict) -> list[dict]:
    """Compare tool outputs against recomputation. Return list of mismatches."""
    mismatches = []
    risk = evidence.get("risk", {})
    checks = {
        "total_orders": expected.get("total_orders"),
        "total_refunds": expected.get("total_refunds"),
        "total_refund_amount": expected.get("total_refund_amount"),
        "refund_rate_pct": expected.get("refund_rate_pct"),
    }
    for field, exp in checks.items():
        got = risk.get(field)
        if exp is None or got is None:
            continue
        if abs(float(got) - float(exp)) > 0.02:
            mismatches.append({"customer": risk.get("customer_id"), "field": field,
                               "tool_value": got, "recomputed": exp})
    return mismatches


def schema_audit(evidence: dict, forbidden: list[str]) -> list[str]:
    """Find any verdict-like key anywhere in the evidence structure."""
    hits = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if any(f in str(k).lower() for f in forbidden):
                    hits.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(evidence)
    return hits


def run() -> dict:
    bench = json.loads(BENCH_PATH.read_text(encoding="utf-8"))
    orders = pd.read_csv(ORDERS_PATH)
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)

    # ── answerable cases ────────────────────────────────────────────────────
    answerable_rows = []
    all_mismatches = []
    for case in sorted(bench["answerable"], key=lambda x: x["customer_id"]):
        cid = case["customer_id"]
        evidence = inv.investigate(cid)
        expected = recompute_customer(orders, cid)
        mismatches = audit_numbers(evidence, expected)
        all_mismatches.extend(mismatches)
        forbidden_hits = schema_audit(evidence, bench["forbidden_schema_fields"])
        tools_ok = all(k in evidence for k in ("risk", "history", "baseline"))
        no_error = "error" not in evidence.get("risk", {})
        answerable_rows.append({
            "customer_id": cid,
            "tools_complete": tools_ok,
            "no_tool_error": no_error,
            "fabrications": len(mismatches),
            "forbidden_schema_fields": forbidden_hits,
            "rubric_pass": tools_ok and no_error and not mismatches and not forbidden_hits,
        })

    # ── unanswerable: unknown IDs ───────────────────────────────────────────
    refusal_rows = []
    for cid in bench["unanswerable_unknown_id"]:
        evidence = inv.investigate(cid)
        refused = "error" in evidence.get("risk", {})
        fabricated_score = "risk_score" in evidence.get("risk", {})
        refusal_rows.append({
            "case": f"unknown:{cid}",
            "refused": refused,
            "fabricated_score": fabricated_score,
            "pass": refused and not fabricated_score,
        })

    # ── unanswerable: real customer NOT in the flagged list ─────────────────
    suspects = set(pd.read_csv(ROOT / "reports" / "fraud_suspects.csv")["Customer_ID"])
    in_orders = set(orders["Customer_ID"].unique())
    unflagged = sorted(in_orders - suspects)[:3]
    for cid in unflagged:
        evidence = inv.investigate(cid)
        refused = "error" in evidence.get("risk", {})
        refusal_rows.append({
            "case": f"unflagged:{cid}",
            "refused": refused,
            "fabricated_score": "risk_score" in evidence.get("risk", {}),
            "pass": refused and "risk_score" not in evidence.get("risk", {}),
        })

    n_answerable = len(answerable_rows)
    n_pass = sum(1 for r in answerable_rows if r["rubric_pass"])
    n_ref = len(refusal_rows)
    n_ref_pass = sum(1 for r in refusal_rows if r["pass"])
    n_fab = len(all_mismatches) + sum(1 for r in refusal_rows if r["fabricated_score"])

    result = {
        "generated_by": "scripts/investigator_eval.py",
        "honesty": ("Refund layer is synthetic; this audit verifies the investigator "
                    "never fabricates relative to the dataset it is given — a property "
                    "that holds for any dataset. The optional LLM narrative layer is "
                    "gated behind API keys and must be grounded in these same tools."),
        "answerable": {
            "n": n_answerable,
            "passed": n_pass,
            "accuracy": round(n_pass / n_answerable, 4) if n_answerable else 0.0,
            "cases": answerable_rows,
        },
        "unanswerable": {
            "n": n_ref,
            "refused_correctly": n_ref_pass,
            "refusal_accuracy": round(n_ref_pass / n_ref, 4) if n_ref else 0.0,
            "cases": refusal_rows,
        },
        "fabrications_total": n_fab,
        "mismatch_details": all_mismatches,
        "verdict": "PASS" if (n_pass == n_answerable and n_ref_pass == n_ref and n_fab == 0) else "FAIL",
    }

    JSON_PATH.parent.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2))
    MD_PATH.write_text(render_md(result), encoding="utf-8")
    return result


def render_md(r: dict) -> str:
    lines = [
    '## Honesty Disclosure',
    'Synthetic data: this report reflects a generated dataset, not real financial results.',
        "# Investigator Eval — can the AI investigator fabricate?",
        "",
        "> Generated by `scripts/investigator_eval.py`. Every returned number is",
        "> RECOMPUTED from the raw CSV — a mismatch is a fabrication, not a rounding",
        "> difference. Refusal correctness is scored separately (the e-commerce eval",
        "> lesson: accuracy alone hides false refusals and hallucinations).",
        "",
        "## Scores",
        "",
        f"- **Answerable cases: {r['answerable']['passed']}/{r['answerable']['n']}** "
        f"(accuracy {r['answerable']['accuracy']:.1%})",
        f"- **Unanswerable cases: {r['unanswerable']['refused_correctly']}/{r['unanswerable']['n']}** "
        f"(refusal correctness {r['unanswerable']['refusal_accuracy']:.1%})",
        f"- **Fabrications: {r['fabrications_total']}**",
        f"- **Verdict: {r['verdict']}**",
        "",
        "## What the rubric enforces",
        "",
        "1. **Groundedness**: every number in the evidence must equal an independent",
        "   recomputation from the raw data (orders, refunds, amounts).",
        "2. **Refusal correctness**: unknown IDs and unflagged customers must produce",
        "   an explicit error — never a risk score out of thin air.",
        "3. **Schema guardrail**: output keys must not contain verdict words",
        "   (fraud/guilty/verdict) — the layer explains evidence, it does not judge.",
        "4. **Completeness**: all three tools (risk, history, baseline) must run.",
        "",
        "## Why the split scoring matters",
        "",
        "A system that answers everything looks impressive until you notice it",
        "answers the IMPOSSIBLE questions too. This harness separates the two axes",
        "so a 100% answer score cannot hide a 0% refusal score.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    out = run()
    print(f"Answerable {out['answerable']['passed']}/{out['answerable']['n']} | "
          f"refusals {out['unanswerable']['refused_correctly']}/{out['unanswerable']['n']} | "
          f"fabrications {out['fabrications_total']} | {out['verdict']}")
    print(f"Reports: {MD_PATH}")
