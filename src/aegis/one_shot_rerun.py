"""Bounded, exactly-one synchronous Scraper Studio collector rerun transport."""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aegis.readonly_collectors import _content_type


DEFAULT_RERUN_WAIT_SECONDS = 50
DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS = 55.0


@dataclass(frozen=True)
class OneShotRerunResult:
    """Safe request metadata plus untrusted but actual output from one documented crawl."""

    operation: str
    endpoint: str
    collector_id: str
    target_url: str
    correlation_id: str
    http_timeout_seconds: float
    elapsed_ms: int
    attempted: bool
    success: bool
    error_class: str | None
    http_status: int | None
    content_type: str | None
    provider_status: str | None
    response_id: str | None
    rows: tuple[dict[str, Any], ...]
    row_count: int | None
    output_schema: dict[str, str] | None
    raw_response_sha256: str | None
    retry_count: int
    key_exposed: bool
    raw_response_bytes: bytes | None = field(repr=False, compare=False)

    def to_safe_metadata(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("rows")
        result.pop("raw_response_bytes")
        return result

    def to_evidence_dict(self) -> dict[str, object]:
        result = self.to_safe_metadata()
        result["rows"] = list(self.rows)
        return result

    def preserve_raw_response(self, path: Path) -> dict[str, object]:
        """Write the exact provider response once to controlled evidence storage.

        The caller must choose an explicit path. Existing evidence is never
        overwritten, and regular metadata/evidence methods never include the
        raw bytes. This preserves the first provider boundary for future
        diagnosis without leaking arbitrary response content into logs.
        """

        if self.raw_response_bytes is None or self.raw_response_sha256 is None:
            raise ValueError("no provider response body is available to preserve")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(self.raw_response_bytes)
        return {
            "path": str(path),
            "sha256": self.raw_response_sha256,
            "bytes": len(self.raw_response_bytes),
        }


UrlOpener = Callable[..., Any]


def _http_error_body(error: HTTPError) -> bytes | None:
    """Read an available error body once without turning capture failure into success."""

    try:
        body = error.read()
    except (AttributeError, OSError, ValueError):
        return None
    return body if isinstance(body, bytes) else None


def rerun_endpoint(collector_id: str, *, wait_seconds: int = DEFAULT_RERUN_WAIT_SECONDS) -> str:
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    if wait_seconds < 25 or wait_seconds > 50:
        raise ValueError("wait_seconds must be between 25 and 50")
    return "https://api.brightdata.com/dca/crawl?" + urlencode({"collector": collector_id, "timeout": f"{wait_seconds}s"})


def _schema(rows: tuple[dict[str, Any], ...]) -> dict[str, str]:
    names: dict[str, set[str]] = {}
    for row in rows:
        for key, value in row.items():
            names.setdefault(key, set()).add(type(value).__name__)
    return {key: "|".join(sorted(types)) for key, types in sorted(names.items())}


def _result(
    *,
    started: float,
    endpoint: str,
    collector_id: str,
    target_url: str,
    correlation_id: str,
    http_timeout_seconds: float,
    attempted: bool,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    content_type: str | None,
    provider_status: str | None = None,
    response_id: str | None = None,
    rows: tuple[dict[str, Any], ...] = (),
    raw_response_bytes: bytes | None = None,
) -> OneShotRerunResult:
    return OneShotRerunResult(
        operation="synchronous_collector_rerun",
        endpoint=endpoint,
        collector_id=collector_id,
        target_url=target_url,
        correlation_id=correlation_id,
        http_timeout_seconds=http_timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        attempted=attempted,
        success=success,
        error_class=error_class,
        http_status=http_status,
        content_type=content_type,
        provider_status=provider_status,
        response_id=response_id,
        rows=rows,
        row_count=len(rows) if success else None,
        output_schema=_schema(rows) if success else None,
        raw_response_sha256=hashlib.sha256(raw_response_bytes).hexdigest() if raw_response_bytes is not None else None,
        retry_count=0,
        key_exposed=False,
        raw_response_bytes=raw_response_bytes,
    )


def rerun_collector_once(
    api_token: str,
    *,
    collector_id: str,
    target_url: str,
    correlation_id: str,
    wait_seconds: int = DEFAULT_RERUN_WAIT_SECONDS,
    http_timeout_seconds: float = DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> OneShotRerunResult:
    """Perform exactly one documented synchronous ``POST /dca/crawl`` request with no retry path."""

    if not api_token.strip():
        raise ValueError("a non-empty API token is required by the caller")
    if not target_url.startswith(("https://", "http://")):
        raise ValueError("target_url must be an HTTP(S) URL")
    if not correlation_id.startswith("mission041b-"):
        raise ValueError("correlation_id must be a Mission 041B correlation ID")
    if http_timeout_seconds <= wait_seconds:
        raise ValueError("http_timeout_seconds must exceed wait_seconds")
    endpoint = rerun_endpoint(collector_id, wait_seconds=wait_seconds)
    started = perf_counter()
    request = Request(
        endpoint,
        data=json.dumps({"url": target_url}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "aegis-one-shot-rerun/1",
            "X-Aegis-Correlation-Id": correlation_id,
        },
        method="POST",
    )
    try:
        with opener(request, timeout=http_timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response)
            raw = response.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _result(
                started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
                correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
                success=False, error_class="MALFORMED_PROVIDER_RESPONSE", http_status=status,
                content_type=content_type, raw_response_bytes=raw,
            )
        if status == 200:
            if not isinstance(payload, list) or not all(isinstance(row, Mapping) for row in payload):
                return _result(
                    started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
                correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
                success=False, error_class="MALFORMED_PROVIDER_RESPONSE", http_status=status,
                content_type=content_type, raw_response_bytes=raw,
                )
            rows = tuple(dict(row) for row in payload)
            return _result(
                started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
                correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
                success=True, error_class=None, http_status=status, content_type=content_type,
                provider_status="COMPLETED", rows=rows, raw_response_bytes=raw,
            )
        if status == 202 and isinstance(payload, Mapping):
            response_id = payload.get("response_id")
            return _result(
                started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
                correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
                success=False, error_class="RERUN_ASYNC_PENDING", http_status=status, content_type=content_type,
                provider_status="PENDING", response_id=response_id if isinstance(response_id, str) else None,
                raw_response_bytes=raw,
            )
        return _result(
            started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
                correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
                success=False, error_class=f"HTTP_{status}", http_status=status, content_type=content_type,
                raw_response_bytes=raw,
        )
    except HTTPError as error:
        raw = _http_error_body(error)
        return _result(
            started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
            correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
            success=False, error_class="HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}",
            http_status=error.code, content_type=error.headers.get_content_type() if error.headers else None,
            raw_response_bytes=raw,
        )
    except (TimeoutError, socket.timeout):
        return _result(
            started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
            correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
            success=False, error_class="RERUN_TIMEOUT", http_status=None, content_type=None,
        )
    except URLError as error:
        return _result(
            started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
            correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
            success=False, error_class="RERUN_TIMEOUT" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "NETWORK_ERROR",
            http_status=None, content_type=None,
        )
    except OSError:
        return _result(
            started=started, endpoint=endpoint, collector_id=collector_id, target_url=target_url,
            correlation_id=correlation_id, http_timeout_seconds=http_timeout_seconds, attempted=True,
            success=False, error_class="NETWORK_ERROR", http_status=None, content_type=None,
        )
