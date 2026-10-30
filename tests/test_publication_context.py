"""Publication guards: partial-month totals and baseline flags need context."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
from kpi_engine import _mom


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


def test_overview_handles_cached_pre_publication_module(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import kpi_engine
    original = kpi_engine._mom

    def previous_schema(orders):
        value = original(orders)
        value.pop("partial_periods", None)
        value.pop("coverage_note", None)
        return value

    monkeypatch.setattr(kpi_engine, "_mom", previous_schema)
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    assert not app.exception
    assert any("not a like-for-like business trend" in item.value for item in app.warning)
    assert not any("Analytics modules are refreshing" in item.value for item in app.warning)


def test_header_population_updates_with_city_filter():
    from streamlit.testing.v1 import AppTest
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.multiselect(key="f_city").set_value(["Metropolitian"]).run(timeout=30)
    assert not app.exception
    rendered = "\n".join(element.value for element in app.markdown)
    assert "34,087 orders in scope" in rendered
    assert "45,584 orders in scope" not in rendered
