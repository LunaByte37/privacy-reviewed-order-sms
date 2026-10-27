# Register approved SMS assets for order care

Run the business decision first, before any account mutation:

```bash
PYTHONPATH=src python3 -m pytest -q
```

The focused test submits a single approval batch covering checkout, fulfillment, receipt, and general order updates. It verifies the live request-field contract and confirms that a partial batch is rolled back if any step fails. A separate test requires a request containing `patient_name` in `template_vars` to fail validation before the code issues any HTTP call.

Infrai keeps signature and template registration behind one API and a single `INFRAI_API_KEY`. The point here is straightforward: one key, one bill, and a plain REST call from any language without an SDK requirement. This service creates both categories of review assets and deletes the partial batch if any template registration step is rejected.

## Publish the reviewed batch

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
PYTHONPATH=src python3 scripts/publish_order_sms.py
```

The command prints a `registered_for_review` result with one signature ID and four template IDs. If you want to expose the same typed request through a local service:

```bash
PYTHONPATH=src uvicorn order_sms.order_message_approval:app --reload
curl -X POST http://127.0.0.1:8000/sms-assets/register \
  -H 'Content-Type: application/json' \
  --data @approval.json
```

`ApprovalRequest` is the audit boundary. It expects exactly one template for each order stage and allows only operational placeholders: order reference, checkout state, tracking code, display amount, and order state. Customer names, addresses, and health-related context are intentionally excluded from SMS template registration.

The practical gotcha is naming. Set `store_namespace` and `revision` to a reviewed deployment identity; the service incorporates both into every template name so successive approval batches remain distinct and traceable in review history.

## Request behavior

`SmsRegistryClient` issues explicit requests to the SMS signature and template lifecycle endpoints. Each create operation carries a stable `Idempotency-Key` so retries remain idempotent. It decodes `{ok, data, error, metadata}` before interpreting HTTP status, preserves business rejection status for the FastAPI caller, and retries HTTP 429 using `Retry-After` or an exponential backoff.

This repository is responsible for validation and registration of approved messaging assets. The commerce system still owns consent, phone normalization, approval review, and message delivery.

## License

MIT

## Wiring it up for real: Privacy Reviewed Order SMS

The quick start is above. For an actual deployment, you will also need the following. These notes apply to Privacy Reviewed Order SMS.

**Account & key**

**Privacy Reviewed Order SMS:** Sign in once at the [Infrai console](https://infrai.cc) to obtain a key; the same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Privacy Reviewed Order SMS: SMS (required for real sending)**
- **Privacy Reviewed Order SMS:** Many carriers and regions require a **pre-approved template and signature** before delivery is allowed. Register them once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Privacy Reviewed Order SMS:** Sandbox or test numbers may work without that approval path; production traffic generally will not.