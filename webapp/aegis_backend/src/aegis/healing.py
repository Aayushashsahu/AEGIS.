"""Mission 004 healing boundary and untrusted RepairCandidate envelope.

No type or transition in this module approves, verifies, activates, commits, or
rolls back a repair. Candidate verification begins in a later mission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .immutability import deep_freeze, freeze_mapping
from .models import ProviderProvenance, utc_now


class HealState(str, Enum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANDIDATE_READY = "CANDIDATE_READY"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class HealProviderEnvelope:
    """Redacted, structured provider response facts retained as data."""

    collector_reference: str
    provider_status: str
    provider_operation_reference: str | None
    preview_result: Any
    diff_summary: str
    approval_command: str | None
    evidence_ref: str
    received_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview_result", deep_freeze(self.preview_result))


@dataclass(frozen=True)
class HealHandle:
    """Immutable snapshot of an asynchronous provider healing operation."""

    heal_id: str = field(default_factory=lambda: f"heal_{uuid4().hex}")
    repair_request_id: str = ""
    collector_reference: str = ""
    correlation_id: str = ""
    status: HealState = HealState.SUBMITTED
    provider_provenance: ProviderProvenance = ProviderProvenance.BRIGHT_DATA
    submitted_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: datetime | None = None
    provider_operation_reference: str | None = None
    provider_status: str | None = None
    evidence_refs: tuple[str, ...] = ()
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    def transition(self, state: HealState, **changes: Any) -> "HealHandle":
        allowed = {
            HealState.SUBMITTED: {HealState.RUNNING, HealState.FAILED, HealState.TIMED_OUT},
            HealState.RUNNING: {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT},
            HealState.AWAITING_APPROVAL: {HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT},
            HealState.CANDIDATE_READY: set(),
            HealState.FAILED: set(),
            HealState.TIMED_OUT: set(),
        }
        if state not in allowed[self.status]:
            raise ValueError(f"invalid heal transition: {self.status.value} -> {state.value}")
        if state is HealState.RUNNING and "started_at" not in changes:
            changes["started_at"] = utc_now()
        if state in {HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT} and "completed_at" not in changes:
            changes["completed_at"] = utc_now()
        return self.__class__(**{**self.__dict__, **changes, "status": state})


@dataclass(frozen=True)
class RepairCandidate:
    """Immutable, untrusted provider proposal awaiting later verification."""

    candidate_id: str = field(default_factory=lambda: f"candidate_{uuid4().hex}")
    repair_request_id: str = ""
    collector_reference: str = ""
    provider_operation_reference: str | None = None
    provider_status: str = ""
    preview_result: Any = None
    diff_summary: str = ""
    approval_command: str | None = None
    raw_evidence_ref: str = ""
    provenance: ProviderProvenance = ProviderProvenance.BRIGHT_DATA
    created_at: datetime = field(default_factory=utc_now)
    latency_ms: int | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview_result", deep_freeze(self.preview_result))
        if self.verification_status not in {VerificationStatus.UNVERIFIED, VerificationStatus.VERIFIED}:
            raise ValueError("RepairCandidate verification status is invalid")
        if not self.raw_evidence_ref:
            raise ValueError("RepairCandidate requires a redacted evidence reference")

    def mark_verified(self, *_: object, **__: object) -> "RepairCandidate":
        raise ValueError("candidate verification belongs to a later mission")

    def mark_accepted(self, *_: object, **__: object) -> "RepairCandidate":
        raise ValueError("candidate acceptance belongs to a later mission")

    def mark_committed(self, *_: object, **__: object) -> "RepairCandidate":
        raise ValueError("candidate commit belongs to a later mission")


@dataclass(frozen=True)
class HealOperationResult:
    handle: HealHandle
    envelope: HealProviderEnvelope | None = None
    candidate: RepairCandidate | None = None
