import json
from email.message import Message
from typing import Any

from aegis.readonly_job_metadata import request_readonly_job_metadata


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


def test_job_metadata_retains_template_reference_and_omits_trigger_identity() -> None:
    seen: list[object] = []

    def opener(request: object, *, timeout: float) -> _Response:
        seen.append(request)
        assert request.full_url.endswith("/vj_mt1pakyc14nagbhvo5")  # type: ignore[attr-defined]
        assert timeout == 10.0
        return _Response({"id": "vj_mt1pakyc14nagbhvo5", "collector": "c_mt09pib13nxqz1coi", "template": "t_example.1", "status": "done", "inputs": 1, "lines": 1, "fails": 0, "pages": 1, "success": 1, "created": "2026-08-21T04:34:00Z", "started": "2026-08-21T04:34:01Z", "finished": "2026-08-21T04:34:30Z", "job_time": 7145, "queue_time": 0, "trigger": "person@example.test"})

    result = request_readonly_job_metadata("secret-token", job_id="vj_mt1pakyc14nagbhvo5", opener=opener)

    assert result.success is True
    assert result.collector_id == "c_mt09pib13nxqz1coi"
    assert result.template_reference == "t_example.1"
    assert "person@example.test" not in str(result.to_safe_dict())
    assert "secret-token" not in str(result.to_safe_dict())
    assert result.retry_count == 0
    assert len(seen) == 1


def test_job_metadata_rejects_malformed_provider_response_without_retry() -> None:
    result = request_readonly_job_metadata("do-not-echo-this-token", job_id="vj_example", opener=lambda *_args, **_kwargs: _Response([]))

    assert result.success is False
    assert result.error_class == "MALFORMED_PROVIDER_RESPONSE"
    assert result.retry_count == 0
    assert "do-not-echo-this-token" not in str(result.to_safe_dict())
