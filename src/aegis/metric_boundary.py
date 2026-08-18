"""Mission 022 compatibility boundary for Mission 010 metrics.

The adapter preserves the complete ParticipantRunEvidence record and creates a
separate immutable, provider-neutral metric-input projection. It never defines
or evaluates a metric formula. Metric calculation is delegated to the existing
``aegis.mutation_metrics.calculate_metrics`` function only after all source
records and evaluator-owned ground truth references pass validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from . import mutation_metrics
from .audit_store import _to_jsonable
from .benchmark_runner import ParticipantRunEvidence, RunnerState
from .immutability import freeze_mapping
from .models import ProviderProvenance
from .mutation_lab import MutationGroundTruth, MutationOutcome, MutationRun


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


METRIC_COMPATIBILITY_MATRIX: Mapping[str, Mapping[str, Any]] = freeze_mapping(
    {
        "DetectionRate": {
            "numerator_source": "metric_input.detected where joined truth severity != L1",
            "denominator_source": "joined MutationGroundTruth severity != L1",
            "required_evidence": ("detected", "ground_truth_reference", "mutation_id", "severity"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records with boolean detection; Baseline A/B are NOT_APPLICABLE",
        },
        "AlarmPrecision": {
            "numerator_source": "metric_input.detected alarms whose joined truth severity != L1",
            "denominator_source": "metric_input.detected alarms",
            "required_evidence": ("detected", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records with boolean detection; Baseline A/B are NOT_APPLICABLE",
        },
        "VerifiedRecovery": {
            "numerator_source": "Mission010 fixed unavailable formula; no repair path",
            "denominator_source": "Mission010 fixed unavailable formula; no repair episodes",
            "required_evidence": ("verification_status", "output_eligible", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "VerificationMissRate": {
            "numerator_source": "Mission010 fixed unavailable formula; no committed repairs",
            "denominator_source": "Mission010 fixed unavailable formula; no commit denominator",
            "required_evidence": ("verification_status", "commit_eligibility", "output_eligible"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "FalseRepairRate": {
            "numerator_source": "Mission010 fixed unavailable formula; no repair-attempt formula",
            "denominator_source": "Mission010 fixed unavailable formula; no repair-attempt denominator",
            "required_evidence": ("candidate", "candidate_accepted", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "UnsafeRefusalRate": {
            "numerator_source": "metric_input.risk_decision in REJECT/QUARANTINE and not output_eligible",
            "denominator_source": "joined truth severity == L5",
            "required_evidence": ("risk_decision", "output_eligible", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records with boolean risk/output fields; Baseline A/B are NOT_APPLICABLE",
        },
        "BlindCommitRate": {
            "numerator_source": "Mission010 fixed unavailable formula; no commit denominator",
            "denominator_source": "Mission010 fixed unavailable formula; no commit denominator",
            "required_evidence": ("commit_eligibility", "verification_status", "risk_decision"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "MTTR": {
            "numerator_source": "Mission010 fixed unavailable formula; no verified commit timestamp",
            "denominator_source": "Mission010 fixed unavailable formula; no verified commit episodes",
            "required_evidence": ("timing_ms", "verification_status", "commit_eligibility"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "CostPerRepair": {
            "numerator_source": "Mission010 fixed unavailable formula; no cost ledger",
            "denominator_source": "Mission010 fixed unavailable formula; no repair episodes",
            "required_evidence": ("cost", "candidate_accepted"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "LLMCallsPerRepair": {
            "numerator_source": "Mission010 fixed unavailable formula; no repair episodes",
            "denominator_source": "Mission010 fixed unavailable formula; no repair episodes",
            "required_evidence": ("llm_calls", "candidate_accepted"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY if a future formula is requested",
            "supported_scope": "NOT_APPLICABLE under Mission010 v1",
        },
        "L5DetectionRate": {
            "numerator_source": "metric_input.detected for joined truth severity == L5",
            "denominator_source": "joined truth severity == L5",
            "required_evidence": ("detected", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records with boolean detection; Baseline A/B are NOT_APPLICABLE",
        },
        "L5QuarantineRate": {
            "numerator_source": "metric_input.quarantine_reference is not null for joined L5 truth",
            "denominator_source": "joined truth severity == L5",
            "required_evidence": ("quarantine_reference", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records; Baseline A/B quarantine is NOT_APPLICABLE",
        },
        "L5VerifiedReExtraction": {
            "numerator_source": "Not implemented by Mission010 v1",
            "denominator_source": "Not implemented by Mission010 v1",
            "required_evidence": ("verification_status", "ground_truth_reference", "output_eligible"),
            "zero_denominator": "Mission010 does not expose this metric",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "UNAVAILABLE_IN_MISSION010_V1",
        },
        "L5BadDataShippedRate": {
            "numerator_source": "metric_input.output_eligible for joined L5 truth",
            "denominator_source": "joined truth severity == L5",
            "required_evidence": ("output_eligible", "ground_truth_reference"),
            "zero_denominator": "Mission010 MetricStatus.NOT_APPLICABLE with value=null",
            "missing_evidence": "FAILED_METRIC_BOUNDARY",
            "supported_scope": "AEGIS records with boolean output eligibility; Baseline B policy output is preserved but not used as AEGIS shipment evidence",
        },
    }
)


@dataclass(frozen=True)
class MetricMutationInput:
    """Immutable duck-typed input accepted by Mission 010 without formula changes."""

    run_id: str
    mutation_id: str
    seed: int
    collector_reference: str
    observation_reference: str
    detection_reference: str
    verification_reference: str | None
    risk_decision_reference: str | None
    ground_truth_reference: str
    detected: bool
    detected_by_existing_detection: bool | str
    detector_severity: str
    outcome: MutationOutcome
    provenance: ProviderProvenance
    timing_ms: Mapping[str, int]
    verification_status: str
    risk_decision: str
    commit_eligibility: str
    output_eligible: bool
    quarantine_reference: str | None
    evidence_refs: tuple[str, ...]
    created_at: datetime
    participant_id: str
    participant_configuration_hash: str
    participant_revision: str
    configuration_hash: str
    benchmark_id: str
    fixture_version: str
    artifact_refs: tuple[str, ...]
    trial_number: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "timing_ms", freeze_mapping(self.timing_ms))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        object.__setattr__(self, "artifact_refs", tuple(dict.fromkeys(self.artifact_refs)))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class ParticipantEvidenceContext:
    """Immutable RunManifest context joined by run ID after execution."""

    run_id: str
    benchmark_id: str
    configuration_hash: str
    participant_configuration_hash: str
    participant_revision: str
    mutation_id: str
    severity: str
    seed: int
    fixture_version: str
    ground_truth_reference: str
    trial_number: int
    artifact_root: str
    artifact_name: str


@dataclass(frozen=True)
class EvidenceCompatibilityRecord:
    """One source-evidence record and its lossless bridge disposition."""

    source_evidence: ParticipantRunEvidence
    context: ParticipantEvidenceContext | None
    metric_input: MetricMutationInput | None
    source_ground_truth_reference: str
    normalized_ground_truth_reference: str
    ground_truth_joined: bool
    metric_eligible: bool
    reason: str
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(
            {
                "source_evidence": self.source_evidence,
                "context": self.context,
                "metric_input": self.metric_input,
                "source_ground_truth_reference": self.source_ground_truth_reference,
                "normalized_ground_truth_reference": self.normalized_ground_truth_reference,
                "ground_truth_joined": self.ground_truth_joined,
                "metric_eligible": self.metric_eligible,
                "reason": self.reason,
                "missing_fields": self.missing_fields,
                "preserved_fields": _preserved_fields(self.source_evidence, self.context),
            }
        )


@dataclass(frozen=True)
class MetricCompatibilityReport:
    records: tuple[EvidenceCompatibilityRecord, ...]
    metric_inputs: tuple[MetricMutationInput, ...]
    ground_truths: Mapping[str, MutationGroundTruth]
    metric_matrix: Mapping[str, Mapping[str, Any]]
    fatal_errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "metric_inputs", tuple(self.metric_inputs))
        object.__setattr__(self, "ground_truths", freeze_mapping(self.ground_truths))
        object.__setattr__(self, "metric_matrix", freeze_mapping(self.metric_matrix))
        object.__setattr__(self, "fatal_errors", tuple(self.fatal_errors))

    @property
    def passed(self) -> bool:
        """Whether all supplied evidence adapted without an integrity failure."""
        return not self.fatal_errors and bool(self.records)

    @property
    def metric_calculation_ready(self) -> bool:
        """Whether Mission 010 has a non-empty honest input scope."""
        return self.passed and bool(self.metric_inputs)

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(
            {
                "compatibility_version": "mission-022-metric-boundary-v1",
                "passed": self.passed,
                "metric_calculation_ready": self.metric_calculation_ready,
                "record_count": len(self.records),
                "metric_input_count": len(self.metric_inputs),
                "metric_input_scope": tuple(sorted({item.participant_id for item in self.metric_inputs})),
                "ground_truth_joined_count": sum(1 for record in self.records if record.ground_truth_joined),
                "fatal_errors": self.fatal_errors,
                "metric_matrix": self.metric_matrix,
                "records": self.records,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


def _trial_number(evidence: ParticipantRunEvidence) -> int:
    if "__trial-" in evidence.run_id:
        return int(evidence.run_id.split("__trial-", 1)[1].split("__", 1)[0])
    return 1


def _stable_truth_id(evidence: ParticipantRunEvidence) -> str:
    digest = hashlib.sha256(evidence.ground_truth_reference.encode("utf-8")).hexdigest()[:16]
    return f"{evidence.mutation_id}-{evidence.seed}-trial-{_trial_number(evidence)}-{digest}"


def _resolve_truth(reference: str, ground_truths: Mapping[str, MutationGroundTruth]) -> MutationGroundTruth | None:
    if reference in ground_truths:
        return ground_truths[reference]
    return ground_truths.get(reference.rsplit("/", 1)[-1])


def _reference(evidence: ParticipantRunEvidence, prefix: str) -> str | None:
    return next((item for item in evidence.evidence_refs if item.startswith(prefix)), None)


def _quarantine_reference(evidence: ParticipantRunEvidence) -> str | None:
    return _reference(evidence, "quarantine://")


def _preserved_fields(evidence: ParticipantRunEvidence, context: ParticipantEvidenceContext | None = None) -> Mapping[str, Any]:
    return {
        "benchmark_id": context.benchmark_id if context is not None else evidence.run_id.split("__", 1)[0],
        "configuration_hash": evidence.configuration_hash,
        "participant_configuration_hash": None if context is None else context.participant_configuration_hash,
        "participant_id": evidence.participant_id,
        "participant_revision": evidence.participant_revision,
        "mutation_id": evidence.mutation_id,
        "severity": evidence.severity,
        "trial_number": _trial_number(evidence) if context is None else context.trial_number,
        "seed": evidence.seed,
        "fixture_version": evidence.fixture_version,
        "ground_truth_reference": evidence.ground_truth_reference,
        "run_id": evidence.run_id,
        "state": evidence.state.value if isinstance(evidence.state, RunnerState) else str(evidence.state),
        "detection": evidence.detected,
        "candidate": evidence.candidate,
        "candidate_application": evidence.candidate_application,
        "verification": evidence.verification_status,
        "risk": evidence.risk_decision,
        "output_eligible": evidence.output_eligible,
        "timings": evidence.timing_ms,
        "cost": evidence.cost,
        "llm_calls": evidence.llm_calls,
        "evidence_refs": evidence.evidence_refs,
        "artifact_refs": evidence.artifact_refs,
        "provenance": evidence.provenance,
    }


def adapt_completed_evidence(
    evidence_records: Sequence[ParticipantRunEvidence],
    ground_truths_by_reference: Mapping[str, MutationGroundTruth],
    contexts_by_run_id: Mapping[str, ParticipantEvidenceContext] | None = None,
) -> MetricCompatibilityReport:
    """Adapt all completed evidence and join truth only after participant execution."""

    ordered = tuple(sorted(evidence_records, key=lambda item: item.run_id))
    records: list[EvidenceCompatibilityRecord] = []
    metric_inputs: list[MetricMutationInput] = []
    joined_truths: dict[str, MutationGroundTruth] = {}
    fatal: list[str] = []
    seen_ids: set[str] = set()
    contexts = contexts_by_run_id or {}

    for evidence in ordered:
        context = contexts.get(evidence.run_id)
        missing: list[str] = []
        if context is None:
            missing.append("participant_configuration_hash/trial_number manifest context")
        elif context.run_id != evidence.run_id or context.ground_truth_reference != evidence.ground_truth_reference:
            fatal.append(f"manifest/evidence identity mismatch for {evidence.run_id}")
            missing.append("matching manifest context")
        if evidence.run_id in seen_ids:
            fatal.append(f"duplicate run_id: {evidence.run_id}")
        seen_ids.add(evidence.run_id)
        if evidence.state is not RunnerState.COMPLETED:
            missing.append("state=COMPLETED")
        if not evidence.evidence_refs:
            missing.append("evidence_refs")
        if not evidence.artifact_refs:
            missing.append("artifact_refs")
        truth = _resolve_truth(evidence.ground_truth_reference, ground_truths_by_reference)
        if truth is None:
            fatal.append(f"missing evaluator ground truth for {evidence.run_id}: {evidence.ground_truth_reference}")
            missing.append("MutationGroundTruth")
        elif truth.mutation_id != evidence.mutation_id or truth.seed != evidence.seed or truth.severity.value != evidence.severity:
            fatal.append(f"ground-truth identity mismatch for {evidence.run_id}")
            missing.append("matching MutationGroundTruth identity")

        stable_id = _stable_truth_id(evidence)
        normalized_reference = f"ground-truth://mission-022/{stable_id}"
        if truth is not None:
            joined_truths[stable_id] = truth

        metric_eligible = (
            not missing
            and evidence.participant_id == "AEGIS"
            and isinstance(evidence.detected, bool)
            and isinstance(evidence.risk_decision, str)
            and isinstance(evidence.output_eligible, bool)
        )
        reason = "AEGIS metric fields complete" if metric_eligible else "participant fields are NOT_APPLICABLE for Mission010 metric scope"
        metric_input: MetricMutationInput | None = None
        if metric_eligible:
            metric_input = MetricMutationInput(
                run_id=evidence.run_id,
                mutation_id=evidence.mutation_id,
                seed=evidence.seed,
                collector_reference="participant-run-evidence-bridge",
                observation_reference=evidence.observation_reference,
                detection_reference=_reference(evidence, "detection://") or evidence.observation_reference,
                verification_reference=_reference(evidence, "verification://"),
                risk_decision_reference=_reference(evidence, "risk://"),
                ground_truth_reference=normalized_reference,
                detected=evidence.detected,
                detected_by_existing_detection="NOT_APPLICABLE",
                detector_severity="NOT_APPLICABLE",
                outcome=MutationOutcome.UNKNOWN,
                provenance=ProviderProvenance.TEST_DOUBLE,
                timing_ms=evidence.timing_ms,
                verification_status=evidence.verification_status,
                risk_decision=evidence.risk_decision,
                commit_eligibility="NOT_APPLICABLE",
                output_eligible=evidence.output_eligible,
                quarantine_reference=_quarantine_reference(evidence),
                evidence_refs=tuple(evidence.evidence_refs) + tuple(evidence.artifact_refs),
                created_at=EPOCH,
                participant_id=evidence.participant_id,
                participant_configuration_hash=context.participant_configuration_hash if context is not None else "NOT_PROVIDED",
                participant_revision=evidence.participant_revision,
                configuration_hash=evidence.configuration_hash,
                benchmark_id=context.benchmark_id if context is not None else evidence.run_id.split("__", 1)[0],
                fixture_version=context.fixture_version if context is not None else evidence.fixture_version,
                artifact_refs=evidence.artifact_refs,
                trial_number=context.trial_number if context is not None else _trial_number(evidence),
            )
            metric_inputs.append(metric_input)
        elif missing:
            fatal.append(f"missing required bridge evidence for {evidence.run_id}: {', '.join(sorted(set(missing)))}")

        records.append(
            EvidenceCompatibilityRecord(
                source_evidence=evidence,
                context=context,
                metric_input=metric_input,
                source_ground_truth_reference=evidence.ground_truth_reference,
                normalized_ground_truth_reference=normalized_reference,
                ground_truth_joined=truth is not None,
                metric_eligible=metric_eligible,
                reason=reason,
                missing_fields=tuple(sorted(set(missing))),
            )
        )

    return MetricCompatibilityReport(
        records=tuple(records),
        metric_inputs=tuple(metric_inputs),
        ground_truths=joined_truths,
        metric_matrix=METRIC_COMPATIBILITY_MATRIX,
        fatal_errors=tuple(sorted(set(fatal))),
    )


def calculate_compatibility_metrics(report: MetricCompatibilityReport):
    """Invoke only Mission 010’s existing calculator after bridge validation."""

    if not report.metric_calculation_ready:
        raise MetricBoundaryError("FAILED_METRIC_BOUNDARY: " + "; ".join(report.fatal_errors or ("no eligible metric inputs",)))
    return mutation_metrics.calculate_metrics(report.metric_inputs, report.ground_truths, generated_at=None)


class MetricBoundaryError(RuntimeError):
    pass


__all__ = [
    "EvidenceCompatibilityRecord",
    "ParticipantEvidenceContext",
    "METRIC_COMPATIBILITY_MATRIX",
    "MetricBoundaryError",
    "MetricCompatibilityReport",
    "MetricMutationInput",
    "adapt_completed_evidence",
    "calculate_compatibility_metrics",
]
