"""Explicitly provider-free final-loop fixtures for the AEGIS demo model."""

from __future__ import annotations

from typing import Any

from .mission056_simulation import MISSION056_EXPECTED_ROW, MISSION056_TARGET_URL, run_mission056_simulation


def run_mission060_future_loop_simulation() -> dict[str, Any]:
    """Return TEST_DOUBLE timeline fixtures; no fixture is real provider evidence."""

    prior = run_mission056_simulation()
    return {
        "schema_version": "mission-060-future-loop-simulation-v1",
        "provenance": "TEST_DOUBLE",
        "provider_operations": 0,
        "success_path": {
            "label": "TEST_DOUBLE / CONTROLLED_REPLAY",
            "timeline": [
                "candidate preview fixture",
                "AEGIS verification PASS fixture",
                "owner approval-result fixture",
                "provider completion fixture",
                "rerun output fixture",
                "risk ACCEPT fixture",
                "downstream eligibility owner-controlled",
            ],
            "rerun_output": [{"input": {"url": MISSION056_TARGET_URL}, **MISSION056_EXPECTED_ROW}],
            "required_field_states": {"title": "PRESENT", "price": "PRESENT", "availability": "PRESENT"},
            "data_shipped": "YES_IN_FIXTURE_ONLY",
            "real_provider_claim": False,
            "canonical_commit_gate": prior["complete_candidate"]["commit"],
        },
        "failure_path": {
            "label": "TEST_DOUBLE / CONTROLLED_REPLAY",
            "timeline": [
                "rerun output fixture",
                "required fields missing",
                "AEGIS verification FAIL fixture",
                "risk REJECT fixture",
                "commit BLOCKED fixture",
                "data shipped NO",
            ],
            "rerun_output": [{"input": {"url": MISSION056_TARGET_URL}}],
            "required_field_states": {"title": "MISSING", "price": "MISSING", "availability": "MISSING"},
            "data_shipped": "NO",
            "real_provider_claim": False,
            "canonical_commit_gate": prior["incomplete_candidate"]["commit"],
        },
    }
