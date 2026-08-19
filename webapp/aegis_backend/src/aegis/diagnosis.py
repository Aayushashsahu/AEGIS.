"""Mission 003: Detection → Diagnosis → Repair Request.

This module contains provider-neutral domain records and bounded diagnostician
seams. It does not execute healing, approve repairs, activate candidates, or
commit provider state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from .immutability import deep_freeze, freeze_mapping
from .models import DetectionResult, DetectionSignal, ExtractionContract, Observation, utc_now


class FailureClass(str, Enum):
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    STRUCTURAL_DRIFT = "STRUCTURAL_DRIFT"
    STATISTICAL_DRIFT = "STATISTICAL_DRIFT"
    SEMANTIC_INVARIANT = "SEMANTIC_INVARIANT"
    SILENT_CORRUPTION = "SILENT_CORRUPTION"
    BEHAVIORAL_DRIFT = "BEHAVIORAL_DRIFT"
    NETWORK_DRIFT = "NETWORK_DRIFT"
    UNKNOWN = "UNKNOWN"


class DiagnosisStatus(str, Enum):
    CREATED = "CREATED"
    REPAIR_REQUESTED = "REPAIR_REQUESTED"


class DiagnosisCertainty(str, Enum):
    """Qualitative certainty; no additive or probabilistic confidence is used."""

    DETERMINED = "DETERMINED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class DiagnosisProvenance(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    TEST_DOUBLE = "TEST_DOUBLE"
    MODEL_ASSISTED = "MODEL_ASSISTED"


class RepairRequestStatus(str, Enum):
    REPAIR_REQUESTED = "REPAIR_REQUESTED"


class RepairBoundaryProvenance(str, Enum):
    TEST_DOUBLE = "TEST_DOUBLE"
    PROVIDER_ADAPTER = "PROVIDER_ADAPTER"


class RepairAttemptState(str, Enum):
    REQUESTED = "REQUESTED"


@dataclass(frozen=True)
class DiagnosisContext:
    """Typed, bounded input to any diagnostician implementation."""

    observation: Observation
    detection: DetectionResult
    contract: ExtractionContract
    detection_id: str
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class Diagnosis:
    """Immutable explanation of a detected anomaly, before repair execution."""

    diagnosis_id: str = field(default_factory=lambda: f"diagnosis_{uuid4().hex}")
    observation_id: str = ""
    detection_id: str = ""
    correlation_id: str = ""
    failure_class: FailureClass = FailureClass.UNKNOWN
    candidate_classes: tuple[FailureClass, ...] = ()
    severity: str = "UNKNOWN"
    affected_fields: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    detector_provenance: tuple[str, ...] = ()
    rationale: str = ""
    certainty: DiagnosisCertainty = DiagnosisCertainty.UNKNOWN
    diagnosis_provenance: DiagnosisProvenance = DiagnosisProvenance.DETERMINISTIC
    timestamp: Any = field(default_factory=utc_now)
    status: DiagnosisStatus = DiagnosisStatus.CREATED

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_classes", tuple(self.candidate_classes))
        object.__setattr__(self, "affected_fields", tuple(self.affected_fields))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "detector_provenance", tuple(self.detector_provenance))

    def mark_repair_requested(self) -> "Diagnosis":
        if self.status is not DiagnosisStatus.CREATED:
            raise ValueError(f"invalid diagnosis transition: {self.status.value} -> REPAIR_REQUESTED")
        return Diagnosis(**{**self.__dict__, "status": DiagnosisStatus.REPAIR_REQUESTED})


@dataclass(frozen=True)
class RepairRequest:
    """Provider-neutral description of what should be restored, not how."""

    repair_request_id: str = field(default_factory=lambda: f"repair_request_{uuid4().hex}")
    collector_reference: str = ""
    observation_id: str = ""
    diagnosis_id: str = ""
    detection_id: str = ""
    correlation_id: str = ""
    affected_fields: tuple[str, ...] = ()
    failure_class: FailureClass = FailureClass.UNKNOWN
    severity: str = "UNKNOWN"
    extraction_contract: ExtractionContract | None = None
    evidence_references: tuple[str, ...] = ()
    target_input: Mapping[str, Any] = field(default_factory=dict)
    repair_objective: str = ""
    constraints: tuple[str, ...] = ()
    mutation_context: Mapping[str, Any] = field(default_factory=dict)
    provenance: DiagnosisProvenance = DiagnosisProvenance.DETERMINISTIC
    timestamp: Any = field(default_factory=utc_now)
    status: RepairRequestStatus = RepairRequestStatus.REPAIR_REQUESTED

    def __post_init__(self) -> None:
        object.__setattr__(self, "affected_fields", tuple(self.affected_fields))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "target_input", freeze_mapping(self.target_input))
        object.__setattr__(self, "mutation_context", freeze_mapping(self.mutation_context))
        if not self.collector_reference:
            raise ValueError("collector_reference is required")
        if self.extraction_contract is None:
            raise ValueError("extraction_contract is required")
        if "commit" in self.repair_objective.lower() or "approve" in self.repair_objective.lower():
            raise ValueError("RepairRequest cannot authorize approval or commit")

    @classmethod
    def from_diagnosis(
        cls,
        diagnosis: Diagnosis,
        *,
        observation: Observation,
        contract: ExtractionContract,
        target_input: Mapping[str, Any] | None = None,
        mutation_context: Mapping[str, Any] | None = None,
    ) -> "RepairRequest":
        if diagnosis.status is not DiagnosisStatus.CREATED:
            raise ValueError("only a newly created Diagnosis can produce a RepairRequest")
        affected = tuple(diagnosis.affected_fields)
        expected = tuple(contract.expected_schema) or tuple(field.name for field in contract.fields)
        unaffected = tuple(field for field in expected if field not in affected)
        affected_text = ", ".join(affected) if affected else "the contract-defined fields"
        unaffected_text = ", ".join(unaffected) if unaffected else "all unaffected fields"
        if diagnosis.failure_class is FailureClass.UNKNOWN:
            objective = (
                "Investigate the detected anomaly and propose a bounded repair hypothesis without "
                "changing the output schema or shipping data."
            )
            constraints = (
                "Do not infer an unobserved failure class.",
                "Do not approve, activate, or commit a candidate.",
            )
        else:
            objective = (
                f"Restore extraction of {affected_text} without changing the output schema, "
                f"while preserving {unaffected_text}."
            )
            constraints = (
                "Preserve the frozen extraction contract and its field semantics.",
                "Preserve known invariants and unaffected fields.",
                "Do not approve, activate, or commit a candidate.",
            )
        evidence = tuple(sorted(set(diagnosis.evidence_references) | set(observation.evidence_refs)))
        return cls(
            collector_reference=observation.collector_id,
            observation_id=diagnosis.observation_id,
            diagnosis_id=diagnosis.diagnosis_id,
            detection_id=diagnosis.detection_id,
            correlation_id=diagnosis.correlation_id,
            affected_fields=affected,
            failure_class=diagnosis.failure_class,
            severity=diagnosis.severity,
            extraction_contract=contract,
            evidence_references=evidence,
            target_input=target_input if target_input is not None else observation.input,
            repair_objective=objective,
            constraints=constraints,
            mutation_context=mutation_context or {},
            provenance=diagnosis.diagnosis_provenance,
        )


@dataclass(frozen=True)
class RepairAttemptHandle:
    """Provider-neutral request acknowledgement; no provider operation is run here."""

    attempt_id: str = field(default_factory=lambda: f"repair_attempt_{uuid4().hex}")
    repair_request_id: str = ""
    status: RepairAttemptState = RepairAttemptState.REQUESTED
    provenance: RepairBoundaryProvenance = RepairBoundaryProvenance.TEST_DOUBLE
    provider_operation_reference: str | None = None
    execution_started: bool = False
    timestamp: Any = field(default_factory=utc_now)


class Diagnostician(Protocol):
    def diagnose(self, context: DiagnosisContext) -> Diagnosis | None:
        """Return a Diagnosis, or None when the DetectionResult is healthy."""


class HealingRequester(Protocol):
    def request_healing(self, repair_request: RepairRequest) -> RepairAttemptHandle:
        """A later provider adapter may implement this; Mission 003 only defines it."""


_CODE_TO_CLASS: dict[str, FailureClass] = {
    "MISSING_FIELD": FailureClass.SCHEMA_DRIFT,
    "NULL_FIELD": FailureClass.SCHEMA_DRIFT,
    "INVALID_TYPE": FailureClass.SCHEMA_DRIFT,
    "UNEXPECTED_FIELD": FailureClass.SCHEMA_DRIFT,
    "DOM_RELOCATION": FailureClass.STRUCTURAL_DRIFT,
    "ORDER_CHANGED": FailureClass.STRUCTURAL_DRIFT,
    "UNEXPECTED_WRAPPER": FailureClass.STRUCTURAL_DRIFT,
    "ROW_COUNT_TOO_LOW": FailureClass.STATISTICAL_DRIFT,
    "ROW_COUNT_TOO_HIGH": FailureClass.STATISTICAL_DRIFT,
    "ROW_COUNT_ANOMALY": FailureClass.STATISTICAL_DRIFT,
    "IMPOSSIBLE_NUMERIC_VALUE": FailureClass.STATISTICAL_DRIFT,
    "NUMERIC_OUT_OF_BOUNDS": FailureClass.STATISTICAL_DRIFT,
    "INVALID_URL": FailureClass.SEMANTIC_INVARIANT,
    "NEGATIVE_NUMERIC_VALUE": FailureClass.SEMANTIC_INVARIANT,
    "EMPTY_REQUIRED_RELATION": FailureClass.SEMANTIC_INVARIANT,
    "FIELD_REPLACEMENT": FailureClass.SILENT_CORRUPTION,
    "ENTITY_MISMATCH": FailureClass.SILENT_CORRUPTION,
    "PLAUSIBLE_DECOY": FailureClass.SILENT_CORRUPTION,
    "UNIT_MISMATCH": FailureClass.SILENT_CORRUPTION,
    "PARTIAL_RESULT": FailureClass.BEHAVIORAL_DRIFT,
    "PAGINATION_INCOMPLETE": FailureClass.BEHAVIORAL_DRIFT,
    "LAZY_LOAD": FailureClass.BEHAVIORAL_DRIFT,
    "TIMEOUT": FailureClass.BEHAVIORAL_DRIFT,
    "NETWORK_ERROR": FailureClass.NETWORK_DRIFT,
    "HTTP_STATUS": FailureClass.NETWORK_DRIFT,
    "PROVIDER_TIMEOUT": FailureClass.NETWORK_DRIFT,
}


def _classify(signals: tuple[DetectionSignal, ...]) -> tuple[FailureClass, tuple[FailureClass, ...], DiagnosisCertainty, str]:
    candidates = tuple(sorted({_CODE_TO_CLASS[signal.code] for signal in signals if signal.code in _CODE_TO_CLASS}, key=lambda item: item.value))
    explicit_unknown = any(signal.code not in _CODE_TO_CLASS for signal in signals)
    if not candidates:
        return FailureClass.UNKNOWN, (), DiagnosisCertainty.UNKNOWN, "No deterministic rule matched the observed evidence pattern."
    if len(candidates) == 1 and not explicit_unknown:
        selected = candidates[0]
        return selected, candidates, DiagnosisCertainty.DETERMINED, f"Deterministic rule matched evidence codes for {selected.value}."
    return (
        FailureClass.UNKNOWN,
        candidates,
        DiagnosisCertainty.AMBIGUOUS if candidates else DiagnosisCertainty.UNKNOWN,
        "Evidence maps to multiple or partially unknown failure classes; no single class is asserted.",
    )


def diagnose_deterministically(context: DiagnosisContext, *, provenance: DiagnosisProvenance = DiagnosisProvenance.DETERMINISTIC) -> Diagnosis | None:
    """Classify only known evidence codes; ambiguity remains UNKNOWN."""

    if not context.detection.detected:
        return None
    signals = tuple(context.detection.signals)
    failure_class, candidate_classes, certainty, rationale = _classify(signals)
    evidence = tuple(sorted(set(context.observation.evidence_refs) | set(context.detection.evidence_refs) | set(context.evidence_refs)))
    return Diagnosis(
        observation_id=context.observation.observation_id,
        detection_id=context.detection_id,
        correlation_id=context.correlation_id or context.observation.collection_id,
        failure_class=failure_class,
        candidate_classes=candidate_classes,
        severity=context.detection.severity,
        affected_fields=context.detection.affected_fields,
        evidence_references=evidence,
        detector_provenance=context.detection.detector_provenance,
        rationale=rationale,
        certainty=certainty,
        diagnosis_provenance=provenance,
    )


class DeterministicDiagnostician:
    def diagnose(self, context: DiagnosisContext) -> Diagnosis | None:
        return diagnose_deterministically(context)


class TestDoubleDiagnostician:
    """Deterministic path explicitly labeled TEST_DOUBLE for local tests."""

    def diagnose(self, context: DiagnosisContext) -> Diagnosis | None:
        return diagnose_deterministically(context, provenance=DiagnosisProvenance.TEST_DOUBLE)


class StructuredDiagnosisBackend(Protocol):
    def __call__(self, context: DiagnosisContext) -> Mapping[str, Any]:
        """Return JSON-like structured fields matching the Diagnosis schema."""


class StructuredModelDiagnostician:
    """Future model seam; the backend is injected and never gains repair authority."""

    def __init__(self, backend: StructuredDiagnosisBackend) -> None:
        self._backend = backend

    def diagnose(self, context: DiagnosisContext) -> Diagnosis | None:
        if not context.detection.detected:
            return None
        payload = dict(self._backend(context))
        raw_class = payload.get("failure_class", FailureClass.UNKNOWN.value)
        try:
            failure_class = FailureClass(str(raw_class))
        except ValueError as exc:
            raise ValueError("structured model output contains an invalid failure_class") from exc
        raw_certainty = payload.get("certainty", DiagnosisCertainty.UNKNOWN.value)
        try:
            certainty = DiagnosisCertainty(str(raw_certainty))
        except ValueError as exc:
            raise ValueError("structured model output contains an invalid certainty") from exc
        evidence = tuple(sorted(set(context.observation.evidence_refs) | set(context.detection.evidence_refs) | set(context.evidence_refs)))
        return Diagnosis(
            observation_id=context.observation.observation_id,
            detection_id=context.detection_id,
            correlation_id=context.correlation_id or context.observation.collection_id,
            failure_class=failure_class,
            candidate_classes=(failure_class,),
            severity=context.detection.severity,
            affected_fields=tuple(payload.get("affected_fields", context.detection.affected_fields)),
            evidence_references=evidence,
            detector_provenance=context.detection.detector_provenance,
            rationale=str(payload.get("rationale", "Model-provided rationale requires deterministic verification later.")),
            certainty=certainty,
            diagnosis_provenance=DiagnosisProvenance.MODEL_ASSISTED,
        )


class NoExecutionRepairBoundary:
    """TEST_DOUBLE boundary that acknowledges a request without executing healing."""

    def request_healing(self, repair_request: RepairRequest) -> RepairAttemptHandle:
        return RepairAttemptHandle(
            repair_request_id=repair_request.repair_request_id,
            provenance=RepairBoundaryProvenance.TEST_DOUBLE,
            provider_operation_reference=None,
            execution_started=False,
        )


def build_repair_request(
    diagnosis: Diagnosis,
    *,
    observation: Observation,
    contract: ExtractionContract,
    target_input: Mapping[str, Any] | None = None,
    mutation_context: Mapping[str, Any] | None = None,
) -> RepairRequest:
    """Create a bounded provider-neutral request and nothing beyond it."""

    return RepairRequest.from_diagnosis(
        diagnosis,
        observation=observation,
        contract=contract,
        target_input=target_input,
        mutation_context=mutation_context,
    )
