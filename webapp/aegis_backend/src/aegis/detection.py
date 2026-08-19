"""Deterministic detection orchestration for Mission 002."""

from __future__ import annotations

from .contracts import evaluate_schema, evaluate_semantic, evaluate_statistical
from .models import DetectionResult, ExtractionContract, Observation


_SEVERITY_ORDER = {"NONE": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}


def evaluate_detection(observation: Observation, contract: ExtractionContract) -> DetectionResult:
    """Evaluate all three deterministic channels and return structured evidence."""

    signals = (
        *evaluate_schema(observation.output, contract),
        *evaluate_statistical(observation.output, contract),
        *evaluate_semantic(observation.output, contract),
    )
    severity = max((signal.severity for signal in signals), key=lambda item: _SEVERITY_ORDER[item], default="NONE")
    affected_fields = tuple(sorted({field for signal in signals for field in signal.affected_fields}))
    evidence_refs = tuple(sorted({ref for signal in signals for ref in signal.evidence_refs}))
    provenance = tuple(sorted({signal.detector for signal in signals}))
    return DetectionResult(
        detected=bool(signals),
        severity=severity,
        signals=signals,
        affected_fields=affected_fields,
        evidence_refs=evidence_refs,
        detector_provenance=provenance or ("schema", "statistical", "semantic"),
    )
