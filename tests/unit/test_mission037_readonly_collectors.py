from __future__ import annotations

import socket
from urllib.error import HTTPError

import pytest

from aegis.readonly_collectors import BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT, request_readonly_collectors_list


CANONICAL = "c_mt09pib13nxqz1coi"


class FakeHeaders(dict):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "application/octet-stream").split(";", 1)[0]


class FakeResponse:
    def __init__(self, status: int, body: bytes, content_type: str = "application/json") -> None:
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


def test_collector_list_returns_only_permitted_safe_metadata_and_matches_canonical_id() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(200, b'{"total": 2, "data": [{"id": "c_other", "name": "hidden"}, {"id": "c_mt09pib13nxqz1coi", "name": "hidden"}]}')

    result = request_readonly_collectors_list("token-not-retained", canonical_collector_id=CANONICAL, timeout_seconds=2, opener=opener)

    assert result.success is True
    assert result.http_status == 200
    assert result.content_type == "application/json"
    assert result.collector_count == 2
    assert result.collector_ids == ("c_other", CANONICAL)
    assert result.canonical_collector_found == "YES"
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert "token-not-retained" not in repr(result.to_safe_dict())
    assert calls[0][0].full_url == BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT
    assert calls[0][1] == 2


def test_absent_canonical_collector_is_not_visible_after_one_successful_read() -> None:
    result = request_readonly_collectors_list(
        "token-not-retained",
        canonical_collector_id=CANONICAL,
        opener=lambda _request, *, timeout: FakeResponse(200, b'{"data": [{"id": "c_other"}]}'),
    )

    assert result.success is True
    assert result.canonical_collector_found == "NO"
    assert result.collector_count == 1
    assert result.retry_count == 0


@pytest.mark.parametrize(("status", "expected_error"), [(401, "HTTP_401"), (403, "HTTP_403_SCOPE")])
def test_authentication_and_scope_rejections_preserve_http_status(status: int, expected_error: str) -> None:
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, status, "forbidden", hdrs=FakeHeaders({"Content-Type": "application/json"}), fp=None)

    result = request_readonly_collectors_list("token-not-retained", canonical_collector_id=CANONICAL, opener=opener)

    assert result.success is False
    assert result.http_status == status
    assert result.error_class == expected_error
    assert result.canonical_collector_found == "UNKNOWN"
    assert result.retry_count == 0
    assert result.key_exposed is False


def test_timeout_and_malformed_response_fail_closed_without_retry() -> None:
    calls = 0

    def timeout_opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        raise socket.timeout()

    timeout_result = request_readonly_collectors_list("token-not-retained", canonical_collector_id=CANONICAL, opener=timeout_opener)
    malformed_result = request_readonly_collectors_list(
        "token-not-retained",
        canonical_collector_id=CANONICAL,
        opener=lambda _request, *, timeout: FakeResponse(200, b'{"data": [{"id": 4}]}'),
    )

    assert timeout_result.error_class == "COLLECTORS_LIST_TIMEOUT"
    assert timeout_result.retry_count == 0
    assert calls == 1
    assert malformed_result.error_class == "MALFORMED_PROVIDER_RESPONSE"
    assert malformed_result.collector_ids == ()


def test_invalid_input_fails_before_any_provider_request() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        request_readonly_collectors_list("", canonical_collector_id=CANONICAL, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="collector ID"):
        request_readonly_collectors_list("token-not-retained", canonical_collector_id="candidate_x", opener=lambda *_args, **_kwargs: None)
