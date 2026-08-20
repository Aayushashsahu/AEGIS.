"""Bounded, server-only Bright Data account-budget transport.

This transport intentionally does not invoke the general CLI client: CLI 0.3.5
does not expose an HTTP abort timeout or a zero-retry option on ``bdata
budget``. It performs the same documented read-only account endpoint request
once, using the canonical CLI credential environment name, and returns only
safe metadata rather than account balance content.
"""

from __future__ import annotations

import json
import re
import socket
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BRIGHT_DATA_BUDGET_ENDPOINT = "https://api.brightdata.com/customer/balance"
DEFAULT_BUDGET_TIMEOUT_SECONDS = 10.0


def _redact(value: object) -> str:
    """Remove credential-shaped content before it can enter an error record."""

    text = " ".join(str(value).split())
    text = re.sub(
        r"(?i)\bauthorization\s*[:=]\s*bearer\s+[^\s,;]+",
        "authorization=[REDACTED]",
        text,
    )
    return re.sub(
        r"(?i)\b(bearer|api[_-]?key|token|cookie|password)\s*[:=]?\s*[^\s,;]+",
        r"\1=[REDACTED]",
        text,
    )


@dataclass(frozen=True)
class ReadOnlyBudgetResult:
    """Redacted result for exactly one read-only budget request."""

    operation: str
    endpoint: str
    timeout_seconds: float
    elapsed_ms: int
    success: bool
    error_class: str | None
    http_status: int | None
    retry_count: int
    key_exposed: bool
    detail: str | None = None

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpener = Callable[..., Any]


def _result(
    *,
    started: float,
    timeout_seconds: float,
    success: bool,
    error_class: str | None,
    http_status: int | None,
    detail: str | None = None,
) -> ReadOnlyBudgetResult:
    return ReadOnlyBudgetResult(
        operation="budget",
        endpoint=BRIGHT_DATA_BUDGET_ENDPOINT,
        timeout_seconds=timeout_seconds,
        elapsed_ms=round((perf_counter() - started) * 1000),
        success=success,
        error_class=error_class,
        http_status=http_status,
        retry_count=0,
        key_exposed=False,
        detail=_redact(detail) if detail else None,
    )


def request_readonly_budget(
    api_key: str,
    *,
    timeout_seconds: float = DEFAULT_BUDGET_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> ReadOnlyBudgetResult:
    """Make one bounded budget request without retaining the credential or response body.

    The caller owns the credential source. This function neither retries nor
    follows redirects, and it classifies response metadata without surfacing
    balance or account content.
    """

    if not api_key.strip():
        raise ValueError("a non-empty API key is required by the caller")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = perf_counter()
    request = Request(
        BRIGHT_DATA_BUDGET_ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "aegis-readonly-budget/1",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            raw = response.read()
        if not 200 <= status < 300:
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class=f"HTTP_{status}",
                http_status=status,
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class="MALFORMED_PROVIDER_RESPONSE",
                http_status=status,
            )
        if not isinstance(payload, Mapping):
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class="MALFORMED_PROVIDER_RESPONSE",
                http_status=status,
            )
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=True,
            error_class=None,
            http_status=status,
        )
    except HTTPError as error:
        error_class = "HTTP_403_SCOPE" if error.code == 403 else f"HTTP_{error.code}"
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class=error_class,
            http_status=error.code,
            detail=str(error),
        )
    except (TimeoutError, socket.timeout):
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="CLI_BUDGET_TIMEOUT",
            http_status=None,
        )
    except URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return _result(
                started=started,
                timeout_seconds=timeout_seconds,
                success=False,
                error_class="CLI_BUDGET_TIMEOUT",
                http_status=None,
            )
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="NETWORK_ERROR",
            http_status=None,
            detail=str(error.reason),
        )
    except OSError as error:
        return _result(
            started=started,
            timeout_seconds=timeout_seconds,
            success=False,
            error_class="NETWORK_ERROR",
            http_status=None,
            detail=str(error),
        )
