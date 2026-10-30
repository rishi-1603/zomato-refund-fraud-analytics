"""Publication guards: partial-month totals and baseline flags need context."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
from kpi_engine import _mom, what_changed


def test_partial_month_is_disclosed_without_changing_arithmetic():
    df = pd.DataFrame({'ID': range(4), 'Order_Date': pd.to_datetime(
        ['2022-03-01', '2022-03-31', '2022-04-01', '2022-04-06']),
        'Refund_Requested': [False, True, False, True], 'Refund_Amount': [0, 10, 0, 5]})
    result = _mom(df)
    assert result['partial_periods'] is True
    assert 'not a like-for-like' in result['coverage_note']
    assert result['exposure_delta_pct'] == -50


def test_observed_complete_boundaries_do_not_claim_partial_month():
    df = pd.DataFrame({'ID': range(4), 'Order_Date': pd.to_datetime(
        ['2022-03-01', '2022-03-31', '2022-04-01', '2022-04-30']),
        'Refund_Requested': [False, True, False, True], 'Refund_Amount': [0, 10, 0, 5]})
    assert _mom(df)['partial_periods'] is False
