from __future__ import annotations

import json
from pathlib import Path

from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.diagnosis import (
    DiagnosisContext,
    FailureClass,
    NoExecutionRepairBoundary,
    build_repair_request,
    diagnose_deterministically,
)
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    Observation,
    ProviderProvenance,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_bright_data_artifact_reaches_repair_request_without_healing() -> None:
    output = json.loads((REPO_ROOT / "experiments/mission_001_collection_output.json").read_text())
    metadata = json.loads((REPO_ROOT / "experiments/mission_001_collection_metadata.json").read_text())
    contract = default_extraction_contract()
    handle = CollectionHandle(
        collection_id=metadata["response_id"],
        collector_id=metadata["collector_id"],
        status=CollectionState.COMPLETED,
        mode=CollectionMode.BATCH,
        provider_operation_ids={
            "response_id": metadata["response_id"],
            "batch_job_id": metadata["batch_job_id"],
        },
        provider_status="COMPLETED",
        latency_ms=metadata["run_latency_ms"],
        provider_provenance=ProviderProvenance.BRIGHT_DATA,
        evidence_refs=("evidence://mission-001/collection-output",),
    )
    observation = Observation.from_result(
        CollectionResult(handle=handle, output=output),
        {"target_url": metadata["target_url"]},
    )
    detection = evaluate_detection(observation, contract)
    context = DiagnosisContext(
        observation=observation,
        detection=detection,
        contract=contract,
        detection_id="detection_mission001_recorded",
        evidence_refs=("evidence://mission-003/recorded-artifact",),
        correlation_id="corr_mission001_recorded",
    )
    diagnosis = diagnose_deterministically(context)
    assert diagnosis is not None
    assert diagnosis.failure_class is FailureClass.SCHEMA_DRIFT
    assert diagnosis.observation_id == observation.observation_id
    assert diagnosis.diagnosis_provenance.value == "DETERMINISTIC"

    request = build_repair_request(diagnosis, observation=observation, contract=contract)
    assert request.collector_reference == metadata["collector_id"]
    assert request.observation_id == observation.observation_id
    assert request.diagnosis_id == diagnosis.diagnosis_id
    assert request.extraction_contract is contract
    assert request.status.value == "REPAIR_REQUESTED"
    assert request.provenance.value == "DETERMINISTIC"
    assert "output schema" in request.repair_objective
    assert "points" in request.repair_objective

    attempt = NoExecutionRepairBoundary().request_healing(request)
    assert attempt.execution_started is False
    assert attempt.provider_operation_reference is None
    assert attempt.repair_request_id == request.repair_request_id
