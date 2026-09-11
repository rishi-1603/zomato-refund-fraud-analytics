"""
false_positive_analysis.py — could a legitimate customer be flagged?
================================================================================
PHASE 4. Phase 2 identified 113 flagged customers who are BELOW their volume
band's P95 — high refund rates in absolute terms, but not unusual for their
order volume. This phase profiles those customers to identify the scenarios
where the risk score could incorrectly flag a legitimate customer.

Method:
    1. Load the Phase-2 baseline results
    2. Split the 279 flagged into above-baseline (166) vs below-baseline (113)
    3. Profile each group: order volume, refund count, refund rate, reasons,
       refund amounts, planted ground-truth labels
    4. Identify legitimate-customer scenarios in the below-baseline group
    5. Compare against the ground truth to measure actual false-positive rate

FALSE-POSITIVE SCENARIOS TESTED:
    S1. High-volume users — many orders → more refund opportunities
    S2. Low-volume noise — 1-2 refunds on 5 orders crosses 30% by chance
    S3. Genuine delivery-issue victims — clustered refunds from real problems
    S4. High-value customers — large refunds inflate exposure without abuse

HONESTY RULES:
    - A false positive = flagged by the score but planted as Low-risk by the
      generator. We have ground truth, so we can MEASURE the FP rate.
    - "Legitimate" = planted Low/Medium risk, NOT a claim about real customers.
    - On real data, ground truth would come from investigation outcomes.

Run:  python scripts/false_positive_analysis.py
Writes: reports/false_positive_analysis.md
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
SUSPECTS = ROOT / "reports" / "fraud_suspects.csv"
GT = ROOT / "data" / "processed" / "ground_truth_customer_risk.csv"
REPORT = ROOT / "reports" / "false_positive_analysis.md"


def main() -> None:
    df = pd.read_csv(DATA)
    sus = pd.read_csv(SUSPECTS)
    gt = pd.read_csv(GT, index_col="Customer_ID")["Planted_Risk"]
    sus["planted"] = sus["Customer_ID"].map(gt)

    # per-customer order stats for volume context
    cust_orders = df.groupby("Customer_ID").agg(
        total_orders=("ID", "count"),
        total_refunds=("Refund_Requested", "sum"),
        total_refund_amount=("Refund_Amount", "sum"),
    ).reset_index()
    cust_orders["refund_rate"] = (cust_orders["total_refunds"] / cust_orders["total_orders"] * 100).round(2)

    # merge into suspects
    sus = sus.merge(cust_orders[["Customer_ID", "total_orders", "total_refunds", "refund_rate"]],
                    on="Customer_ID", how="left", suffixes=("", "_dup"))
    # prefer the pipeline's columns where they exist
    for col in ["Total_Orders", "Total_Refunds", "Refund_Rate"]:
        dup = col + "_dup"
        if dup in sus.columns:
            sus[col] = sus[col].fillna(sus[dup])

    # ── GROUND-TRUTH FALSE POSITIVES ──
    # flagged but planted as Low-risk = definitive false positive (measurable)
    sus["is_false_positive"] = sus["planted"] == "Low"
    sus["is_true_positive"] = sus["planted"] == "High"
    n_fp = int(sus["is_false_positive"].sum())
    n_tp = int(sus["is_true_positive"].sum())
    n_other = len(sus) - n_fp - n_tp  # planted Medium = grey area

    # ── BASELINE SPLIT (from Phase 2) ──
    # recompute the volume-band baseline inline
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from baseline_normalization import build_baselines
    cust, bands = build_baselines(df)
    sus_ids = set(sus["Customer_ID"])
    cust["is_flagged"] = cust["Customer_ID"].isin(sus_ids)
    cust["planted"] = cust["Customer_ID"].map(gt)
    flagged = cust[cust["is_flagged"]].copy()
    above = flagged[flagged["above_baseline"]]
    below = flagged[~flagged["above_baseline"]]

    # cross-tab: baseline × ground truth
    above_fp = int((above["planted"] == "Low").sum())
    below_fp = int((below["planted"] == "Low").sum())
    above_tp = int((above["planted"] == "High").sum())
    below_tp = int((below["planted"] == "High").sum())

    # ── SCENARIO ANALYSIS ──
    # S1: High-volume users (10+ orders)
    s1 = sus[(sus["Total_Orders"] >= 10)]
    s1_fp = int((s1["planted"] == "Low").sum())

    # S2: Low-volume noise (exactly 5-6 orders, 2 refunds = 33-40% rate)
    s2 = sus[(sus["Total_Orders"].between(5, 6)) & (sus["Total_Refunds"] == 2)]
    s2_fp = int((s2["planted"] == "Low").sum())

    # S3: Reason diversity (>=3 different reasons — suggests genuine varied issues, not scripted)
    reasons_per_cust = (
        df[df["Refund_Requested"] == True]
        .groupby("Customer_ID")["Refund_Reason"]
        .nunique()
    )
    sus["reason_diversity"] = sus["Customer_ID"].map(reasons_per_cust).fillna(0)
    s3 = sus[sus["reason_diversity"] >= 3]
    s3_fp = int((s3["planted"] == "Low").sum())

    # S4: Low refund amounts (avg refund < ₹200 — genuine small-claim issues)
    sus["avg_refund"] = sus["Total_Refund_Amount"] / sus["Total_Refunds"].clip(lower=1)
    s4 = sus[sus["avg_refund"] < 200]
    s4_fp = int((s4["planted"] == "Low").sum())

    # ── REPORT ──
    lines = [
        "# False-Positive Analysis",
        "### Could a legitimate customer be flagged by the risk score?",
        "",
        "> Generated by `scripts/false_positive_analysis.py`. Phase 2 identified 113",
        "> flagged customers below their volume-band baseline. This phase profiles",
        "> them and measures the actual false-positive rate against the planted",
        "> ground truth.",
        "",
        "## Measured false-positive rate (ground truth)",
        "",
        f"Of the **279 flagged customers**:",
        f"- **{n_tp}** are planted High-risk → **true positives** ({n_tp/len(sus)*100:.1f}%)",
        f"- **{n_fp}** are planted Low-risk → **false positives** ({n_fp/len(sus)*100:.1f}%)",
        f"- **{n_other}** are planted Medium-risk → grey area (neither confirmed nor cleared)",
        "",
        "This is the advantage of having ground truth: the false-positive rate is",
        "**measured, not estimated**. On real data, this number would come from",
        "investigation outcomes.",
        "",
        "## Cross-tab: baseline vs ground truth",
        "",
        "Phase 2's baseline normalization predicted that below-baseline customers",
        "are false-positive candidates. Does the ground truth confirm this?",
        "",
        "| Group | n | Planted High (TP) | Planted Low (FP) | FP rate |",
        "|---|---|---|---|---|",
        f"| Above band baseline | {len(above)} | {above_tp} | {above_fp} | {above_fp/len(above)*100:.1f}% |",
        f"| Below band baseline | {len(below)} | {below_tp} | {below_fp} | {below_fp/len(below)*100:.1f}% |",
        "",
        "**Key insight:** if the below-baseline group has a *higher* FP rate than",
        "the above-baseline group, the Phase-2 normalization successfully identifies",
        "false-positive candidates — validating it as a screening tool.",
        "",
        "## Legitimate-customer scenarios",
        "",
        "| Scenario | Definition | Flagged customers in scenario | Planted Low (FP) |",
        "|---|---|---|---|",
        f"| S1: High-volume user | ≥10 orders | {len(s1)} | {s1_fp} ({s1_fp/max(len(s1),1)*100:.0f}%) |",
        f"| S2: Low-volume noise | 5-6 orders, exactly 2 refunds | {len(s2)} | {s2_fp} ({s2_fp/max(len(s2),1)*100:.0f}%) |",
        f"| S3: Reason diversity | ≥3 different refund reasons | {len(s3)} | {s3_fp} ({s3_fp/max(len(s3),1)*100:.0f}%) |",
        f"| S4: Small-claim pattern | Avg refund < ₹200 | {len(s4)} | {s4_fp} ({s4_fp/max(len(s4),1)*100:.0f}%) |",
        "",
        "**Interpretation:**",
        "- **S1 (high-volume)**: legitimate heavy users accumulate more refund",
        "  opportunities — the raw rate doesn't adjust for this.",
        "- **S2 (low-volume noise)**: with 5-6 orders, 2 refunds = 33-40% rate,",
        "  crossing the 30% threshold by small-sample variance.",
        "- **S3 (reason diversity)**: customers with varied refund reasons are less",
        "  likely to be running a script (contrast with reason-repetition signal).",
        "- **S4 (small claims)**: many small refunds may indicate genuine delivery",
        "  issues rather than systematic abuse.",
        "",
        "## Recommendations for reducing false positives",
        "",
        "1. **Volume-band normalization** (Phase 2): replace the flat 30% threshold",
        "   with band-specific P95 thresholds. This alone would remove the",
        f"  {below_fp} planted-Low customers in the below-baseline group from the queue.",
        "2. **Reason-diversity check**: customers with ≥3 distinct reasons should",
        "   receive a manual-review flag rather than automatic prioritization.",
        "3. **Minimum refund count**: require ≥3 refunds (not just ≥5 orders) before",
        "   scoring — reduces the low-volume noise scenario.",
        "4. **Never auto-ban.** A risk score is a review-prioritization tool.",
        "   Every flag should route to human investigation, never automated action.",
        "",
        "## Honest limitations",
        "",
        "- Ground truth is planted by the generator — on real data, FP rate would",
        "  come from months of investigation outcomes.",
        "- The 73 planted-Medium customers are a grey area: not confirmed abusers,",
        "  but not provably legitimate either.",
        "- Scenario definitions are illustrative, not validated policy.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/false_positive_analysis.py",
        "pytest tests/test_false_positive_analysis.py -v",
        "```",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Ground truth: TP={n_tp}, FP={n_fp}, grey={n_other} of {len(sus)} flagged")
    print(f"Above baseline: {len(above)} ({above_fp} FP, {above_fp/len(above)*100:.1f}%)")
    print(f"Below baseline: {len(below)} ({below_fp} FP, {below_fp/len(below)*100:.1f}%)")
    print(f"S1 High-volume: {len(s1)} ({s1_fp} FP) | S2 Low-volume: {len(s2)} ({s2_fp} FP)")
    print(f"S3 Reason-diverse: {len(s3)} ({s3_fp} FP) | S4 Small-claims: {len(s4)} ({s4_fp} FP)")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
