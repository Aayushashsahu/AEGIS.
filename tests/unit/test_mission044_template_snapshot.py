from __future__ import annotations

import json
from email.message import Message
from typing import Any

from aegis.readonly_template_snapshot import request_readonly_template_snapshot


class _Response:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self._status = status
        self.headers = Message()
        self.headers.add_header("Content-Type", "application/json")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def getcode(self) -> int:
        return self._status

    def read(self) -> bytes:
        return self._payload


def test_snapshot_retains_only_documented_safe_schema_metadata() -> None:
    seen: list[object] = []

    def opener(request: object, *, timeout: float) -> _Response:
        seen.append(request)
        assert timeout == 10.0
        return _Response({"data": [{"id": "c_mt09pib13nxqz1coi", "name": "aegis-mission-033-v1", "active": True, "last_run": "2026-08-20T00:00:00Z", "deliver": {"type": "api_pull"}, "output_schema": {"type": "object", "fields": {"title": {"type": "text", "active": True}}}}]})

    result = request_readonly_template_snapshot("secret-token", collector_id="c_mt09pib13nxqz1coi", collector_name="aegis-mission-033-v1", opener=opener)
    assert result.success is True
    assert result.collector_found == "YES"
    assert result.output_schema == {"type": "object", "fields": {"title": {"type": "text", "active": True}}}
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert len(seen) == 1


def test_snapshot_marks_absent_collector_without_retry() -> None:
    result = request_readonly_template_snapshot("secret-token", collector_id="c_mt09pib13nxqz1coi", collector_name="aegis-mission-033-v1", opener=lambda *_args, **_kwargs: _Response({"data": []}))
    assert result.success is True
    assert result.collector_found == "NO"
    assert result.output_schema is None
    assert result.retry_count == 0


def test_snapshot_rejects_malformed_provider_response_without_secret_echo() -> None:
    result = request_readonly_template_snapshot("do-not-echo-this-token", collector_id="c_mt09pib13nxqz1coi", collector_name="aegis-mission-033-v1", opener=lambda *_args, **_kwargs: _Response({"unexpected": []}))
    assert result.error_class == "MALFORMED_PROVIDER_RESPONSE"
    assert "do-not-echo-this-token" not in str(result.to_safe_dict())
