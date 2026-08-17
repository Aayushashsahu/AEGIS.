from __future__ import annotations

from dataclasses import replace

import pytest

import aegis.benchmark_runner as runner_module
from aegis.benchmark_config import default_validation_config, freeze_config
from aegis.benchmark_runner import (
    AegisAdapter,
    BaselineAAdapter,
    BaselineBAdapter,
    BenchmarkRunner,
    FreezeSnapshot,
    ParticipantId,
    ParticipantReadinessStatus,
    ParticipantRegistry,
    RunnerDryRunStatus,
    RunnerState,
    deterministic_artifact_name,
    deterministic_run_id,
    validate_freeze,
)


def config():
    return default_validation_config(code_revision="mission012-code", repository_state="DIRTY_USER_FILES_PRESERVED")


def specs(current):
    return {spec.baseline_id: spec for spec in current.baselines}


def ready_baseline_a_config():
    current = config()
    baseline_a = specs(current)["BASELINE_A"]
    ready_a = replace(
        baseline_a,
        implementation_revision="baseline-a-v1",
        configuration_hash="baseline-a-config-v1",
        status="READY",
    )
    return freeze_config(replace(current, baselines=(ready_a, specs(current)["BASELINE_B"], specs(current)["AEGIS"])))


def test_all_three_participant_slots_exist_in_registry() -> None:
    registry = ParticipantRegistry(config())
    assert tuple(adapter.participant_id for adapter in registry.all()) == ("BASELINE_A", "BASELINE_B", "AEGIS")
    assert set(registry.readiness(config())) == {"BASELINE_A", "BASELINE_B", "AEGIS"}


def test_not_ready_participants_block_validation_only_runner() -> None:
    result = BenchmarkRunner(config()).dry_run()
    assert result.status is RunnerDryRunStatus.BLOCKED_NOT_READY
    assert result.expected_run_count == 18
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_results_generated == 0
    assert result.execution_authorized is False
    assert result.participant_readiness["BASELINE_A"].status is ParticipantReadinessStatus.NOT_READY
    assert result.participant_readiness["BASELINE_B"].status is ParticipantReadinessStatus.NOT_READY
    assert result.participant_readiness["AEGIS"].status is ParticipantReadinessStatus.NOT_READY_FOR_BENCHMARK
    assert all(item.state is RunnerState.PLANNED for item in result.plan)


def test_baseline_a_readiness_is_explicit_and_does_not_use_aegis_controls() -> None:
    current = config()
    readiness = BaselineAAdapter(specs(current)["BASELINE_A"]).readiness(current)
    assert readiness.participant_id == "BASELINE_A"
    assert readiness.contract_ready is True
    assert readiness.benchmark_ready is False
    assert readiness.status is ParticipantReadinessStatus.NOT_READY
    assert readiness.checks["aegis_detection"] == "NOT_USED"
    assert readiness.checks["aegis_verification"] == "NOT_USED"
    assert readiness.checks["risk_governor"] == "NOT_USED"
    assert readiness.checks["commit_gate"] == "NOT_USED"


def test_baseline_a_can_normalize_one_controlled_fixture_run_when_slot_is_ready() -> None:
    current = ready_baseline_a_config()
    spec = specs(current)["BASELINE_A"]
    adapter = BaselineAAdapter(spec)
    readiness = adapter.readiness(current)
    assert readiness.ready is True
    execution_input = BenchmarkRunner(current).build_input("BASELINE_A", "M001", 12345)
    prepared = adapter.prepare(execution_input)
    evidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
    assert evidence.participant_id == "BASELINE_A"
    assert evidence.mutation_id == "M001"
    assert evidence.seed == 12345
    assert evidence.verification_status == "NOT_APPLICABLE"
    assert evidence.risk_decision == "NOT_APPLICABLE"
    assert evidence.output_eligible == "NOT_APPLICABLE"
    assert evidence.provenance == "TEST_DOUBLE"
    assert evidence.artifact_refs == (f"{current.artifact_root}/{execution_input.artifact_name}",)


@pytest.mark.parametrize("field", ["model_id", "prompt_revision", "implementation_revision", "configuration_hash"])
def test_baseline_b_missing_required_metadata_fails_closed(field: str) -> None:
    current = config()
    baseline_b = specs(current)["BASELINE_B"]
    missing = replace(baseline_b, **{field: "TBD"})
    readiness = BaselineBAdapter(missing).readiness(current)
    assert readiness.status is ParticipantReadinessStatus.NOT_READY
    assert readiness.benchmark_ready is False
    assert any(field in error for error in readiness.errors)


def test_aegis_test_double_normalization_preserves_common_schema_and_safety_fields() -> None:
    current = config()
    adapter = AegisAdapter(specs(current)["AEGIS"])
    readiness = adapter.readiness(current)
    assert readiness.status is ParticipantReadinessStatus.NOT_READY_FOR_BENCHMARK
    assert readiness.contract_ready is True
    execution_input = BenchmarkRunner(current).build_input("AEGIS", "M005", 12345)
    prepared = adapter.prepare(execution_input)
    evidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
    assert evidence.participant_id == "AEGIS"
    assert evidence.run_id == execution_input.run_id
    assert evidence.mutation_id == "M005"
    assert evidence.severity == "L5"
    assert evidence.seed == 12345
    assert evidence.verification_status in {"FAIL", "INCONCLUSIVE", "PASS"}
    assert evidence.risk_decision in {"REJECT", "QUARANTINE", "ACCEPT"}
    assert evidence.output_eligible is False
    assert evidence.provenance == "TEST_DOUBLE"
    assert evidence.observation_reference
    assert evidence.evidence_refs
    assert evidence.artifact_refs


