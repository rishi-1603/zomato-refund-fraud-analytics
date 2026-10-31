# Refund review: findings and policy considerations

This case study examines how a review team could prioritize customer records using consistent metrics, activity-level comparisons and stated operating costs. Delivery attributes are public-source data; customer identifiers, refunds, amounts and risk labels are generated. No actual fraud or prevented loss is established.

## Review population

The data contains 45,584 orders, 9,895 observed customer IDs and 3,596 refund requests. Synthetic refund value totals ₹974,343.55.

The current rule requires at least five orders and a refund rate above 30%. It places 279 customers in the score pool, holding 38.78% of refund value. The weighted score ranks those records; it is not a calibrated probability or a fraud determination.

## What changes the interpretation

Of those 279 flags, 113 are at or below their order-volume band's P95 refund-rate baseline. That is comparison context, not a confirmed false-positive count. Reviewers should consider service problems, small denominators and the underlying evidence before drawing conclusions.

Coverage is a separate issue: only 131 of 299 generated High labels enter the eligible pool, and eight reach the High tier. Ranking quality within a restricted pool cannot establish end-to-end coverage.

## Review-policy scenarios

With a ₹250 review cost, ₹100 false-positive friction cost and 50% recovery assumption, the three tier policies produce modeled net values of:

| Policy | Reviews | Modeled net value |
|---|---:|---:|
| High tier | 8 | ₹8,274 |
| High + Medium | 115 | ₹92,125 |
| All flagged | 279 | ₹65,006 |

High + Medium has the largest modeled net value among these three tier policies. The report also examines top-k budgets; this is not a search over every possible policy. Costs and recovery need actual operating evidence before adoption.

## Network and time-period checks

The shared-delivery-person permutation test returned p = 0.76. It did not detect excess clustering beyond chance; it does not establish that organized abuse is absent.

The dataset ends on 6 April 2022. April-versus-March totals are not comparable full months. The dashboard identifies that coverage limitation rather than treating the raw decline as an operational finding.

## Before a pilot

Collect investigator outcomes, measure review time and customer friction, revisit the eligibility funnel, and compare policies at a fixed review capacity. Customer action should not follow automatically from a score or baseline position.

[KPI reconciliation](kpi_reconciliation.md) · [Score validation](score_validation.md) · [Policy scenarios](alert_economics.md) · [Assumptions](assumptions_and_limitations.md)
