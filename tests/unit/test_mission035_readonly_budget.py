from __future__ import annotations

import socket
from urllib.error import HTTPError, URLError

import pytest

from aegis.readonly_budget import BRIGHT_DATA_BUDGET_ENDPOINT, request_readonly_budget


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self.body


def test_success_is_preserved_without_account_payload_or_retry() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(200, b'{"balance": 12.5}')

    result = request_readonly_budget("agent-key-secret", timeout_seconds=2.5, opener=opener)

    assert result.success is True
    assert result.http_status == 200
    assert result.error_class is None
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert "balance" not in result.to_safe_dict()
    assert calls[0][0].full_url == BRIGHT_DATA_BUDGET_ENDPOINT
    assert calls[0][1] == 2.5


def test_http_timeout_is_bounded_and_redacted_without_retry() -> None:
    calls = 0

    def opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        assert timeout == 1
        raise socket.timeout("Authorization: Bearer agent-key-secret")

    result = request_readonly_budget("agent-key-secret", timeout_seconds=1, opener=opener)

    assert result.success is False
    assert result.error_class == "CLI_BUDGET_TIMEOUT"
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert result.detail is None
    assert calls == 1


def test_network_error_redacts_an_authorization_bearer_value() -> None:
    def opener(_request, *, timeout):
        raise URLError("Authorization: Bearer agent-key-secret")

    result = request_readonly_budget("agent-key-secret", timeout_seconds=1, opener=opener)

    assert result.success is False
    assert result.error_class == "NETWORK_ERROR"
    assert result.retry_count == 0
    assert "agent-key-secret" not in (result.detail or "")
    assert "[REDACTED]" in (result.detail or "")


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [(403, "HTTP_403_SCOPE"), (404, "HTTP_404")],
)
def test_http_statuses_remain_distinct_from_timeout(status: int, expected_error: str) -> None:
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, status, "error", hdrs=None, fp=None)

    result = request_readonly_budget("agent-key-secret", timeout_seconds=1, opener=opener)

    assert result.success is False
    assert result.http_status == status
    assert result.error_class == expected_error
    assert result.error_class != "CLI_BUDGET_TIMEOUT"
    assert result.retry_count == 0


@pytest.mark.parametrize("body", [b"not-json", b"[]"])
def test_malformed_provider_response_fails_safely(body: bytes) -> None:
    result = request_readonly_budget(
        "agent-key-secret",
        opener=lambda _request, *, timeout: FakeResponse(200, body),
    )

    assert result.success is False
    assert result.error_class == "MALFORMED_PROVIDER_RESPONSE"
    assert result.retry_count == 0
    assert result.key_exposed is False


def test_configuration_validation_never_accepts_empty_key_or_infinite_timeout() -> None:
    with pytest.raises(ValueError, match="non-empty API key"):
        request_readonly_budget("", opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="positive"):
        request_readonly_budget("agent-key-secret", timeout_seconds=0, opener=lambda *_args, **_kwargs: None)
