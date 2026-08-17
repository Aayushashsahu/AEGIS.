from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.diagnosis import (
    DiagnosisCertainty,
    DiagnosisContext,
    DiagnosisProvenance,
    FailureClass,
    NoExecutionRepairBoundary,
    RepairRequest,
    StructuredModelDiagnostician,
    TestDoubleDiagnostician,
    diagnose_deterministically,
    build_repair_request,
)
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    DetectionResult,
    DetectionSignal,
    Observation,
    ProviderProvenance,
)
from aegis.test_double import DeterministicBrightDataTestDouble, TestDoubleScenario


def make_observation(scenario: TestDoubleScenario = TestDoubleScenario.HEALTHY) -> Observation:
    adapter = DeterministicBrightDataTestDouble(scenario)
    collector = adapter.create_collector(
        request=__import__("aegis").CollectorRequest(
            target_url="https://example.test",
            extraction_prompt="extract stories",
            provider=ProviderProvenance.TEST_DOUBLE,
        )
    )
    handle = adapter.run_collector(collector, target_url="https://example.test")
    handle = adapter.poll_collection(handle)
    handle = adapter.poll_collection(handle)
    return Observation.from_result(
        adapter.retrieve_output(handle),
        {"target_url": "https://example.test"},
    )


def context_for(
    observation: Observation,
    *,
    contract=None,
    detection=None,
    detection_id: str = "detection-test-1",
) -> DiagnosisContext:
    extraction_contract = contract or default_extraction_contract()
    detection_result = detection or evaluate_detection(observation, extraction_contract)
    return DiagnosisContext(
        observation=observation,
        detection=detection_result,
        contract=extraction_contract,
        detection_id=detection_id,
        evidence_refs=("evidence://mission-003/context",),
        correlation_id="corr-test-1",
    )


def test_healthy_observation_produces_no_diagnosis() -> None:
    assert diagnose_deterministically(context_for(make_observation())) is None


def test_missing_field_maps_to_schema_drift() -> None:
    diagnosis = diagnose_deterministically(context_for(make_observation(TestDoubleScenario.MISSING_FIELD)))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.SCHEMA_DRIFT
    assert diagnosis.certainty is DiagnosisCertainty.DETERMINED
    assert diagnosis.affected_fields == ("author",)


def test_statistical_drift_maps_to_statistical_drift() -> None:
    contract = replace(default_extraction_contract(), expected_row_count=2)
    observation = make_observation(TestDoubleScenario.STATISTICAL_DRIFT)
    diagnosis = diagnose_deterministically(context_for(observation, contract=contract))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.STATISTICAL_DRIFT


def test_semantic_invariant_maps_to_semantic_invariant() -> None:
    diagnosis = diagnose_deterministically(context_for(make_observation(TestDoubleScenario.SEMANTIC_CORRUPTION)))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.SEMANTIC_INVARIANT
    assert "url" in diagnosis.affected_fields


def test_explicit_silent_corruption_maps_to_l5_class() -> None:
    observation = make_observation()
    detection = DetectionResult(
        detected=True,
        severity="L5",
        signals=(DetectionSignal(
            detector="independent_evidence",
            code="FIELD_REPLACEMENT",
            message="field is associated with a different entity",
            severity="L5",
            affected_fields=("points",),
            evidence_refs=("evidence://l5/field-replacement",),
        ),),
        affected_fields=("points",),
        evidence_refs=("evidence://l5/field-replacement",),
        detector_provenance=("semantic", "independent_evidence"),
    )
    diagnosis = diagnose_deterministically(context_for(observation, detection=detection))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.SILENT_CORRUPTION
    assert diagnosis.severity == "L5"


def test_unknown_pattern_remains_unknown() -> None:
    observation = make_observation()
    detection = DetectionResult(
        detected=True,
        severity="L3",
        signals=(DetectionSignal(
            detector="custom",
            code="UNCLASSIFIED_PATTERN",
            message="evidence was intentionally not mapped",
            severity="L3",
            affected_fields=("title",),
            evidence_refs=("evidence://unknown/pattern",),
        ),),
        affected_fields=("title",),
        evidence_refs=("evidence://unknown/pattern",),
        detector_provenance=("custom",),
    )
    diagnosis = diagnose_deterministically(context_for(observation, detection=detection))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.UNKNOWN
    assert diagnosis.certainty is DiagnosisCertainty.UNKNOWN


