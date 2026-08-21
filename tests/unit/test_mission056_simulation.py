from aegis.mission056_simulation import run_mission056_simulation


def test_provider_free_simulation_proves_healthy_drift_and_candidate_safety_paths() -> None:
    simulation = run_mission056_simulation()

    assert simulation["provenance"] == "TEST_DOUBLE"
    assert simulation["provider_operations"] == 0
    assert simulation["baseline"]["detection"]["detected"] is False
    assert simulation["controlled_drift"]["detection"]["detected"] is True
    assert simulation["controlled_drift"]["lineage"]["classification"] == "DECODED_PROVIDER_OUTPUT_INCOMPLETE"
    assert simulation["complete_candidate"]["verification"]["overall_status"] == "PASS"
    assert simulation["complete_candidate"]["risk"]["decision"] == "ACCEPT"
    assert simulation["complete_candidate"]["commit"]["eligibility"] == "BLOCKED"
    assert simulation["complete_candidate"]["downstream"]["eligible"] is False
    assert simulation["incomplete_candidate"]["verification"]["overall_status"] == "FAIL"
    assert simulation["incomplete_candidate"]["risk"]["decision"] == "REJECT"
    assert simulation["incomplete_candidate"]["commit"]["eligibility"] == "BLOCKED"
    assert simulation["incomplete_candidate"]["downstream"]["eligible"] is False
