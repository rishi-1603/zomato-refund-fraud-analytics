"""
build_excel_workbook.py — regenerate the Excel review workbook
================================================================================
Builds reports/FoodTrust_Review_Workbook.xlsx from the processed dataset and the
flagged-customer extract.

The workbook is self-contained: the Orders sheet holds order-level rows, and
every figure on the summary sheets is a live Excel formula (COUNTA / COUNTIF /
SUMIF / AVERAGEIF) over those rows. Nothing on a summary sheet is a typed-in
number, so a reviewer can trace each total back to the rows behind it.

HONESTY RULES (same as the dashboard):
    - The refund layer is synthetic and seeded. Refund values are not real losses.
    - A flag is a review priority from a rule-based score, not confirmed fraud,
      and not a machine-learning prediction.

Refresh:  python scripts/build_excel_workbook.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
SUSPECTS_PATH = ROOT / "reports" / "fraud_suspects.csv"
OUTPUT_PATH = ROOT / "reports" / "FoodTrust_Review_Workbook.xlsx"

# Must stay identical to dashboard/app.py (pd.cut bins) and docs.
TIER_BINS = [-1, 40, 70, 100]
TIER_LABELS = ["Low", "Medium", "High"]

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="D9E2F3")
TITLE_FONT = Font(bold=True, size=14, color="1F3864")
BOLD = Font(bold=True)
THIN_TOP = Border(top=Side(style="thin", color="8EA9DB"))

INR = '#,##0.00'
COUNT = '#,##0'
PCT = '0.00%'
DAY = 'dd-mmm-yyyy'


def _header(ws, labels, row=1):
    # append() keeps _current_row in sync so a later ws.append starts on the next
    # row; styling cells directly would leave a blank phantom row behind.
    ws.append(list(labels))
    for col, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30
    ws.freeze_panes = f"A{row + 1}"


def _widths(ws, widths):
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def _total_row(ws, row, ncols):
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = BOLD
        cell.fill = TOTAL_FILL
        cell.border = THIN_TOP


def _read_me(wb, orders, suspects):
    ws = wb.create_sheet("Read Me")
    ws["A1"] = "FoodTrust Review Workbook"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = "Refund review prioritisation for a food-delivery order book"
    ws["A2"].font = Font(italic=True, color="595959")

    first = orders["Order_Date"].min().date()
    last = orders["Order_Date"].max().date()
    lines = [
        ("Purpose",
         "Summarise refund activity and rank customers for human review, with every "
         "summary figure traceable to the Orders sheet."),
        ("Source data",
         f"{len(orders):,} orders, {first:%d %b %Y} to {last:%d %b %Y}, "
         f"{orders['Order_Date'].nunique()} active days."),
        ("Flagged customers",
         f"{len(suspects):,} customers meet the eligibility rule (5+ orders and a refund "
         "rate above 30%) and carry a 0-100 review score."),
        ("Disclosure",
         "The refund layer is synthetic and seeded onto a public Zomato dataset. "
         "Refund values are not real losses and are not confirmed fraud."),
        ("Language",
         "A flag is a review priority, not an accusation. The score is rule-based and "
         "uncalibrated: 70 does not mean a 70% chance of anything."),
        ("How to refresh",
         "Run: python scripts/build_excel_workbook.py"),
        ("Formulas",
         "Summary sheets recalculate on open (Excel, Google Sheets, LibreOffice). "
         "If a viewer shows blanks, open the file in Excel and press F9."),
    ]
    row = 4
    for label, text in lines:
        ws.cell(row=row, column=1, value=label).font = BOLD
        ws.cell(row=row, column=1).alignment = Alignment(vertical="top")
        cell = ws.cell(row=row, column=2, value=text)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[row].height = 46
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="Sheet guide").font = BOLD
    row += 1
    guide = [
        ("Orders", "Order-level rows: date, city, refund flag, reason, amount."),
        ("KPI Summary", "Headline counts and rates, all formulas over Orders."),
        ("Refund Reasons", "Volume and value by claim reason, with shares."),
        ("City Breakdown", "Orders, refund rate and exposure by city type."),
        ("Review Queue", "Flagged customers, ranked by review score, filterable."),
        ("Risk Tiers", "Queue counts and exposure by priority tier."),
        ("Daily Trend", "Daily refund count and value, with a chart."),
    ]
    for name, text in guide:
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=text)
        row += 1

    _widths(ws, {"A": 20, "B": 104})
    ws.sheet_view.showGridLines = False


def _orders_sheet(wb, orders):
    ws = wb.create_sheet("Orders")
    _header(ws, ["Order Date", "City", "Refund Requested", "Refund Reason",
                 "Refund Amount (INR)", "First Order For Customer"])

    first_seen = ~orders["Customer_ID"].duplicated()
    rows = zip(
        orders["Order_Date"].dt.date,
        orders["City"].fillna("Unknown"),
        orders["Refund_Requested"].map({True: "Yes", False: "No"}),
        orders["Refund_Reason"].fillna(""),
        orders["Refund_Amount"],
        first_seen.astype(int),
    )
    for r in rows:
        ws.append(list(r))

    last = len(orders) + 1
    for row in range(2, last + 1):
        ws.cell(row=row, column=1).number_format = DAY
        ws.cell(row=row, column=5).number_format = INR
    ws.auto_filter.ref = f"A1:F{last}"
    _widths(ws, {"A": 12, "B": 14, "C": 17, "D": 22, "E": 20, "F": 22})


def _kpi_sheet(wb, orders, n_queue):
    ws = wb.create_sheet("KPI Summary")
    last = len(orders) + 1
    qlast = n_queue + 1
    o = "Orders!"
    _header(ws, ["Metric", "Value", "Definition"])

    kpis = [
        ("Total orders", f"=COUNTA({o}$A$2:$A${last})", COUNT,
         "Rows in the order book."),
        ("Refund requests", f'=COUNTIF({o}$C$2:$C${last},"Yes")', COUNT,
         "Orders where a refund was requested."),
        ("Refund rate", "=B3/B2", PCT, "Refund requests / total orders."),
        ("Refund value (INR)", f"=SUM({o}$E$2:$E${last})", INR,
         "Sum of refund amounts."),
        ("Average refund (INR)", "=B5/B3", INR, "Refund value / refund requests."),
        ("Unique customers", f"=SUM({o}$F$2:$F${last})", COUNT,
         "Customers counted once, using the first-order flag."),
        ("First order date", f"=MIN({o}$A$2:$A${last})", DAY, "Earliest order in scope."),
        ("Last order date", f"=MAX({o}$A$2:$A${last})", DAY, "Latest order in scope."),
        ("Customers flagged", f"=COUNTA('Review Queue'!$B$2:$B${qlast})", COUNT,
         "Customers in the review queue."),
        ("Flagged exposure (INR)", f"=SUM('Review Queue'!$F$2:$F${qlast})", INR,
         "Refund value attached to flagged customers."),
        ("Flagged share of value", "=B11/B5", PCT,
         "Flagged exposure / total refund value."),
    ]
    for i, (label, formula, fmt, definition) in enumerate(kpis, start=2):
        ws.cell(row=i, column=1, value=label)
        value = ws.cell(row=i, column=2, value=formula)
        value.number_format = fmt
        value.font = BOLD
        ws.cell(row=i, column=3, value=definition).alignment = Alignment(wrap_text=True)

    _widths(ws, {"A": 24, "B": 16, "C": 52})
    ws.sheet_view.showGridLines = False


def _reason_sheet(wb, orders):
    ws = wb.create_sheet("Refund Reasons")
    last = len(orders) + 1
    o = "Orders!"
    _header(ws, ["Refund Reason", "Refunds", "Share of Refunds",
                 "Refund Value (INR)", "Share of Value", "Avg Refund (INR)"])

    reasons = (
        orders.loc[orders["Refund_Requested"], "Refund_Reason"]
        .value_counts().index.tolist()
    )
    total = len(reasons) + 2
    for i, reason in enumerate(reasons, start=2):
        ws.cell(row=i, column=1, value=reason)
        ws.cell(row=i, column=2, value=f'=COUNTIF({o}$D$2:$D${last},$A{i})').number_format = COUNT
        ws.cell(row=i, column=3, value=f"=B{i}/$B${total}").number_format = PCT
        ws.cell(row=i, column=4,
                value=f"=SUMIF({o}$D$2:$D${last},$A{i},{o}$E$2:$E${last})").number_format = INR
        ws.cell(row=i, column=5, value=f"=D{i}/$D${total}").number_format = PCT
        ws.cell(row=i, column=6, value=f"=IFERROR(D{i}/B{i},0)").number_format = INR

    ws.cell(row=total, column=1, value="Total")
    for col, fmt in ((2, COUNT), (3, PCT), (4, INR), (5, PCT)):
        letter = get_column_letter(col)
        ws.cell(row=total, column=col, value=f"=SUM({letter}2:{letter}{total - 1})").number_format = fmt
    ws.cell(row=total, column=6, value=f"=IFERROR(D{total}/B{total},0)").number_format = INR
    _total_row(ws, total, 6)

    ws.conditional_formatting.add(
        f"B2:B{total - 1}",
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"),
    )
    _widths(ws, {"A": 24, "B": 12, "C": 16, "D": 20, "E": 15, "F": 18})
    ws.sheet_view.showGridLines = False


def _city_sheet(wb, orders):
    ws = wb.create_sheet("City Breakdown")
    last = len(orders) + 1
    o = "Orders!"
    _header(ws, ["City", "Orders", "Refund Requests", "Refund Rate",
                 "Refund Value (INR)", "Share of Value"])

    cities = orders["City"].fillna("Unknown").value_counts().index.tolist()
    for i, city in enumerate(cities, start=2):
        ws.cell(row=i, column=1, value=city)
        ws.cell(row=i, column=2, value=f'=COUNTIF({o}$B$2:$B${last},$A{i})').number_format = COUNT
        ws.cell(row=i, column=3,
                value=f'=COUNTIFS({o}$B$2:$B${last},$A{i},{o}$C$2:$C${last},"Yes")').number_format = COUNT
        ws.cell(row=i, column=4, value=f"=IFERROR(C{i}/B{i},0)").number_format = PCT
        ws.cell(row=i, column=5,
                value=f"=SUMIF({o}$B$2:$B${last},$A{i},{o}$E$2:$E${last})").number_format = INR

    total = len(cities) + 2
    for i in range(2, total):
        ws.cell(row=i, column=6, value=f"=IFERROR(E{i}/$E${total},0)").number_format = PCT

    ws.cell(row=total, column=1, value="Total")
    for col, fmt in ((2, COUNT), (3, COUNT), (4, PCT), (5, INR), (6, PCT)):
        letter = get_column_letter(col)
        if col == 4:
            formula = f"=IFERROR(C{total}/B{total},0)"
        elif col == 6:
            formula = f"=SUM(F2:F{total - 1})"
        else:
            formula = f"=SUM({letter}2:{letter}{total - 1})"
        ws.cell(row=total, column=col, value=formula).number_format = fmt
    _total_row(ws, total, 6)

    _widths(ws, {"A": 16, "B": 12, "C": 17, "D": 13, "E": 20, "F": 15})
    ws.sheet_view.showGridLines = False


def _queue_sheet(wb, orders, suspects):
    ws = wb.create_sheet("Review Queue")

    latest_city = (
        orders.sort_values("Order_Date")
        .groupby("Customer_ID")["City"].last()
        .rename("City")
    )
    queue = suspects.merge(latest_city, on="Customer_ID", how="left")
    queue["Risk_Tier"] = pd.cut(queue["Fraud_Risk_Score"], bins=TIER_BINS, labels=TIER_LABELS)
    queue = queue.sort_values("Fraud_Risk_Score", ascending=False).reset_index(drop=True)

    _header(ws, ["Rank", "Customer ID", "City", "Orders", "Refunds",
                 "Refund Value (INR)", "Refund Rate", "Reason Repetition",
                 "Refunds Per Day", "Review Score", "Review Tier"])

    for i, r in queue.iterrows():
        row = i + 2
        ws.cell(row=row, column=1, value=i + 1)
        ws.cell(row=row, column=2, value=r["Customer_ID"])
        ws.cell(row=row, column=3, value=r["City"] if pd.notna(r["City"]) else "Unknown")
        ws.cell(row=row, column=4, value=int(r["Total_Orders"])).number_format = COUNT
        ws.cell(row=row, column=5, value=int(r["Total_Refunds"])).number_format = COUNT
        ws.cell(row=row, column=6, value=float(r["Total_Refund_Amount"])).number_format = INR
        ws.cell(row=row, column=7, value=float(r["Refund_Rate"]) / 100).number_format = PCT
        ws.cell(row=row, column=8, value=float(r["Reason_Repetition_Rate"]) / 100).number_format = PCT
        ws.cell(row=row, column=9, value=float(r["Refunds_Per_Day"])).number_format = '0.000'
        ws.cell(row=row, column=10, value=float(r["Fraud_Risk_Score"])).number_format = '0.00'
        ws.cell(row=row, column=11, value=str(r["Risk_Tier"]))

    last = len(queue) + 1
    ws.auto_filter.ref = f"A1:K{last}"

    ws.conditional_formatting.add(
        f"F2:F{last}",
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"),
    )
    ws.conditional_formatting.add(
        f"J2:J{last}",
        ColorScaleRule(
            start_type="num", start_value=0, start_color="63BE7B",
            mid_type="num", mid_value=40, mid_color="FFEB84",
            end_type="num", end_value=100, end_color="F8696B",
        ),
    )
    for tier, fill, font in (
        ("High", "FFC7CE", "9C0006"),
        ("Medium", "FFEB9C", "9C6500"),
        ("Low", "C6EFCE", "006100"),
    ):
        ws.conditional_formatting.add(
            f"K2:K{last}",
            CellIsRule(
                operator="equal", formula=[f'"{tier}"'],
                fill=PatternFill(start_color=fill, end_color=fill, fill_type="solid"),
                font=Font(color=font, bold=True),
            ),
        )

    _widths(ws, {"A": 7, "B": 13, "C": 14, "D": 9, "E": 9, "F": 19,
                 "G": 12, "H": 16, "I": 15, "J": 13, "K": 12})
    return queue


def _tier_sheet(wb, queue):
    ws = wb.create_sheet("Risk Tiers")
    last = len(queue) + 1
    q = "'Review Queue'!"
    _header(ws, ["Review Tier", "Customers", "Share of Flagged",
                 "Refund Exposure (INR)", "Share of Exposure", "Avg Score"])

    for i, tier in enumerate(["High", "Medium", "Low"], start=2):
        ws.cell(row=i, column=1, value=tier)
        ws.cell(row=i, column=2, value=f'=COUNTIF({q}$K$2:$K${last},$A{i})').number_format = COUNT
        ws.cell(row=i, column=3, value=f"=B{i}/$B$5").number_format = PCT
        ws.cell(row=i, column=4,
                value=f"=SUMIF({q}$K$2:$K${last},$A{i},{q}$F$2:$F${last})").number_format = INR
        ws.cell(row=i, column=5, value=f"=D{i}/$D$5").number_format = PCT
        ws.cell(row=i, column=6,
                value=f"=IFERROR(AVERAGEIF({q}$K$2:$K${last},$A{i},{q}$J$2:$J${last}),0)").number_format = '0.00'

    ws.cell(row=5, column=1, value="Total")
    for col, fmt in ((2, COUNT), (3, PCT), (4, INR), (5, PCT)):
        letter = get_column_letter(col)
        ws.cell(row=5, column=col, value=f"=SUM({letter}2:{letter}4)").number_format = fmt
    ws.cell(row=5, column=6,
            value="=IFERROR(SUMPRODUCT(B2:B4,F2:F4)/B5,0)").number_format = '0.00'
    _total_row(ws, 5, 6)

    _widths(ws, {"A": 16, "B": 12, "C": 16, "D": 21, "E": 17, "F": 11})
    ws.sheet_view.showGridLines = False


def _daily_sheet(wb, orders):
    ws = wb.create_sheet("Daily Trend")
    last = len(orders) + 1
    o = "Orders!"
    _header(ws, ["Order Date", "Refund Requests", "Refund Value (INR)",
                 "Cumulative Value (INR)"])

    days = sorted(orders["Order_Date"].dt.date.unique())
    for i, day in enumerate(days, start=2):
        ws.cell(row=i, column=1, value=day).number_format = DAY
        ws.cell(row=i, column=2, value=f'=COUNTIF({o}$A$2:$A${last},$A{i})').number_format = COUNT
        ws.cell(row=i, column=3,
                value=f"=SUMIF({o}$A$2:$A${last},$A{i},{o}$E$2:$E${last})").number_format = INR
        prior = "0" if i == 2 else f"D{i - 1}"
        ws.cell(row=i, column=4, value=f"={prior}+C{i}").number_format = INR

    last_day = len(days) + 1
    chart = LineChart()
    chart.title = "Daily refund value"
    chart.y_axis.title = "INR"
    chart.x_axis.title = "Order date"
    chart.height = 8.5
    chart.width = 20
    chart.add_data(Reference(ws, min_col=3, min_row=1, max_row=last_day), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last_day))
    ws.add_chart(chart, "F2")

    _widths(ws, {"A": 13, "B": 17, "C": 20, "D": 22})


def build(out_path: Path = OUTPUT_PATH) -> Path:
    """Write the workbook and return its path."""
    orders = pd.read_csv(ORDERS_PATH)
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)
    suspects = pd.read_csv(SUSPECTS_PATH)

    wb = Workbook()
    wb.remove(wb.active)

    _read_me(wb, orders, suspects)
    _orders_sheet(wb, orders)
    _kpi_sheet(wb, orders, len(suspects))
    _reason_sheet(wb, orders)
    _city_sheet(wb, orders)
    queue = _queue_sheet(wb, orders, suspects)
    _tier_sheet(wb, queue)
    _daily_sheet(wb, orders)

    wb.calculation.fullCalcOnLoad = True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")
