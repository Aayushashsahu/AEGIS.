"""Bounded, single-request Scraper Studio collector discovery transport."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT = "https://api.brightdata.com/dca/collectors_list"
DEFAULT_COLLECTORS_LIST_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ReadOnlyCollectorsListResult:
    """Safe metadata from one collector-list request; never stores the token or raw body."""

    operation: str
    endpoint: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    collector_count: int | None
    collector_ids: tuple[str, ...]
    canonical_collector_found: str
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["collector_ids"] = list(self.collector_ids)
        return result


UrlOpener = Callable[..., Any]


def _result(
    *,
    started: float,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    collector_ids: tuple[str, ...] = (),
    canonical_collector_id: str,
) -> ReadOnlyCollectorsListResult:
    found = "UNKNOWN" if not success else ("YES" if canonical_collector_id in collector_ids else "NO")
    return ReadOnlyCollectorsListResult(
        operation="collectors_list",
        endpoint=BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        collector_count=len(collector_ids) if success else None,
        collector_ids=collector_ids,
        canonical_collector_found=found,
        retry_count=0,
        key_exposed=False,
    )


def _content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    get_content_type = getattr(headers, "get_content_type", None)
    if callable(get_content_type):
        return str(get_content_type())
    get = getattr(headers, "get", None)
    if callable(get):
        value = get("Content-Type")
        return str(value) if value else None
    return None


def request_readonly_collectors_list(
    api_token: str,
    *,
    canonical_collector_id: str,
    timeout_seconds: float = DEFAULT_COLLECTORS_LIST_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyCollectorsListResult:
    """Perform exactly one bounded GET and retain only permitted collector metadata."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    if not canonical_collector_id.startswith("c_"):
        raise ValueError("canonical_collector_id must be a collector ID")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = perf_counter()
    request = Request(
        BRIGHT_DATA_COLLECTORS_LIST_ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "User-Agent": "aegis-readonly-collectors-list/1",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            raw = response.read()
        if not 200 <= status < 300:
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class=f"HTTP_{status}",
                http_status=status,
                content_type=content_type,
                canonical_collector_id=canonical_collector_id,
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
            rows = payload["data"] if isinstance(payload, Mapping) else None
            if not isinstance(rows, list):
                raise ValueError("missing data list")
            collector_ids = tuple(str(row["id"]) for row in rows if isinstance(row, Mapping) and isinstance(row.get("id"), str))
            if len(collector_ids) != len(rows):
                raise ValueError("collector entry without string id")
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class="MALFORMED_PROVIDER_RESPONSE",
                http_status=status,
                content_type=content_type,
                canonical_collector_id=canonical_collector_id,
            )
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=True,
            error_class=None,
            http_status=status,
            content_type=content_type,
            collector_ids=collector_ids,
            canonical_collector_id=canonical_collector_id,
        )
    except HTTPError as error:
        error_class = "HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}"
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class=error_class,
            http_status=error.code,
            content_type=error.headers.get_content_type() if error.headers else None,
            canonical_collector_id=canonical_collector_id,
        )
    except (TimeoutError, socket.timeout):
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="COLLECTORS_LIST_TIMEOUT",
            http_status=None,
            content_type=None,
            canonical_collector_id=canonical_collector_id,
        )
    except URLError as error:
        error_class = "COLLECTORS_LIST_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR"
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class=error_class,
            http_status=None,
            content_type=None,
            canonical_collector_id=canonical_collector_id,
        )
    except OSError:
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="NETWORK_ERROR",
            http_status=None,
            content_type=None,
            canonical_collector_id=canonical_collector_id,
        )
