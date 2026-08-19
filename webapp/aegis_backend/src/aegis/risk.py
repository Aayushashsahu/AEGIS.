"""Mission 005 deterministic risk policy and metric event hooks.

This module does not expose approval, activation, commit, rollback, watch,
memory, or benchmark execution. ACCEPT means eligible for a later commit stage
only; it is not production activation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .healing import RepairCandidate
from .immutability import freeze_mapping
from .models import ProviderProvenance, utc_now
from .verification import CheckStatus, EvidenceChannel, VerificationOverallStatus, VerificationResult


class RiskDecisionType(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


class RiskReason(str, Enum):
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    DETERMINISTIC_FAILURE = "DETERMINISTIC_FAILURE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CRITICAL_CONTRADICTION = "CRITICAL_CONTRADICTION"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    CANDIDATE_NOT_UNVERIFIED = "CANDIDATE_NOT_UNVERIFIED"


@dataclass(frozen=True)
class RiskPolicy:
    """Explicit deterministic policy; no additive confidence weights."""

    required_accept_channels: tuple[EvidenceChannel, ...] = (
        EvidenceChannel.CONTRACT,
        EvidenceChannel.SEMANTIC_INVARIANT,
        EvidenceChannel.INDEPENDENT_EVIDENCE,
    )
    history_is_optional: bool = True
    unknown_requires_quarantine: bool = True
    critical_failure_requires_reject: bool = True


@dataclass(frozen=True)
class RiskDecision:
    decision_id: str = field(default_factory=lambda: f"risk_{uuid4().hex}")
    candidate_id: str = ""
    verification_id: str = ""
    decision: RiskDecisionType = RiskDecisionType.QUARANTINE
    reason_code: RiskReason = RiskReason.INSUFFICIENT_EVIDENCE
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str = ""
    provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE
    created_at: datetime = field(default_factory=utc_now)
    eligible_for_future_commit: bool = False
    production_commit_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        if self.production_commit_performed:
            raise ValueError("Mission 005 cannot perform a production commit")
        if self.decision is not RiskDecisionType.ACCEPT and self.eligible_for_future_commit:
            raise ValueError("only ACCEPT can be eligible for a future commit")


class RiskGovernor:
    """Apply the frozen evidence policy without any provider operation."""

    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()

    def decide(
        self,
        verification: VerificationResult,
        candidate: RepairCandidate,
        *,
        correlation_id: str = "",
        candidate_metadata: Mapping[str, Any] | None = None,
    ) -> RiskDecision:
        refs = tuple(sorted(set(verification.evidence_refs)))
        if candidate.verification_status.value != "UNVERIFIED":
            return RiskDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                decision=RiskDecisionType.REJECT,
                reason_code=RiskReason.CANDIDATE_NOT_UNVERIFIED,
                evidence_refs=refs,
                correlation_id=correlation_id,
                provenance=candidate.provenance,
            )
        checks_by_channel = {check.channel: check for check in verification.checks}
        critical_failures = [check for check in verification.checks if check.status is CheckStatus.FAIL and check.critical]
        if critical_failures and self.policy.critical_failure_requires_reject:
            reason = RiskReason.CRITICAL_CONTRADICTION if any(check.category in {"INDEPENDENCE", "INDEPENDENT_MATCH"} for check in critical_failures) else RiskReason.DETERMINISTIC_FAILURE
            return RiskDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                decision=RiskDecisionType.REJECT,
                reason_code=reason,
                evidence_refs=refs,
                correlation_id=correlation_id,
                provenance=candidate.provenance,
            )
        if verification.overall_status is VerificationOverallStatus.FAIL:
            return RiskDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                decision=RiskDecisionType.REJECT,
                reason_code=RiskReason.DETERMINISTIC_FAILURE,
                evidence_refs=refs,
                correlation_id=correlation_id,
                provenance=candidate.provenance,
            )
        if any(checks_by_channel.get(channel) is None or checks_by_channel[channel].status is not CheckStatus.PASS for channel in self.policy.required_accept_channels):
            return RiskDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                decision=RiskDecisionType.QUARANTINE,
                reason_code=RiskReason.UNKNOWN_EVIDENCE if verification.unknown_checks else RiskReason.INSUFFICIENT_EVIDENCE,
                evidence_refs=refs,
                correlation_id=correlation_id,
                provenance=candidate.provenance,
            )
        if verification.overall_status is not VerificationOverallStatus.PASS:
            return RiskDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                decision=RiskDecisionType.QUARANTINE,
                reason_code=RiskReason.UNKNOWN_EVIDENCE,
                evidence_refs=refs,
                correlation_id=correlation_id,
                provenance=candidate.provenance,
            )
        return RiskDecision(
            candidate_id=candidate.candidate_id,
            verification_id=verification.verification_id,
            decision=RiskDecisionType.ACCEPT,
            reason_code=RiskReason.SUFFICIENT_EVIDENCE,
            evidence_refs=refs,
            correlation_id=correlation_id,
            provenance=candidate.provenance,
            eligible_for_future_commit=True,
        )


class MetricEventType(str, Enum):
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    RISK_DECISION_RECORDED = "RISK_DECISION_RECORDED"
    COMMIT_RECORDED = "COMMIT_RECORDED"


@dataclass(frozen=True)
class MetricEvent:
    event_id: str = field(default_factory=lambda: f"metric_event_{uuid4().hex}")
    event_type: MetricEventType = MetricEventType.VERIFICATION_COMPLETED
    candidate_id: str = ""
    decision: RiskDecisionType | None = None
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


class SafetyMetricHooks:
    """Collect events needed for later metrics without running benchmarks."""

    def __init__(self) -> None:
        self._events: list[MetricEvent] = []

    def record_verification(self, result: VerificationResult) -> MetricEvent:
        event = MetricEvent(
            event_type=MetricEventType.VERIFICATION_COMPLETED,
            candidate_id=result.candidate_id,
            evidence_refs=result.evidence_refs,
            correlation_id=result.correlation_id,
        )
        self._events.append(event)
        return event

    def record_risk_decision(self, decision: RiskDecision) -> MetricEvent:
        event = MetricEvent(
            event_type=MetricEventType.RISK_DECISION_RECORDED,
            candidate_id=decision.candidate_id,
            decision=decision.decision,
            evidence_refs=decision.evidence_refs,
            correlation_id=decision.correlation_id,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[MetricEvent, ...]:
        return tuple(self._events)

    @property
    def blind_commit_count(self) -> int:
        return sum(1 for event in self._events if event.event_type is MetricEventType.COMMIT_RECORDED and event.decision is not RiskDecisionType.ACCEPT)

    @property
    def total_commit_count(self) -> int:
        return sum(1 for event in self._events if event.event_type is MetricEventType.COMMIT_RECORDED)

    @property
    def blind_commit_rate(self) -> float:
        """A zero-event safety counter; no commit operation exists in Mission 005."""
        return 0.0 if self.total_commit_count == 0 else self.blind_commit_count / self.total_commit_count

    @property
    def blind_commit_rate_status(self) -> str:
        return "NOT_APPLICABLE" if self.total_commit_count == 0 else "MEASURED"
