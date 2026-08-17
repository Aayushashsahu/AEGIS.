"""Mission 006 commit eligibility and quarantine safety boundary.

This module decides eligibility only. It never calls Bright Data, executes an
approval command, activates a provider version, writes a production output,
or performs rollback/watch/memory/benchmark operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .healing import RepairCandidate, VerificationStatus
from .immutability import freeze_mapping
from .models import ExtractionContract, ProviderProvenance, utc_now
from .risk import RiskDecision, RiskDecisionType
from .verification import CheckStatus, EvidenceChannel, VerificationOverallStatus, VerificationResult


class CommitEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


class CommitBlockReason(str, Enum):
    RISK_NOT_ACCEPT = "RISK_NOT_ACCEPT"
    VERIFICATION_NOT_PASS = "VERIFICATION_NOT_PASS"
    REQUIRED_EVIDENCE_MISSING = "REQUIRED_EVIDENCE_MISSING"
    CRITICAL_VERIFICATION_FAILURE = "CRITICAL_VERIFICATION_FAILURE"
    INVALID_CANDIDATE_PROVENANCE = "INVALID_CANDIDATE_PROVENANCE"
    CANDIDATE_NOT_VERIFIED = "CANDIDATE_NOT_VERIFIED"
    KNOWN_GOOD_MISSING = "KNOWN_GOOD_MISSING"
    INVALID_AUTHORIZATION = "INVALID_AUTHORIZATION"
    IDENTIFIERS_MISSING = "IDENTIFIERS_MISSING"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    QUARANTINED = "QUARANTINED"
    REQUISITE_REVERIFICATION = "REQUISITE_REVERIFICATION"
    PRODUCTION_SIDE_EFFECT_ATTEMPTED = "PRODUCTION_SIDE_EFFECT_ATTEMPTED"


class QuarantineStatus(str, Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"


class CommitMetricEventType(str, Enum):
    COMMIT_DECISION_RECORDED = "COMMIT_DECISION_RECORDED"
    QUARANTINE_RECORDED = "QUARANTINE_RECORDED"
    UNSAFE_REFUSAL_RECORDED = "UNSAFE_REFUSAL_RECORDED"


@dataclass(frozen=True)
class AuthorizationContext:
    """Provider-neutral authorization evidence, not an auth executor."""

    actor: str
    authorization_reference: str
    scopes: tuple[str, ...] = ()
    correlation_id: str = ""
    valid: bool = True
    provenance: str = "TEST_DOUBLE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scopes", tuple(self.scopes))

    def is_valid_for_eligibility(self) -> bool:
        return bool(
            self.valid
            and self.actor.strip()
            and self.authorization_reference.strip()
            and self.correlation_id.strip()
            and "candidate_commit_eligibility" in self.scopes
        )


@dataclass(frozen=True)
class KnownGoodVersion:
    """AEGIS-level known-good reference; not a Bright Data rollback claim."""

    pipeline_reference: str
    version_reference: str
    observation_reference: str
    verification_reference: str
    provenance: ProviderProvenance
    correlation_id: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        required = (
            self.pipeline_reference,
            self.version_reference,
            self.observation_reference,
            self.verification_reference,
            self.correlation_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("KnownGoodVersion requires all provider-neutral references")


@dataclass(frozen=True)
class CommitDecision:
    """Immutable eligibility decision; it cannot perform the downstream side effect."""

    decision_id: str = field(default_factory=lambda: f"commit_decision_{uuid4().hex}")
    candidate_id: str = ""
    verification_id: str = ""
    risk_decision_id: str = ""
    eligibility: CommitEligibility = CommitEligibility.BLOCKED
    reason_code: CommitBlockReason | None = None
    block_reasons: tuple[CommitBlockReason, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    known_good_version_reference: str | None = None
    authorization_reference: str | None = None
    correlation_id: str = ""
    provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE
    created_at: datetime = field(default_factory=utc_now)
    production_commit_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "block_reasons", tuple(dict.fromkeys(self.block_reasons)))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        if self.production_commit_performed:
            raise ValueError("Mission 006 CommitDecision cannot perform production commit")
        if self.eligibility is CommitEligibility.ELIGIBLE and self.block_reasons:
            raise ValueError("eligible decision cannot contain block reasons")
        if self.eligibility is CommitEligibility.BLOCKED and not self.block_reasons:
            raise ValueError("blocked decision requires at least one safety reason")


@dataclass(frozen=True)
class QuarantineRecord:
    """Immutable forensic record; status changes are represented as new ledger entries."""

    quarantine_id: str = field(default_factory=lambda: f"quarantine_{uuid4().hex}")
    candidate_id: str = ""
    repair_request_id: str = ""
    verification_id: str = ""
    risk_decision_id: str = ""
    risk_decision: RiskDecisionType = RiskDecisionType.QUARANTINE
    reason_code: str = ""
    failed_checks: tuple[str, ...] = ()
    unknown_checks: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    candidate_provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE
    correlation_id: str = ""
    status: QuarantineStatus = QuarantineStatus.OPEN
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    reentry_verification_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "failed_checks", tuple(self.failed_checks))
        object.__setattr__(self, "unknown_checks", tuple(self.unknown_checks))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        if not self.candidate_id or not self.verification_id or not self.risk_decision_id or not self.correlation_id:
            raise ValueError("QuarantineRecord requires candidate, verification, risk, and correlation identifiers")

    @classmethod
    def from_evaluation(
        cls,
        candidate: RepairCandidate,
        verification: VerificationResult,
        risk_decision: RiskDecision,
        *,
        reason_code: str,
        correlation_id: str,
    ) -> "QuarantineRecord":
        refs = tuple(sorted(set(verification.evidence_refs) | set(risk_decision.evidence_refs) | {candidate.raw_evidence_ref}))
        return cls(
            candidate_id=candidate.candidate_id,
            repair_request_id=candidate.repair_request_id,
            verification_id=verification.verification_id,
            risk_decision_id=risk_decision.decision_id,
            risk_decision=risk_decision.decision,
            reason_code=reason_code,
            failed_checks=verification.failed_checks,
            unknown_checks=verification.unknown_checks,
            evidence_refs=refs,
            candidate_provenance=candidate.provenance,
            correlation_id=correlation_id,
        )

    def with_status(
        self,
        status: QuarantineStatus,
        *,
        reentry_verification_id: str | None = None,
    ) -> "QuarantineRecord":
        """Return a new state record; this is representation, not release authority."""

        return QuarantineRecord(
            **{
                **self.__dict__,
                "status": status,
                "updated_at": utc_now(),
                "reentry_verification_id": reentry_verification_id,
            }
        )


@dataclass(frozen=True)
class QuarantineLedger:
    """Append-only in-memory ledger preserving every quarantine state record."""

    records: tuple[QuarantineRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))

    def append(self, record: QuarantineRecord) -> "QuarantineLedger":
        return QuarantineLedger(records=self.records + (record,))

    def record_for_decision(
        self,
        candidate: RepairCandidate,
        verification: VerificationResult,
        risk_decision: RiskDecision,
        commit_decision: CommitDecision | None = None,
    ) -> "QuarantineLedger":
        if risk_decision.decision is not RiskDecisionType.QUARANTINE and commit_decision is None:
            raise ValueError("a quarantine ledger record requires a quarantine risk decision or commit block")
        reason = (
            commit_decision.reason_code.value
            if commit_decision and commit_decision.reason_code
            else risk_decision.reason_code.value
        )
        return self.append(
            QuarantineRecord.from_evaluation(
                candidate,
                verification,
                risk_decision,
                reason_code=reason,
                correlation_id=verification.correlation_id,
            )
        )

    def current(self, quarantine_id: str) -> QuarantineRecord | None:
        current = None
        for record in self.records:
            if record.quarantine_id == quarantine_id:
                current = record
        return current

    def latest_for_candidate(self, candidate_id: str) -> QuarantineRecord | None:
        current = None
        for record in self.records:
            if record.candidate_id == candidate_id:
                current = record
        return current


@dataclass(frozen=True)
class OutputEligibility:
    eligible: bool
    candidate_id: str
    commit_decision_id: str
    reason: str
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


class OutputEligibilityBoundary:
    """Authorize only a future output path; it has no sink or write operation."""

    @staticmethod
    def evaluate(
        commit_decision: CommitDecision,
        *,
        quarantine_record: QuarantineRecord | None = None,
    ) -> OutputEligibility:
        if commit_decision.eligibility is not CommitEligibility.ELIGIBLE:
            return OutputEligibility(
                eligible=False,
                candidate_id=commit_decision.candidate_id,
                commit_decision_id=commit_decision.decision_id,
                reason="commit gate is BLOCKED",
                evidence_refs=commit_decision.evidence_refs,
                correlation_id=commit_decision.correlation_id,
            )
        if quarantine_record is not None:
            if quarantine_record.status is not QuarantineStatus.RELEASED:
                return OutputEligibility(
                    eligible=False,
                    candidate_id=commit_decision.candidate_id,
                    commit_decision_id=commit_decision.decision_id,
                    reason="candidate has an active quarantine record",
                    evidence_refs=quarantine_record.evidence_refs,
                    correlation_id=commit_decision.correlation_id,
                )
            if quarantine_record.reentry_verification_id != commit_decision.verification_id:
                return OutputEligibility(
                    eligible=False,
                    candidate_id=commit_decision.candidate_id,
                    commit_decision_id=commit_decision.decision_id,
                    reason="released quarantine requires a new verification re-entry",
                    evidence_refs=quarantine_record.evidence_refs,
                    correlation_id=commit_decision.correlation_id,
                )
        return OutputEligibility(
            eligible=True,
            candidate_id=commit_decision.candidate_id,
            commit_decision_id=commit_decision.decision_id,
            reason="eligible for a future production-output stage only",
            evidence_refs=commit_decision.evidence_refs,
            correlation_id=commit_decision.correlation_id,
        )


class CommitGate:
    """Deterministic fail-closed precondition evaluator."""

    REQUIRED_CHANNELS = (
        EvidenceChannel.CONTRACT,
        EvidenceChannel.SEMANTIC_INVARIANT,
        EvidenceChannel.INDEPENDENT_EVIDENCE,
    )

    def evaluate(
        self,
        candidate: RepairCandidate,
        verification: VerificationResult,
        risk_decision: RiskDecision,
        contract: ExtractionContract,
        known_good_version: KnownGoodVersion | None,
        authorization: AuthorizationContext | None,
        *,
        correlation_id: str,
        quarantine_record: QuarantineRecord | None = None,
    ) -> CommitDecision:
        reasons: list[CommitBlockReason] = []
        if risk_decision.decision is not RiskDecisionType.ACCEPT or not risk_decision.eligible_for_future_commit:
            reasons.append(CommitBlockReason.RISK_NOT_ACCEPT)
        if verification.overall_status is not VerificationOverallStatus.PASS or not verification.eligible_for_future_commit:
            reasons.append(CommitBlockReason.VERIFICATION_NOT_PASS)
        if any(check.status is CheckStatus.FAIL and check.critical for check in verification.checks):
            reasons.append(CommitBlockReason.CRITICAL_VERIFICATION_FAILURE)
        checks = {check.channel: check for check in verification.checks}
        for channel in self.REQUIRED_CHANNELS:
            check = checks.get(channel)
            if check is None or check.status is not CheckStatus.PASS:
                reasons.append(CommitBlockReason.REQUIRED_EVIDENCE_MISSING)
            elif not check.evidence_refs:
                reasons.append(CommitBlockReason.EVIDENCE_INCOMPLETE)
        if not verification.evidence_refs or not risk_decision.evidence_refs:
            reasons.append(CommitBlockReason.EVIDENCE_INCOMPLETE)
        if candidate.provenance not in {ProviderProvenance.BRIGHT_DATA, ProviderProvenance.TEST_DOUBLE}:
            reasons.append(CommitBlockReason.INVALID_CANDIDATE_PROVENANCE)
        if candidate.verification_status is not VerificationStatus.VERIFIED:
            reasons.append(CommitBlockReason.CANDIDATE_NOT_VERIFIED)
        if known_good_version is None:
            reasons.append(CommitBlockReason.KNOWN_GOOD_MISSING)
        elif known_good_version.correlation_id != correlation_id:
            reasons.append(CommitBlockReason.IDENTIFIERS_MISSING)
        if authorization is None or not authorization.is_valid_for_eligibility():
            reasons.append(CommitBlockReason.INVALID_AUTHORIZATION)
        elif authorization.correlation_id != correlation_id:
            reasons.append(CommitBlockReason.INVALID_AUTHORIZATION)
        if verification.correlation_id and verification.correlation_id != correlation_id:
            reasons.append(CommitBlockReason.IDENTIFIERS_MISSING)
        if risk_decision.correlation_id and risk_decision.correlation_id != correlation_id:
            reasons.append(CommitBlockReason.IDENTIFIERS_MISSING)
        required_ids = (
            candidate.candidate_id,
            candidate.repair_request_id,
            verification.verification_id,
            risk_decision.decision_id,
            correlation_id,
        )
        if any(not identifier.strip() for identifier in required_ids):
            reasons.append(CommitBlockReason.IDENTIFIERS_MISSING)
        if not candidate.raw_evidence_ref:
            reasons.append(CommitBlockReason.EVIDENCE_INCOMPLETE)
        if quarantine_record is not None:
            if quarantine_record.status is not QuarantineStatus.RELEASED:
                reasons.append(CommitBlockReason.QUARANTINED)
            elif quarantine_record.reentry_verification_id != verification.verification_id:
                reasons.append(CommitBlockReason.REQUISITE_REVERIFICATION)
        reasons = list(dict.fromkeys(reasons))
        refs = tuple(sorted(set(verification.evidence_refs) | set(risk_decision.evidence_refs) | {candidate.raw_evidence_ref}))
        if reasons:
            return CommitDecision(
                candidate_id=candidate.candidate_id,
                verification_id=verification.verification_id,
                risk_decision_id=risk_decision.decision_id,
                eligibility=CommitEligibility.BLOCKED,
                reason_code=reasons[0],
                block_reasons=tuple(reasons),
                evidence_refs=refs,
                known_good_version_reference=known_good_version.version_reference if known_good_version else None,
                authorization_reference=authorization.authorization_reference if authorization else None,
                correlation_id=correlation_id,
                provenance=candidate.provenance if candidate.provenance in {ProviderProvenance.BRIGHT_DATA, ProviderProvenance.TEST_DOUBLE} else ProviderProvenance.TEST_DOUBLE,
            )
        return CommitDecision(
            candidate_id=candidate.candidate_id,
            verification_id=verification.verification_id,
            risk_decision_id=risk_decision.decision_id,
            eligibility=CommitEligibility.ELIGIBLE,
            block_reasons=(),
            evidence_refs=refs,
            known_good_version_reference=known_good_version.version_reference if known_good_version else None,
            authorization_reference=authorization.authorization_reference if authorization else None,
            correlation_id=correlation_id,
            provenance=candidate.provenance,
        )


@dataclass(frozen=True)
class CommitMetricEvent:
    event_id: str = field(default_factory=lambda: f"commit_metric_{uuid4().hex}")
    event_type: CommitMetricEventType = CommitMetricEventType.COMMIT_DECISION_RECORDED
    candidate_id: str = ""
    commit_decision_id: str = ""
    correlation_id: str = ""
    created_at: datetime = field(default_factory=utc_now)


class CommitSafetyMetricHooks:
    """Prepare quarantine/refusal metrics without claiming measured benchmarks."""

    def __init__(self) -> None:
        self._events: list[CommitMetricEvent] = []
        self._decision_count = 0
        self._quarantine_count = 0
        self._unsafe_refusal_count = 0

    def record_commit_decision(self, decision: CommitDecision) -> CommitMetricEvent:
        self._decision_count += 1
        if CommitBlockReason.QUARANTINED in decision.block_reasons or CommitBlockReason.REQUISITE_REVERIFICATION in decision.block_reasons:
            self._quarantine_count += 1
        if decision.eligibility is CommitEligibility.BLOCKED:
            self._unsafe_refusal_count += 1
        event = CommitMetricEvent(
            event_type=CommitMetricEventType.COMMIT_DECISION_RECORDED,
            candidate_id=decision.candidate_id,
            commit_decision_id=decision.decision_id,
            correlation_id=decision.correlation_id,
        )
        self._events.append(event)
        return event

    def record_quarantine(self, record: QuarantineRecord) -> CommitMetricEvent:
        self._quarantine_count += 1
        event = CommitMetricEvent(
            event_type=CommitMetricEventType.QUARANTINE_RECORDED,
            candidate_id=record.candidate_id,
            correlation_id=record.correlation_id,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[CommitMetricEvent, ...]:
        return tuple(self._events)

    @property
    def quarantine_count(self) -> int:
        return self._quarantine_count

    @property
    def unsafe_refusal_count(self) -> int:
        return self._unsafe_refusal_count

    @property
    def quarantine_rate(self) -> float | None:
        return None if self._decision_count == 0 else self._quarantine_count / self._decision_count

    @property
    def unsafe_refusal_rate(self) -> float | None:
        return None if self._decision_count == 0 else self._unsafe_refusal_count / self._decision_count

    @property
    def metric_status(self) -> str:
        return "NOT_APPLICABLE" if self._decision_count == 0 else "INSTRUMENTED_NOT_BENCHMARKED"
