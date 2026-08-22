"""Raw-first, fail-closed transport for one documented Scraper Studio batch run.

This module deliberately owns only collection triggering and result retrieval.
It does not heal, approve, publish, commit, roll back, or convert a collection
result into a repaired candidate.  The provider response remains untrusted
until callers route its completed rows through the existing observation and
detection boundaries.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from .models import CollectionHandle, CollectionMode, CollectionResult, CollectionState, ProviderProvenance
from .readonly_collectors import _content_type


BRIGHT_DATA_API_TOKEN_ENV = "BRIGHT_DATA_API_TOKEN"
TRIGGER_ENDPOINT = "https://api.brightdata.com/dca/trigger"
DATASET_ENDPOINT = "https://api.brightdata.com/dca/dataset"
JOB_LOG_ENDPOINT = "https://api.brightdata.com/dca/log"
DEFAULT_TRIGGER_TIMEOUT_SECONDS = 20.0
DEFAULT_POLL_TIMEOUT_SECONDS = 15.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_POLL_ATTEMPTS = 18


class TriggerState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class RawProviderResponse:
    """One provider response retained only for controlled raw-evidence storage."""

    stage: str
    http_status: int | None
    content_type: str | None
    body: bytes | None = field(repr=False, compare=False)

    @property
    def sha256(self) -> str | None:
        return hashlib.sha256(self.body).hexdigest() if self.body is not None else None

    def safe_metadata(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "sha256": self.sha256,
            "bytes": len(self.body) if self.body is not None else None,
        }


@dataclass(frozen=True)
class BatchTriggerResult:
    """One trigger plus bounded result polling; all data remains provider-untrusted."""

    collector_id: str
    correlation_id: str
    target_url: str
    state: TriggerState
    error_class: str | None
    error_message: str | None
    trigger_attempts: int
    poll_attempts: int
    elapsed_ms: int
    collection_id: str | None
    provider_status: str | None
    rows: tuple[dict[str, Any], ...]
    raw_responses: tuple[RawProviderResponse, ...] = field(repr=False, compare=False)

    @property
    def success(self) -> bool:
        return self.state is TriggerState.COMPLETED

    @property
    def provider_operation_ids(self) -> Mapping[str, str]:
        return {"provider_collection_id": self.collection_id} if self.collection_id else {}

    def to_safe_metadata(self) -> dict[str, object]:
        return {
            "schema_version": "bright-data-batch-trigger-v1",
            "collector_id": self.collector_id,
            "correlation_id": self.correlation_id,
            "target_url_sha256": hashlib.sha256(self.target_url.encode("utf-8")).hexdigest(),
            "state": self.state.value,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "trigger_attempts": self.trigger_attempts,
            "poll_attempts": self.poll_attempts,
            "elapsed_ms": self.elapsed_ms,
            "provider_collection_id": self.collection_id,
            "provider_status": self.provider_status,
            "provider_identifier_state": "PRESENT" if self.collection_id else "NOT_RETURNED_BY_PROVIDER",
            "row_count": len(self.rows) if self.success else None,
            "output_schema": sorted({key for row in self.rows for key in row}),
            "raw_responses": [response.safe_metadata() for response in self.raw_responses],
            "retry_count": 0,
            "key_exposed": False,
        }

    def preserve_raw_responses(self, directory: Path) -> tuple[dict[str, object], ...]:
        """Persist every received body once, before any downstream normalisation."""

        directory.mkdir(parents=True, exist_ok=True)
        artifacts: list[dict[str, object]] = []
        for index, response in enumerate(self.raw_responses, start=1):
            if response.body is None:
                continue
            filename = f"{index:03d}_{response.stage.replace('/', '_')}.bin"
            path = directory / filename
            with path.open("xb") as handle:
                handle.write(response.body)
            artifacts.append({"path": str(path), **response.safe_metadata()})
        return tuple(artifacts)

    def to_collection_result(self, *, evidence_refs: Sequence[str]) -> CollectionResult:
        """Normalize completed provider rows into the existing untrusted collection model."""

        if not self.success:
            raise ValueError("only a completed trigger result can become a CollectionResult")
        handle = CollectionHandle(
            collection_id=f"collection_{uuid4().hex}",
            collector_id=self.collector_id,
            correlation_id=self.correlation_id,
            status=CollectionState.COMPLETED,
            mode=CollectionMode.BATCH,
            provider_operation_ids=self.provider_operation_ids,
            provider_status=self.provider_status,
            latency_ms=self.elapsed_ms,
            output_schema=tuple(sorted({key for row in self.rows for key in row})),
            provider_provenance=ProviderProvenance.BRIGHT_DATA,
            evidence_refs=tuple(evidence_refs),
        )
        return CollectionResult(handle=handle, output=self.rows)


@dataclass(frozen=True)
class KnownCollectionStatus:
    """Read-only status for an already-known provider collection ID."""

    collection_id: str
    state: str
    http_status: int | None
    provider_status: str | None
    error_class: str | None
    raw_response: RawProviderResponse | None = field(repr=False, compare=False)

    @property
    def is_active(self) -> bool:
        return self.state == "ACTIVE"


UrlOpener = Callable[..., Any]
Sleeper = Callable[[float], None]
RawResponseSink = Callable[[RawProviderResponse], None]


def _valid_collector_id(value: str) -> str:
    if not value.startswith("c_") or not value.replace("_", "").isalnum():
        raise ValueError("collector_id must be a safe Bright Data collector ID")
    return value


def _safe_target_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("target_url must be a credential-free absolute HTTP(S) URL")
    return value


def _safe_collection_id(value: str) -> str:
    if not value.startswith("j_") or not value.replace("_", "").isalnum():
        raise ValueError("collection_id must be a safe Bright Data collection ID")
    return value


def _error_body(error: HTTPError) -> bytes | None:
    try:
        raw = error.read()
    except (AttributeError, OSError, ValueError):
        return None
    return raw if isinstance(raw, bytes) else None


def _read(request: Request, *, timeout: float, opener: UrlOpener, stage: str) -> RawProviderResponse:
    with opener(request, timeout=timeout) as response:
        return RawProviderResponse(
            stage=stage,
            http_status=int(response.getcode()),
            content_type=_content_type(response),
            body=response.read(),
        )


def _record_raw(responses: list[RawProviderResponse], response: RawProviderResponse, sink: RawResponseSink | None) -> None:
    """Record and optionally persist a provider response before parsing it."""

    responses.append(response)
    if sink is not None:
        sink(response)


def _decode_object(response: RawProviderResponse) -> Mapping[str, object] | None:
    if response.body is None:
        return None
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _decode_rows(response: RawProviderResponse) -> tuple[dict[str, Any], ...] | None:
    if response.body is None:
        return None
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list) or not all(isinstance(row, Mapping) for row in payload):
        return None
    return tuple(dict(row) for row in payload)


def _result(
    *,
    started: float,
    collector_id: str,
    correlation_id: str,
    target_url: str,
    state: TriggerState,
    error_class: str | None,
    error_message: str | None,
    trigger_attempts: int,
    poll_attempts: int,
    collection_id: str | None,
    provider_status: str | None,
    rows: tuple[dict[str, Any], ...] = (),
    raw_responses: Sequence[RawProviderResponse] = (),
) -> BatchTriggerResult:
    return BatchTriggerResult(
        collector_id=collector_id,
        correlation_id=correlation_id,
        target_url=target_url,
        state=state,
        error_class=error_class,
        error_message=error_message,
        trigger_attempts=trigger_attempts,
        poll_attempts=poll_attempts,
        elapsed_ms=round((perf_counter() - started) * 1000),
        collection_id=collection_id,
        provider_status=provider_status,
        rows=rows,
        raw_responses=tuple(raw_responses),
    )


def _poll_existing_batch_collection(
    api_token: str,
    *,
    collector_id: str,
    target_url: str,
    correlation_id: str,
    collection_id: str,
    started: float,
    trigger_attempts: int,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
    max_poll_attempts: int,
    opener: UrlOpener,
    sleeper: Sleeper,
    raw_responses: list[RawProviderResponse],
    raw_response_sink: RawResponseSink | None,
) -> BatchTriggerResult:
    """Poll one known collection without creating another provider collection."""

    dataset_url = f"{DATASET_ENDPOINT}?{urlencode({'id': collection_id})}"
    for poll_attempt in range(1, max_poll_attempts + 1):
        if poll_attempt > 1:
            sleeper(poll_interval_seconds)
        poll_request = Request(
            dataset_url,
            headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json", "X-Aegis-Correlation-Id": correlation_id},
            method="GET",
        )
        stage = f"dataset_poll_{poll_attempt:03d}"
        try:
            poll = _read(poll_request, timeout=poll_timeout_seconds, opener=opener, stage=stage)
            _record_raw(raw_responses, poll, raw_response_sink)
        except HTTPError as error:
            _record_raw(raw_responses, RawProviderResponse(stage, error.code, _content_type(error) if error.headers else None, _error_body(error)), raw_response_sink)
            return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", error_message="dataset poll rejected", trigger_attempts=trigger_attempts, poll_attempts=poll_attempt, collection_id=collection_id, provider_status=None, raw_responses=raw_responses)
        except (TimeoutError, socket.timeout):
            return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.TIMED_OUT, error_class="POLL_TIMEOUT", error_message="dataset poll exceeded bounded timeout", trigger_attempts=trigger_attempts, poll_attempts=poll_attempt, collection_id=collection_id, provider_status=None, raw_responses=raw_responses)
        except URLError as error:
            return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="NETWORK_ERROR", error_message=type(error.reason).__name__, trigger_attempts=trigger_attempts, poll_attempts=poll_attempt, collection_id=collection_id, provider_status=None, raw_responses=raw_responses)

        rows = _decode_rows(poll)
        if poll.http_status == 200 and rows is not None:
            return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.COMPLETED, error_class=None, error_message=None, trigger_attempts=trigger_attempts, poll_attempts=poll_attempt, collection_id=collection_id, provider_status="COMPLETED", rows=rows, raw_responses=raw_responses)
        status_payload = _decode_object(poll)
        status = str(status_payload.get("status", "")).lower() if status_payload else ""
        if poll.http_status in {200, 202} and isinstance(status_payload, Mapping) and status in {"building", "running", "queued", "collecting"}:
            continue
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="MALFORMED_DATASET_RESPONSE" if poll.http_status in {200, 202} else f"HTTP_{poll.http_status}", error_message="dataset response was neither a documented pending status nor a JSON row array", trigger_attempts=trigger_attempts, poll_attempts=poll_attempt, collection_id=collection_id, provider_status=status or None, raw_responses=raw_responses)

    return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.TIMED_OUT, error_class="POLL_WINDOW_EXHAUSTED", error_message="dataset did not become ready before the bounded poll window elapsed", trigger_attempts=trigger_attempts, poll_attempts=max_poll_attempts, collection_id=collection_id, provider_status="PENDING", raw_responses=raw_responses)


def trigger_batch_collection_once(
    api_token: str,
    *,
    collector_id: str,
    target_url: str,
    correlation_id: str,
    trigger_timeout_seconds: float = DEFAULT_TRIGGER_TIMEOUT_SECONDS,
    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_poll_attempts: int = DEFAULT_MAX_POLL_ATTEMPTS,
    opener: UrlOpener = urlopen,
    sleeper: Sleeper = time.sleep,
    raw_response_sink: RawResponseSink | None = None,
) -> BatchTriggerResult:
    """Run one documented batch trigger and bounded dataset polling sequence.

    There is exactly one trigger request. Dataset reads are status polls rather
    than trigger retries; a transport or parse failure stops immediately.
    """

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    collector_id = _valid_collector_id(collector_id)
    target_url = _safe_target_url(target_url)
    if not correlation_id.strip():
        raise ValueError("correlation_id is required")
    if trigger_timeout_seconds <= 0 or poll_timeout_seconds <= 0 or poll_interval_seconds < 0 or max_poll_attempts <= 0:
        raise ValueError("timeouts, poll interval, and max_poll_attempts must be positive")

    started = perf_counter()
    raw_responses: list[RawProviderResponse] = []
    trigger_url = f"{TRIGGER_ENDPOINT}?{urlencode({'collector': collector_id})}"
    request = Request(
        trigger_url,
        data=json.dumps([{"url": target_url}]).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "aegis-collector-trigger/1",
            "X-Aegis-Correlation-Id": correlation_id,
        },
        method="POST",
    )
    try:
        trigger = _read(request, timeout=trigger_timeout_seconds, opener=opener, stage="trigger")
        _record_raw(raw_responses, trigger, raw_response_sink)
    except HTTPError as error:
        raw = _error_body(error)
        _record_raw(raw_responses, RawProviderResponse("trigger", error.code, _content_type(error) if error.headers else None, raw), raw_response_sink)
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", error_message="trigger request rejected", trigger_attempts=1, poll_attempts=0, collection_id=None, provider_status=None, raw_responses=raw_responses)
    except (TimeoutError, socket.timeout):
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.TIMED_OUT, error_class="TRIGGER_TIMEOUT", error_message="trigger request exceeded bounded timeout", trigger_attempts=1, poll_attempts=0, collection_id=None, provider_status=None, raw_responses=raw_responses)
    except URLError as error:
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="NETWORK_ERROR", error_message=type(error.reason).__name__, trigger_attempts=1, poll_attempts=0, collection_id=None, provider_status=None, raw_responses=raw_responses)

    payload = _decode_object(trigger)
    if trigger.http_status != 200 or payload is None or not isinstance(payload.get("collection_id"), str):
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="MALFORMED_TRIGGER_RESPONSE" if trigger.http_status == 200 else f"HTTP_{trigger.http_status}", error_message="trigger response did not contain a provider collection_id", trigger_attempts=1, poll_attempts=0, collection_id=None, provider_status=None, raw_responses=raw_responses)
    try:
        collection_id = _safe_collection_id(str(payload["collection_id"]))
    except ValueError:
        return _result(started=started, collector_id=collector_id, correlation_id=correlation_id, target_url=target_url, state=TriggerState.FAILED, error_class="MALFORMED_TRIGGER_RESPONSE", error_message="trigger returned an unsafe collection_id", trigger_attempts=1, poll_attempts=0, collection_id=None, provider_status=None, raw_responses=raw_responses)

    return _poll_existing_batch_collection(
        api_token,
        collector_id=collector_id,
        target_url=target_url,
        correlation_id=correlation_id,
        collection_id=collection_id,
        started=started,
        trigger_attempts=1,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
        opener=opener,
        sleeper=sleeper,
        raw_responses=raw_responses,
        raw_response_sink=raw_response_sink,
    )


def resume_batch_collection_once(
    api_token: str,
    *,
    collector_id: str,
    target_url: str,
    correlation_id: str,
    collection_id: str,
    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_poll_attempts: int = DEFAULT_MAX_POLL_ATTEMPTS,
    opener: UrlOpener = urlopen,
    sleeper: Sleeper = time.sleep,
    raw_response_sink: RawResponseSink | None = None,
) -> BatchTriggerResult:
    """Resume bounded output retrieval for a known collection without a trigger request."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    collector_id = _valid_collector_id(collector_id)
    target_url = _safe_target_url(target_url)
    collection_id = _safe_collection_id(collection_id)
    if not correlation_id.strip():
        raise ValueError("correlation_id is required")
    if poll_timeout_seconds <= 0 or poll_interval_seconds < 0 or max_poll_attempts <= 0:
        raise ValueError("poll timeout, interval, and max_poll_attempts must be positive")
    return _poll_existing_batch_collection(
        api_token,
        collector_id=collector_id,
        target_url=target_url,
        correlation_id=correlation_id,
        collection_id=collection_id,
        started=perf_counter(),
        trigger_attempts=0,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
        opener=opener,
        sleeper=sleeper,
        raw_responses=[],
        raw_response_sink=raw_response_sink,
    )


