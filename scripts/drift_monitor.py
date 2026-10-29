"""
drift_monitor.py — is the refund-fraud data still behaving like the data the
score was built on?
================================================================================
THE STORY THIS SCRIPT TELLS:

A risk score is calibrated on a data distribution. If the distribution moves,
the score's economics move with it — the 88% precision of the alert policy
(scripts/alert_economics.py) is only valid while the inputs hold still.

This script is the monitoring console an ops team would run weekly:
  1. Splits the order stream into a REFERENCE window (first 2 weeks) and
     weekly MONITORING windows.
  2. Measures drift feature-by-feature: PSI (population stability index) for
     numeric and categorical inputs, plus the business metric that actually
     matters — the refund rate.
  3. Grades each cell with standard thresholds:
       PSI < 0.10 stable · 0.10–0.25 moderate · > 0.25 significant
  4. Emits a per-week verdict and the earliest week any feature went
     significant — the retrain trigger question.
  5. Writes reports/drift_monitor.json + reports/drift_monitor.md.

HONESTY DISCLOSURE: the order stream is synthetic (seeded generator). Drift
numbers here demonstrate the monitoring method; they are not evidence about a
real production system. Thresholds (0.10 / 0.25) are the industry-standard
PSI conventions, cited in the report as such.

Run:  python scripts/drift_monitor.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import random
random.seed(0)
np.random.seed(0)



ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
JSON_PATH = ROOT / "reports" / "drift_monitor.json"
MD_PATH = ROOT / "reports" / "drift_monitor.md"

NUMERIC_FEATURES = ["Delivery_person_Age", "Delivery_person_Ratings",
                    "Time_taken (min)", "multiple_deliveries"]
CAT_FEATURES = ["Weather_conditions", "Road_traffic_density", "City"]

PSI_STABLE = 0.10
PSI_SIGNIFICANT = 0.25


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population stability index against decile bins cut on the reference."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]
    if len(ref) < 20 or len(cur) < 20:
        return 0.0
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_pct = np.histogram(ref, bins=edges)[0] / max(len(ref), 1)
    cur_pct = np.histogram(cur, bins=edges)[0] / max(len(cur), 1)
    ref_pct = np.clip(ref_pct, 1e-6, None)
    cur_pct = np.clip(cur_pct, 1e-6, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def psi_categorical(reference: pd.Series, current: pd.Series) -> float:
    """PSI over category shares; unseen categories enter as their own bucket."""
    ref = reference.astype(str).where(reference.notna(), "missing")
    cur = current.astype(str).where(current.notna(), "missing")
    cats = sorted(set(ref.unique()) | set(cur.unique()))
    ref_pct = ref.value_counts(normalize=True).reindex(cats, fill_value=0).clip(1e-6)
    cur_pct = cur.value_counts(normalize=True).reindex(cats, fill_value=0).clip(1e-6)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def grade(psi_value: float) -> str:
    if psi_value < PSI_STABLE:
        return "stable"
    if psi_value < PSI_SIGNIFICANT:
        return "moderate"
    return "significant"


def run() -> dict:
    df = pd.read_csv(ORDERS_PATH)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
    df["Week"] = df["Order_Date"].dt.to_period("W-SUN").astype(str)

    weeks = sorted(df["Week"].unique())
    ref_weeks = weeks[:2]
    monitor_weeks = weeks[2:]

    ref = df[df["Week"].isin(ref_weeks)]
    ref_refund_rate = float(ref["Refund_Requested"].mean())

    week_reports = []
    for w in monitor_weeks:
        cur = df[df["Week"] == w]
        cells = {}
        for f in NUMERIC_FEATURES:
            p = psi(ref[f].astype(float).values, cur[f].astype(float).values)
            cells[f] = {"psi": round(p, 4), "grade": grade(p)}
        for f in CAT_FEATURES:
            p = psi_categorical(ref[f], cur[f])
            cells[f] = {"psi": round(p, 4), "grade": grade(p)}

        cur_refund_rate = float(cur["Refund_Requested"].mean())
        worst = max(cells.items(), key=lambda kv: kv[1]["psi"])
        n_sig = sum(1 for c in cells.values() if c["grade"] == "significant")
        n_mod = sum(1 for c in cells.values() if c["grade"] == "moderate")

        week_reports.append({
            "week": w,
            "orders": int(len(cur)),
            "refund_rate": round(cur_refund_rate, 4),
            "refund_rate_delta_pp": round((cur_refund_rate - ref_refund_rate) * 100, 2),
            "features": cells,
            "worst_feature": worst[0],
            "worst_psi": worst[1]["psi"],
            "n_significant": n_sig,
            "n_moderate": n_mod,
            "verdict": "DRIFT" if n_sig else ("WATCH" if n_mod else "STABLE"),
        })

    first_sig = next((r["week"] for r in week_reports if r["n_significant"] > 0), None)
    first_watch = next((r["week"] for r in week_reports if r["verdict"] != "STABLE"), None)

    result = {
        "generated_by": "scripts/drift_monitor.py",
        "honesty": ("Synthetic seeded order stream. Demonstrates the monitoring "
                    "method, not evidence about a real production system. PSI "
                    "thresholds 0.10/0.25 are the standard conventions."),
        "reference_window": {"weeks": ref_weeks, "orders": int(len(ref)),
                             "refund_rate": round(ref_refund_rate, 4)},
        "monitoring_weeks": week_reports,
        "thresholds": {"stable": PSI_STABLE, "significant": PSI_SIGNIFICANT},
        "first_watch_week": first_watch,
        "first_drift_week": first_sig,
        "overall_verdict": ("DRIFT_DETECTED" if first_sig else
                            ("WATCH" if first_watch else "STABLE")),
    }

    JSON_PATH.parent.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    MD_PATH.write_text(render_md(result), encoding="utf-8")
    return result


def render_md(r: dict) -> str:
    ref = r["reference_window"]
    lines = [
    '## Honesty Disclosure',
    'Synthetic data: this report reflects a generated dataset, not real financial results.',
        "# Drift Monitor — is the score still facing the same data?",
        "",
        "> Generated by `scripts/drift_monitor.py`. Reference window: first 2 weeks",
        f"> ({ref['weeks'][0]} -> {ref['weeks'][1]}, {ref['orders']:,} orders, refund rate",
        f"> {ref['refund_rate']:.2%}). PSI conventions: <0.10 stable · 0.10–0.25 moderate · >0.25 significant.",
        "> Synthetic stream — monitoring method demonstration, not production evidence.",
        "",
        "## Weekly verdicts",
        "",
        "| Week | Orders | Refund rate | Δ vs ref | Worst feature | Max PSI | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for w in r["monitoring_weeks"]:
        lines.append(
            f"| {w['week']} | {w['orders']:,} | {w['refund_rate']:.2%} | "
            f"{w['refund_rate_delta_pp']:+.2f} pp | {w['worst_feature']} | {w['worst_psi']:.3f} | "
            f"**{w['verdict']}** |")

    lines += [
        "",
        f"**Overall verdict: `{r['overall_verdict']}`**",
        f"- First week to leave STABLE: **{r['first_watch_week'] or '—'}**",
        f"- First week with significant drift: **{r['first_drift_week'] or 'none'}**",
        "",
        "## Why this belongs next to the alert economics",
        "",
        "- The alert policy's break-even precision (28.2%) assumes the score's inputs",
        "  hold still. This console is the tripwire for that assumption.",
        "- **The retrain rule is explicit**: if any feature PSI > 0.25 for 2 consecutive",
        "  weeks, rebuild the score before trusting its precision again.",
        "- Monitoring the refund RATE (business metric) alongside feature PSI catches",
        "  the drift that matters even when inputs look stable.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    out = run()
    print(f"Overall: {out['overall_verdict']} | first watch week: {out['first_watch_week']} | "
          f"first drift week: {out['first_drift_week']}")
    print(f"Report: {MD_PATH}")
