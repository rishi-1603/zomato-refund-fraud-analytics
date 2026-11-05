"""Deterministic, bounded review-capacity scenarios for the current flagged queue.

No ground-truth label, provider or arbitrary query is used. A selected risk
flag is not confirmed fraud; historical refund exposure is not loss avoided.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from numbers import Real

import pandas as pd

REQUIRED = ['Customer_ID', 'Fraud_Risk_Score', 'Total_Refund_Amount', 'Total_Orders', 'Total_Refunds']


def _number(value, name, upper, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f'{name} must be a finite number.')
    if value < 0 or value > upper or (integer and int(value) != value):
        raise ValueError(f'{name} must be within the supported range.')
    return int(value) if integer else float(value)


def _text(value, name, maximum=500):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'{name} must be text of at most {maximum} characters.')
    return value.strip()


def plan_reviews(flagged: pd.DataFrame, capacity, review_cost, recoverable_fraction,
                 action='Review flagged cases', success_metric='Confirmed review outcomes',
                 follow_up='Compare reviewed results with an agreed baseline',
                 observed_note='', status='proposed', filter_context=None):
    """Return (aggregate record, selected queue) without using synthetic labels."""
    capacity = _number(capacity, 'Capacity', 1_000_000, integer=True)
    review_cost = _number(review_cost, 'Review cost', 10_000_000)
    recovery = _number(recoverable_fraction, 'Recoverable fraction', 1)
    if status not in {'proposed', 'approved', 'deferred'}:
        raise ValueError('Choose a supported decision status.')
    if filter_context is not None and not isinstance(filter_context, dict):
        raise ValueError('Filter context must be a JSON object.')
    try:
        filters = json.loads(json.dumps(filter_context or {}, allow_nan=False, sort_keys=True))
    except (TypeError, ValueError):
        raise ValueError('Filter context must be JSON-compatible.') from None
    if len(json.dumps(filters)) > 4000:
        raise ValueError('Filter context is too large.')
    if not isinstance(flagged, pd.DataFrame) or not set(REQUIRED).issubset(flagged.columns):
        raise ValueError('The current queue is missing required columns.')
    data = flagged[REQUIRED].copy()
    if data.Customer_ID.isna().any() or data.Customer_ID.duplicated().any() or not data.Customer_ID.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError('Customer identifiers must be present and unique within the queue.')
    for col in REQUIRED[1:]:
        if data[col].map(lambda value: isinstance(value, bool)).any():
            raise ValueError(f'{col} cannot contain booleans.')
        data[col] = pd.to_numeric(data[col], errors='coerce')
        if data[col].isna().any() or not data[col].map(math.isfinite).all() or (data[col] < 0).any():
            raise ValueError(f'{col} must contain finite non-negative values.')
    if (data.Total_Orders.mod(1) != 0).any() or (data.Total_Refunds.mod(1) != 0).any():
        raise ValueError('Order and refund counts must be whole numbers.')
    if (data.Fraud_Risk_Score > 100).any() or (data.Total_Refunds > data.Total_Orders).any():
        raise ValueError('Queue values violate the score or refund-count contract.')
    ranked = data.sort_values(['Fraud_Risk_Score', 'Customer_ID'], ascending=[False, True], kind='stable').reset_index(drop=True)
    selected = ranked.head(min(capacity, len(ranked))).copy()
    exposure = float(selected.Total_Refund_Amount.sum())
    n = len(selected)
    # Fixed read-only query against only the selected aggregate customer rows.
    with sqlite3.connect(':memory:') as connection:
        selected.to_sql('review_scope', connection, index=False)
        connection.execute('PRAGMA query_only = ON')
        sql_n, sql_refunds, sql_exposure = connection.execute(
            'SELECT COUNT(*), COALESCE(SUM(Total_Refunds),0), COALESCE(SUM(Total_Refund_Amount),0) FROM review_scope'
        ).fetchone()
    if sql_n != n or sql_refunds != int(selected.Total_Refunds.sum()) or not math.isclose(float(sql_exposure), exposure, rel_tol=1e-10, abs_tol=1e-6):
        raise ValueError('SQL/pandas queue reconciliation failed; no record is published.')
    def scenario(fraction):
        gross = exposure * fraction
        cost = n * review_cost
        return {'assumed_recoverable_fraction': fraction, 'assumed_recoverable_inr': gross,
                'review_cost_inr': cost, 'modeled_net_inr': gross - cost}
    payload = ranked.to_json(orient='records', double_precision=15)
    scope_id = hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]
    note = _text(observed_note, 'Observed note')
    return ({
        'schema_version': 1, 'project': 'refund_risk', 'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source': {'dataset': 'data/processed/zomato_with_refunds.csv',
                   'classification': 'public delivery attributes; synthetic refund layer',
                   'reconciliation': 'PASS', 'definition': 'Selected queue count, refund count and exposure reconciled in SQLite and pandas.'},
        'scope': {'scope_id': scope_id,
            'eligible_customers': len(ranked), 'selected_customers': n, 'filter_context': filters,
            'definition': 'Filtered eligible customer queue; customer metrics and scores use full source history.'},
        'evidence': {'selected_historical_exposure_inr': exposure,
                     'selected_historical_refund_count': int(selected.Total_Refunds.sum())},
        'assumptions': {'capacity': capacity, 'review_cost_per_customer_inr': review_cost,
                        'base_recoverable_fraction': recovery},
        'scenarios': {'low': scenario(recovery * .5), 'base': scenario(recovery),
                      'high': scenario(min(1.0, recovery * 1.5)),
                      'break_even_recovery_fraction': n * review_cost / exposure if exposure else None},
        'decision': {'status': status, 'action': _text(action, 'Action'),
                     'success_metric': _text(success_metric, 'Success metric'),
                     'follow_up': _text(follow_up, 'Follow-up')},
        'observed_outcome': {'source': 'user-entered, unverified', 'note': note} if note else None,
        'limitations': 'Synthetic refund data and labels; a risk flag is not confirmed fraud. Recovery fractions and costs are assumptions, not observed savings. The queue uses full-history customer metrics and pool-relative scores; filters select customers, not matching order rows. No causal effect is established.',
    }, selected)
