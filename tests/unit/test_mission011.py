from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from aegis.benchmark_config import (
    DryRunStatus,
    ValidationStatus,
    compute_configuration_hash,
    default_validation_config,
    freeze_config,
    run_dry_run,
    validate_config,
)


MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")


def config():
    return default_validation_config(code_revision="abc123", repository_state="DIRTY_USER_FILES_PRESERVED")


def error_contains(result, text: str) -> bool:
    return any(text in error for error in result.errors)


def test_valid_validation_config_passes_and_records_expected_freeze_fields() -> None:
    current = config()
    result = validate_config(current)
    assert result.status is ValidationStatus.VALID
    assert result.valid is True
    assert current.configuration_hash == compute_configuration_hash(current)
    assert current.mutation_class_ids == MUTATIONS
    assert current.mutation_severity == {"M001": "L1", "M002": "L2", "M003": "L3", "M004": "L4", "M005": "L5", "M006": "L5"}
    assert current.seeds == (12345,)
    assert tuple(baseline.baseline_id for baseline in current.baselines) == ("BASELINE_A", "BASELINE_B", "AEGIS")
    assert all(baseline.status == "NOT_READY" for baseline in current.baselines)
    assert result.warnings
    assert current.artifact_contract == {
        "configs": "benchmarks/configs",
        "manifests": "benchmarks/manifests",
        "runs": "benchmarks/runs",
        "results": "benchmarks/results",
        "reports": "benchmarks/reports",
    }
    assert result.checks["artifact_contract"] == "PASS"


def test_benchmark_config_and_nested_policies_are_immutable() -> None:
    current = config()
    with pytest.raises(FrozenInstanceError):
        current.benchmark_id = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        current.timeout_policy["total_ms"] = 1  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        current.baselines[0].status = "READY"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "needle"),
    [
        ("mutation_class_ids", ("M001", "M002", "M003", "M004", "M005"), "missing mutation classes"),
        ("mutation_class_ids", MUTATIONS + ("M006",), "duplicate mutation IDs"),
        ("mutation_severity", {"M001": "L1", "M002": "L2", "M003": "L3", "M004": "L4", "M005": "L7", "M006": "L5"}, "invalid severity mapping"),
        ("seeds", (), "missing seed list"),
        ("code_revision", "", "missing code_revision"),
        ("fixture_version", "999", "fixture_version does not match"),
        ("metric_formula_version", "wrong-formula", "metric_formula_version must equal"),
        ("artifact_root", "", "missing artifact_root"),
    ],
)
def test_invalid_configuration_fields_fail_closed(field: str, value, needle: str) -> None:
    current = config()
    changes = {field: value}
    if field == "seeds":
        changes["trial_count"] = 0
    invalid = replace(current, **changes)
    result = validate_config(invalid)
    assert result.status is ValidationStatus.INVALID
    assert result.valid is False
    assert error_contains(result, needle)


def test_duplicate_mutation_ids_fail_even_when_the_set_is_complete() -> None:
    invalid = replace(config(), mutation_class_ids=("M001", "M002", "M003", "M004", "M005", "M005"))
    result = validate_config(invalid)
    assert result.status is ValidationStatus.INVALID
    assert error_contains(result, "duplicate mutation IDs")
    assert error_contains(result, "missing mutation classes: M006")


def test_incomplete_baseline_slots_fail_closed() -> None:
    invalid = replace(config(), baselines=config().baselines[:2])
    result = validate_config(invalid)
    assert result.status is ValidationStatus.INVALID
    assert error_contains(result, "missing baselines: AEGIS")


def test_invalid_timeout_and_retry_policies_fail_closed() -> None:
    invalid_timeout = replace(config(), timeout_policy={"collection_ms": 0, "healing_ms": 900000, "polling_ms": 300000, "verification_ms": 30000, "total_ms": 1})
    timeout_result = validate_config(invalid_timeout)
    assert timeout_result.status is ValidationStatus.INVALID
    assert error_contains(timeout_result, "timeout_policy.collection_ms invalid")
    assert error_contains(timeout_result, "timeout_policy.total_ms must cover")

    invalid_retry = replace(config(), retry_policy={"mode": "UNBOUNDED", "max_attempts": 0, "backoff_ms": -1})
    retry_result = validate_config(invalid_retry)
    assert retry_result.status is ValidationStatus.INVALID
    assert error_contains(retry_result, "retry_policy.mode invalid")
    assert error_contains(retry_result, "retry_policy.max_attempts invalid")
    assert error_contains(retry_result, "retry_policy.backoff_ms invalid")


