"""Fixture-only future approval boundary for Mission 034.

This module intentionally has no CLI runner, HTTP client, subprocess call, or
provider command construction. It exercises AEGIS authorization and audit
semantics against controlled fixtures only. A separately authorized future
provider transport would need to implement and verify the documented external
operation before this boundary could be connected to a real provider.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import uuid4

from .immutability import freeze_mapping
from .models import ProviderProvenance, utc_now


MISSION034_CANDIDATE_ID = "candidate_m033_a0d9aa5a0d056720"
MISSION034_COLLECTOR_ID = "c_mt09pib13nxqz1coi"
BRIGHT_DATA_CLI_CREDENTIAL_ENV = "BRIGHTDATA_API_KEY"
BRIGHT_DATA_DCA_TOKEN_ENV = "BRIGHT_DATA_API_TOKEN"


class ApprovalBoundaryError(RuntimeError):
    """Raised when fixture-only future approval requirements are not satisfied."""


class ApprovalResult(str, Enum):
    FIXTURE_APPROVED = "FIXTURE_APPROVED"


class CollectorAccessStatus(str, Enum):
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CliCredentialConfiguration:
    """Secret-free configuration fact for a future server-side CLI transport."""

    source_name: str
    configured: bool


def validate_cli_credential_environment(environment: Mapping[str, str]) -> CliCredentialConfiguration:
    """Validate the documented CLI credential name without retaining a secret value.

    The DCA bearer token name is intentionally not an alias: the read-only
    Mission 034 diagnostic observed a scope/permission mismatch when it was
    mapped to the CLI credential interface.
    """

    if environment.get(BRIGHT_DATA_CLI_CREDENTIAL_ENV, "").strip():
        return CliCredentialConfiguration(BRIGHT_DATA_CLI_CREDENTIAL_ENV, True)
    if environment.get(BRIGHT_DATA_DCA_TOKEN_ENV, "").strip():
        raise ApprovalBoundaryError(
            "DCA token is configured, but the future Bright Data CLI approval boundary requires BRIGHTDATA_API_KEY."
        )
    raise ApprovalBoundaryError("BRIGHTDATA_API_KEY is required for the future Bright Data CLI approval boundary.")


@dataclass(frozen=True)
class ReadOnlyCollectorAccessResult:
    """Fail-closed result for an unavailable documented collector-inspection capability."""

    collector_id: str
    status: CollectorAccessStatus
    provider_called: bool
    reason: str

    def __post_init__(self) -> None:
        if self.provider_called:
            raise ValueError("safe UNKNOWN collector access result cannot call a provider")


class ReadOnlyCollectorAccessBoundary:
    """Preserve unknown access rather than inventing a provider metadata endpoint."""

    def __init__(self, *, expected_collector_id: str = MISSION034_COLLECTOR_ID) -> None:
        self.expected_collector_id = expected_collector_id

    def inspect(self, collector_id: str) -> ReadOnlyCollectorAccessResult:
        if collector_id != self.expected_collector_id:
            raise ApprovalBoundaryError("collector lookup does not match the canonical Mission 034 collector")
        return ReadOnlyCollectorAccessResult(
            collector_id=collector_id,
            status=CollectorAccessStatus.UNKNOWN,
            provider_called=False,
            reason="No documented harmless collector metadata lookup is implemented by the canonical adapter.",
        )


@dataclass(frozen=True)
class FixtureApprovalAuthorization:
    """Exact, expiring, fixture-only approval authority; never provider authority."""

    candidate_id: str
    collector_id: str
    operator: str
    authorization_reference: str
    correlation_id: str
    authorized_at: datetime
    expires_at: datetime
    operation_count: int = 0
    retry_count: int = 0
    automatic_commit_enabled: bool = False
    automatic_rollback_enabled: bool = False
    provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE

    def __post_init__(self) -> None:
        if self.authorized_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("approval authorization timestamps must be timezone-aware")


@dataclass(frozen=True)
class FixtureApprovalRecord:
    """Append-only fixture audit record; it cannot represent a real provider operation."""

    approval_id: str
    candidate_id: str
    collector_id: str
    operator: str
    authorization_reference: str
    authorization_timestamp: datetime
    correlation_id: str
    provider_operation_id: str
    provider_response_metadata: Mapping[str, str]
    result: ApprovalResult
    provenance: ProviderProvenance
    real_provider_mutation_performed: bool
    automatic_commit_performed: bool
    automatic_rollback_performed: bool
    evidence_hash: str
    recorded_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_response_metadata", freeze_mapping(self.provider_response_metadata))
        if self.provenance is not ProviderProvenance.TEST_DOUBLE:
            raise ValueError("fixture approval records must remain TEST_DOUBLE")
        if self.real_provider_mutation_performed or self.automatic_commit_performed or self.automatic_rollback_performed:
            raise ValueError("fixture approval records cannot perform provider, commit, or rollback side effects")


class FixtureOnlyApprovalGate:
    """A single-use local gate for future approval semantics; never calls a provider."""

    def __init__(
        self,
        *,
        expected_candidate_id: str = MISSION034_CANDIDATE_ID,
        expected_collector_id: str = MISSION034_COLLECTOR_ID,
        now: datetime | None = None,
    ) -> None:
        self.expected_candidate_id = expected_candidate_id
        self.expected_collector_id = expected_collector_id
        self._now = now
        self._records: tuple[FixtureApprovalRecord, ...] = ()

    @property
    def records(self) -> tuple[FixtureApprovalRecord, ...]:
        return self._records

    def approve_candidate(
        self,
        candidate_id: str,
        collector_id: str,
        authorization_context: FixtureApprovalAuthorization,
    ) -> FixtureApprovalRecord:
        """Create one TEST_DOUBLE record after exact fail-closed validation."""

        if candidate_id != self.expected_candidate_id or authorization_context.candidate_id != candidate_id:
            raise ApprovalBoundaryError("approval candidate does not match the authorized Mission 034 candidate")
        if collector_id != self.expected_collector_id or authorization_context.collector_id != collector_id:
            raise ApprovalBoundaryError("approval collector does not match the authorized Mission 034 collector")
        if not authorization_context.operator.strip() or not authorization_context.authorization_reference.strip() or not authorization_context.correlation_id.strip():
            raise ApprovalBoundaryError("approval authorization is incomplete")
        if authorization_context.provenance is not ProviderProvenance.TEST_DOUBLE:
            raise ApprovalBoundaryError("future approval fixture requires TEST_DOUBLE provenance")
        current_time = self._now or datetime.now(timezone.utc)
        if authorization_context.authorized_at > current_time or authorization_context.expires_at <= current_time:
            raise ApprovalBoundaryError("approval authorization is not currently valid")
        if authorization_context.operation_count != 0 or self._records:
            raise ApprovalBoundaryError("approval operation budget is exhausted")
        if authorization_context.retry_count != 0:
            raise ApprovalBoundaryError("approval retry budget must be zero")
        if authorization_context.automatic_commit_enabled or authorization_context.automatic_rollback_enabled:
            raise ApprovalBoundaryError("automatic commit and rollback must remain disabled")

        response_metadata = {"fixture": "controlled", "provider_called": "false", "status": "fixture_approved"}
        evidence_payload = {
            "candidate_id": candidate_id,
            "collector_id": collector_id,
            "operator": authorization_context.operator,
            "authorization_reference": authorization_context.authorization_reference,
            "correlation_id": authorization_context.correlation_id,
            "provider_response_metadata": response_metadata,
            "result": ApprovalResult.FIXTURE_APPROVED.value,
            "provenance": ProviderProvenance.TEST_DOUBLE.value,
        }
        record = FixtureApprovalRecord(
            approval_id=f"fixture_approval_{uuid4().hex}",
            candidate_id=candidate_id,
            collector_id=collector_id,
            operator=authorization_context.operator,
            authorization_reference=authorization_context.authorization_reference,
            authorization_timestamp=authorization_context.authorized_at,
            correlation_id=authorization_context.correlation_id,
            provider_operation_id="fixture-approval-operation-1",
            provider_response_metadata=response_metadata,
            result=ApprovalResult.FIXTURE_APPROVED,
            provenance=ProviderProvenance.TEST_DOUBLE,
            real_provider_mutation_performed=False,
            automatic_commit_performed=False,
            automatic_rollback_performed=False,
            evidence_hash=hashlib.sha256(
                json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        )
        self._records = (*self._records, record)
        return record
