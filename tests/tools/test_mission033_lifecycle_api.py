from __future__ import annotations

from pathlib import Path

from scripts.mission032_lifecycle_api import dispatch


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mission033_real_provider_candidate_projection_is_truthful_and_read_only() -> None:
    result = dispatch(REPO_ROOT, {"action": "mission033"})

    assert result["case"]["case_id"] == "mission_033_real_provider_candidate"
    assert result["case"]["collector_id"].startswith("c_")
    assert result["replay"]["candidate"]["provenance"] == "REAL_PROVIDER"
    assert result["replay"]["verification"]["overall_status"] == "PASS"
    assert result["replay"]["risk"]["decision"] == "ACCEPT"
    assert result["replay"]["commit"]["eligibility"] == "BLOCKED"
    assert result["replay"]["approval"]["provider_approval_executed"] is False
    assert result["replay"]["post_heal"]["corrected_live_output_claimed"] is False
    assert result["graph"]["provenance"] == "REAL_PROVIDER"
