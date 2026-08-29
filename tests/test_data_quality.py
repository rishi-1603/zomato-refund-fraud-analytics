"""
test_data_quality.py — data quality checks for the Zomato refund dataset
=========================================================================
If any of these fail, every KPI, score, and dashboard number is untrustworthy.
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "data" / "processed" / "zomato_with_refunds.csv"
RAW_PATH = ROOT / "data" / "raw" / "Zomato Dataset.csv"

VALID_REASONS = {"Late Delivery", "Wrong Item", "Missing Item", "Poor Quality",
                 "Damaged Packaging", "Item Not Received"}


@pytest.fixture(scope="module")
def orders():
    return pd.read_csv(ORDERS_PATH)


def test_expected_row_count(orders):
    assert len(orders) == 45_584, f"Expected 45,584 orders, found {len(orders)}"


def test_order_ids_unique_and_complete(orders):
    assert orders["ID"].notna().all()
    assert orders["ID"].is_unique, "Duplicate order IDs would double-count KPIs"


def test_customer_id_format(orders):
    ids = orders["Customer_ID"].dropna()
    assert ids.str.match(r"^CUST\d{5}$").all(), "Customer_ID format drifted"
    assert ids.nunique() <= 10_000, "More customers than the generator creates"


def test_refund_flag_is_boolean(orders):
    vals = set(orders["Refund_Requested"].dropna().unique())
    assert vals <= {True, False}, f"Refund_Requested has non-boolean values: {vals}"


def test_refund_amount_consistency(orders):
    """No refund requested → amount must be 0; refund requested → amount > 0."""
    no_refund = orders[~orders["Refund_Requested"].astype(bool)]
    assert (no_refund["Refund_Amount"] == 0).all(), "Refund amount > 0 without a refund"
    refunded = orders[orders["Refund_Requested"].astype(bool)]
    assert (refunded["Refund_Amount"] > 0).all(), "Refund requested with zero amount"


def test_refund_reason_present_when_refunded(orders):
    refunded = orders[orders["Refund_Requested"].astype(bool)]
    missing = refunded["Refund_Reason"].isna().sum()
    assert missing == 0, f"{missing} refunds have no reason"


def test_refund_reasons_are_valid_categories(orders):
    reasons = set(orders["Refund_Reason"].dropna().unique())
    unknown = reasons - VALID_REASONS
    assert not unknown, f"Unknown refund reasons appeared: {unknown}"


def test_ratings_in_valid_range(orders):
    """The public raw dataset contains a known quirk: 53 rows rated 6.0 on a
    5-star scale (plus ~1.9k NaNs). We assert the observed bounds [1, 6] and
    pin the quirk count so any change to the raw data is caught."""
    r = orders["Delivery_person_Ratings"].dropna()
    assert r.between(1, 6).all(), "Delivery ratings outside observed bounds [1,6]"
    n_six = int((r == 6.0).sum())
    assert n_six == 53, (
        f"Out-of-scale (6.0) rating count changed: {n_six} vs 53 — "
        "raw dataset may have been altered")


def test_raw_dataset_untouched():
    """The raw public dataset must stay exactly as committed — the refund layer
    is generated on top of it, never by editing it."""
    raw = pd.read_csv(RAW_PATH)
    assert len(raw) == 45_584
    assert "Refund_Requested" not in raw.columns, (
        "Raw dataset must not contain generated refund columns")


def test_processed_extends_raw_not_replaces():
    """Processed file = raw columns + exactly the 4 generated columns."""
    raw = pd.read_csv(RAW_PATH)
    processed = pd.read_csv(ORDERS_PATH)
    assert list(processed.columns)[: len(raw.columns)] == list(raw.columns)
    added = set(processed.columns) - set(raw.columns)
    assert added == {"Customer_ID", "Refund_Requested", "Refund_Reason", "Refund_Amount"}, (
        f"Unexpected generated columns: {added}")
