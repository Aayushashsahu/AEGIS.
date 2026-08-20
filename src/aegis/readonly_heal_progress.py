"""Bounded, one-request read-only inspection of a Scraper Studio Self-Healing job."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aegis.readonly_collectors import _content_type


DEFAULT_HEAL_PROGRESS_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ReadOnlyHealProgressResult:
    """Redacted result from one progress GET; stores no raw provider body or credential."""

    operation: str
    endpoint: str
    requested_collector_id: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    provider_status: str | None
    progress_status: str
    provider_job_id: str | None
    provider_revision: str | None
    provider_timestamp: str | None
    preview_present: bool | None
    candidate_found: str
    collector_match: str
    retry_count: int
    key_exposed: bool

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpener = Callable[..., Any]


def heal_progress_endpoint(collector_id: str) -> str:
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    return f"https://api.brightdata.com/dca/collectors/{collector_id}/refactor_template/progress"


def _contains_exact(value: object, target: str) -> bool:
    if isinstance(value, str):
        return value == target
    if isinstance(value, Mapping):
        return any(_contains_exact(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact(item, target) for item in value)
    return False


def _find_key(value: object, key: str) -> object | None:
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        for item in value.values():
            found = _find_key(item, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_key(item, key)
            if found is not None:
                return found
    return None


def _first_string_for_keys(value: object, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = _find_key(value, key)
        if isinstance(candidate, str):
            return candidate
    return None


def _classify_progress_status(provider_status: str | None) -> str:
    if provider_status is None:
        return "UNKNOWN"
    normalized = provider_status.strip().lower()
    if normalized in {"done", "completed", "complete", "success", "succeeded"}:
        return "COMPLETED"
    if normalized in {"failed", "error", "rejected", "cancelled", "canceled"}:
        return "FAILED"
    if normalized in {"pending", "pending_answer", "awaiting_approval", "queued"}:
        return "PENDING"
    if normalized in {"running", "in_progress", "processing"}:
        return "RUNNING"
    return "UNKNOWN"


def _result(
    *,
    started: float,
    endpoint: str,
    collector_id: str,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    provider_status: str | None = None,
    progress_status: str = "UNKNOWN",
    provider_job_id: str | None = None,
    provider_revision: str | None = None,
    provider_timestamp: str | None = None,
    preview_present: bool | None = None,
    candidate_found: str = "UNKNOWN",
    collector_match: str = "UNKNOWN",
) -> ReadOnlyHealProgressResult:
    return ReadOnlyHealProgressResult(
        operation="self_healing_progress",
        endpoint=endpoint,
        requested_collector_id=collector_id,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        provider_status=provider_status,
        progress_status=progress_status,
        provider_job_id=provider_job_id,
        provider_revision=provider_revision,
        provider_timestamp=provider_timestamp,
        preview_present=preview_present,
        candidate_found=candidate_found,
        collector_match=collector_match,
        retry_count=0,
        key_exposed=False,
    )


def request_readonly_heal_progress(
    api_token: str,
    *,
    collector_id: str,
    candidate_id: str,
    timeout_seconds: float = DEFAULT_HEAL_PROGRESS_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyHealProgressResult:
    """Perform exactly one documented GET and parse only allowed status metadata."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    endpoint = heal_progress_endpoint(collector_id)
    if not candidate_id.startswith("candidate_"):
        raise ValueError("candidate_id must be an AEGIS candidate ID")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = perf_counter()
    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "User-Agent": "aegis-readonly-heal-progress/1",
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
                endpoint=endpoint,
                collector_id=collector_id,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class=f"HTTP_{status}",
                http_status=status,
                content_type=content_type,
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("expected JSON object")
            status_value = _find_key(payload, "status")
            provider_status = status_value if isinstance(status_value, str) else None
            progress_status = _classify_progress_status(provider_status)
            provider_job_id = _first_string_for_keys(payload, ("job_id", "operation_id", "automation_job_id"))
            provider_revision = _first_string_for_keys(payload, ("revision_id", "template_id", "template_revision"))
            provider_timestamp = _first_string_for_keys(payload, ("completed_at", "updated_at", "created_at", "timestamp"))
            preview_present = _find_key(payload, "preview_result") is not None
            candidate_found = "YES" if _contains_exact(payload, candidate_id) else "NO"
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            return _result(
                started=started,
                endpoint=endpoint,
                collector_id=collector_id,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class="MALFORMED_PROVIDER_RESPONSE",
                http_status=status,
                content_type=content_type,
            )
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            timeout_seconds=timeout_seconds,
            success=True,
            error_class=None,
            http_status=status,
            content_type=content_type,
            provider_status=provider_status,
            progress_status=progress_status,
            provider_job_id=provider_job_id,
            provider_revision=provider_revision,
            provider_timestamp=provider_timestamp,
            preview_present=preview_present,
            candidate_found=candidate_found,
            collector_match="YES",
        )
    except HTTPError as error:
        error_class = "HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}"
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class=error_class,
            http_status=error.code,
            content_type=error.headers.get_content_type() if error.headers else None,
        )
    except (TimeoutError, socket.timeout):
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="HEAL_PROGRESS_TIMEOUT",
            http_status=None,
            content_type=None,
        )
    except URLError as error:
        error_class = "HEAL_PROGRESS_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR"
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class=error_class,
            http_status=None,
            content_type=None,
        )
    except OSError:
        return _result(
            started=started,
            endpoint=endpoint,
            collector_id=collector_id,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="NETWORK_ERROR",
            http_status=None,
            content_type=None,
        )
