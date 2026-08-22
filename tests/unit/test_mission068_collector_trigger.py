from __future__ import annotations

import json
import socket
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError

import pytest

from aegis.collector_trigger import TriggerState, inspect_known_collection_once, resume_batch_collection_once, trigger_batch_collection_once
from aegis.models import Observation
from scripts.trigger_collector import ROOT, _result_evidence


COLLECTOR = "c_mt09pib13nxqz1coi"
TARGET = "https://example.test/product"
CORRELATION = "mission068-live-trigger-test"


class Headers(dict):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "application/octet-stream").split(";", 1)[0]


class Response:
    def __init__(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.status = status
        self.body = body
        self.headers = Headers({"Content-Type": content_type})

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self.body

    def close(self) -> None:
        return None


def test_documented_batch_trigger_polls_to_rows_and_preserves_only_real_collection_id(tmp_path) -> None:
    calls = []
    responses = iter((
        Response(200, b'{"collection_id":"j_real123"}'),
        Response(200, b'{"status":"building"}'),
        Response(200, b'[{"title":"Widget","price":{"value":599},"availability":"Available"}]'),
    ))

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return next(responses)

    persisted = []

    def raw_sink(response) -> None:
        path = tmp_path / f"{len(persisted) + 1:03d}_{response.stage}.bin"
        path.write_bytes(response.body)
        persisted.append(path)

    result = trigger_batch_collection_once(
        "token-not-retained",
        collector_id=COLLECTOR,
        target_url=TARGET,
        correlation_id=CORRELATION,
        opener=opener,
        sleeper=lambda _: None,
        raw_response_sink=raw_sink,
    )

    assert result.state is TriggerState.COMPLETED
    assert result.collection_id == "j_real123"
    assert result.provider_operation_ids == {"provider_collection_id": "j_real123"}
    assert result.trigger_attempts == 1
    assert result.poll_attempts == 2
    assert json.loads(calls[0][0].data.decode("utf-8")) == [{"url": TARGET}]
    assert calls[0][0].get_method() == "POST"
    assert all(request.get_method() == "GET" for request, _ in calls[1:])
    assert result.to_safe_metadata()["provider_identifier_state"] == "PRESENT"
    assert "token-not-retained" not in repr(result.to_safe_metadata())
    artifacts = result.preserve_raw_responses(tmp_path / "raw")
    assert len(artifacts) == 3
    assert (tmp_path / "raw" / "003_dataset_poll_002.bin").read_bytes().startswith(b"[")
    assert [path.name for path in persisted] == ["001_trigger.bin", "002_dataset_poll_001.bin", "003_dataset_poll_002.bin"]
    assert persisted[-1].read_bytes().startswith(b"[")
    collection = result.to_collection_result(evidence_refs=("evidence://raw/003",))
    observation = Observation.from_result(collection, {"target_url": TARGET})
    assert observation.provider_operation_ids == {"provider_collection_id": "j_real123"}
    assert observation.trust_status == "UNTRUSTED_UNTIL_VERIFIED"


def test_trigger_response_without_documented_id_fails_closed_and_keeps_raw_bytes(tmp_path) -> None:
    body = b'{"status":"accepted-but-no-id"}'
    result = trigger_batch_collection_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=lambda *_args, **_kwargs: Response(200, body), sleeper=lambda _: None)

    assert result.state is TriggerState.FAILED
    assert result.error_class == "MALFORMED_TRIGGER_RESPONSE"
    assert result.collection_id is None
    assert result.provider_operation_ids == {}
    assert result.to_safe_metadata()["provider_identifier_state"] == "NOT_RETURNED_BY_PROVIDER"
    artifacts = result.preserve_raw_responses(tmp_path / "raw")
    assert artifacts[0]["sha256"] == sha256(body).hexdigest()
    assert (tmp_path / "raw" / "001_trigger.bin").read_bytes() == body


def test_dataset_poll_window_exhaustion_does_not_issue_a_second_trigger() -> None:
    calls = []
    responses = iter((Response(200, b'{"collection_id":"j_pending123"}'), Response(200, b'{"status":"building"}'), Response(200, b'{"status":"running"}')))

    def opener(request, *, timeout):
        calls.append(request)
        return next(responses)

    result = trigger_batch_collection_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, max_poll_attempts=2, opener=opener, sleeper=lambda _: None)

    assert result.state is TriggerState.TIMED_OUT
    assert result.error_class == "POLL_WINDOW_EXHAUSTED"
    assert result.trigger_attempts == 1
    assert result.poll_attempts == 2
    assert sum(request.get_method() == "POST" for request in calls) == 1


