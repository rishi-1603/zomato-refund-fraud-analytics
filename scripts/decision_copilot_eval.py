"""Evaluate authored bounded queue questions against independent raw aggregates.

Timing is in-process only, after data load. No external provider calls or
provider charges occur; CPU/infrastructure cost is not measured.
"""
from __future__ import annotations
import json
import math
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.decision_copilot import ask  # noqa: E402
from dashboard.app import build_customer_risk_table  # noqa: E402

BENCH = ROOT / 'evals/decision_copilot_benchmark.json'


def run(bench_path=BENCH):
    orders = pd.read_csv(ROOT / 'data/processed/zomato_with_refunds.csv')
    orders['Order_Date'] = pd.to_datetime(orders['Order_Date'], dayfirst=True)
    queue = build_customer_risk_table(orders)
    known_scores = pd.read_csv(ROOT / 'reports/fraud_suspects.csv').set_index('Customer_ID')['Fraud_Risk_Score']
    cases = json.loads(Path(bench_path).read_text(encoding='utf-8'))['cases']
    findings, latencies = [], []
    for case in cases:
        start = time.perf_counter()
        answer = ask(queue, case['question'])
        latencies.append((time.perf_counter() - start) * 1000)
        if case['expected'] == 'refuse':
            correct = not answer['ok'] and 'value' not in answer
        else:
            metric = case['metric']
            cid = case.get('customer_id')
            if cid:
                customer_orders = orders[orders.Customer_ID.eq(cid)]
                n, refunds = len(customer_orders), int(customer_orders.Refund_Requested.eq(True).sum())  # noqa: E712
                expected = {'refund rate': refunds / n * 100, 'order count': n, 'refund count': refunds,
                            'refund exposure': float(customer_orders.Refund_Amount.sum()),
                            'risk score': float(known_scores.loc[cid])}[metric]
            elif metric == 'queue_count':
                expected = len(known_scores)
            else:
                expected = float(orders[orders.Customer_ID.isin(known_scores.index)].Refund_Amount.sum())
            correct = answer['ok'] and math.isclose(float(answer['value']), float(expected), rel_tol=1e-9, abs_tol=1e-6) and bool(answer.get('scope_id')) and bool(answer.get('formula')) and bool(answer.get('source_columns'))
        findings.append({'question': case['question'], 'expected': case['expected'], 'passed': bool(correct), 'status': answer.get('status')})
    durations = sorted(latencies)
    p95 = durations[math.ceil(len(durations)*.95)-1] if durations else None
    answerable = [x for x in findings if x['expected']=='answer']
    refusals = [x for x in findings if x['expected']=='refuse']
    return {'case_count':len(findings), 'answerable_passed':sum(x['passed'] for x in answerable),
            'answerable_total':len(answerable), 'refusals_passed':sum(x['passed'] for x in refusals),
            'refusals_total':len(refusals), 'pass':all(x['passed'] for x in findings),
            'latency_ms':{'p50':statistics.median(durations) if durations else None,'p95':p95},
            'measurement_scope':'Local in-process deterministic queue queries after data load. No provider/API calls; provider spend is zero. Hardware, dataset and latency differ by environment; infrastructure cost not measured.',
            'cases':findings}


def main():
    result=run()
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
