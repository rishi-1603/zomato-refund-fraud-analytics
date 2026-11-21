"""Render the FoodTrust project report to reports/FoodTrust_Project_Report.pdf.

All figures are taken from reports/ and README.md; nothing is generated at build
time except layout. Run: python scripts/build_report_pdf.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "FoodTrust_Project_Report.pdf"
CHARTS = ROOT / "docs" / "chart_renders"

NAVY = colors.HexColor("#0A0F1E")
ACCENT = colors.HexColor("#3B82F6")
MUTED = colors.HexColor("#5B6779")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5,
                      leading=14, alignment=TA_JUSTIFY, spaceAfter=7)
body_left = ParagraphStyle("body_left", parent=body, alignment=0)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED)
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=13,
                    leading=17, textColor=NAVY, spaceBefore=14, spaceAfter=6)
title = ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=19,
                       leading=23, textColor=NAVY, alignment=0, spaceAfter=4)
subtitle = ParagraphStyle("subtitle", parent=body, fontSize=10.5, leading=14,
                          textColor=MUTED, alignment=0, spaceAfter=14)
caption = ParagraphStyle("caption", parent=small, alignment=1, spaceBefore=3)


def table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#D5DBE6")),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
    ]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                  ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF3FB")),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT)]
    t.setStyle(TableStyle(style))
    return t


def figure(path, width_cm, cap):
    if not path.exists():
        return []
    w, h = ImageReader(str(path)).getSize()
    return [Image(str(path), width=width_cm * cm, height=width_cm * cm * h / w),
            Paragraph(cap, caption), Spacer(1, 8)]


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                            leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="FoodTrust - Refund Risk & Marketplace Intelligence",
                            author="Rishi Dappu")
    s = []
    s += [Paragraph("FoodTrust — Food Delivery Fraud, Trust &amp; Marketplace Risk Intelligence", title),
          Paragraph("A rules-based review-priority system for delivery refunds, with "
                    "volume-band normalisation and capacity-aware policy simulation", subtitle),
          Paragraph("Rishi Dappu, Data Analyst &nbsp;|&nbsp; Zomato case study &nbsp;|&nbsp; "
                    "45,584 orders, 9,895 customers, 11 Feb – 6 Apr 2022", small),
          Spacer(1, 14)]

    s += [Paragraph("Abstract", h1), Paragraph(
        "Refund abuse programmes usually start with a ranking problem and end with a "
        "false-positive problem. This study builds a transparent review-priority score over "
        "45,584 delivery orders, then tests whether the accounts it flags are genuinely "
        "unusual once order volume is taken into account. Two hundred and seventy-nine "
        "accounts clear the eligibility rule and hold 38.8% of historical refund value. "
        "However, 113 of those 279 (40.5%) sit at or below the 95th percentile refund rate "
        "of their own volume band, so volume alone explains their position. Under stated "
        "cost assumptions, reviewing only the High and Medium tiers returns the highest "
        "modelled net value while cutting review volume from 279 to 115 cases. The score is "
        "uncalibrated, the refund layer is synthetic, and a flag is a review priority — "
        "never a finding of fraud.", body)]

    s += [Paragraph("1. Problem", h1), Paragraph(
        "A food delivery marketplace loses money twice: to refunds that should not have been "
        "paid, and to investigations that consume analyst time without recovering anything. "
        "Naive outlier detection makes the second loss worse, because high-frequency "
        "customers generate more refunds in absolute terms even when their refund rate is "
        "ordinary. The business question is therefore not \"who refunded the most\" but "
        "\"which accounts deserve a human review first, what does that review cost, and how "
        "many legitimate customers does the policy touch\".", body)]

    s += [Paragraph("2. Data and disclosure", h1), Paragraph(
        "Delivery attributes come from a public Zomato order dataset of 45,584 rows covering "
        "11 February to 6 April 2022 across 44 active days. The refund layer — refund events, "
        "amounts, reasons and customer identifiers — is synthetic and generated for this case "
        "study. It is disclosed as synthetic in the README, in the dashboard header and in "
        "every downstream report. February and April are partial calendar months, so "
        "month-over-month comparisons are suppressed rather than presented as a trend.", body)]

    s += [Paragraph("3. Method", h1), Paragraph(
        "<b>Review score.</b> A weighted rule score scaled 0–100: refund rate 40%, reason "
        "repetition 30%, refund frequency 20%, reason breadth 10%. Weights live in "
        "<i>dashboard/risk_rules.py</i> with a written rationale, and a sensitivity check "
        "confirms the ranking is stable (Spearman rho &gt; 0.95 across alternative weightings).", body),
        Paragraph(
        "<b>Eligibility.</b> An account enters the queue only with at least 5 orders and a "
        "refund rate above 30%. The threshold is a review gate, not a probability.", body),
        Paragraph(
        "<b>Volume-band normalisation.</b> Customers are grouped by order-count band, and each "
        "customer's refund rate is compared with the 95th percentile of their band. Band "
        "membership is computed from full unfiltered history, so a dashboard filter cannot "
        "move a customer into a different band.", body),
        Paragraph(
        "<b>Policy simulation.</b> Review cost, recovery rate and investigation capacity are "
        "explicit inputs. The simulation reports reviews, precision against the planted "
        "synthetic labels, and modelled net value — never realised savings.", body)]

    s += [PageBreak(), Paragraph("4. Findings", h1),
          table([["Metric", "Value"],
                 ["Delivery orders analysed", "45,584"],
                 ["Refund requests", "3,596 (7.9% of orders)"],
                 ["Historical refund value", "INR 9,74,344"],
                 ["Customers", "9,895 (2,515 with at least one refund)"],
                 ["Accounts flagged for review", "279"],
                 ["Refund value held by flagged accounts", "INR 3,77,892 (38.8%)"],
                 ["Flagged accounts at or below band P95", "113 of 279 (40.5%)"],
                 ["Flagged pool by tier", "Low 164 · Medium 107 · High 8"]],
                [10.2 * cm, 6.4 * cm]),
          Spacer(1, 10)]
    s += figure(CHARTS / "00_monthly_order_volume_vs_refund_rate_observed_data.png", 15.5,
                "Figure 1. Observed monthly order volume against refund rate. Partial months "
                "are shown but not compared.")
    s += [Paragraph(
        "Refund value is concentrated: 279 accounts hold 38.8% of historical refund exposure, "
        "which justifies a queue but not a conclusion. The volume-band check is the more "
        "important result. Two in five flagged accounts refund at a rate their own order "
        "volume already explains, so a policy that treats every flag as suspicious would "
        "spend most of its review capacity on normal high-frequency behaviour.", body)]

    s += [Paragraph("5. Policy economics", h1),
          table([["Policy", "Reviews", "Precision vs planted labels", "Modelled net value (INR)"],
                 ["High tier", "8", "100.0%", "8,274"],
                 ["High + Medium tiers", "115", "87.8%", "92,125"],
                 ["All flagged accounts", "279", "46.9%", "65,006"]],
                [5.6 * cm, 2.6 * cm, 4.6 * cm, 4.4 * cm]),
          Spacer(1, 6),
          Paragraph(
        "On those assumptions the High + Medium policy returns the most modelled value, with "
        "a break-even precision of 28.2%. The 279-case policy is not free: it reviews 164 "
        "additional accounts for less net value. These are modelled outcomes under stated "
        "assumptions; a real rollout needs actual investigation costs and case outcomes.", body)]

    s += [Paragraph("6. Validation", h1), Paragraph(
        "Eight headline KPIs are reconciled between pandas and SQL with zero mismatches. The "
        "test suite covers 214 tests across KPI definitions, the SQL layer, drift monitoring, "
        "the network check, policy economics, case lifecycle and the evidence tool, and runs "
        "in CI. A delivery-person permutation test returns p = 0.76, so there is no evidence "
        "of High-label clustering beyond chance. A weekly PSI monitor reports the score inputs "
        "as stable in the seeded stream.", body)]

    s += [Paragraph("7. Limitations", h1), Paragraph(
        "The refund layer is synthetic, so precision figures describe the planted labels rather "
        "than real fraud. The score is uncalibrated: 0–100 is a ranking, not a probability. "
        "Cost and recovery inputs in the policy simulation are assumptions. The observation "
        "window is eight weeks with two partial months, which limits seasonality claims. "
        "Network findings are reported as a null result, not as evidence of collusion.", body)]

    s += [Paragraph("8. Reproducibility", h1), Paragraph(
        "Every figure in this report is regenerated by the repository's scripts and pinned by "
        "tests. The dashboard exposes the same KPIs with sidebar filters, an explanation of "
        "each flag, and a capacity-limited review planner. Repository: "
        "github.com/rishi-1603/zomato-refund-fraud-analytics. Dashboard: "
        "zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app.", body_left)]

    doc.build(s)
    return OUT


if __name__ == "__main__":
    path = build()
    assert path.stat().st_size > 20_000, "PDF looks empty"
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
