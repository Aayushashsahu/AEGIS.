"""Bounded read-only Scraper Studio job-metadata diagnostic for Mission 049."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aegis.readonly_collectors import _content_type


BRIGHT_DATA_JOB_METADATA_ENDPOINT = "https://api.brightdata.com/dca/log"
DEFAULT_READONLY_JOB_METADATA_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ReadOnlyJobMetadataResult:
    """Safe metadata from one GET /dca/log/{job_id}; raw body and credentials are not retained."""

    operation: str
    endpoint: str
    job_id: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    collector_id: str | None
    template_reference: str | None
    status: str | None
    inputs: int | None
    lines: int | None
    fails: int | None
    pages: int | None
    success_count: int | None
    created: str | None
    started: str | None
    finished: str | None
    job_time_ms: int | None
    queue_time_ms: int | None
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpener = Callable[..., Any]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _result(
    *,
    started: float,
    endpoint: str,
    job_id: str,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    row: Mapping[str, Any] | None = None,
) -> ReadOnlyJobMetadataResult:
    return ReadOnlyJobMetadataResult(
        operation="job_metadata",
        endpoint=endpoint,
        job_id=job_id,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        collector_id=_text(row.get("collector")) if isinstance(row, Mapping) else None,
        template_reference=_text(row.get("template")) if isinstance(row, Mapping) else None,
        status=_text(row.get("status")) if isinstance(row, Mapping) else None,
        inputs=_number(row.get("inputs")) if isinstance(row, Mapping) else None,
        lines=_number(row.get("lines")) if isinstance(row, Mapping) else None,
        fails=_number(row.get("fails")) if isinstance(row, Mapping) else None,
        pages=_number(row.get("pages")) if isinstance(row, Mapping) else None,
        success_count=_number(row.get("success")) if isinstance(row, Mapping) else None,
        created=_text(row.get("created")) if isinstance(row, Mapping) else None,
        started=_text(row.get("started")) if isinstance(row, Mapping) else None,
        finished=_text(row.get("finished")) if isinstance(row, Mapping) else None,
        job_time_ms=_number(row.get("job_time")) if isinstance(row, Mapping) else None,
        queue_time_ms=_number(row.get("queue_time")) if isinstance(row, Mapping) else None,
        retry_count=0,
        key_exposed=False,
    )


def request_readonly_job_metadata(
    api_token: str,
    *,
    job_id: str,
    timeout_seconds: float = DEFAULT_READONLY_JOB_METADATA_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyJobMetadataResult:
    """Perform one documented GET /dca/log/{job_id} request with no retry path."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    if not job_id.strip():
        raise ValueError("job_id is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    endpoint = f"{BRIGHT_DATA_JOB_METADATA_ENDPOINT}/{job_id}"
    started = perf_counter()
    request = Request(endpoint, headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json", "User-Agent": "aegis-readonly-job-metadata/1"}, method="GET")
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            raw = response.read()
        if not 200 <= status < 300:
            return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class=f"HTTP_{status}", http_status=status, content_type=content_type)
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("metadata is not an object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class="MALFORMED_PROVIDER_RESPONSE", http_status=status, content_type=content_type)
        return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=True, error_class=None, http_status=status, content_type=content_type, row=payload)
    except HTTPError as error:
        return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", http_status=error.code, content_type=error.headers.get_content_type() if error.headers else None)
    except (TimeoutError, socket.timeout):
        return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class="JOB_METADATA_TIMEOUT", http_status=None, content_type=None)
    except URLError as error:
        return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class="JOB_METADATA_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR", http_status=None, content_type=None)
    except OSError:
        return _result(started=started, endpoint=endpoint, job_id=job_id, timeout_seconds=timeout_seconds, success=False, error_class="NETWORK_ERROR", http_status=None, content_type=None)
