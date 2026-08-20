from __future__ import annotations

import json
import socket
from urllib.error import HTTPError

import pytest

from aegis.one_shot_approval import approval_endpoint, approve_pending_self_healing_once


COLLECTOR = "c_mt09pib13nxqz1coi"
CORRELATION = "mission040-approval-c_mt09pib13nxqz1coi"


class FakeHeaders(dict):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "application/octet-stream").split(";", 1)[0]


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"", content_type: str = "application/json") -> None:
        self.status = status
        self.body = body
        self.headers = FakeHeaders({"Content-Type": content_type})

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self.body


def test_approval_uses_one_documented_post_and_discards_raw_response() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(200, b'{"secret_preview":"must-not-retain"}')

    result = approve_pending_self_healing_once("token-not-retained", collector_id=COLLECTOR, correlation_id=CORRELATION, timeout_seconds=2, opener=opener)

    assert result.success is True
    assert result.http_status == 200
    assert result.resulting_provider_state == "RESUME_ACCEPTED"
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert "token-not-retained" not in repr(result.to_safe_dict())
    assert "must-not-retain" not in repr(result.to_safe_dict())
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == approval_endpoint(COLLECTOR)
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {"message": True}
    assert timeout == 2


@pytest.mark.parametrize(("status", "error_class"), [(401, "HTTP_401"), (403, "HTTP_403_SCOPE"), (404, "HTTP_404"), (409, "HTTP_409")])
def test_http_error_is_recorded_once_without_retry(status: int, error_class: str) -> None:
    calls = 0

    def opener(request, *, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, status, "failure", hdrs=FakeHeaders({"Content-Type": "application/json"}), fp=None)

    result = approve_pending_self_healing_once("token-not-retained", collector_id=COLLECTOR, correlation_id=CORRELATION, opener=opener)

    assert result.success is False
    assert result.attempted is True
    assert result.error_class == error_class
    assert result.retry_count == 0
    assert calls == 1


def test_timeout_has_no_second_request() -> None:
    calls = 0

    def opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        raise socket.timeout()

    result = approve_pending_self_healing_once("token-not-retained", collector_id=COLLECTOR, correlation_id=CORRELATION, opener=opener)

    assert result.error_class == "APPROVAL_TIMEOUT"
    assert result.retry_count == 0
    assert calls == 1


def test_invalid_input_fails_before_request() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        approve_pending_self_healing_once("", collector_id=COLLECTOR, correlation_id=CORRELATION, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="collector ID"):
        approve_pending_self_healing_once("token-not-retained", collector_id="invalid", correlation_id=CORRELATION, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="Mission 040"):
        approve_pending_self_healing_once("token-not-retained", collector_id=COLLECTOR, correlation_id="bad", opener=lambda *_args, **_kwargs: None)
