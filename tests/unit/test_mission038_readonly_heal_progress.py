from __future__ import annotations

import socket
from urllib.error import HTTPError

import pytest

from aegis.readonly_heal_progress import heal_progress_endpoint, request_readonly_heal_progress


COLLECTOR = "c_mt09pib13nxqz1coi"
CANDIDATE = "candidate_m033_a0d9aa5a0d056720"


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


def test_progress_lookup_is_one_get_and_retains_only_safe_candidate_preview_metadata() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(200, b'{"status":"pending_answer","preview_result":[{"title":"not retained"}],"candidate_id":"candidate_m033_a0d9aa5a0d056720"}')

    result = request_readonly_heal_progress("token-not-retained", collector_id=COLLECTOR, candidate_id=CANDIDATE, timeout_seconds=2, opener=opener)

    assert result.success is True
    assert result.http_status == 200
    assert result.provider_status == "pending_answer"
    assert result.preview_present is True
    assert result.candidate_found == "YES"
    assert result.collector_match == "YES"
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert "token-not-retained" not in repr(result.to_safe_dict())
    assert "not retained" not in repr(result.to_safe_dict())
    assert calls[0][0].full_url == heal_progress_endpoint(COLLECTOR)
    assert calls[0][1] == 2


def test_successful_response_without_aeigis_candidate_identifier_reports_no_match() -> None:
    result = request_readonly_heal_progress(
        "token-not-retained",
        collector_id=COLLECTOR,
        candidate_id=CANDIDATE,
        opener=lambda _request, *, timeout: FakeResponse(200, b'{"status":"pending_answer"}'),
    )

    assert result.success is True
    assert result.candidate_found == "NO"
    assert result.preview_present is False
    assert result.retry_count == 0


@pytest.mark.parametrize(("status", "expected_error"), [(401, "HTTP_401"), (403, "HTTP_403_SCOPE"), (404, "HTTP_404")])
def test_http_failure_is_structured_without_a_retry(status: int, expected_error: str) -> None:
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, status, "error", hdrs=FakeHeaders({"Content-Type": "application/json"}), fp=None)

    result = request_readonly_heal_progress("token-not-retained", collector_id=COLLECTOR, candidate_id=CANDIDATE, opener=opener)

    assert result.success is False
    assert result.http_status == status
    assert result.error_class == expected_error
    assert result.candidate_found == "UNKNOWN"
    assert result.collector_match == "UNKNOWN"
    assert result.retry_count == 0


def test_timeout_and_malformed_response_fail_closed_without_provider_retry() -> None:
    calls = 0

    def timeout_opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        raise socket.timeout()

    timeout_result = request_readonly_heal_progress("token-not-retained", collector_id=COLLECTOR, candidate_id=CANDIDATE, opener=timeout_opener)
    malformed_result = request_readonly_heal_progress(
        "token-not-retained",
        collector_id=COLLECTOR,
        candidate_id=CANDIDATE,
        opener=lambda _request, *, timeout: FakeResponse(200, b"[]"),
    )

    assert timeout_result.error_class == "HEAL_PROGRESS_TIMEOUT"
    assert timeout_result.retry_count == 0
    assert calls == 1
    assert malformed_result.error_class == "MALFORMED_PROVIDER_RESPONSE"


def test_invalid_inputs_fail_before_request() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        request_readonly_heal_progress("", collector_id=COLLECTOR, candidate_id=CANDIDATE, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="collector ID"):
        request_readonly_heal_progress("token-not-retained", collector_id="j_bad", candidate_id=CANDIDATE, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="candidate ID"):
        request_readonly_heal_progress("token-not-retained", collector_id=COLLECTOR, candidate_id="c_bad", opener=lambda *_args, **_kwargs: None)
