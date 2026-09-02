from __future__ import annotations

from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .sms_registry_client import InfraiError, SmsRegistryClient


class OrderStage(str, Enum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    ORDER_UPDATE = "order_update"


class TemplateApproval(BaseModel):
    stage: OrderStage
    content: str = Field(min_length=1, max_length=480)
    template_vars: tuple[str, ...] = Field(min_length=1)

    @field_validator("template_vars")
    @classmethod
    def allow_only_operational_fields(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {
            "order_id",
            "checkout_status",
            "tracking_code",
            "amount",
            "order_status",
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"customer data fields are not allowed: {sorted(unknown)}")
        if len(values) != len(set(values)):
            raise ValueError("template_vars must be unique")
        return values


class ApprovalRequest(BaseModel):
    store_namespace: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,31}$")
    revision: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,15}$")
    signature_name: str = Field(min_length=2, max_length=32)
    signature_content: str = Field(min_length=2, max_length=64)
    templates: tuple[TemplateApproval, ...]

    @field_validator("templates")
    @classmethod
    def require_complete_order_lifecycle(
        cls, templates: tuple[TemplateApproval, ...]
    ) -> tuple[TemplateApproval, ...]:
        stages = [item.stage for item in templates]
        required = set(OrderStage)
        if set(stages) != required or len(stages) != len(required):
            raise ValueError("provide one template for every order stage")
        return templates


class RegisteredTemplate(BaseModel):
    stage: OrderStage
    name: str
    template_id: str
    template_vars: tuple[str, ...]


class ApprovalResult(BaseModel):
    signature_id: str
    templates: tuple[RegisteredTemplate, ...]
    state: str = "registered_for_review"


def register_approved_assets(
    request: ApprovalRequest, client: SmsRegistryClient
) -> ApprovalResult:
    batch = f"{request.store_namespace}-{request.revision}"
    signature = client.create_signature(
        name=request.signature_content,
        idempotency_key=f"{batch}:signature",
    )
    signature_id = str(signature["id"])

    registered: list[RegisteredTemplate] = []
    try:
        for template in request.templates:
            name = f"{batch}-{template.stage.value}"
            result = client.create_template(
                name=name,
                body=template.content,
                idempotency_key=f"{batch}:template:{template.stage.value}",
            )
            registered.append(
                RegisteredTemplate(
                    stage=template.stage,
                    name=name,
                    template_id=str(result["id"]),
                    template_vars=template.template_vars,
                )
            )
    except Exception:
        for item in reversed(registered):
            client.delete_template(item.template_id)
        client.delete_signature(signature_id)
        raise
    return ApprovalResult(signature_id=signature_id, templates=tuple(registered))


app = FastAPI(title="Order SMS approval registry")


@app.post("/sms-assets/register", response_model=ApprovalResult)
def register(request: ApprovalRequest) -> ApprovalResult:
    try:
        return register_approved_assets(request, SmsRegistryClient.from_env())
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=error.detail) from error
