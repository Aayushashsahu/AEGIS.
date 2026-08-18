from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_executor import (
    EXPECTED_BENCHMARK_RUN_ID,
    EXPECTED_CONFIGURATION_HASH,
    BenchmarkExecutor,
    FixtureController,
    deterministic_trial_run_id,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"


def config():
    return load_benchmark_config(CONFIG_PATH)


def smoke_ok():
    return {"pass": True, "status": "VALID", "checks": {}}


def source_ok(_revision: str, _path: str) -> bool:
    return True


def fake_model(_system_prompt: str, _repair_prompt: str):
    return {"candidates": [{"candidate": {"code": "safe-test-double-candidate"}}]}


def make_executor(tmp_path: Path, **kwargs) -> BenchmarkExecutor:
    output = tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID
    return BenchmarkExecutor(
        config(),
        repository_root=tmp_path,
        output_root=output,
        source_revision_checker=source_ok,
        smoke_evidence_validator=smoke_ok,
        model_caller=fake_model,
        **kwargs,
    )


def test_cli_requires_explicit_mode_and_run_output(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    no_mode = subprocess.run(
        [sys.executable, "scripts/benchmark_runner.py", "--config", str(CONFIG_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert no_mode.returncode == 2
    assert "--dry-run or --run" in no_mode.stdout
    spec = importlib.util.spec_from_file_location("aegis_benchmark_cli", ROOT / "scripts/benchmark_runner.py")
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    parsed = cli.build_parser().parse_args(["--config", str(CONFIG_PATH), "--run"])
    assert parsed.run is True
    assert parsed.output is None


def test_dry_run_remains_execution_free_and_does_not_create_future_root(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [sys.executable, "scripts/benchmark_runner.py", "--config", str(CONFIG_PATH), "--dry-run"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["execution_authorized"] is False
    assert payload["benchmark_runs_executed"] == 0
    assert payload["provider_operations_executed"] == 0
    assert payload["healing_operations_executed"] == 0
    assert payload["metric_results_generated"] == 0
    assert not (ROOT / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID).exists()


def test_execution_gate_accepts_corrected_config_and_plans_180(tmp_path: Path) -> None:
    executor = make_executor(tmp_path)
    gate = executor.execution_gate()
    assert gate.passed is True
    assert gate.configuration_hash == EXPECTED_CONFIGURATION_HASH
    assert gate.benchmark_run_id == EXPECTED_BENCHMARK_RUN_ID
    assert gate.expected_run_count == 180
    assert len(executor.plan_manifests()) == 180


def test_wrong_hash_blocks_execution(tmp_path: Path) -> None:
    bad = replace(config(), configuration_hash="wrong-hash")
    executor = BenchmarkExecutor(
        bad,
        repository_root=tmp_path,
        output_root=tmp_path / "benchmarks/runs" / "wrong",
        source_revision_checker=source_ok,
        smoke_evidence_validator=smoke_ok,
        model_caller=fake_model,
    )
    gate = executor.execution_gate()
    assert gate.passed is False
    assert "configuration_hash" in gate.errors
    assert executor.execute().execution_authorized is False
    assert not (tmp_path / "benchmarks/runs" / "wrong").exists()


def test_wrong_participant_revision_blocks_execution(tmp_path: Path) -> None:
    current = config()
    altered = replace(current.baselines[0], implementation_revision="wrong-revision")
    bad = replace(current, baselines=(altered, *current.baselines[1:]), configuration_hash=current.configuration_hash)
    executor = BenchmarkExecutor(
        bad,
        repository_root=tmp_path,
        output_root=tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID,
        source_revision_checker=source_ok,
        smoke_evidence_validator=smoke_ok,
        model_caller=fake_model,
    )
    assert executor.execution_gate().passed is False


def test_fairness_failure_blocks_execution(tmp_path: Path) -> None:
    class UnfairExecutor(BenchmarkExecutor):
        def _trial_input(self, participant_id: str, mutation_id: str, trial_number: int, seed: int):
            result = super()._trial_input(participant_id, mutation_id, trial_number, seed)
            if participant_id == "AEGIS":
                return replace(result, trial_metadata={"ground_truth_runtime_payload": "LEAKED"})
            return result

    output = tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID
    executor = UnfairExecutor(
        config(),
        repository_root=tmp_path,
        output_root=output,
        source_revision_checker=source_ok,
        smoke_evidence_validator=smoke_ok,
        model_caller=fake_model,
    )
    gate = executor.execution_gate()
    assert gate.passed is False
    assert "fairness" in gate.errors


def test_output_root_collision_is_rejected_before_execution(tmp_path: Path) -> None:
    smoke_root = tmp_path / "benchmarks/runs" / "mission_016_floor_59a11e27a71f"
    with pytest.raises(ValueError, match="overlaps forbidden root"):
        BenchmarkExecutor(
            config(),
            repository_root=tmp_path,
            output_root=smoke_root,
            source_revision_checker=source_ok,
            smoke_evidence_validator=smoke_ok,
            model_caller=fake_model,
        )


def test_trial_ids_are_deterministic_and_unique_across_trials() -> None:
    ids = {
        deterministic_trial_run_id(EXPECTED_BENCHMARK_RUN_ID, "AEGIS", "M005", trial, 12345, EXPECTED_CONFIGURATION_HASH)
        for trial in range(1, 11)
    }
    assert len(ids) == 10
    assert ids == {
        deterministic_trial_run_id(EXPECTED_BENCHMARK_RUN_ID, "AEGIS", "M005", trial, 12345, EXPECTED_CONFIGURATION_HASH)
        for trial in range(1, 11)
    }


def test_exact_180_execution_opportunities_and_raw_terminal_evidence(tmp_path: Path) -> None:
    executor = make_executor(tmp_path)
    summary = executor.execute()
    assert summary.status == "FAILED_METRIC_BOUNDARY"
    assert summary.execution_authorized is True
    assert summary.planned_runs == 180
    assert summary.completed_runs == 180
    assert summary.failed_runs == 0
    assert summary.timed_out_runs == 0
    assert summary.invalidated_runs == 0
    assert summary.benchmark_runs_executed == 180
    assert summary.provider_operations_executed == 60
    raw_files = sorted((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "raw").glob("*.json"))
    assert len(raw_files) == 180
    assert len({path.name for path in raw_files}) == 180
    sample = json.loads(raw_files[0].read_text(encoding="utf-8"))
    assert sample["artifact_schema"] == "participant-run-evidence-v1"
    assert sample["terminal_state"] == "COMPLETED"
    log = json.loads((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "execution_log.json").read_text(encoding="utf-8"))
    assert log["planned_runs"] == 180
    assert log["completed_runs"] == 180
    assert log["metric_results_generated"] == 0
    assert "Mission 010 metric boundary incompatibility" in summary.errors[0]
    assert not (tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "metrics/mission-010-metrics.json").exists()


def test_reset_is_called_between_trials(tmp_path: Path) -> None:
    class CountingFixtureController(FixtureController):
        def __init__(self, lab):
            super().__init__(lab)
            self.reset_calls = 0

        def reset(self):
            self.reset_calls += 1
            return super().reset()

    controller = CountingFixtureController(make_executor(tmp_path).lab)
    executor = make_executor(tmp_path, fixture_controller=controller)
    summary = executor.execute()
    assert summary.status == "FAILED_METRIC_BOUNDARY"
    assert controller.reset_calls == 180


def test_reset_failure_invalidates_and_halts_with_artifact(tmp_path: Path) -> None:
    class FailingResetController(FixtureController):
        def __init__(self, lab):
            super().__init__(lab)
            self.calls = 0

        def reset(self):
            self.calls += 1
            if self.calls == 1:
                return type(super().reset())(False, "injected reset failure")
            return super().reset()

    controller = FailingResetController(make_executor(tmp_path).lab)
    executor = make_executor(tmp_path, fixture_controller=controller)
    summary = executor.execute()
    assert summary.status == "FAILED"
    assert summary.invalidated_runs == 1
    assert summary.completed_runs == 0
    assert "injected reset failure" in summary.errors
    raw = list((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "raw").glob("*.json"))
    assert len(raw) == 1
    assert json.loads(raw[0].read_text(encoding="utf-8"))["terminal_state"] == "INVALIDATED"


def test_mission019_smoke_root_is_not_touched_by_test_execution(tmp_path: Path) -> None:
    smoke_root = tmp_path / "benchmarks/runs" / "mission_016_floor_59a11e27a71f"
    smoke_root.mkdir(parents=True)
    marker = smoke_root / "marker.txt"
    marker.write_text("immutable", encoding="utf-8")
    executor = make_executor(tmp_path)
    summary = executor.execute()
    assert summary.status == "FAILED_METRIC_BOUNDARY"
    assert marker.read_text(encoding="utf-8") == "immutable"
    assert not (smoke_root / "raw").exists()
