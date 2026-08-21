"""Fail-closed, provider-free authorization and evidence rules for future calls.

The module deliberately prepares or rejects operation envelopes only.  It has
no network dependency and cannot execute a Bright Data request.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from urllib.parse import urlparse

from .immutability import freeze_mapping


class OperationAccess(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATION = "MUTATION"


class ProviderIdentifierState(str, Enum):
    PRESENT = "PRESENT"
    NOT_RETURNED_BY_PROVIDER = "NOT_RETURNED_BY_PROVIDER"


@dataclass(frozen=True)
class FutureVersionBoundRun:
    """Provider-free contract for one future, explicitly versioned production run.

    The type is evidence preparation only.  It never invokes a CLI, reads a
    credential, or contacts a provider.
    """

    mission: str
    collector_id: str
    target_url: str
    explicit_version: str
    correlation_id: str
    prompt_sha256: str
    authorization_reference: str
    max_operations: int
    retry_budget: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        parsed = urlparse(self.target_url)
        if not self.mission.strip() or not self.collector_id.startswith("c_"):
            raise ValueError("mission and collector_id are required")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("target_url must be an absolute HTTP(S) URL")
        if not self.explicit_version.strip() or not self.correlation_id.strip():
            raise ValueError("explicit_version and correlation_id are required")
        if len(self.prompt_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.prompt_sha256):
            raise ValueError("prompt_sha256 must be a lowercase SHA-256 digest")
        if not self.authorization_reference.strip():
            raise ValueError("authorization_reference is required")
        if self.max_operations != 1 or self.retry_budget != 0:
            raise ValueError("version-bound runs require exactly one operation and zero retries")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def prepared_cli_arguments(self) -> tuple[str, ...]:
        """Return unexecuted CLI arguments for a future preflight-approved run."""

        return (
            "bdata",
            "scraper",
            "run",
            self.collector_id,
            self.target_url,
            "--version",
            self.explicit_version,
            "--json",
        )

    def required_evidence(self) -> Mapping[str, str]:
        """Return the mandatory correlation and raw-first evidence fields."""

        return freeze_mapping({
            "AEGIS_CORRELATION_ID": self.correlation_id,
            "collector_id": self.collector_id,
            "target_url_sha256": hashlib.sha256(self.target_url.encode("utf-8")).hexdigest(),
            "explicit_version": self.explicit_version,
            "prompt_sha256": self.prompt_sha256,
            "operation_type": "VERSION_BOUND_RUN",
            "authorization_reference": self.authorization_reference,
            "provider_operation_id": "CAPTURE_OR_NOT_RETURNED_BY_PROVIDER",
            "provider_run_id": "CAPTURE_OR_NOT_RETURNED_BY_PROVIDER",
            "provider_response_id": "CAPTURE_OR_NOT_RETURNED_BY_PROVIDER",
            "raw_response": "CAPTURE_RAW_FIRST",
            "raw_response_sha256": "CAPTURE_AFTER_RAW_RESPONSE",
        })


def preserve_provider_identifier_provenance(
    provider_identifiers: Mapping[str, str] | None,
    *,
    local_identifiers: tuple[str, ...] = (),
) -> tuple[ProviderIdentifierState, Mapping[str, str]]:
    """Preserve only provider-returned IDs and reject any local fallback value."""

    local_values = {value for value in local_identifiers if value.strip()}
    identifiers = {
        key: value
        for key, value in (provider_identifiers or {}).items()
        if isinstance(key, str) and key.startswith("provider_") and isinstance(value, str) and value.strip()
    }
    if any(value in local_values for value in identifiers.values()):
        raise ValueError("local identifiers cannot be presented as provider identifiers")
    if not identifiers:
        return ProviderIdentifierState.NOT_RETURNED_BY_PROVIDER, freeze_mapping({})
    return ProviderIdentifierState.PRESENT, freeze_mapping(identifiers)


@dataclass(frozen=True)
class FutureProviderAuthorization:
    """Bounded authorization evidence; never a capability to execute a call."""

    mission: str
    collector_id: str
    candidate_id: str | None
    operator: str
    authorized_at_utc: str
    expires_at_utc: str
    scope: str
    max_operations: int
    max_retries: int
    timeout_seconds: float
    allowed_operation: str
    prohibited_operations: tuple[str, ...]
    automatic_commit: bool = False
    automatic_rollback: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "prohibited_operations", tuple(self.prohibited_operations))
        if not self.mission.strip() or not self.collector_id.startswith("c_"):
            raise ValueError("mission and collector_id are required")
        if not self.operator.strip() or not self.scope.strip() or not self.allowed_operation.strip():
            raise ValueError("operator, scope, and allowed_operation are required")
        if self.max_operations != 1 or self.max_retries != 0:
            raise ValueError("future authorization must allow exactly one operation and zero retries")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.automatic_commit or self.automatic_rollback:
            raise ValueError("automatic commit and rollback are prohibited")
        for value in (self.authorized_at_utc, self.expires_at_utc):
            if not value.endswith("Z"):
                raise ValueError("authorization timestamps must be UTC with a Z suffix")
            datetime.fromisoformat(value.removesuffix("Z") + "+00:00")

    def validates(
        self,
        *,
        operation: str,
        collector_id: str,
        candidate_id: str | None,
        now_utc: str,
        attempted_operations: int,
        retry_count: int,
    ) -> bool:
        """Return true only for the exact bounded, unexpired operation."""

        if operation != self.allowed_operation or operation in self.prohibited_operations:
            return False
        if collector_id != self.collector_id or candidate_id != self.candidate_id:
            return False
        if attempted_operations >= self.max_operations or retry_count > self.max_retries:
            return False
        now = datetime.fromisoformat(now_utc.removesuffix("Z") + "+00:00")
        expiry = datetime.fromisoformat(self.expires_at_utc.removesuffix("Z") + "+00:00")
        return now <= expiry


@dataclass(frozen=True)
class ProviderOperationEnvelope:
    """Raw-first evidence descriptor; it does not carry secrets or run code."""

    mission: str
    operation: str
    access: OperationAccess
    correlation_id: str
    collector_id: str
    target_url_sha256: str
    timeout_seconds: float
    retry_budget: int
    authorization_reference: str
    artifact_destination: str
    raw_response_sha256: str | None
    provider_identifiers: Mapping[str, str]
    provider_identifier_state: ProviderIdentifierState
    failure_class: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_identifiers", freeze_mapping(self.provider_identifiers))
        if not self.correlation_id.strip() or not self.authorization_reference.strip():
            raise ValueError("correlation_id and authorization_reference are required")
        if self.timeout_seconds <= 0 or self.retry_budget != 0:
            raise ValueError("operations require a positive timeout and zero retry budget")
        if not self.artifact_destination.strip():
            raise ValueError("artifact_destination is required")
        if self.provider_identifier_state is ProviderIdentifierState.NOT_RETURNED_BY_PROVIDER and self.provider_identifiers:
            raise ValueError("not-returned identifier state cannot include provider identifiers")
        if self.raw_response_sha256 is not None and len(self.raw_response_sha256) != 64:
            raise ValueError("raw_response_sha256 must be a SHA-256 digest")

    def to_evidence_dict(self) -> dict[str, object]:
        return asdict(self)


def build_raw_first_envelope(
    *,
    mission: str,
    operation: str,
    access: OperationAccess,
    correlation_id: str,
    collector_id: str,
    target_url: str,
    timeout_seconds: float,
    authorization_reference: str,
    artifact_destination: str,
    raw_response_bytes: bytes | None,
    provider_identifiers: Mapping[str, str] | None,
    failure_class: str | None = None,
) -> ProviderOperationEnvelope:
    """Build raw-first metadata without synthesizing absent provider IDs."""

    identifiers = {key: value for key, value in (provider_identifiers or {}).items() if isinstance(value, str) and value.strip()}
    return ProviderOperationEnvelope(
        mission=mission,
        operation=operation,
        access=access,
        correlation_id=correlation_id,
        collector_id=collector_id,
        target_url_sha256=hashlib.sha256(target_url.encode("utf-8")).hexdigest(),
        timeout_seconds=timeout_seconds,
        retry_budget=0,
        authorization_reference=authorization_reference,
        artifact_destination=artifact_destination,
        raw_response_sha256=hashlib.sha256(raw_response_bytes).hexdigest() if raw_response_bytes is not None else None,
        provider_identifiers=identifiers,
        provider_identifier_state=(ProviderIdentifierState.PRESENT if identifiers else ProviderIdentifierState.NOT_RETURNED_BY_PROVIDER),
        failure_class=failure_class,
    )