def test_all_participants_receive_identical_shared_trial_metadata() -> None:
    current = config()
    runner = BenchmarkRunner(current)
    metadata = [runner.build_input(participant_id, "M001", 12345).shared_metadata() for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS")]
    assert metadata[0] == metadata[1] == metadata[2]
    assert metadata[0]["mutation_id"] == "M001"
    assert metadata[0]["seed"] == 12345
    assert metadata[0]["fixture_version"] == current.fixture_version
    assert metadata[0]["ground_truth_reference"] == "ground-truth://gpu-price-staging/v1/M001/12345"
    assert metadata[0]["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED"


def test_freeze_snapshot_rejects_changed_configuration_hash() -> None:
    current = config()
    snapshot = FreezeSnapshot.from_config(current)
    changed = freeze_config(replace(current, prompt_version="prompt-v2"))
    result = validate_freeze(changed, snapshot)
    assert result.valid is False
    assert "freeze mismatch: configuration_hash" in result.errors


def test_freeze_snapshot_rejects_changed_fixture_seed_and_baseline_hash() -> None:
    current = config()
    snapshot = FreezeSnapshot.from_config(current)
    changed_fixture = freeze_config(replace(current, fixture_version="2"))
    changed_seed = freeze_config(replace(current, seeds=(54321,), trial_count=1))
    baseline = specs(current)["BASELINE_A"]
    changed_baseline = replace(baseline, configuration_hash="baseline-a-new-hash")
    changed_baseline_config = freeze_config(replace(current, baselines=(changed_baseline, specs(current)["BASELINE_B"], specs(current)["AEGIS"])))
    assert "freeze mismatch: fixture_version" in validate_freeze(changed_fixture, snapshot).errors
    assert "freeze mismatch: seeds" in validate_freeze(changed_seed, snapshot).errors
    assert "freeze mismatch: baseline_configuration_hashes" in validate_freeze(changed_baseline_config, snapshot).errors


def test_runner_plan_is_deterministic_and_artifact_names_are_stable() -> None:
    current = config()
    first = BenchmarkRunner(current).dry_run()
    second = BenchmarkRunner(current).dry_run()
    assert first.to_json() == second.to_json()
    assert first.plan == second.plan
    assert len(first.plan) == 18
    assert first.plan[0].participant_id == "BASELINE_A"
    assert first.plan[0].mutation_id == "M001"
    assert first.plan[-1].participant_id == "AEGIS"
    assert first.plan[-1].mutation_id == "M006"
    assert deterministic_run_id("AEGIS", "M005", 12345, current.configuration_hash) == deterministic_run_id("AEGIS", "M005", 12345, current.configuration_hash)
    assert deterministic_artifact_name("AEGIS", "M005", 12345, current.configuration_hash).endswith(".json")
    assert first.plan[0].artifact_name == deterministic_artifact_name("BASELINE_A", "M001", 12345, current.configuration_hash)


def test_dry_run_does_not_call_mutation_execution_or_metric_calculation(monkeypatch) -> None:
    current = config()
    lab = runner_module.MutationLab()
    calls = {"run": 0, "metrics": 0}

    def forbidden_run(*args, **kwargs):
        calls["run"] += 1
        raise AssertionError("benchmark participant execution must not occur during dry-run")

    monkeypatch.setattr(lab, "run", forbidden_run)
    original_metric = runner_module._metric_calculator_available

    def counting_metric():
        calls["metrics"] += 1
        return original_metric()

    monkeypatch.setattr(runner_module, "_metric_calculator_available", counting_metric)
    result = BenchmarkRunner(current, lab=lab).dry_run()
    assert result.status is RunnerDryRunStatus.BLOCKED_NOT_READY
    assert calls["run"] == 0
    assert calls["metrics"] == 1
    assert result.metric_results_generated == 0


def test_mission_010_is_the_only_metric_authority() -> None:
    assert hasattr(__import__("aegis.mutation_metrics", fromlist=["calculate_metrics"]), "calculate_metrics")
    assert not hasattr(runner_module, "calculate_metrics")
    assert "DetectionRate" not in runner_module.__dict__
    assert "AlarmPrecision" not in runner_module.__dict__


def test_participant_provenance_and_no_production_controls_are_explicit() -> None:
    current = config()
    registry = ParticipantRegistry(current)
    for readiness in registry.readiness(current).values():
        assert readiness.provenance == "TEST_DOUBLE"
    runner = BenchmarkRunner(current)
    assert not hasattr(runner, "approve")
    assert not hasattr(runner, "commit")
    assert not hasattr(runner, "rollback")
    assert runner.dry_run().execution_authorized is False
