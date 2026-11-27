"""
test_excel_workbook.py — the Excel deliverable must reconcile with the KPI engine
================================================================================
reports/FoodTrust_Review_Workbook.xlsx is a deliverable, not a screenshot: the
summary sheets are live formulas over an order-level sheet. These tests rebuild
the workbook into a temp folder and check the rows those formulas read, plus the
row alignment that a phantom header row once broke (data must start at row 2).

The review queue is compared against dashboard/app.build_customer_risk_table, so
a stale reports/fraud_suspects.csv fails here instead of shipping.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dashboard"))

import importlib.util  # noqa: E402

from build_excel_workbook import build  # noqa: E402
from kpi_engine import compute_kpis  # noqa: E402

DATA = ROOT / "data" / "processed" / "zomato_with_refunds.csv"


def _load_app():
    spec = importlib.util.spec_from_file_location(
        "zomato_dashboard_app_xlsx", str(ROOT / "dashboard" / "app.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def context(tmp_path_factory):
    from openpyxl import load_workbook

    orders = pd.read_csv(DATA)
    orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], dayfirst=True)
    suspects = _load_app().build_customer_risk_table(orders)
    path = build(tmp_path_factory.mktemp("xlsx") / "workbook.xlsx")
    return load_workbook(path), orders, suspects, compute_kpis(orders, suspects)


def test_sheet_inventory(context):
    wb, _, _, _ = context
    assert wb.sheetnames == [
        "Read Me", "Orders", "KPI Summary", "Refund Reasons",
        "City Breakdown", "Review Queue", "Risk Tiers", "Daily Trend",
    ]


def test_orders_sheet_starts_at_row_two(context):
    wb, orders, _, _ = context
    ws = wb["Orders"]
    assert ws["A1"].value == "Order Date"
    assert ws["A2"].value is not None
    assert ws.max_row == len(orders) + 1


def test_orders_sheet_totals_match_kpi_engine(context):
    wb, _, _, kpis = context
    ws = wb["Orders"]

    yes = sum(1 for (v,) in ws.iter_rows(min_row=2, min_col=3, max_col=3, values_only=True) if v == "Yes")
    amount = sum(v for (v,) in ws.iter_rows(min_row=2, min_col=5, max_col=5, values_only=True))
    first_flags = sum(v for (v,) in ws.iter_rows(min_row=2, min_col=6, max_col=6, values_only=True))

    assert ws.max_row - 1 == kpis["total_orders"] == 45_584
    assert yes == kpis["refund_orders"] == 3_596
    assert round(amount, 2) == round(kpis["refund_exposure"], 2) == 974_343.55
    assert first_flags == kpis["customers"] == 9_895


def test_kpi_formulas_cover_every_order_row(context):
    wb, orders, _, _ = context
    ws = wb["KPI Summary"]
    last = len(orders) + 1

    assert ws["B2"].value == f"=COUNTA(Orders!$A$2:$A${last})"
    assert ws["B3"].value == f'=COUNTIF(Orders!$C$2:$C${last},"Yes")'
    assert ws["B5"].value == f"=SUM(Orders!$E$2:$E${last})"
    assert ws["B12"].value == "=B11/B5"
    # Guard the row alignment: a blank row 2 would shrink every total by one.
    assert ws["B2"].value.endswith(f"$A${len(orders) + 1})")


def test_review_queue_matches_dashboard(context):
    wb, _, suspects, kpis = context
    ws = wb["Review Queue"]

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) == len(suspects) == 279
    assert round(sum(r[5] for r in rows), 2) == round(kpis["flagged_exposure"], 2) == 377_891.92

    tiers = pd.Series([r[10] for r in rows]).value_counts().to_dict()
    assert tiers == {"Low": 164, "Medium": 107, "High": 8}
    assert tiers["High"] == kpis["high_tier_count"]


def test_tier_sheet_formulas_point_at_the_queue(context):
    wb, _, suspects, _ = context
    ws = wb["Risk Tiers"]
    last = len(suspects) + 1

    assert ws["A2"].value == "High"
    assert ws["B2"].value == f"=COUNTIF('Review Queue'!$K$2:$K${last},$A2)"
    assert ws["D2"].value == f"=SUMIF('Review Queue'!$K$2:$K${last},$A2,'Review Queue'!$F$2:$F${last})"