def test_ambiguous_evidence_is_not_collapsed_into_false_certainty() -> None:
    observation = make_observation()
    detection = DetectionResult(
        detected=True,
        severity="L3",
        signals=(
            DetectionSignal("schema", "MISSING_FIELD", "missing", "L2", ("points",), ("evidence://schema",)),
            DetectionSignal("semantic", "INVALID_URL", "invalid", "L3", ("url",), ("evidence://semantic",)),
        ),
        affected_fields=("points", "url"),
        evidence_refs=("evidence://schema", "evidence://semantic"),
        detector_provenance=("schema", "semantic"),
    )
    diagnosis = diagnose_deterministically(context_for(observation, detection=detection))
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.UNKNOWN
    assert diagnosis.certainty is DiagnosisCertainty.AMBIGUOUS
    assert set(diagnosis.candidate_classes) == {FailureClass.SCHEMA_DRIFT, FailureClass.SEMANTIC_INVARIANT}


def test_evidence_and_provenance_survive_diagnosis() -> None:
    observation = make_observation(TestDoubleScenario.TYPE_CORRUPTION)
    diagnosis = diagnose_deterministically(context_for(observation))
    assert diagnosis is not None
    assert "evidence://mission-003/context" in diagnosis.evidence_references
    assert diagnosis.detector_provenance == ("schema",)
    assert diagnosis.observation_id == observation.observation_id
    assert diagnosis.detection_id == "detection-test-1"
    assert diagnosis.correlation_id == "corr-test-1"


def test_repair_request_preserves_contract_and_unaffected_fields() -> None:
    observation = make_observation(TestDoubleScenario.MISSING_FIELD)
    contract = default_extraction_contract()
    diagnosis = diagnose_deterministically(context_for(observation, contract=contract))
    assert diagnosis is not None
    request = build_repair_request(
        diagnosis,
        observation=observation,
        contract=contract,
    )
    assert isinstance(request, RepairRequest)
    assert request.collector_reference == observation.collector_id
    assert request.failure_class is FailureClass.SCHEMA_DRIFT
    assert request.extraction_contract is contract
    assert request.affected_fields == ("author",)
    assert "author" in request.repair_objective
    assert "title" in request.repair_objective
    assert "output schema" in request.repair_objective
    assert request.status.value == "REPAIR_REQUESTED"
    assert all(field.name not in {"api_endpoint", "bdata_command", "provider_token"} for field in fields(request))


def test_test_double_diagnosis_is_explicitly_labeled() -> None:
    diagnosis = TestDoubleDiagnostician().diagnose(context_for(make_observation(TestDoubleScenario.MISSING_FIELD)))
    assert diagnosis is not None
    assert diagnosis.diagnosis_provenance is DiagnosisProvenance.TEST_DOUBLE


def test_structured_model_seam_requires_typed_output_but_needs_no_external_model() -> None:
    def backend(context: DiagnosisContext):
        return {
            "failure_class": "SCHEMA_DRIFT",
            "certainty": "AMBIGUOUS",
            "affected_fields": ["author"],
            "rationale": "bounded injected backend",
        }

    diagnosis = StructuredModelDiagnostician(backend).diagnose(
        context_for(make_observation(TestDoubleScenario.MISSING_FIELD))
    )
    assert diagnosis is not None
    assert diagnosis.diagnosis_provenance is DiagnosisProvenance.MODEL_ASSISTED
    assert diagnosis.failure_class is FailureClass.SCHEMA_DRIFT
    assert diagnosis.certainty is DiagnosisCertainty.AMBIGUOUS


def test_no_execution_boundary_never_starts_healing() -> None:
    observation = make_observation(TestDoubleScenario.MISSING_FIELD)
    diagnosis = diagnose_deterministically(context_for(observation))
    assert diagnosis is not None
    request = build_repair_request(diagnosis, observation=observation, contract=default_extraction_contract())
    handle = NoExecutionRepairBoundary().request_healing(request)
    assert handle.execution_started is False
    assert handle.provider_operation_reference is None
    assert handle.status.value == "REQUESTED"
    assert "approve" not in request.repair_objective.lower()
    assert "commit" not in request.repair_objective.lower()


def test_repair_request_is_immutable() -> None:
    observation = make_observation(TestDoubleScenario.MISSING_FIELD)
    diagnosis = diagnose_deterministically(context_for(observation))
    assert diagnosis is not None
    request = build_repair_request(diagnosis, observation=observation, contract=default_extraction_contract())
    with pytest.raises((AttributeError, TypeError)):
        request.repair_objective = "approve"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.target_input["target_url"] = "https://evil.test"  # type: ignore[index]
