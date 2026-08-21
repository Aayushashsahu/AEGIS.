from pathlib import Path

from scripts.mission032_lifecycle_api import dispatch


ROOT = Path(__file__).resolve().parents[2]


def test_real_provider_case_preserves_terminal_no_candidate_boundary() -> None:
    payload = dispatch(ROOT, {"action": "historical"})
    graph = payload["graph"]
    assert payload["case"]["case_id"] == "mission_029_real_provider"
    assert graph["mode"] == "REAL_PROVIDER"
    assert graph["domain_decision"] == "blocked"
    assert graph["display_decision"] == "BLOCKED"
    status = {node["id"]: node["display_status"] for node in graph["nodes"]}
    assert status["CANDIDATE"] == "UNAVAILABLE"
    assert status["VERIFICATION"] == "UNAVAILABLE"
    assert status["COMMIT"] == "BLOCKED"


def test_controlled_replay_uses_canonical_verification_risk_and_commit_logic() -> None:
    payload = dispatch(ROOT, {"action": "controlled"})
    graph = payload["graph"]
    assert graph["mode"] == "TEST_DOUBLE_CONTROLLED_REPLAY"
    assert graph["domain_decision"] == "reject"
    assert graph["display_decision"] == "REJECT"
    assert payload["replay"]["verification"]["overall_status"] == "FAIL"
    assert payload["replay"]["risk"]["decision"] == "REJECT"
    assert payload["replay"]["output_eligible"] is False


def test_configured_case_is_provider_free_and_has_no_inferred_evidence() -> None:
    payload = dispatch(ROOT, {"action": "configured", "case": {"case_id": "case_test", "name": "Test", "target_url": "https://example.com", "collector_id": None, "description": None, "fields": [{"name": "title", "type": "text", "description": "title"}], "invariants": ["title_present"], "correlation_id": "corr_test", "created_at": "2026-08-19T00:00:00+00:00", "updated_at": "2026-08-19T00:00:00+00:00"}})
    assert payload["case"]["lifecycle"]["event_count"] == 0
    assert payload["graph"]["mode"] == "CONFIGURED_CASE"
    assert payload["graph"]["nodes"] == [payload["graph"]["nodes"][0]]
    assert payload["graph"]["nodes"][0]["id"] == "TARGET"


def test_benchmark_projection_is_read_only_and_preserves_scope() -> None:
    payload = dispatch(ROOT, {"action": "benchmark"})
    assert payload["status"] == "AVAILABLE"
    assert payload["summary"]["run_id"] == "mission_028_recovery_floor_4812160675146552"
    assert payload["summary"]["controlled_aegis_metrics"]["provenance"] == "TEST_DOUBLE_CONTROLLED_HARNESS"


def test_downstream_projection_blocks_the_controlled_silent_corruption_output() -> None:
    payload = dispatch(ROOT, {"action": "downstream"})
    assert payload["provenance"] == "TEST_DOUBLE"
    assert payload["mode"] == "CONTROLLED_REPLAY"
    assert payload["product"]["expected_price"] == 599
    assert payload["product"]["observed_price"] == 29.99
    assert payload["verification"]["status"] == "FAIL"
    assert payload["risk"]["decision"] == "REJECT"
    assert payload["commit"]["eligibility"] == "BLOCKED"
    assert payload["output"]["eligible"] is False


def test_mission050_preserves_unknown_low_cause_and_real_provider_fail_closed_boundary() -> None:
    payload = dispatch(ROOT, {"action": "mission050"})
    graph = payload["graph"]
    replay = payload["replay"]
    statuses = {node["id"]: node["display_status"] for node in graph["nodes"]}

    assert graph["mode"] == "REAL_PROVIDER_CAUSAL_BOUNDARY"
    assert graph["provenance"] == "REAL_PROVIDER"
    assert replay["cause"] == "UNKNOWN"
    assert replay["confidence"] == "LOW"
    assert replay["real_provider_chain"]["http_status"] == 200
    assert replay["real_provider_chain"]["required_fields"] == {"title": "MISSING", "price": "MISSING", "availability": "MISSING"}
    assert statuses["VERIFICATION"] == "ANOMALY"
    assert statuses["RISK"] == "ANOMALY"
    assert statuses["COMMIT"] == "BLOCKED"
    assert replay["real_provider_chain"]["data_shipped"] == "NO"
    assert replay["controlled_replay_boundary"]["provenance"] == "TEST_DOUBLE"
    assert replay["controlled_replay_boundary"]["status"] == "SEPARATE"
    assert replay["output_eligible"] is False
    assert replay["provider_operations_this_mission"] == 0
    assert replay["new_provider_requests_this_mission"] == 0
