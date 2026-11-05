# Investigator case workflow

This is a **synthetic-data investigation demonstration**, not evidence of fraud or an official Zomato case-management process. The current application does not provide persistent case management, an OTP workflow, verified GPS arrival or account restrictions.

## Review a flagged customer

1. Apply the dashboard's city/volume and investigation filters. The review queue selects customers; their risk scores, exposure and order counts are computed from the full committed order history. Last-order-date filtering is not an order-level time-period filter.
2. Inspect the customer's reported refund counts, repeated reasons and volume-band comparison. The score is an uncalibrated, pool-relative review signal; a flag is **not confirmed fraud**. Being inside a P95 band does not establish an error or clear a customer.
3. Use the deterministic evidence tools in `dashboard/ai_investigator.py` for the supported customer lookup. Optional provider narration is separate, can be wrong and is not validated by the authored deterministic benchmark.
4. Record a proposed review policy in **Decision & Value**. Specify capacity, an assumed review cost and an assumed recoverable share of historical exposure. The modeled net is an illustrative scenario, not realized savings or evidence that an individual refund was inappropriate.
5. Download the aggregate JSON decision record and, if needed, the synthetic customer queue CSV. Data is not saved to a server. The optional follow-up note is user-entered and unverified. Do not enter real personal or sensitive data.

Before any real operational action, an organization would need verified evidence, a defined review process, governed data, appropriate privacy controls and evaluation of customer harm. This demo does not automate account actions or establish financial losses prevented.
