from __future__ import annotations

from aegis.mission060_simulation import run_mission060_future_loop_simulation


def test_future_loop_scenarios_are_explicit_test_double_and_separate_provenance() -> None:
    report = run_mission060_future_loop_simulation()

    assert report["provenance"] == "TEST_DOUBLE"
    assert report["provider_operations"] == 0
    assert report["success_path"]["label"] == "TEST_DOUBLE / CONTROLLED_REPLAY"
    assert report["success_path"]["data_shipped"] == "YES_IN_FIXTURE_ONLY"
    assert report["success_path"]["real_provider_claim"] is False
    assert report["failure_path"]["data_shipped"] == "NO"
    assert report["failure_path"]["required_field_states"]["title"] == "MISSING"
