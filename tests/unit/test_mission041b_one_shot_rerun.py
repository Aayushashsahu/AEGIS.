from __future__ import annotations

import json
import socket
from hashlib import sha256
from urllib.error import HTTPError

import pytest

from aegis.one_shot_rerun import rerun_collector_once, rerun_endpoint


COLLECTOR = "c_mt09pib13nxqz1coi"
TARGET = "https://example.test/mission-033/target"
CORRELATION = "mission041b-rerun-c_mt09pib13nxqz1coi"


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


def test_sync_rerun_uses_exactly_one_documented_post_and_preserves_real_rows(tmp_path) -> None:
    calls = []
    body = b'[{"title":"Widget","price":{"currency":"USD","value":599},"availability":"Available"}]'

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(200, body)

    result = rerun_collector_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener)

    assert result.success is True
    assert result.http_status == 200
    assert result.provider_status == "COMPLETED"
    assert result.row_count == 1
    assert result.output_schema == {"availability": "str", "price": "dict", "title": "str"}
    assert result.retry_count == 0
    assert result.key_exposed is False
    assert result.to_evidence_dict()["rows"] == [
        {"title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"}
    ]
    assert "token-not-retained" not in repr(result.to_evidence_dict())
    assert result.raw_response_sha256 == sha256(body).hexdigest()
    raw_path = tmp_path / "response.json"
    assert result.preserve_raw_response(raw_path) == {
        "path": str(raw_path),
        "sha256": sha256(body).hexdigest(),
        "bytes": len(body),
    }
    assert raw_path.read_bytes() == body
    with pytest.raises(FileExistsError):
        result.preserve_raw_response(raw_path)
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == rerun_endpoint(COLLECTOR)
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {"url": TARGET}
    assert timeout == 55


def test_accepted_async_response_does_not_poll_or_claim_output() -> None:
    calls = 0

    def opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        return FakeResponse(202, b'{"response_id":"r_safe"}')

    result = rerun_collector_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener)

    assert result.success is False
    assert result.error_class == "RERUN_ASYNC_PENDING"
    assert result.response_id == "r_safe"
    assert result.rows == ()
    assert result.retry_count == 0
    assert calls == 1


@pytest.mark.parametrize(("status", "error_class"), [(401, "HTTP_401"), (403, "HTTP_403_SCOPE"), (404, "HTTP_404")])
def test_http_error_stops_after_one_attempt(status: int, error_class: str) -> None:
    calls = 0

    def opener(request, *, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, status, "failure", hdrs=FakeHeaders({"Content-Type": "application/json"}), fp=None)

    result = rerun_collector_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener)

    assert result.error_class == error_class
    assert result.retry_count == 0
    assert calls == 1


def test_timeout_and_invalid_input_fail_closed() -> None:
    calls = 0

    def timeout_opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        raise socket.timeout()

    result = rerun_collector_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=timeout_opener)
    assert result.error_class == "RERUN_TIMEOUT"
    assert calls == 1
    with pytest.raises(ValueError, match="HTTP"):
        rerun_collector_once("token-not-retained", collector_id=COLLECTOR, target_url="bad", correlation_id=CORRELATION, opener=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="between 25 and 50"):
        rerun_endpoint(COLLECTOR, wait_seconds=10)
