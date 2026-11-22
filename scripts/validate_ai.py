"""Validate the AI investigation copilot on 10 random flagged customers + edge cases."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import os, random, json
# Load key from env or local secrets file (never hardcode)
key = os.environ.get("GOOGLE_API_KEY", "")
if not key:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    sp = __import__("pathlib").Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    if sp.exists():
        with open(sp, "rb") as f:
            key = tomllib.load(f).get("GOOGLE_API_KEY", "")
if key:
    os.environ["GOOGLE_API_KEY"] = key
else:
    print("WARNING: GOOGLE_API_KEY not set; AI narration will be skipped (deterministic evidence only).")

import pandas as pd
from dashboard.ai_investigator import investigate_with_llm

sus = pd.read_csv("reports/fraud_suspects.csv")
random.seed(42)
sample = sus.sample(10, random_state=42)["Customer_ID"].tolist()

results = []
for cid in sample:
    row = sus[sus["Customer_ID"] == cid].iloc[0]
    r = investigate_with_llm(cid)
    ev = r.get("evidence", {})
    risk = ev.get("risk", {})
    hist = ev.get("history", {})
    base = ev.get("baseline", {})

    checks = []
    # 1. ok
    checks.append(("ok", r.get("ok") is True))
    # 2. evidence risk score matches CSV
    checks.append(("risk_score", abs(risk.get("risk_score", -1) - float(row["Fraud_Risk_Score"])) < 1e-6))
    # 3. refund rate matches
    checks.append(("refund_rate", abs(risk.get("refund_rate_pct", -1) - float(row["Refund_Rate"])) < 1e-6))
    # 4. total refunds matches
    checks.append(("total_refunds", risk.get("total_refunds") == int(row["Total_Refunds"])))
    # 5. total orders matches
    checks.append(("total_orders", risk.get("total_orders") == int(row["Total_Orders"])))
    # 6. exposure matches
    checks.append(("exposure", abs(risk.get("total_refund_amount", -1) - float(row["Total_Refund_Amount"])) < 1e-6))
    # 7. history refund count matches
    checks.append(("hist_count", hist.get("refund_count") == int(row["Total_Refunds"])))
    # 8. history exposure matches
    checks.append(("hist_exposure", abs(hist.get("total_refund_amount", -1) - float(row["Total_Refund_Amount"])) < 1e-6))
    # 9. explanation present and non-trivial
    expl = r.get("explanation") or ""
    checks.append(("explanation_present", len(expl) > 80))
    # 10. explanation mentions the risk score (grounded) — loose check
    checks.append(("explanation_mentions_score", str(int(round(risk["risk_score"]))) in expl or f"{risk['risk_score']:.2f}" in expl))
    # 11. volume band present
    checks.append(("volume_band", base.get("volume_band") is not None))

    passed = all(v for _, v in checks)
    results.append({"cid": cid, "passed": passed, "checks": checks, "has_expl": bool(expl), "expl_len": len(expl)})
    print(f"{cid}: {'PASS' if passed else 'FAIL'}  expl_len={len(expl)}")
    for name, v in checks:
        if not v:
            print(f"     FAIL: {name}")

# Edge cases
print("\n--- Edge cases ---")
# Invalid customer
r = investigate_with_llm("CUST99999")
print("invalid id -> ok:", r.get("ok"), "| error:", r.get("error", "")[:60])
# Non-flagged customer (pick one not in suspects)
allcust = pd.read_csv("data/processed/zomato_with_refunds.csv")["Customer_ID"].unique()
flagged = set(sus["Customer_ID"])
nonflagged = [c for c in allcust if c not in flagged][0]
r2 = investigate_with_llm(nonflagged)
print(f"non-flagged {nonflagged} -> ok:", r2.get("ok"), "| error:", (r2.get("error") or "")[:60])

# Summary
n_pass = sum(1 for r in results if r["passed"])
print(f"\n=== {n_pass}/{len(results)} random customers passed all checks ===")
print("All explanations present:", all(r["has_expl"] for r in results))
# Save report
with open("reports/ai_validation_report.json", "w") as f:
    json.dump({"sample": sample, "results": results, "n_pass": n_pass}, f, indent=2, default=str)
print("Saved reports/ai_validation_report.json")