from __future__ import annotations

import json
from pathlib import Path

from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    Observation,
    ProviderProvenance,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_bright_data_output_becomes_untrusted_observation() -> None:
    output = json.loads((REPO_ROOT / "experiments/mission_001_collection_output.json").read_text())
    metadata = json.loads((REPO_ROOT / "experiments/mission_001_collection_metadata.json").read_text())
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
    result = evaluate_detection(observation, default_extraction_contract())
    assert observation.provider_provenance is ProviderProvenance.BRIGHT_DATA
    assert observation.trust_status == "UNTRUSTED_UNTIL_VERIFIED"
    assert observation.row_count == metadata["row_count"]
    assert result.detected is True
    assert "MISSING_FIELD" in {signal.code for signal in result.signals}
