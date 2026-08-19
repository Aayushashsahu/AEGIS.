"""Mission 007 post-commit watch and regression detection.

The watch engine evaluates later Observations with the existing deterministic
detection boundary. It never repairs, approves, activates, commits, rolls back,
or modifies provider state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .commit_gate import (
    CommitDecision,
    CommitEligibility,
    KnownGoodVersion,
    QuarantineLedger,
    QuarantineRecord,
)
from .detection import evaluate_detection
from .healing import RepairCandidate, VerificationStatus
from .models import DetectionResult, ExtractionContract, Observation, ProviderProvenance, utc_now
from .risk import RiskDecision, RiskDecisionType


class WatchState(str, Enum):
    COMMITTED = "COMMITTED"
    WATCHING = "WATCHING"
    HEALTHY = "HEALTHY"
    REGRESSION = "REGRESSION"
    UNKNOWN = "UNKNOWN"
    QUARANTINED = "QUARANTINED"


class WatchResultStatus(str, Enum):
    HEALTHY = "HEALTHY"
    REGRESSION = "REGRESSION"
    UNKNOWN = "UNKNOWN"


class WatchProvenance(str, Enum):
    BRIGHT_DATA = "BRIGHT_DATA"
    TEST_DOUBLE = "TEST_DOUBLE"


@dataclass(frozen=True)
class WatchPolicy:
    """Bounded post-commit policy; unknown is not automatically quarantined."""

    policy_id: str = "mission007-default"
    require_evidence_refs: bool = True
    quarantine_min_severity: str = "L2"
    enabled: bool = True

    def should_quarantine(self, severity: str) -> bool:
        order = {"NONE": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
        return order.get(severity, 5) >= order.get(self.quarantine_min_severity, 2)


@dataclass(frozen=True)
class WatchRegistration:
    registration_id: str = field(default_factory=lambda: f"watch_registration_{uuid4().hex}")
    pipeline_reference: str = ""
    candidate_reference: str = ""
    committed_verification_reference: str = ""
    known_good_version: KnownGoodVersion | None = None
    expected_contract: ExtractionContract | None = None
    correlation_id: str = ""
    watch_policy: WatchPolicy = field(default_factory=WatchPolicy)
    candidate_provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE
    state: WatchState = WatchState.COMMITTED
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.pipeline_reference or not self.candidate_reference or not self.committed_verification_reference or not self.correlation_id:
            raise ValueError("WatchRegistration requires pipeline, candidate, verification, and correlation references")
        if self.known_good_version is None or self.expected_contract is None:
            raise ValueError("WatchRegistration requires known-good version and expected contract")
        if self.known_good_version.correlation_id != self.correlation_id:
            raise ValueError("WatchRegistration known-good correlation must match")

    def start_watching(self) -> "WatchRegistration":
        if self.state is not WatchState.COMMITTED:
            raise ValueError(f"watch registration cannot start from {self.state.value}")
        return replace(self, state=WatchState.WATCHING)

    def transition(self, state: WatchState) -> "WatchRegistration":
        allowed = {
            WatchState.COMMITTED: {WatchState.WATCHING},
            WatchState.WATCHING: {WatchState.HEALTHY, WatchState.REGRESSION, WatchState.UNKNOWN},
            WatchState.REGRESSION: {WatchState.QUARANTINED},
            WatchState.HEALTHY: set(),
            WatchState.UNKNOWN: set(),
            WatchState.QUARANTINED: set(),
        }
        if state not in allowed[self.state]:
            raise ValueError(f"invalid watch transition: {self.state.value} -> {state.value}")
        return replace(self, state=state)


@dataclass(frozen=True)
class WatchCycle:
    cycle_id: str = field(default_factory=lambda: f"watch_cycle_{uuid4().hex}")
    pipeline_reference: str = ""
    observation_reference: str = ""
    detection_reference: str = ""
    timestamp: datetime = field(default_factory=utc_now)
    status: WatchState = WatchState.WATCHING
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str = ""
    provenance: WatchProvenance = WatchProvenance.TEST_DOUBLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        if not self.pipeline_reference or not self.observation_reference or not self.detection_reference or not self.correlation_id:
            raise ValueError("WatchCycle requires pipeline, observation, detection, and correlation references")

    def transition(self, state: WatchState) -> "WatchCycle":
        allowed = {
            WatchState.WATCHING: {WatchState.HEALTHY, WatchState.REGRESSION, WatchState.UNKNOWN},
            WatchState.REGRESSION: {WatchState.QUARANTINED},
        }
        if state not in allowed.get(self.status, set()):
            raise ValueError(f"invalid watch cycle transition: {self.status.value} -> {state.value}")
        return replace(self, status=state, timestamp=utc_now())


@dataclass(frozen=True)
class WatchResult:
    cycle_id: str
    status: WatchResultStatus
    detection_reference: str
    detection: DetectionResult
    evidence_refs: tuple[str, ...]
    affected_fields: tuple[str, ...]
    severity: str
    provenance: WatchProvenance
    correlation_id: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        object.__setattr__(self, "affected_fields", tuple(dict.fromkeys(self.affected_fields)))


@dataclass(frozen=True)
class RegressionEvent:
    regression_id: str = field(default_factory=lambda: f"regression_{uuid4().hex}")
    pipeline_reference: str = ""
    candidate_reference: str = ""
    watch_cycle_reference: str = ""
    failed_evidence_refs: tuple[str, ...] = ()
    affected_fields: tuple[str, ...] = ()
    severity: str = "NONE"
    timestamp: datetime = field(default_factory=utc_now)
    correlation_id: str = ""
    provenance: WatchProvenance = WatchProvenance.TEST_DOUBLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "failed_evidence_refs", tuple(dict.fromkeys(self.failed_evidence_refs)))
        object.__setattr__(self, "affected_fields", tuple(dict.fromkeys(self.affected_fields)))
        if not self.pipeline_reference or not self.candidate_reference or not self.watch_cycle_reference or not self.correlation_id:
            raise ValueError("RegressionEvent requires pipeline, candidate, cycle, and correlation references")


@dataclass(frozen=True)
class WatchEvaluation:
    registration: WatchRegistration
    cycle: WatchCycle
    result: WatchResult
    regression_event: RegressionEvent | None = None
    quarantine_ledger: QuarantineLedger | None = None
    quarantine_record: QuarantineRecord | None = None


class WatchMetricEventType(str, Enum):
    WATCH_RESULT_RECORDED = "WATCH_RESULT_RECORDED"
    REGRESSION_RECORDED = "REGRESSION_RECORDED"
    WATCH_UNKNOWN_RECORDED = "WATCH_UNKNOWN_RECORDED"
    WATCH_QUARANTINE_RECORDED = "WATCH_QUARANTINE_RECORDED"


@dataclass(frozen=True)
class WatchMetricEvent:
    event_id: str = field(default_factory=lambda: f"watch_metric_{uuid4().hex}")
    event_type: WatchMetricEventType = WatchMetricEventType.WATCH_RESULT_RECORDED
    cycle_id: str = ""
    correlation_id: str = ""
    created_at: datetime = field(default_factory=utc_now)


class WatchMetricHooks:
    """Instrument watch outcomes for later metrics; no benchmark execution."""

    def __init__(self) -> None:
        self._events: list[WatchMetricEvent] = []
        self._cycle_count = 0
        self._regression_count = 0
        self._unknown_count = 0
        self._quarantine_count = 0

    def record(self, evaluation: WatchEvaluation) -> tuple[WatchMetricEvent, ...]:
        self._cycle_count += 1
        created: list[WatchMetricEvent] = [
            WatchMetricEvent(
                event_type=WatchMetricEventType.WATCH_RESULT_RECORDED,
                cycle_id=evaluation.cycle.cycle_id,
                correlation_id=evaluation.result.correlation_id,
            )
        ]
        if evaluation.result.status is WatchResultStatus.REGRESSION:
            self._regression_count += 1
            created.append(WatchMetricEvent(
                event_type=WatchMetricEventType.REGRESSION_RECORDED,
                cycle_id=evaluation.cycle.cycle_id,
                correlation_id=evaluation.result.correlation_id,
            ))
        if evaluation.result.status is WatchResultStatus.UNKNOWN:
            self._unknown_count += 1
            created.append(WatchMetricEvent(
                event_type=WatchMetricEventType.WATCH_UNKNOWN_RECORDED,
                cycle_id=evaluation.cycle.cycle_id,
                correlation_id=evaluation.result.correlation_id,
            ))
        if evaluation.quarantine_record is not None:
            self._quarantine_count += 1
            created.append(WatchMetricEvent(
                event_type=WatchMetricEventType.WATCH_QUARANTINE_RECORDED,
                cycle_id=evaluation.cycle.cycle_id,
                correlation_id=evaluation.result.correlation_id,
            ))
        self._events.extend(created)
        return tuple(created)

    @property
    def events(self) -> tuple[WatchMetricEvent, ...]:
        return tuple(self._events)

    @property
    def regression_rate(self) -> float | None:
        return None if self._cycle_count == 0 else self._regression_count / self._cycle_count

    @property
    def watch_failure_rate(self) -> float | None:
        return None if self._cycle_count == 0 else self._unknown_count / self._cycle_count

    @property
    def unsafe_refusal_rate(self) -> float | None:
        return None if self._regression_count == 0 else self._quarantine_count / self._regression_count

    @property
    def metric_status(self) -> str:
        return "NOT_APPLICABLE" if self._cycle_count == 0 else "INSTRUMENTED_NOT_BENCHMARKED"


class WatchEngine:
    """Evaluate a post-commit Observation; no repair or rollback operations exist."""

    def register(
        self,
        candidate: RepairCandidate,
        verification: Any,
        risk_decision: RiskDecision,
        commit_decision: CommitDecision,
        known_good_version: KnownGoodVersion,
        contract: ExtractionContract,
        *,
        pipeline_reference: str,
        correlation_id: str,
        watch_policy: WatchPolicy | None = None,
    ) -> WatchRegistration:
        if commit_decision.eligibility is not CommitEligibility.ELIGIBLE:
            raise ValueError("watch registration requires an ELIGIBLE CommitDecision")
        if risk_decision.decision is not RiskDecisionType.ACCEPT:
            raise ValueError("watch registration requires RiskDecision.ACCEPT")
        if getattr(verification, "overall_status", None).value != "PASS":
            raise ValueError("watch registration requires a passing verification")
        if candidate.verification_status is not VerificationStatus.VERIFIED:
            raise ValueError("watch registration requires a verified candidate")
        if commit_decision.correlation_id != correlation_id or known_good_version.correlation_id != correlation_id:
            raise ValueError("watch registration correlation mismatch")
        return WatchRegistration(
            pipeline_reference=pipeline_reference,
            candidate_reference=candidate.candidate_id,
            committed_verification_reference=verification.verification_id,
            known_good_version=known_good_version,
            expected_contract=contract,
            correlation_id=correlation_id,
            watch_policy=watch_policy or WatchPolicy(),
            candidate_provenance=candidate.provenance,
        )

    def evaluate(
        self,
        registration: WatchRegistration,
        observation: Observation,
        *,
        observation_reference: str,
        ledger: QuarantineLedger | None = None,
    ) -> WatchEvaluation:
        if not registration.watch_policy.enabled:
            raise ValueError("watch policy is disabled")
        active = registration.start_watching() if registration.state is WatchState.COMMITTED else registration
        if active.state is not WatchState.WATCHING:
            raise ValueError("watch evaluation requires a WATCHING registration")
        detection = evaluate_detection(observation, active.expected_contract)
        detection_reference = f"detection_{uuid4().hex}"
        refs = tuple(sorted(set(observation.evidence_refs) | set(detection.evidence_refs)))
        provenance = WatchProvenance(active.candidate_provenance.value)
        cycle = WatchCycle(
            pipeline_reference=active.pipeline_reference,
            observation_reference=observation_reference,
            detection_reference=detection_reference,
            status=WatchState.WATCHING,
            evidence_refs=refs,
            correlation_id=active.correlation_id,
            provenance=provenance,
        )
        if active.watch_policy.require_evidence_refs and not observation.evidence_refs:
            result = WatchResult(
                cycle_id=cycle.cycle_id,
                status=WatchResultStatus.UNKNOWN,
                detection_reference=detection_reference,
                detection=detection,
                evidence_refs=refs,
                affected_fields=detection.affected_fields,
                severity=detection.severity,
                provenance=provenance,
                correlation_id=active.correlation_id,
            )
            return WatchEvaluation(registration=active.transition(WatchState.UNKNOWN), cycle=cycle.transition(WatchState.UNKNOWN), result=result, quarantine_ledger=ledger)
        if not detection.detected:
            result = WatchResult(
                cycle_id=cycle.cycle_id,
                status=WatchResultStatus.HEALTHY,
                detection_reference=detection_reference,
                detection=detection,
                evidence_refs=refs,
                affected_fields=(),
                severity="NONE",
                provenance=provenance,
                correlation_id=active.correlation_id,
            )
            return WatchEvaluation(registration=active.transition(WatchState.HEALTHY), cycle=cycle.transition(WatchState.HEALTHY), result=result, quarantine_ledger=ledger)
        regression = RegressionEvent(
            pipeline_reference=active.pipeline_reference,
            candidate_reference=active.candidate_reference,
            watch_cycle_reference=cycle.cycle_id,
            failed_evidence_refs=refs,
            affected_fields=detection.affected_fields,
            severity=detection.severity,
            correlation_id=active.correlation_id,
            provenance=provenance,
        )
        result = WatchResult(
            cycle_id=cycle.cycle_id,
            status=WatchResultStatus.REGRESSION,
            detection_reference=detection_reference,
            detection=detection,
            evidence_refs=refs,
            affected_fields=detection.affected_fields,
            severity=detection.severity,
            provenance=provenance,
            correlation_id=active.correlation_id,
        )
        next_ledger = ledger
        quarantine_record = None
        next_registration = active.transition(WatchState.REGRESSION)
        next_cycle = cycle.transition(WatchState.REGRESSION)
        if active.watch_policy.should_quarantine(detection.severity):
            quarantine_id = f"quarantine_{regression.regression_id}"
            next_ledger = (ledger or QuarantineLedger()).record_watch_regression(
                quarantine_id=quarantine_id,
                candidate_id=active.candidate_reference,
                registration_id=active.registration_id,
                verification_id=active.committed_verification_reference,
                reason_code=f"WATCH_REGRESSION_{detection.severity}",
                failed_checks=tuple(signal.code for signal in detection.signals),
                evidence_refs=refs,
                candidate_provenance=active.candidate_provenance,
                correlation_id=active.correlation_id,
            )
            quarantine_record = next_ledger.latest_for_candidate(active.candidate_reference)
            next_registration = next_registration.transition(WatchState.QUARANTINED)
            next_cycle = next_cycle.transition(WatchState.QUARANTINED)
        return WatchEvaluation(
            registration=next_registration,
            cycle=next_cycle,
            result=result,
            regression_event=regression,
            quarantine_ledger=next_ledger,
            quarantine_record=quarantine_record,
        )
