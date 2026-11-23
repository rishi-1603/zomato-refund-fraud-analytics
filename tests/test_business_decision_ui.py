from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'dashboard/app.py'


def button(app,label):
    # Check regular buttons first
    for b in app.button:
        if b.label == label:
            return b
    # Check all widgets in the tree recursively
    def find_in_tree(tree):
        if isinstance(tree, dict):
            for key, value in tree.items():
                if hasattr(value, 'label') and value.label == label:
                    return value
                if hasattr(value, 'children'):
                    result = find_in_tree(value.children)
                    if result:
                        return result
                if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                    result = find_in_tree(value)
                    if result:
                        return result
        elif isinstance(tree, (list, tuple, set)):
            for item in tree:
                if hasattr(item, 'label') and item.label == label:
                    return item
                if hasattr(item, 'children'):
                    result = find_in_tree(item.children)
                    if result:
                        return result
        return None
    
    result = find_in_tree(app._tree)
    if result:
        return result
    raise StopIteration(f"Button with label '{label}' not found")


def test_decision_workflow_uses_filtered_queue_and_clears_on_scope_change(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    app=AppTest.from_file(str(APP)).run(timeout=90)
    assert not app.exception
    # Navigate to "4. Review Operations" page (selectbox)
    app.selectbox(key="Navigation").set_value("4. Review Operations").run(timeout=90)
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


def test_history_add_snapshot_and_followup_are_user_entered(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    app=AppTest.from_file(str(APP)).run(timeout=90)
    # Navigate to "4. Review Operations" page (selectbox)
    app.selectbox(key="Navigation").set_value("4. Review Operations").run(timeout=90)
    assert not app.exception
    button(app,'Build review decision').click().run(timeout=90)
    button(app,'Add current snapshot to history').click().run(timeout=90)
    assert not app.exception
    assert len(app.session_state['refund_history']['entries'])==1
    app.text_input(key='refund_follow_metric').set_value('Verified review cases')
    app.text_input(key='refund_follow_unit').set_value('cases')
    app.text_input(key='refund_follow_baseline').set_value('5')
    app.text_input(key='refund_follow_observed').set_value('8')
    button(app,'Add follow-up').click().run(timeout=90)
    assert not app.exception
    entry=app.session_state['refund_history']['entries'][0]
    assert entry['followups'][0]['difference']==3
    assert entry['followups'][0]['verification']=='user-entered, unverified'


def test_copilot_refuses_out_of_scope_and_clears_after_filter_change(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    app=AppTest.from_file(str(APP)).run(timeout=90)
    # Navigate to "4. Review Operations" page (selectbox)
    app.selectbox(key="Navigation").set_value("4. Review Operations").run(timeout=90)
    assert not app.exception
    app.text_input(key='refund_copilot_question').set_value('How many flagged customers?')
    button(app,'Calculate queue answer').click().run(timeout=90)
    assert not app.exception
    assert app.session_state['refund_copilot_answer']['value']==279
    app.multiselect(key='f_tier').set_value(['High']).run(timeout=90)
    assert 'refund_copilot_answer' not in app.session_state
    app.text_input(key='refund_copilot_question').set_value('What is the refund rate for CUST99999?')
    button(app,'Calculate queue answer').click().run(timeout=90)
    assert not app.exception
    assert app.session_state['refund_copilot_answer']['status']=='outside_scope'