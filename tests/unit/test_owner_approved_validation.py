from __future__ import annotations

import json
from pathlib import Path

from aegis.owner_approved_validation import OwnerValidationStatus, load_owner_payload, validate_owner_configuration


ROOT = Path(__file__).resolve().parents[2]
OWNER_PATH = ROOT / "benchmarks/configs/mission_014_owner_approved_participants.json"
OLD_HASH = "fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3"


def report():
    return validate_owner_configuration(load_owner_payload(OWNER_PATH), source_configuration_hash=OLD_HASH)


def test_owner_payload_preserves_three_participants_and_blocks_missing_freeze_fields() -> None:
    result = report()
    assert set(result.participants) == {"BASELINE_A", "BASELINE_B", "AEGIS"}
    assert result.status is OwnerValidationStatus.BLOCKED_NOT_READY
    for participant in result.participants.values():
        assert participant.status is OwnerValidationStatus.BLOCKED_NOT_READY
        assert "participant_hash" in participant.placeholder_fields
        assert "participant_hash is not computed" in " ".join(participant.errors)
        assert any("implementation.revision" in error for error in participant.errors)


def test_owner_review_is_blocked_without_timestamp_rationale_correlation_and_final_hash() -> None:
    review = report().owner_review
    assert review.approved is True
    assert review.reviewer == "PROJECT_OWNER"
    assert review.status is OwnerValidationStatus.BLOCKED_NOT_READY
    assert review.missing_fields == ("approval_timestamp", "approved_configuration_hash", "correlation_id", "rationale")


def test_fairness_blocks_exact_owner_values_with_different_timeouts() -> None:
    fairness = report().fairness
    assert fairness.status is OwnerValidationStatus.BLOCKED_NOT_READY
    assert fairness.checks["mutation_id"] == "PASS"
    assert fairness.checks["seed"] == "PASS"
    assert fairness.checks["ground_truth_runtime_payload"] == "PASS"
    assert fairness.checks["timeout_policy"] == "FAIL"
    assert fairness.checks["retry_policy"] == "PASS"
    assert any("timeout_policy differs" in conflict for conflict in fairness.conflicts)


def test_blocked_report_never_creates_promotions_or_new_hash_and_never_executes() -> None:
    result = report()
    assert result.source_configuration_hash == OLD_HASH
    assert result.new_configuration_hash == "NOT_GENERATED"
    assert result.promotions_created == 0
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_results_generated == 0
    assert result.execution_authorized is False


def test_owner_payload_is_machine_readable_and_does_not_change_frozen_inputs() -> None:
    payload = json.loads(OWNER_PATH.read_text(encoding="utf-8"))
    assert payload["participants"]["BASELINE_A"]["benchmark"]["mutation_set"] == ["M001", "M002", "M003", "M004", "M005", "M006"]
    assert payload["participants"]["BASELINE_B"]["benchmark"]["seed"] == 12345
    assert payload["participants"]["AEGIS"]["metrics"]["calculator"] == "mission-010-metrics-v1"
