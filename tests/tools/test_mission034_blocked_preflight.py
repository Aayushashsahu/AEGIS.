from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "experiments" / "mission_034_bright_data_approval_rerun"


def load_json(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_blocked_preflight_records_exact_identifier_and_time_failures() -> None:
    preflight = load_json("preflight.json")
    checks = {item["name"]: item for item in preflight["checks"]}

    assert preflight["status"] == "BLOCKED_INVALID_AUTHORIZATION"
    assert checks["candidate_id_matches_canonical_evidence"]["status"] == "PASS"
    assert checks["collector_id_matches_canonical_evidence"]["status"] == "FAIL"
    assert checks["collector_id_matches_canonical_evidence"]["expected"] == "c_mt09pib13nxqz1coi"
    assert checks["authorization_time_is_recorded_utc"]["status"] == "FAIL"


def test_blocked_preflight_has_zero_provider_mutations_and_no_synthetic_artifacts() -> None:
    ledger = load_json("operation_ledger.json")
    summary = load_json("summary.json")
    manifest = load_json("artifact_hashes.json")

    assert all(value == 0 for value in ledger["operations"].values())
    assert summary["approval"] == "NOT_ATTEMPTED"
    assert summary["post_approval_rerun"] == "NOT_ATTEMPTED"
    assert summary["provenance"] == "NO_MISSION_034_PROVIDER_OUTPUT"
    for filename in manifest["absent_by_design"]:
        assert not (ARTIFACTS / filename).exists()


def test_blocked_preflight_artifact_hashes_match_manifest() -> None:
    manifest = load_json("artifact_hashes.json")
    for filename, expected_hash in manifest["artifacts"].items():
        actual_hash = hashlib.sha256((ARTIFACTS / filename).read_bytes()).hexdigest()
        assert actual_hash == expected_hash


def test_corrected_authorization_and_preflight_stop_at_transport_gate() -> None:
    authorization = load_json("authorization_corrected.json")
    preflight = load_json("preflight_corrected.json")
    checks = {item["name"]: item for item in preflight["checks"]}

    assert authorization["candidate_id"] == "candidate_m033_a0d9aa5a0d056720"
    assert authorization["collector_id"] == "c_mt09pib13nxqz1coi"
    assert authorization["agent_delegation"]
    assert authorization["operation_budget"]["bright_data_approve"] == 1
    assert authorization["operation_budget"]["bright_data_collector_run"] == 1
    assert authorization["operation_budget"]["additional_retries"] == 0
    assert preflight["status"] == "BLOCKED_TRANSPORT_UNAVAILABLE"
    assert checks["credential_authentication_probe"]["status"] == "PASS"
    assert checks["documented_approval_rerun_transport"]["status"] == "FAIL"
    assert all(value == 0 for value in preflight["provider_operations_executed"].values())


def test_corrected_transport_block_has_no_real_provider_output() -> None:
    ledger = load_json("operation_ledger_corrected.json")
    summary = load_json("summary_corrected.json")

    assert all(value == 0 for value in ledger["operations"].values())
    assert summary["approval"] == "NOT_ATTEMPTED"
    assert summary["rerun"] == "NOT_ATTEMPTED"
    assert summary["real_provider_output"] == "ABSENT"
    assert summary["commit"] == "BLOCKED"
