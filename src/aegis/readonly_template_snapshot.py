"""Bounded one-request Scraper Studio final output-schema snapshot transport."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aegis.readonly_collectors import BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT, _content_type


DEFAULT_TEMPLATE_SNAPSHOT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ReadOnlyTemplateSnapshotResult:
    """Safe metadata for one documented collector-list schema snapshot."""

    operation: str
    endpoint: str
    collector_id: str
    requested_name: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    collector_found: str
    name: str | None
    active: bool | None
    last_run: str | None
    delivery_type: str | None
    output_schema: dict[str, object] | None
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpener = Callable[..., Any]


def _result(
    *,
    started: float,
    endpoint: str,
    collector_id: str,
    requested_name: str,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    collector_found: str,
    row: Mapping[str, Any] | None = None,
) -> ReadOnlyTemplateSnapshotResult:
    deliver = row.get("deliver") if isinstance(row, Mapping) else None
    output_schema = row.get("output_schema") if isinstance(row, Mapping) else None
    return ReadOnlyTemplateSnapshotResult(
        operation="collector_output_schema_snapshot",
        endpoint=endpoint,
        collector_id=collector_id,
        requested_name=requested_name,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        collector_found=collector_found,
        name=row.get("name") if isinstance(row, Mapping) and isinstance(row.get("name"), str) else None,
        active=row.get("active") if isinstance(row, Mapping) and isinstance(row.get("active"), bool) else None,
        last_run=row.get("last_run") if isinstance(row, Mapping) and isinstance(row.get("last_run"), str) else None,
        delivery_type=deliver.get("type") if isinstance(deliver, Mapping) and isinstance(deliver.get("type"), str) else None,
        output_schema=dict(output_schema) if isinstance(output_schema, Mapping) else None,
        retry_count=0,
        key_exposed=False,
    )


def request_readonly_template_snapshot(
    api_token: str,
    *,
    collector_id: str,
    collector_name: str,
    timeout_seconds: float = DEFAULT_TEMPLATE_SNAPSHOT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyTemplateSnapshotResult:
    """Perform exactly one documented GET ``/dca/collectors_list?search=...`` with no retry path."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    if not collector_name.strip():
        raise ValueError("collector_name is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    endpoint = BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT + "?" + urlencode({"search": collector_name})
    started = perf_counter()
    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "User-Agent": "aegis-readonly-template-snapshot/1",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            raw = response.read()
        if not 200 <= status < 300:
            return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class=f"HTTP_{status}", http_status=status, content_type=content_type, collector_found="UNKNOWN")
        try:
            payload = json.loads(raw.decode("utf-8"))
            rows = payload.get("data") if isinstance(payload, Mapping) else None
            if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
                raise ValueError("missing data list")
            matched = next((row for row in rows if row.get("id") == collector_id), None)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class="MALFORMED_PROVIDER_RESPONSE", http_status=status, content_type=content_type, collector_found="UNKNOWN")
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=True, error_class=None, http_status=status, content_type=content_type, collector_found="YES" if matched is not None else "NO", row=matched)
    except HTTPError as error:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}", http_status=error.code, content_type=error.headers.get_content_type() if error.headers else None, collector_found="UNKNOWN")
    except (TimeoutError, socket.timeout):
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class="TEMPLATE_SNAPSHOT_TIMEOUT", http_status=None, content_type=None, collector_found="UNKNOWN")
    except URLError as error:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class="TEMPLATE_SNAPSHOT_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR", http_status=None, content_type=None, collector_found="UNKNOWN")
    except OSError:
        return _result(started=started, endpoint=endpoint, collector_id=collector_id, requested_name=collector_name, timeout_seconds=timeout_seconds, success=False, error_class="NETWORK_ERROR", http_status=None, content_type=None, collector_found="UNKNOWN")