def test_ready_baseline_requires_real_implementation_and_configuration_metadata() -> None:
    baseline = config().baselines[0]
    invalid_ready = replace(config(), baselines=(replace(baseline, status="READY"),) + config().baselines[1:])
    result = validate_config(invalid_ready)
    assert result.status is ValidationStatus.INVALID
    assert error_contains(result, "ready baseline BASELINE_A lacks a real configuration hash")


def test_changed_frozen_field_invalidates_the_configuration_hash() -> None:
    changed = replace(config(), prompt_version="prompt-v2")
    result = validate_config(changed)
    assert result.status is ValidationStatus.INVALID
    assert error_contains(result, "configuration_hash does not match")
    assert changed.configuration_hash != compute_configuration_hash(changed)


def test_freeze_config_recomputes_the_same_hash_without_mutating_input() -> None:
    current = config()
    frozen = freeze_config(current)
    assert frozen.configuration_hash == current.configuration_hash
    assert frozen.to_json() == current.to_json()
    assert current.configuration_hash == compute_configuration_hash(current)


def test_dry_run_is_validation_only_and_generates_no_metric_values_or_side_effects() -> None:
    result = run_dry_run(config(), repository_root=".")
    assert result.status is DryRunStatus.VALIDATION_ONLY
    assert result.valid is True
    assert result.render().splitlines()[:2] == ["VALIDATION ONLY", "NO BENCHMARK EXECUTED"]
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_values_generated == 0
    assert result.benchmark_execution_authorized is False
    assert result.metric_calculator_available is True
    assert result.artifact_path_check.startswith("PASS_")
    assert len(result.fixture_checks) == 6
    assert len(result.seed_checks) == 6
    assert set(result.baseline_checks) == {"BASELINE_A", "BASELINE_B", "AEGIS"}
    assert all(value == "PASS" for value in result.fixture_checks.values())
    assert all(value == "PASS" for value in result.seed_checks.values())
    assert all(value.endswith("RESOLVABLE_METADATA") for value in result.baseline_checks.values())
    assert all(step["execution"] == "NOT_EXECUTED" for step in result.execution_plan)
    assert all(step["configuration_hash"] == result.configuration_hash for step in result.execution_plan)
    assert len(result.execution_plan) == 18


def test_execution_plan_is_byte_identical_for_repeated_dry_runs_and_reordered_input_is_canonical() -> None:
    first = run_dry_run(config(), repository_root=".")
    second = run_dry_run(config(), repository_root=".")
    assert first.to_json() == second.to_json()
    assert first.execution_plan == second.execution_plan
    assert first.configuration_hash == second.configuration_hash
    assert [step["baseline_id"] for step in first.execution_plan[:6]] == ["AEGIS"] * 6
    assert [step["mutation_id"] for step in first.execution_plan[:6]] == list(MUTATIONS)


def test_dry_run_invalid_config_does_not_create_an_execution_plan() -> None:
    invalid = replace(config(), code_revision="")
    result = run_dry_run(invalid, repository_root=".")
    assert result.status is DryRunStatus.INVALID
    assert result.valid is False
    assert result.execution_plan == ()
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.metric_values_generated == 0


def test_dry_run_json_is_machine_readable_and_has_no_metric_result_values() -> None:
    payload = json.loads(run_dry_run(config(), repository_root=".").to_json())
    assert payload["validation_only"] is True
    assert payload["notice"] == "VALIDATION ONLY — NO BENCHMARK EXECUTED"
    assert payload["metric_values_generated"] == 0
    assert payload["benchmark_execution_authorized"] is False
    assert payload["benchmark_runs_executed"] == 0
    assert payload["provider_operations_executed"] == 0
    assert payload["healing_operations_executed"] == 0
    assert payload["execution_plan"]


def test_no_full_benchmark_or_provider_execution_api_is_exposed_by_dry_run_result() -> None:
    result = run_dry_run(config(), repository_root=".")
    assert not hasattr(result, "execute")
    assert not hasattr(result, "run_benchmark")
    assert not hasattr(result, "approve")
    assert not hasattr(result, "rollback")
