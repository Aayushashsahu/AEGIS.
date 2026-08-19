from __future__ import annotations

import json
from pathlib import Path

from scripts.mission033_verify_candidate import project_candidate_verification


def _run(*, operation_id: str, output: list[dict[str, object]]) -> dict[str, object]:
    return {
        "operation_id": operation_id,
        "collector_id": "c_mission033",
        "status": "COMPLETED",
        "elapsed_ms": 1000,
        "stderr": f"Triggered (response_id: {operation_id})",
        "stdout": output,
    }


def test_real_preview_can_pass_deterministic_verification_but_remains_unapproved(tmp_path: Path) -> None:
    (tmp_path / "provider_operations").mkdir()
    (tmp_path / "target_contract.json").write_text(json.dumps({"target_url": "https://example.test/target"}), encoding="utf-8")
    (tmp_path / "repair_request.json").write_text(json.dumps({"repair_request_id": "repair_m033"}), encoding="utf-8")
    (tmp_path / "initial_run.json").write_text(json.dumps(_run(
        operation_id="v1",
        output=[{"title": "AEGIS Verification Widget", "price": {"currency": "USD", "symbol": "$", "value": 599}, "availability": "Available"}],
    )), encoding="utf-8")
    (tmp_path / "provider_operations" / "operation_001_heal.json").write_text(json.dumps({
        **_run(operation_id="operation_001_heal", output=[]),
        "command_sha256": "a" * 64,
        "stdout": {
            "status": "awaiting_approval",
            "preview_result": [{"title": "AEGIS Verification Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"}],
            "diff_summary": "one step",
            "next_step": "bdata scraper approve c_mission033 --url https://example.test/target",
        },
    }), encoding="utf-8")

    result = project_candidate_verification(tmp_path)

    assert result["verification"].overall_status.value == "PASS"
    assert result["risk"].decision.value == "ACCEPT"
    assert result["commit"].eligibility.value == "BLOCKED"
    assert result["output"].eligible is False
    assert result["approval"]["provider_approval_executed"] is False
    assert result["post_heal"]["corrected_live_output_claimed"] is False
