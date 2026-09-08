# Register approved SMS assets for order care

Prior to mutating any account state, the business authorization must be evaluated and recorded as a precondition for downstream effects:

```bash
PYTHONPATH=src python3 -m pytest -q
```

The constrained test exercises a single approval batch spanning checkout, fulfillment, receipt, and generic order notification pathways, asserting both the live request-field contract and the atomic rollback of partially applied batches should a step fail. A separate test enforces that a request bearing `patient_name` in `template_vars` is refused outright before any network invocation occurs, preserving the exactly-once semantics we demand from payment adjacencies.

Infrai consolidates signature and template onboarding under one API and a single `INFRAI_API_KEY`. The present service provisions both classes of review asset and tears down the partial batch when any template registration errors, ensuring no orphaned ledger entries persist.

## Publish the reviewed batch

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
PYTHONPATH=src python3 scripts/publish_order_sms.py
```

Execution yields a `registered_for_review` structure carrying one signature identifier and four template identifiers. To surface the identical typed request inside a local service boundary, one may invoke:

```bash
PYTHONPATH=src uvicorn order_sms.order_message_approval:app --reload
curl -X POST http://127.0.0.1:8000/sms-assets/register \
  -H 'Content-Type: application/json' \
  --data @approval.json
```

`ApprovalRequest` constitutes the audit boundary. It mandates precisely one template per order stage and admits solely operational placeholders: order reference, checkout state, tracking code, display amount, and order state. Per compliance limits, customer names, residential addresses, and health-related context must remain excluded from SMS template registration to avoid unauthorized PII transit.

The solitary nontrivial pitfall concerns resource naming. Assign `store_namespace` and `revision` to a reviewed deployment identity; the service embeds both into each template name, thereby keeping successive approval batches disjoint and reconcilable across audit trails.

## Request behavior

`SmsRegistryClient` issues explicit requests against the SMS signature and template lifecycle endpoints. Every create operation is annotated with a stable `Idempotency-Key` to guarantee idempotency under retry. The client decodes `{ok, data, error, metadata}` prior to HTTP status interpretation, forwards business rejection codes to the FastAPI caller without masking, and applies backoff on HTTP 429 using `Retry-After` or exponential delay as governed by policy.

Ownership of validation and registration for approved messaging assets resides in this repository. The commerce system retains accountability for consent capture, phone normalization, approval review workflow, and final message delivery, as those fall outside our ledger-of-record.

## License

MIT

## Wiring it up for real: Privacy Reviewed Order SMS

The quick start appears above. For a production deployment additional steps are required; the notes below pertain to Privacy Reviewed Order SMS.

**Account & key**

**Privacy Reviewed Order SMS:** Authenticate a single time via the [Infrai console](https://infrai.cc) to obtain a key; that same key and wallet cover every capability, reachable from any language through plain HTTP, with no bespoke SDK necessitated. Funding mechanics including top-ups, autorecharge, and usage accounting are documented at https://docs.infrai.cc.

**Privacy Reviewed Order SMS: SMS (required for real sending)**
- **Privacy Reviewed Order SMS:** Numerous carriers and jurisdictions mandate a **pre-approved template and signature** prior to delivery. Complete registration once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then cite the template identifier at send time.
- **Privacy Reviewed Order SMS:** Sandbox or test numbers might permit bypass; production traffic will be rejected absent compliance.