import math
import pandas as pd
import pytest

from dashboard.decision_engine import plan_reviews


@pytest.fixture
def flagged():
    return pd.DataFrame([
        {'Customer_ID':'b','Fraud_Risk_Score':80.0,'Total_Refund_Amount':200.0,'Total_Orders':7,'Total_Refunds':3},
        {'Customer_ID':'a','Fraud_Risk_Score':80.0,'Total_Refund_Amount':100.0,'Total_Orders':5,'Total_Refunds':2},
        {'Customer_ID':'c','Fraud_Risk_Score':60.0,'Total_Refund_Amount':50.0,'Total_Orders':8,'Total_Refunds':3},
    ])


def test_capacity_selection_and_scenarios_are_reproducible(flagged):
    record, queue = plan_reviews(flagged, capacity=2, review_cost=40, recoverable_fraction=0.2)
    assert list(queue.Customer_ID) == ['a', 'b']
    assert record['source']['reconciliation'] == 'PASS'
    assert record['scope']['eligible_customers'] == 3
    assert record['evidence']['selected_historical_exposure_inr'] == 300
    assert record['scenarios']['base']['assumed_recoverable_inr'] == pytest.approx(60)
    assert record['scenarios']['base']['review_cost_inr'] == 80
    assert record['scenarios']['base']['modeled_net_inr'] == pytest.approx(-20)
    assert record['observed_outcome'] is None


def test_capacity_zero_and_above_pool(flagged):
    record, queue = plan_reviews(flagged, 0, 50, 0.1)
    assert queue.empty and record['scenarios']['base']['modeled_net_inr'] == 0
    assert record['scenarios']['break_even_recovery_fraction'] is None
    record, queue = plan_reviews(flagged, 30, 50, 0.1)
    assert len(queue) == 3 and record['scope']['selected_customers'] == 3


@pytest.mark.parametrize('kwargs', [dict(capacity=-1), dict(capacity=1.5), dict(review_cost=-1),
                                    dict(review_cost=math.inf), dict(recoverable_fraction=1.1),
                                    dict(recoverable_fraction=float('nan'))])
def test_invalid_assumptions_rejected(flagged, kwargs):
    arguments=dict(capacity=2, review_cost=50, recoverable_fraction=0.1);arguments.update(kwargs)
    with pytest.raises(ValueError): plan_reviews(flagged, **arguments)


def test_invalid_data_and_duplicate_customers_block_publication(flagged):
    with pytest.raises(ValueError): plan_reviews(pd.concat([flagged,flagged.head(1)]), 2, 50, .1)
    modified=flagged.copy();modified.loc[0,'Total_Refund_Amount']=-10
    with pytest.raises(ValueError): plan_reviews(modified, 2, 50, .1)


def test_scenarios_do_not_use_planted_labels_or_claim_fraud(flagged):
    a,_=plan_reviews(flagged,2,50,.1)
    with_labels=flagged.assign(Planted_Risk=['High','Low','High'])
    b,_=plan_reviews(with_labels,2,50,.1)
    assert a['scenarios'] == b['scenarios']
    assert 'not confirmed fraud' in a['limitations'].lower()


def test_fractional_counts_are_rejected(flagged):
    flagged['Total_Refunds'] = flagged['Total_Refunds'].astype(float)
    flagged.loc[0, 'Total_Refunds'] = 1.5
    with pytest.raises(ValueError, match='whole numbers'):
        plan_reviews(flagged, 2, 50, .1)


def test_observed_outcome_is_explicitly_user_reported(flagged):
    rec, _ = plan_reviews(flagged, 2, 50, .1, observed_note='Follow-up not independently checked')
    assert rec['observed_outcome']['source'] == 'user-entered, unverified'
    assert 'Follow-up' in rec['observed_outcome']['note']


def test_boolean_values_do_not_become_numeric(flagged):
    flagged['Total_Refund_Amount'] = flagged['Total_Refund_Amount'].astype(object)
    flagged.loc[0, 'Total_Refund_Amount'] = True
    with pytest.raises(ValueError, match='booleans'):
        plan_reviews(flagged, 2, 50, .1)


def test_record_keeps_explicit_effective_filter_context(flagged):
    filters={'risk_tiers':['High'], 'last_order_date_range':['2022-03-01','2022-04-06']}
    rec, _ = plan_reviews(flagged, 2, 50, .1, filter_context=filters)
    filters['risk_tiers'].append('Low')
    assert rec['scope']['filter_context']['risk_tiers'] == ['High']


def test_invalid_filter_context_rejected(flagged):
    with pytest.raises(ValueError, match='Filter context'):
        plan_reviews(flagged, 2, 50, .1, filter_context={'bad': float('nan')})