def inspect_known_collection_once(
    api_token: str,
    *,
    collection_id: str,
    timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> KnownCollectionStatus:
    """Read one known job status; it cannot discover an unknown collector run."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    collection_id = _safe_collection_id(collection_id)
    request = Request(f"{JOB_LOG_ENDPOINT}/{collection_id}", headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"}, method="GET")
    try:
        response = _read(request, timeout=timeout_seconds, opener=opener, stage="job_status")
    except HTTPError as error:
        raw = RawProviderResponse("job_status", error.code, _content_type(error) if error.headers else None, _error_body(error))
        return KnownCollectionStatus(collection_id, "UNKNOWN", error.code, None, "HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", raw)
    except (TimeoutError, socket.timeout):
        return KnownCollectionStatus(collection_id, "UNKNOWN", None, None, "STATUS_TIMEOUT", None)
    except URLError as error:
        return KnownCollectionStatus(collection_id, "UNKNOWN", None, None, "NETWORK_ERROR", None)
    payload = _decode_object(response)
    provider_status = str(payload.get("status", "")).lower() if payload else ""
    if response.http_status != 200 or not provider_status:
        return KnownCollectionStatus(collection_id, "UNKNOWN", response.http_status, None, "MALFORMED_STATUS_RESPONSE", response)
    state = "ACTIVE" if provider_status in {"building", "running", "queued"} else "TERMINAL" if provider_status in {"done", "failed", "cancelled"} else "UNKNOWN"
    return KnownCollectionStatus(collection_id, state, response.http_status, provider_status, None if state != "UNKNOWN" else "UNKNOWN_PROVIDER_STATUS", response)
