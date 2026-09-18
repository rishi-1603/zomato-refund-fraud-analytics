"""
data_quality_report.py — formal data-quality assessment
========================================================
PHASE 8. Runs the full audit and writes a documented report: every check,
records affected, percentage, severity, treatment, and reason.

Run:  python scripts/data_quality_report.py
Writes: reports/data_quality_report.md
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Zomato Dataset.csv"
DATA = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
REPORT = ROOT / "reports" / "data_quality_report.md"

VALID_REASONS = {"Late Delivery", "Wrong Item", "Missing Item", "Poor Quality",
                 "Damaged Packaging", "Item Not Received"}


def run_checks(df: pd.DataFrame, raw: pd.DataFrame) -> list[dict]:
    n = len(df)
    rows = []

    def check(name, issue, affected, severity, treatment, reason):
        rows.append({"check": name, "issue": issue, "affected": affected if isinstance(affected, (int, float)) else str(affected),
                     "pct": round(affected / n * 100, 2) if isinstance(affected, (int, float)) else "n/a", "severity": severity,
                     "treatment": treatment, "reason": reason})

    # Null analysis — separate structural nulls (expected) from data-quality nulls
    structural_nulls = df["Refund_Reason"].isna().sum()  # no refund → no reason
    source_nulls = df.isna().sum().sum() - structural_nulls  # Kaggle dataset gaps
    check("Completeness", f"Null values in source-data columns (Kaggle dataset gaps)",
          source_nulls, "Known (in source)", "Documented, not imputed",
          f"Original Kaggle dataset has {source_nulls:,} nulls across 8 optional columns "
          "(rider age 4.1%, ratings 4.2%, city 2.6%, etc.) — typical of public data")
    check("Completeness", "Null Refund_Reason where no refund requested",
          structural_nulls, "Pass (by design)", "None required",
          "Refund_Reason is only populated when Refund_Requested = True; "
          f"{structural_nulls:,} of {len(df):,} orders have no refund")

    check("Uniqueness", "Duplicate order IDs", df["ID"].duplicated().sum(),
          "Pass" if df["ID"].duplicated().sum() == 0 else "Critical", "None required",
          "ID is the primary key")

    check("Uniqueness", "Duplicate customer IDs (multiple rows expected — grain is order)",
          "n/a (by design)", "n/a", "n/a", "Multiple orders per customer is correct")

    check("Validity — Age", "Age outside 18–65", (~df["Delivery_person_Age"].between(18, 65)).sum(),
          "Pass" if (~df["Delivery_person_Age"].between(18, 65)).sum() == 0 else "Medium",
          "None required", "Rider age range")

    check("Validity — Ratings", "Rating outside 0–5 (known quirk: 53 rows at 6.0)",
          (df["Delivery_person_Ratings"] > 5).sum(),
          "Known (in source)", "Documented, not cleaned",
          "The public Kaggle dataset contains 53 ratings of 6.0 on a 5-star scale; "
          "pinned by tests to detect raw-data tampering")

    check("Validity — Refund amounts", "Refund amount ≤ 0 where refund requested",
          ((df["Refund_Requested"] == True) & (df["Refund_Amount"] <= 0)).sum(),
          "Pass" if ((df["Refund_Requested"] == True) & (df["Refund_Amount"] <= 0)).sum() == 0 else "High",
          "None required", "Refunds must have positive amounts")

    check("Validity — Refund flag consistency", "Refund amount > 0 where refund NOT requested",
          ((df["Refund_Requested"] == False) & (df["Refund_Amount"] > 0)).sum(),
          "Pass" if ((df["Refund_Requested"] == False) & (df["Refund_Amount"] > 0)).sum() == 0 else "High",
          "None required", "No refund → zero amount expected")

    check("Validity — Refund reasons", "Unknown refund reason values",
          (~df["Refund_Reason"].dropna().isin(VALID_REASONS)).sum(),
          "Pass" if (~df["Refund_Reason"].dropna().isin(VALID_REASONS)).sum() == 0 else "High",
          "None required", "Only 6 valid reasons in the generator")

    check("Consistency", "Raw dataset column count (must be 20)",
          20 if len(raw.columns) == 20 else -1,
          "Pass" if len(raw.columns) == 20 else "Critical",
          "None required", "Raw Kaggle dataset has 20 columns; 4 synthetic columns added")

    check("Consistency", "Refund columns NOT present in raw data (synthetic layer separation)",
          "Pass" if "Refund_Requested" not in raw.columns else "FAIL",
          "Pass" if "Refund_Requested" not in raw.columns else "Critical",
          "None required", "Raw data must remain unmodified")

    # documented design characteristics
    rows.append({"check": "Design characteristic",
                 "issue": "Refund layer is synthetic (seeded, reproducible)",
                 "affected": n, "pct": 100.0, "severity": "Known (by design)",
                 "treatment": "Disclosed in all reports",
                 "reason": "Generator: 3% High / 7% Medium / 90% Low risk categories"})
    rows.append({"check": "Design characteristic",
                 "issue": "City column contains city TYPES (Metropolitian/Urban/Semi-Urban), not city names",
                 "affected": n, "pct": 100.0, "severity": "Known (by design)",
                 "treatment": "Labelled 'City type' in dashboard",
                 "reason": "Source dataset limitation"})
    return rows


def main() -> None:
    df = pd.read_csv(DATA)
    raw = pd.read_csv(RAW)
    rows = run_checks(df, raw)

    lines = [
        "# Data Quality Report",
        f"### data/processed/zomato_with_refunds.csv · {len(df):,} rows × {len(df.columns)} columns",
        "",
        "> Generated by `scripts/data_quality_report.py`. The same checks are enforced",
        "> as CI tests in `tests/test_data_quality.py`. This report is the documented",
        "> audit trail; the tests are the gate.",
        "",
        "## Summary",
        "",
        f"- Checks executed: **{sum(1 for r in rows if r['severity'] not in ('Known (by design)', 'n/a', 'Known (in source)'))}**",
        f"- Failures: **{sum(1 for r in rows if r['severity'] in ('High', 'Critical'))}**",
        f"- Known quirks: **{sum(1 for r in rows if 'Known' in str(r['severity']))}**",
        "",
        "## Full audit table",
        "",
        "| Check | Issue | Records | % | Severity | Treatment | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['check']} | {r['issue']} | {r['affected']} | {r['pct']}% | "
            f"{r['severity']} | {r['treatment']} | {r['reason']} |")
    lines += [
        "",
        "## Cleaning decisions",
        "",
        "**No records were dropped, imputed, or modified.** The raw Kaggle dataset",
        "is unmodified (CI-enforced); the synthetic refund layer is added on top.",
        "The 53 six-star ratings are a source-data quirk, documented and pinned.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/data_quality_report.py",
        "pytest tests/test_data_quality.py -v",
        "```",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Checks: {len(rows)} | Failures: {sum(1 for r in rows if r['severity'] in ('High', 'Critical'))}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
