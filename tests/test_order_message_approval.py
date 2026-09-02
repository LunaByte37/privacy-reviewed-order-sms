from typing import Any

import pytest
from pydantic import ValidationError

from order_sms.order_message_approval import ApprovalRequest, register_approved_assets


def approval_payload() -> dict[str, Any]:
    return {
        "store_namespace": "clinic-store",
        "revision": "r7",
        "signature_name": "Clinic Store",
        "signature_content": "Clinic Store",
        "templates": [
            {"stage": "checkout", "content": "{{order_id}} {{checkout_status}}", "template_vars": ["order_id", "checkout_status"]},
            {"stage": "fulfillment", "content": "{{order_id}} {{tracking_code}}", "template_vars": ["order_id", "tracking_code"]},
            {"stage": "receipt", "content": "{{order_id}} {{amount}}", "template_vars": ["order_id", "amount"]},
            {"stage": "order_update", "content": "{{order_id}} {{order_status}}", "template_vars": ["order_id", "order_status"]},
        ],
    }


class RecordingClient:
    def __init__(self) -> None:
        self.signature: dict[str, Any] = {}
        self.templates: list[dict[str, Any]] = []
        self.deleted: list[tuple[str, str]] = []

    def create_signature(self, *, name: str, idempotency_key: str) -> dict[str, Any]:
        self.signature = {"name": name, "idempotency_key": idempotency_key}
        return {"id": "sig-approved-7"}

    def create_template(
        self, *, name: str, body: str, idempotency_key: str
    ) -> dict[str, Any]:
        self.templates.append(
            {"name": name, "body": body, "idempotency_key": idempotency_key}
        )
        return {"id": f"tpl-{len(self.templates)}"}

    def delete_signature(self, signature_id: str) -> dict[str, Any]:
        self.deleted.append(("signature", signature_id))
        return {}

    def delete_template(self, template_id: str) -> dict[str, Any]:
        self.deleted.append(("template", template_id))
        return {}


def test_create_requests_follow_live_contract() -> None:
    client = RecordingClient()
    result = register_approved_assets(ApprovalRequest.model_validate(approval_payload()), client)  # type: ignore[arg-type]

    assert result.state == "registered_for_review"
    assert [item.stage.value for item in result.templates] == [
        "checkout", "fulfillment", "receipt", "order_update"
    ]
    assert set(client.signature) == {"name", "idempotency_key"}
    assert client.signature["name"] == "Clinic Store"
    assert all(set(item) == {"name", "body", "idempotency_key"} for item in client.templates)
    assert client.templates[1]["name"] == "clinic-store-r7-fulfillment"


def test_partial_batch_is_deleted_when_template_creation_fails() -> None:
    class FailingClient(RecordingClient):
        def create_template(
            self, *, name: str, body: str, idempotency_key: str
        ) -> dict[str, Any]:
            if len(self.templates) == 2:
                raise RuntimeError("template rejected")
            return super().create_template(
                name=name, body=body, idempotency_key=idempotency_key
            )

    client = FailingClient()
    with pytest.raises(RuntimeError, match="template rejected"):
        register_approved_assets(ApprovalRequest.model_validate(approval_payload()), client)  # type: ignore[arg-type]

    assert client.deleted == [
        ("template", "tpl-2"),
        ("template", "tpl-1"),
        ("signature", "sig-approved-7"),
    ]


def test_customer_identity_cannot_enter_template_variables() -> None:
    payload = approval_payload()
    payload["templates"][0]["template_vars"].append("patient_name")

    with pytest.raises(ValidationError, match="customer data fields are not allowed"):
        ApprovalRequest.model_validate(payload)
