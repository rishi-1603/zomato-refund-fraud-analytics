"""Bounded deterministic question answering over the selected synthetic queue.

No model, arbitrary SQL or external provider is used. Unknown wording, multiple
metrics and IDs outside the supplied queue are refused instead of guessed.
"""
from __future__ import annotations

import re

try:
    from decision_engine import plan_reviews
except ImportError:
    from dashboard.decision_engine import plan_reviews

CAUTION = ('Synthetic refund layer. Queue scores are not probabilities or proof of fraud; '
           'customer aggregates use full source history and no causal or realized-savings claim is supported.')


def _refuse(message, status='unsupported'):
    return {'ok': False, 'status': status, 'text': message, 'warnings': [CAUTION]}


def ask(flagged, question):
    if not isinstance(question, str) or not question.strip() or len(question) > 300:
        return _refuse('Enter a question of at most 300 characters.', 'invalid_input')
    q = ' '.join(question.lower().strip().split()).rstrip('?').strip()
    try:
        record, queue = plan_reviews(flagged, len(flagged), 0, 0)
    except (ValueError, TypeError):
        return _refuse('The current queue fails its data checks.', 'data_unavailable')
    source = ['Customer_ID']
    customer = None
    if re.fullmatch(r'(?:how many|number of) (?:flagged|eligible) customers', q):
        value, unit, formula = len(queue), 'customers', 'COUNT(selected eligible customers)'
    elif re.fullmatch(r'(?:what is|show) (?:the )?total (?:queue|refund) exposure', q):
        value, unit, formula = float(queue.Total_Refund_Amount.sum()), 'INR', 'SUM(full-history refund amount for selected queue customers)'
        source.append('Total_Refund_Amount')
    else:
        match = re.fullmatch(r'(?:what is|show) (?:the )?(refund rate|order count|refund count|refund exposure|risk score) (?:for|of) (cust\d{5})', q)
        if not match:
            return _refuse('Unsupported or ambiguous question. Ask one supported queue metric at a time.')
        metric, customer = match.groups()
        customer = customer.upper()
        row = queue[queue.Customer_ID.eq(customer)]
        if row.empty:
            return _refuse('That customer is not in the current filtered review queue.', 'outside_scope')
        row = row.iloc[0]
        if metric == 'refund rate':
            if row.Total_Orders == 0:
                return _refuse('The customer has no valid order denominator.', 'data_unavailable')
            value, unit, formula = float(row.Total_Refunds / row.Total_Orders * 100), 'percent', '100 × full-history refunds / full-history orders'
            source += ['Total_Refunds', 'Total_Orders']
        elif metric == 'order count':
            value, unit, formula = int(row.Total_Orders), 'orders', 'COUNT(full-history customer orders)'
            source.append('Total_Orders')
        elif metric == 'refund count':
            value, unit, formula = int(row.Total_Refunds), 'refunds', 'COUNT(full-history customer refunds)'
            source.append('Total_Refunds')
        elif metric == 'refund exposure':
            value, unit, formula = float(row.Total_Refund_Amount), 'INR', 'SUM(full-history customer refund amounts)'
            source.append('Total_Refund_Amount')
        else:
            value, unit, formula = float(row.Fraud_Risk_Score), 'score', 'Existing full-population, pool-relative risk score'
            source.append('Fraud_Risk_Score')
    return {'ok': True, 'status': 'answered', 'value': value, 'unit': unit, 'customer_id': customer,
            'scope_id': record['scope']['scope_id'], 'scope_customers': len(queue),
            'formula': formula, 'source_columns': source, 'reconciliation': record['source']['reconciliation'],
            'warnings': [CAUTION]}
