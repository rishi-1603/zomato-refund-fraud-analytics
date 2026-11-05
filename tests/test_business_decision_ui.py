from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'dashboard/app.py'


def button(app,label):
    return next(b for b in app.button if b.label==label)


def test_decision_workflow_uses_filtered_queue_and_clears_on_scope_change(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    app=AppTest.from_file(str(APP)).run(timeout=90)
    assert not app.exception
    button(app,'Build review decision').click().run(timeout=90)
    assert not app.exception
    record=app.session_state['refund_decision_record']
    assert record['scope']['eligible_customers']==279
    assert record['scope']['selected_customers']==50
    assert record['observed_outcome'] is None
    assert record['scope']['filter_context']['risk_tiers'] == ['Low', 'Medium', 'High']
    app.multiselect(key='f_tier').set_value(['High']).run(timeout=90)
    assert not app.exception
    assert 'refund_decision_record' not in app.session_state
    button(app,'Build review decision').click().run(timeout=90)
    assert not app.exception
    assert app.session_state['refund_decision_record']['scope']['eligible_customers']==8
