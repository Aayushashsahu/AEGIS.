from __future__ import annotations

import json
from pathlib import Path

from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.diagnosis import DiagnosisContext, build_repair_request, diagnose_deterministically
from aegis.healing import HealState, VerificationStatus
from aegis.models import CollectionHandle, CollectionMode, CollectionResult, CollectionState, Observation, ProviderProvenance
from aegis.test_double import DeterministicBrightDataHealingTestDouble, HealTestDoubleScenario


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_bright_data_request_reaches_unverified_test_double_candidate() -> None:
    output = json.loads((REPO_ROOT / "experiments/mission_001_collection_output.json").read_text())
    metadata = json.loads((REPO_ROOT / "experiments/mission_001_collection_metadata.json").read_text())
    contract = default_extraction_contract()
    handle = CollectionHandle(
        collection_id=metadata["response_id"],
        collector_id=metadata["collector_id"],
        status=CollectionState.COMPLETED,
        mode=CollectionMode.BATCH,
        provider_operation_ids={"response_id": metadata["response_id"], "batch_job_id": metadata["batch_job_id"]},
        provider_status="COMPLETED",
        latency_ms=metadata["run_latency_ms"],
        provider_provenance=ProviderProvenance.BRIGHT_DATA,
        evidence_refs=("evidence://mission-001/collection-output",),
    )
    observation = Observation.from_result(CollectionResult(handle=handle, output=output), {"target_url": metadata["target_url"]})
    detection = evaluate_detection(observation, contract)
    diagnosis = diagnose_deterministically(DiagnosisContext(
        observation=observation,
        detection=detection,
        contract=contract,
        detection_id="detection-mission004-recorded",
        evidence_refs=("evidence://mission-004/recorded-artifact",),
        correlation_id="corr-mission004-recorded",
    ))
    assert diagnosis is not None
    request = build_repair_request(diagnosis, observation=observation, contract=contract)

    healing = DeterministicBrightDataHealingTestDouble(HealTestDoubleScenario.HEAL_AWAITING_APPROVAL)
    submitted = healing.request_healing(request)
    running = healing.poll_healing(submitted)
    awaiting = healing.poll_healing(running)
    assert awaiting.status is HealState.AWAITING_APPROVAL
    result = healing.retrieve_heal_result(awaiting)
    assert result.candidate is not None
    assert result.candidate.verification_status is VerificationStatus.UNVERIFIED
    assert result.candidate.provenance is ProviderProvenance.TEST_DOUBLE
    assert result.candidate.repair_request_id == request.repair_request_id
    assert result.candidate.collector_reference == metadata["collector_id"]
