"""Bounded, explicitly authorized single-call Bright Data Self-Healing approval transport."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aegis.readonly_collectors import _content_type


DEFAULT_APPROVAL_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class OneShotApprovalResult:
    """Safe metadata from one approval POST; never retains credentials or response body."""

    operation: str
    endpoint: str
    collector_id: str
    correlation_id: str
    timeout_seconds: float
    elapsed_ms: int
    attempted: bool
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    resulting_provider_state: str | None
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpener = Callable[..., Any]


def approval_endpoint(collector_id: str) -> str:
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    return f"https://api.brightdata.com/dca/collectors/{collector_id}/resume_automation_job"


def _result(
    *,
    started: float,
    endpoint: str,
    collector_id: str,
    correlation_id: str,
    timeout_seconds: float,
    attempted: bool,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    resulting_provider_state: str | None,
) -> OneShotApprovalResult:
    return OneShotApprovalResult(
        operation="resume_self_healing_job",
        endpoint=endpoint,
        collector_id=collector_id,
        correlation_id=correlation_id,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        attempted=attempted,
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        resulting_provider_state=resulting_provider_state,
        retry_count=0,
        key_exposed=False,
    )


def approve_pending_self_healing_once(
    api_token: str,
    *,
    collector_id: str,
    correlation_id: str,
    timeout_seconds: float = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> OneShotApprovalResult:
    """Perform one documented approval POST with ``message=true`` and no retries."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    endpoint = approval_endpoint(collector_id)
    if not correlation_id.startswith("mission040-"):
        raise ValueError("correlation_id must be a Mission 040 correlation ID")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = perf_counter()
    request = Request(
        endpoint,
        data=json.dumps({"message": True}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "aegis-one-shot-approval/1",
            "X-Aegis-Correlation-Id": correlation_id,
        },
        method="POST",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            response.read()  # Deliberately discard body: no preview, diff, or raw payload is persisted.
        if 200 <= status < 300:
            return _result(
                started=started,
                endpoint=endpoint,
                collector_id=collector_id,
                correlation_id=correlation_id,
                timeout_seconds=timeout_seconds,
                attempted=True,
                success=True,
                error_class=None,
                http_status=status,
                content_type=content_type,
                resulting_provider_state="RESUME_ACCEPTED",
            )
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds,
            attempted=True,
            success=False,
            error_class=f"HTTP_{status}",
            http_status=status,
            content_type=content_type,
            resulting_provider_state=None,
        )
    except HTTPError as error:
        error_class = "HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}"
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds,
            attempted=True,
            success=False,
            error_class=error_class,
            http_status=error.code,
            content_type=error.headers.get_content_type() if error.headers else None,
            resulting_provider_state=None,
        )
    except (TimeoutError, socket.timeout):
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds,
            attempted=True,
            success=False,
            error_class="APPROVAL_TIMEOUT",
            http_status=None,
            content_type=None,
            resulting_provider_state=None,
        )
    except URLError as error:
        error_class = "APPROVAL_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR"
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds,
            attempted=True,
            success=False,
            error_class=error_class,
            http_status=None,
            content_type=None,
            resulting_provider_state=None,
        )
    except OSError:
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds,
            attempted=True,
            success=False,
            error_class="NETWORK_ERROR",
            http_status=None,
            content_type=None,
            resulting_provider_state=None,
        )