def test_collecting_202_is_pending_and_known_collection_resume_never_triggers() -> None:
    responses = iter((
        Response(200, b'{"collection_id":"j_collecting123"}'),
        Response(202, b'{"status":"collecting"}'),
        Response(200, b'[{"input":{"url":"https://example.test/product"}}]'),
    ))
    calls = []

    def opener(request, *, timeout):
        calls.append(request)
        return next(responses)

    result = trigger_batch_collection_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener, sleeper=lambda _: None)
    assert result.success is True
    assert result.poll_attempts == 2

    resumed_calls = []
    resumed = resume_batch_collection_once(
        "token-not-retained",
        collector_id=COLLECTOR,
        target_url=TARGET,
        correlation_id=CORRELATION,
        collection_id="j_collecting123",
        opener=lambda request, *, timeout: (resumed_calls.append(request) or Response(200, b'[]')),
        sleeper=lambda _: None,
    )
    assert resumed.success is True
    assert resumed.trigger_attempts == 0
    assert resumed.collection_id == "j_collecting123"
    assert len(resumed_calls) == 1
    assert resumed_calls[0].get_method() == "GET"


@pytest.mark.parametrize(("status", "expected"), ((401, "HTTP_401"), (403, "HTTP_403_SCOPE"), (404, "HTTP_404")))
def test_trigger_http_error_stops_without_poll_or_retry(status: int, expected: str) -> None:
    calls = 0

    def opener(request, *, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, status, "failure", hdrs=Headers({"Content-Type": "application/json"}), fp=Response(status, b'{"error":"safe"}'))

    result = trigger_batch_collection_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener, sleeper=lambda _: None)
    assert result.error_class == expected
    assert result.trigger_attempts == 1
    assert result.poll_attempts == 0
    assert calls == 1


def test_known_job_status_detects_active_run_without_triggering() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append(request)
        return Response(200, b'{"status":"running"}')

    status = inspect_known_collection_once("token-not-retained", collection_id="j_active123", opener=opener)
    assert status.is_active is True
    assert status.provider_status == "running"
    assert len(calls) == 1
    assert calls[0].get_method() == "GET"


def test_transport_timeout_is_terminal_and_never_leaks_a_token() -> None:
    def opener(*_args, **_kwargs):
        raise socket.timeout()

    result = trigger_batch_collection_once("token-not-retained", collector_id=COLLECTOR, target_url=TARGET, correlation_id=CORRELATION, opener=opener, sleeper=lambda _: None)
    assert result.state is TriggerState.TIMED_OUT
    assert result.error_class == "TRIGGER_TIMEOUT"
    assert "token-not-retained" not in repr(result.to_safe_metadata())


def test_completed_trigger_persists_existing_observation_and_detection_events(tmp_path) -> None:
    responses = iter((
        Response(200, b'{"collection_id":"j_audit123"}'),
        Response(200, b'[{"input":{"url":"https://example.test/product"}}]'),
    ))
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    raw_dir = output_dir / "raw"

    def raw_sink(response) -> None:
        raw_dir.mkdir(exist_ok=True)
        (raw_dir / f"{response.stage}.bin").write_bytes(response.body)

    result = trigger_batch_collection_once(
        "token-not-retained",
        collector_id=COLLECTOR,
        target_url=TARGET,
        correlation_id=CORRELATION,
        opener=lambda _request, *, timeout: next(responses),
        sleeper=lambda _: None,
        raw_response_sink=raw_sink,
    )
    artifacts = tuple(
        {
            **artifact,
            "path": str(ROOT / "experiments" / "mission_068_real_collector_trigger" / "runs" / "fixture" / "raw" / Path(str(artifact["path"])).name),
        }
        for artifact in result.preserve_raw_responses(tmp_path / "artifact-copy")
    )
    evidence = _result_evidence(
        result=result,
        target_url=TARGET,
        correlation_id=CORRELATION,
        raw_artifacts=artifacts,
        output_dir=output_dir,
    )

    assert result.success is True
    assert (output_dir / "audit.sqlite").is_file()
    assert evidence["audit"]["observation_event_id"]
    assert evidence["audit"]["detection_event_id"]
    assert evidence["detection"]["detected"] is True
    assert evidence["verification"]["status"] == "NOT_APPLICABLE"
    assert evidence["commit"]["status"] == "BLOCKED"
