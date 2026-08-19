from __future__ import annotations

import json
from pathlib import Path

from scripts.mission033_lifecycle import FIELDS, build_provider_prompt, mission033_contract, project_lifecycle
from aegis.diagnosis import FailureClass


def _envelope(*, operation_id: str, response_id: str, output: list[dict[str, object]]) -> dict[str, object]:
    return {
        "operation_id": operation_id,
        "collector_id": "c_mission033",
        "status": "COMPLETED",
        "elapsed_ms": 1000,
        "stderr": f"Triggered (response_id: {response_id})",
        "stdout": output,
    }


def test_project_lifecycle_reuses_canonical_schema_drift_path(tmp_path: Path) -> None:
    evidence = tmp_path
    (evidence / "provider_operations").mkdir()
    (evidence / "target_contract.json").write_text(
        json.dumps({"target_url": "https://example.test/mission-033/target"}), encoding="utf-8"
    )
    (evidence / "initial_run.json").write_text(
        json.dumps(_envelope(
            operation_id="operation_001_run",
            response_id="d2t-v1",
            output=[{"title": "AEGIS Verification Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"}],
        )),
        encoding="utf-8",
    )
    (evidence / "provider_operations" / "operation_002_run.json").write_text(
        json.dumps(_envelope(
            operation_id="operation_002_run",
            response_id="d2t-v2",
            output=[{"input": {"url": "https://example.test/mission-033/target"}}],
        )),
        encoding="utf-8",
    )

    result = project_lifecycle(evidence)

    assert result["detection"].detected is True
    assert result["detection"].affected_fields == tuple(sorted(FIELDS))
    assert result["diagnosis"].failure_class is FailureClass.SCHEMA_DRIFT
    assert result["heal_request"]["within_documented_limit"] is True
    assert "approve" not in result["heal_request"]["prompt"].lower()
    assert json.loads((evidence / "corruption_observation.json").read_text())["provenance"] == "REAL_PROVIDER"


def test_provider_prompt_contains_only_extraction_repair_content() -> None:
    class Request:
        affected_fields = FIELDS

    prompt = build_provider_prompt(Request())

    assert len(prompt) <= 1000
    for forbidden in ("approve", "commit", "verification", "risk", "benchmark", "aegis"):
        assert forbidden not in prompt.lower()


def test_owned_product_contract_requires_three_fields() -> None:
    assert tuple(field.name for field in mission033_contract().fields) == FIELDS
