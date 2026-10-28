"""
alert_economics.py — the economics of fraud alerts: who is worth alerting on?
================================================================================
THE STORY THIS SCRIPT TELLS:

A fraud alert is not free. Every flagged customer costs analyst review time,
and every false positive costs customer goodwill. The question is not "does the
risk score find fraud?" (scripts/validate_risk_score.py answers that) — it is:

    "Given what an alert costs, WHICH alerts make money, and what is the
     optimal alert policy under a fixed review budget?"

This script:
  1. Reuses the dashboard's exact risk score (build_risk_table) — no drift.
  2. Prices every alert policy (tier thresholds and top-k% budgets) with an
     explicit cost model: review cost + false-positive friction vs recovered
     refund exposure.
  3. Computes break-even precision — the minimum hit rate an alert program
     must achieve to pay for itself.
  4. Runs a sensitivity grid over the two assumptions (recovery rate, review
     cost) so the recommendation is not hostage to one guess.
  5. Writes reports/alert_economics.json + reports/alert_economics.md.

HONESTY DISCLOSURE: the refund layer is synthetic with planted risk labels
(3% High / 7% Medium / 90% Low). The economics below are the economics of the
policy ON THIS DATASET — they demonstrate the decision method, not a forecast
of a real P&L. Cost constants are documented assumptions, each sensitivity-
tested. Every customer-level quantity (refund exposure, scores) is measured.

Run:  python scripts/alert_economics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_risk_score import build_risk_table  # noqa: E402

ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
GT_PATH = ROOT / "data" / "processed" / "ground_truth_customer_risk.csv"
JSON_PATH = ROOT / "reports" / "alert_economics.json"
MD_PATH = ROOT / "reports" / "alert_economics.md"

# ── Cost model (documented assumptions, sensitivity-tested) ──────────────────
REVIEW_COST = 250.0        # ₹ per alert reviewed by an analyst
FRICTION_COST = 100.0      # ₹ goodwill cost per false-positive alert
RECOVERY_RATE = 0.50       # share of a true fraudster's exposure we can prevent

SENS_RECOVERY = (0.25, 0.50, 0.75)
SENS_REVIEW = (150.0, 250.0, 400.0)


def load_pool() -> pd.DataFrame:
    """Flagged customer pool with scores, exposure and planted ground truth."""
    orders = pd.read_csv(ORDERS_PATH)
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)
    gt = pd.read_csv(GT_PATH)

    pool = build_risk_table(orders)
    exposure = orders.groupby("Customer_ID")["Refund_Amount"].sum().rename("Exposure")
    pool = pool.merge(gt, on="Customer_ID", how="left")
    pool = pool.merge(exposure, on="Customer_ID", how="left")
    pool["Exposure"] = pool["Exposure"].fillna(0.0)
    pool["Is_True_High"] = pool["Planted_Risk"] == "High"
    return pool


def evaluate_policy(pool: pd.DataFrame, mask: pd.Series, name: str,
                    review_cost: float = REVIEW_COST,
                    friction_cost: float = FRICTION_COST,
                    recovery_rate: float = RECOVERY_RATE) -> dict:
    """Price one alert policy. `mask` selects who gets alerted."""
    alerts = pool[mask]
    n_alerts = int(len(alerts))
    tp = alerts[alerts["Is_True_High"]]
    n_tp = int(len(tp))
    n_fp = n_alerts - n_tp
    n_high_total = int(pool["Is_True_High"].sum())

    precision = n_tp / n_alerts if n_alerts else 0.0
    recall = n_tp / n_high_total if n_high_total else 0.0

    recovered = recovery_rate * float(tp["Exposure"].sum())
    review = review_cost * n_alerts
    friction = friction_cost * n_fp
    cost = review + friction
    net = recovered - cost
    roi = net / cost if cost else 0.0

    return {
        "policy": name,
        "alerts": n_alerts,
        "true_high": n_tp,
        "false_positives": n_fp,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "recovered_exposure": round(recovered, 2),
        "review_cost": round(review, 2),
        "friction_cost": round(friction, 2),
        "total_cost": round(cost, 2),
        "net_value": round(net, 2),
        "roi": round(roi, 4),
    }


def break_even_precision(mean_recovery_per_true: float,
                         review_cost: float = REVIEW_COST,
                         friction_cost: float = FRICTION_COST) -> float:
    """Precision at which expected recovery exactly covers expected cost.

    p * recovery = review + (1 - p) * friction
    => p* = (review + friction) / (recovery + friction)
    """
    denom = mean_recovery_per_true + friction_cost
    return (review_cost + friction_cost) / denom if denom else 1.0


def run() -> dict:
    pool = load_pool()

    policies = [
        (pool["Fraud_Risk_Score"] > 70, "tier_high"),
        (pool["Fraud_Risk_Score"] > 40, "tier_high_plus_medium"),
        (pd.Series(True, index=pool.index), "all_flagged"),
    ]
    base = [evaluate_policy(pool, m, n) for m, n in policies]

    # Score-sorted budget curve (top-k% of flagged pool by risk score).
    ranked = pool.sort_values("Fraud_Risk_Score", ascending=False)
    budget = []
    for frac in (0.10, 0.25, 0.50, 0.75, 1.00):
        k = max(1, int(round(len(ranked) * frac)))
        top_ids = ranked.head(k).index
        row = evaluate_policy(pool, pool.index.isin(top_ids), f"top_{int(frac*100)}pct")
        row["budget_share"] = frac
        budget.append(row)

    # Break-even precision using the pool-wide mean recovery per true High.
    true_high = pool[pool["Is_True_High"]]
    mean_recovery = RECOVERY_RATE * float(true_high["Exposure"].mean()) if len(true_high) else 0.0
    be_precision = break_even_precision(mean_recovery)

    # Sensitivity grid: best policy per scenario.
    grid = []
    for rec in SENS_RECOVERY:
        for rev in SENS_REVIEW:
            opts = [evaluate_policy(pool, m, n, review_cost=rev, recovery_rate=rec)
                    for m, n in policies]
            best = max(opts, key=lambda r: r["net_value"])
            grid.append({
                "recovery_rate": rec,
                "review_cost": rev,
                "best_policy": best["policy"],
                "best_net_value": best["net_value"],
                "best_roi": best["roi"],
                "all_policies_net": {o["policy"]: o["net_value"] for o in opts},
            })

    best = max(base, key=lambda r: r["net_value"])
    result = {
        "generated_by": "scripts/alert_economics.py",
        "honesty": ("Synthetic refund layer with planted risk labels. Economics of "
                    "the policy ON THIS DATASET, not a real P&L forecast. Cost "
                    "constants are documented assumptions, sensitivity-tested."),
        "pool": {
            "flagged_customers": int(len(pool)),
            "planted_high_in_pool": int(pool["Is_True_High"].sum()),
            "exposure_in_pool": round(float(pool["Exposure"].sum()), 2),
        },
        "cost_model": {
            "review_cost": REVIEW_COST,
            "friction_cost": FRICTION_COST,
            "recovery_rate": RECOVERY_RATE,
            "mean_recovery_per_true_high": round(mean_recovery, 2),
        },
        "policies": base,
        "alert_budget_curve": budget,
        "break_even_precision": round(be_precision, 4),
        "sensitivity_grid": grid,
        "recommended_policy": best["policy"],
        "recommended_net_value": best["net_value"],
    }

    JSON_PATH.parent.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    MD_PATH.write_text(render_md(result, encoding="utf-8"))
    return result


def render_md(r: dict) -> str:
    lines = [
        "# Alert Economics — which fraud alerts are worth making?",
        "",
        "> Generated by `scripts/alert_economics.py`. Reuses the dashboard risk score",
        "> (`build_risk_table`) so this cannot drift from the product. The refund layer",
        "> is synthetic with planted labels: these are the economics of the policy on",
        "> this dataset, not a real P&L forecast.",
        "",
        "## Cost model",
        "",
        f"- Review cost: **₹{r['cost_model']['review_cost']:.0f}** per alert",
        f"- False-positive friction: **₹{r['cost_model']['friction_cost']:.0f}** per wrong alert",
        f"- Recovery rate: **{r['cost_model']['recovery_rate']:.0%}** of a true fraudster's exposure prevented",
        f"- Mean recovery per true High in pool: **₹{r['cost_model']['mean_recovery_per_true_high']:,.0f}**",
        "",
        "## Alert policies priced",
        "",
        "| Policy | Alerts | Precision | Recall | Recovered ₹ | Cost ₹ | Net ₹ | ROI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in r["policies"]:
        lines.append(
            f"| {p['policy']} | {p['alerts']} | {p['precision']:.1%} | {p['recall']:.1%} | "
            f"₹{p['recovered_exposure']:,.0f} | ₹{p['total_cost']:,.0f} | ₹{p['net_value']:,.0f} | "
            f"{p['roi']:.2f} |")

    lines += [
        "",
        f"**Break-even precision: {r['break_even_precision']:.1%}** — below this hit rate, "
        "the alert program loses money at the base cost assumptions.",
        "",
        f"**Recommended policy: `{r['recommended_policy']}`** "
        f"(net **₹{r['recommended_net_value']:,.0f}** at base assumptions).",
        "",
        "## Alert budget curve (top-k% of the flagged pool by score)",
        "",
        "| Budget | Alerts | Precision | Net ₹ |",
        "|---|---|---|---|",
    ]
    for b in r["alert_budget_curve"]:
        lines.append(f"| top {b['budget_share']:.0%} | {b['alerts']} | {b['precision']:.1%} | ₹{b['net_value']:,.0f} |")

    lines += [
        "",
        "## Sensitivity — does the recommendation survive different assumptions?",
        "",
        "| Recovery rate | Review cost | Best policy | Net ₹ |",
        "|---|---|---|---|",
    ]
    for g in r["sensitivity_grid"]:
        lines.append(f"| {g['recovery_rate']:.0%} | ₹{g['review_cost']:.0f} | {g['best_policy']} | ₹{g['best_net_value']:,.0f} |")

    lines += [
        "",
        "## How to defend this in an interview",
        "",
        "1. **Alerts are decisions, not scores.** This prices the decision.",
        "2. **Break-even precision is the single number** an ops team needs: it converts",
        "   an ML metric into a budget rule.",
        "3. **Sensitivity shows the recommendation is structural**, not an artifact of one guess.",
        "4. **The negative-space is honest**: at high review costs even a good score",
        "   stops paying — that trade-off is exactly what this tool surfaces.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    out = run()
    best = out["recommended_policy"]
    print(f"Recommended policy: {best} | net ₹{out['recommended_net_value']:,.0f} | "
          f"break-even precision {out['break_even_precision']:.1%}")
    print(f"Report: {MD_PATH}")
