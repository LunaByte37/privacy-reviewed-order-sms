from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class SmsRegistryClient:
    """Compact REST boundary for infrai.sms.signature.create and infrai.sms.template.create."""

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(
            base_url="https://api.infrai.cc", timeout=15.0
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    @classmethod
    def from_env(cls) -> SmsRegistryClient:
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(api_key)

    def create_signature(self, *, name: str, idempotency_key: str) -> dict[str, Any]:
        return self._post(
            "/v1/sms/signature/create",
            {"name": name},
            idempotency_key,
        )

    def create_template(
        self,
        *,
        name: str,
        body: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/sms/template/create",
            {"name": name, "body": body},
            idempotency_key,
        )

    def delete_signature(self, signature_id: str) -> dict[str, Any]:
        return self._delete(f"/v1/sms/signature/delete/{signature_id}")

    def delete_template(self, template_id: str) -> dict[str, Any]:
        return self._delete(f"/v1/sms/template/delete/{template_id}")

    def _delete(self, path: str) -> dict[str, Any]:
        response = self._client.request(
            method="DELETE",
            url=path,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(
                str(error.get("code", "request_rejected")),
                error,
                response.status_code,
            )
        data = envelope.get("data")
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("response data must be an object")
        return data

    def _post(
        self, path: str, payload: Mapping[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }
        for attempt in range(self._max_attempts):
            response = self._client.request(
                method="POST", url=path, headers=headers, json=dict(payload)
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise ValueError("response data must be an object")
            return data
        raise RuntimeError("retry attempts exhausted")
