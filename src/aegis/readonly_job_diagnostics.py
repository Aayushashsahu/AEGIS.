"""Bounded read-only Scraper Studio job-list diagnostics for Mission 049."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aegis.readonly_collectors import _content_type


BRIGHT_DATA_JOBS_LIST_ENDPOINT = "https://api.brightdata.com/dca/collector/jobs"
DEFAULT_READONLY_JOBS_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ReadOnlyJobsListResult:
    """Safe metadata from one documented jobs-list request; raw body and credentials are never retained."""

    operation: str
    endpoint: str
    collector_id: str
    from_date: str
    to_date: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    total: int | None
    jobs: tuple[dict[str, object], ...]
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["jobs"] = list(self.jobs)
        return result


UrlOpener = Callable[..., Any]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _safe_job(row: Mapping[str, Any]) -> dict[str, object]:
    job_id = _text(row.get("id"))
    if not job_id:
        raise ValueError("job entry is missing id")
    # The documented response includes a trigger object with user/IP data. It is deliberately omitted.
    return {
        "id": job_id,
        "status": _text(row.get("status")),
        "queued": _text(row.get("queued")),
        "started": _text(row.get("started")),
        "finished": _text(row.get("finished")),
        "inputs": _number(row.get("inputs")),
        "page_loads": _number(row.get("page_loads")),
        "total_pages": _number(row.get("total_pages")),
        "failed_pages": _number(row.get("failed_pages")),
        "data_lines": _number(row.get("data_lines")),
        "expired": _text(row.get("expired")),
    }


def _result(
    *,
    started: float,
    endpoint: str,
    collector_id: str,
    from_date: str,
    to_date: str,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    total: int | None = None,
    jobs: tuple[dict[str, object], ...] = (),
) -> ReadOnlyJobsListResult:
    return ReadOnlyJobsListResult(
        operation="collector_jobs_list",
        endpoint=endpoint,
        collector_id=collector_id,
        from_date=from_date,
        to_date=to_date,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        total=total,
        jobs=jobs,
        retry_count=0,
        key_exposed=False,
    )


def request_readonly_jobs_list(
    api_token: str,
    *,
    collector_id: str,
    from_date: str,
    to_date: str,
    timeout_seconds: float = DEFAULT_READONLY_JOBS_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyJobsListResult:
    """Perform one documented GET /dca/collector/jobs request with no retry path."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    if len(from_date) != 10 or len(to_date) != 10:
        raise ValueError("from_date and to_date must use YYYY-MM-DD")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    endpoint = BRIGHT_DATA_JOBS_LIST_ENDPOINT + "?" + urlencode(
        {"collector": collector_id, "from_date": from_date, "to_date": to_date, "offset": 0, "limit": 50, "sort_asc": -1}
    )
    started = perf_counter()
    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "User-Agent": "aegis-readonly-jobs-list/1",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            raw = response.read()
        if not 200 <= status < 300:
            return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class=f"HTTP_{status}", http_status=status, content_type=content_type)
        try:
            payload = json.loads(raw.decode("utf-8"))
            rows = payload.get("data") if isinstance(payload, Mapping) else None
            if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
                raise ValueError("missing data list")
            total = _number(payload.get("total")) if isinstance(payload, Mapping) else None
            jobs = tuple(_safe_job(row) for row in rows)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class="MALFORMED_PROVIDER_RESPONSE", http_status=status, content_type=content_type)
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=True, error_class=None, http_status=status, content_type=content_type, total=total, jobs=jobs)
    except HTTPError as error:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", http_status=error.code, content_type=error.headers.get_content_type() if error.headers else None)
    except (TimeoutError, socket.timeout):
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class="JOBS_LIST_TIMEOUT", http_status=None, content_type=None)
    except URLError as error:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class="JOBS_LIST_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR", http_status=None, content_type=None)
    except OSError:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, from_date=from_date, to_date=to_date, timeout_seconds=timeout_seconds, success=False, error_class="NETWORK_ERROR", http_status=None, content_type=None)
