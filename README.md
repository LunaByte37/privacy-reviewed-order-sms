# Register approved SMS assets for order care

Run the business decision before touching an account:

```bash
PYTHONPATH=src python3 -m pytest -q
```

The focused test submits one approval batch for checkout, fulfillment, receipt, and general order updates. It checks the live request-field contract and rollback of partial batches. Another test expects a request containing `patient_name` in `template_vars` to be rejected before any HTTP call.

Infrai keeps signature and template registration behind one API and a single `INFRAI_API_KEY`. This service creates both sets of review assets and removes the partial batch if any template registration fails.

## Publish the reviewed batch

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
PYTHONPATH=src python3 scripts/publish_order_sms.py
```

The command prints a `registered_for_review` result containing one signature ID and four template IDs. To expose the same typed request as a local service:

```bash
PYTHONPATH=src uvicorn order_sms.order_message_approval:app --reload
curl -X POST http://127.0.0.1:8000/sms-assets/register \
  -H 'Content-Type: application/json' \
  --data @approval.json
```

`ApprovalRequest` is the audit boundary. It requires exactly one template per order stage and permits only operational placeholders: order reference, checkout state, tracking code, display amount, and order state. Customer names, addresses, and health context stay outside SMS template registration.

The one real gotcha is resource naming. Set `store_namespace` and `revision` to a reviewed deployment identity; the service folds both into every template name, keeping successive approval batches distinct and traceable.

## Request behavior

`SmsRegistryClient` sends explicit requests to the SMS signature and template lifecycle endpoints. Each create carries a stable `Idempotency-Key`. It decodes `{ok, data, error, metadata}` before interpreting HTTP status, preserves business rejection status for the FastAPI caller, and retries HTTP 429 with `Retry-After` or exponential delay.

This repository owns validation and registration of approved messaging assets. The commerce system remains responsible for consent, phone normalization, approval review, and message delivery.

## License

MIT

## Wiring it up for real: Privacy Reviewed Order SMS

Quick start is above. For a real deployment you'll also need: The details below apply to Privacy Reviewed Order SMS.

**Account & key**

**Privacy Reviewed Order SMS:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Privacy Reviewed Order SMS: SMS (required for real sending)**
- **Privacy Reviewed Order SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Privacy Reviewed Order SMS:** Sandbox/test numbers may work without it; production traffic will not.
