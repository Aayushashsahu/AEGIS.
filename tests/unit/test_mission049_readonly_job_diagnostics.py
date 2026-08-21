import json
from email.message import Message
from typing import Any
from urllib.parse import parse_qs, urlparse

from aegis.readonly_job_diagnostics import request_readonly_jobs_list


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


def test_jobs_list_retains_documented_safe_metadata_and_omits_trigger_identity() -> None:
    requests: list[object] = []

    def opener(request: object, *, timeout: float) -> _Response:
        requests.append(request)
        assert timeout == 10.0
        query = parse_qs(urlparse(request.full_url).query)  # type: ignore[attr-defined]
        assert query == {"collector": ["c_mt09pib13nxqz1coi"], "from_date": ["2026-08-21"], "to_date": ["2026-08-21"], "offset": ["0"], "limit": ["50"], "sort_asc": ["-1"]}
        return _Response({"total": 1, "data": [{"id": "j_example", "status": "done", "queued": "2026-08-21T04:34:00Z", "started": "2026-08-21T04:34:01Z", "finished": "2026-08-21T04:34:07Z", "inputs": 1, "page_loads": 1, "total_pages": 1, "failed_pages": 0, "data_lines": 1, "expired": "2026-08-28T00:00:00Z", "trigger": {"user": "person@example.test", "ip": "192.0.2.1"}}]})

    result = request_readonly_jobs_list("secret-token", collector_id="c_mt09pib13nxqz1coi", from_date="2026-08-21", to_date="2026-08-21", opener=opener)

    assert result.success is True
    assert result.total == 1
    assert result.jobs[0]["id"] == "j_example"
    assert "trigger" not in result.jobs[0]
    assert "person@example.test" not in str(result.to_safe_dict())
    assert "secret-token" not in str(result.to_safe_dict())
    assert result.retry_count == 0
    assert len(requests) == 1


def test_jobs_list_fails_closed_on_malformed_response_without_retry() -> None:
    result = request_readonly_jobs_list("do-not-echo-this-token", collector_id="c_mt09pib13nxqz1coi", from_date="2026-08-21", to_date="2026-08-21", opener=lambda *_args, **_kwargs: _Response({"unexpected": []}))

    assert result.success is False
    assert result.error_class == "MALFORMED_PROVIDER_RESPONSE"
    assert result.retry_count == 0
    assert "do-not-echo-this-token" not in str(result.to_safe_dict())
