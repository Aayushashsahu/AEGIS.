from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import aegis.benchmark_executor as executor_module
from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_executor import (
    EXPECTED_BENCHMARK_RUN_ID,
    EXPECTED_CONFIGURATION_HASH,
    BenchmarkExecutor,
    FixtureController,
    FixtureResetResult,
)
from aegis.benchmark_resume import ResumeValidationError, inspect_existing_run
from aegis.benchmark_runner import RunnerState

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"


def config():
    return load_benchmark_config(CONFIG_PATH)


def smoke_ok():
    return {"pass": True, "status": "VALID", "checks": {}}


def source_ok(_revision: str, _path: str) -> bool:
    return True


def fake_model(_system_prompt: str, _repair_prompt: str):
    return {"candidates": [{"candidate": {"code": "safe-resume-test-double"}}]}


def make_executor(tmp_path: Path, **kwargs) -> BenchmarkExecutor:
    return BenchmarkExecutor(
        config(),
        repository_root=tmp_path,
        output_root=tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID,
        source_revision_checker=source_ok,
        smoke_evidence_validator=smoke_ok,
        model_caller=fake_model,
        **kwargs,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_interrupted_root(tmp_path: Path) -> tuple[BenchmarkExecutor, tuple[Path, ...]]:
    """Create a deterministic interrupted TEST_DOUBLE root; never uses real providers."""

    fresh = make_executor(tmp_path)
    summary = fresh.execute()
    assert summary.status == "COMPLETED"
    root = fresh.output_root
    by_participant: dict[str, list[Path]] = {"BASELINE_A": [], "BASELINE_B": [], "AEGIS": []}
    for path in sorted((root / "raw").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_participant[payload["manifest"]["participant_id"]].append(path)

    # Preserve all A, 36 B (26 completed + the ten known frozen failures), and no AEGIS.
    known_failed = {("M001", 3), ("M001", 10), ("M002", 3), ("M003", 5), ("M003", 6), ("M003", 8), ("M003", 10), ("M004", 1), ("M004", 3), ("M004", 4)}
    failed_paths = []
    completed_candidates = []
    for path in by_participant["BASELINE_B"]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        pair = (payload["manifest"]["mutation_id"], int(payload["manifest"]["run_id"].split("__trial-", 1)[1].split("__", 1)[0]))
        if pair in known_failed:
            failed_paths.append(path)
        else:
            completed_candidates.append(path)
    keep_paths = set(failed_paths + completed_candidates[:26])
    for path in by_participant["AEGIS"] + [path for path in by_participant["BASELINE_B"] if path not in keep_paths]:
        path.unlink()
    for path in failed_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["terminal_state"] = RunnerState.FAILED.value
        payload["errors"] = ["pre-existing failed attempt; frozen retry_count=0"]
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(root / "metrics")
    shutil.rmtree(root / "reports")
    (root / "metrics").mkdir()
    (root / "reports").mkdir()
    (root / "execution_log.json").write_text(
        json.dumps(
            {
                "status": "RUNNING",
                "benchmark_run_id": EXPECTED_BENCHMARK_RUN_ID,
                "configuration_hash": EXPECTED_CONFIGURATION_HASH,
                "planned_runs": 180,
                "runs": [],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    existing = tuple(sorted((root / "raw").glob("*.json")))
    return fresh, existing


def test_empty_root_starts_normally(tmp_path: Path) -> None:
    executor = make_executor(tmp_path)
    gate = executor.execution_gate()
    assert gate.passed is True
    assert gate.checks["artifact_root_absent"] is True
    assert gate.checks["artifact_root_resumable"] is True
    assert gate.checks["missing_run_count"] == 180
    assert not executor.output_root.exists()


def test_interrupted_counts_and_deterministic_missing_set(tmp_path: Path) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    executor = make_executor(tmp_path)
    gate = executor.execution_gate()
    assert gate.passed is True
    assert gate.checks["artifact_root_absent"] is False
    assert gate.checks["artifact_root_resumable"] is True
    assert gate.checks["existing_terminal_artifacts_valid"] is True
    assert gate.checks["missing_run_set_computed"] is True
    assert gate.checks["missing_run_count"] == 84
    assert executor._resume_inspection is not None
    assert executor._resume_inspection.terminal_counts == {
        "COMPLETED": 86,
        "FAILED": 10,
        "INVALIDATED": 0,
        "TIMED_OUT": 0,
    }
    expected_missing = tuple(manifest.run_id for manifest in executor._resume_inspection.missing_manifests)
    executor_again = make_executor(tmp_path)
    second_gate = executor_again.execution_gate()
    assert second_gate.passed is True
    assert executor_again._resume_inspection is not None
    assert tuple(manifest.run_id for manifest in executor_again._resume_inspection.missing_manifests) == expected_missing
    assert len(existing) == 96


def test_all_terminal_states_are_consumed_and_never_retried(tmp_path: Path) -> None:
    _, _ = seed_interrupted_root(tmp_path)
    executor = make_executor(tmp_path)
    manifests = executor.plan_manifests()
    inspection = executor._resume_inspection if executor.execution_gate().passed else None
    assert inspection is not None
    by_state = {state: [] for state in ("COMPLETED", "FAILED", "TIMED_OUT", "INVALIDATED")}
    for artifact in inspection.artifacts_by_run_id.values():
        by_state[artifact.state].append(artifact.manifest.run_id)
    assert len(by_state["COMPLETED"]) == 86
    assert len(by_state["FAILED"]) == 10
    assert not set(by_state["FAILED"]) & {manifest.run_id for manifest in inspection.missing_manifests}
    assert tuple(manifest.run_id for manifest in inspection.missing_manifests) == tuple(
        manifest.run_id for manifest in manifests if manifest.run_id not in inspection.artifacts_by_run_id
    )


def test_malformed_artifact_blocks_resume_before_execution(tmp_path: Path) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    path = existing[0]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("terminal_state")
    path.write_text(json.dumps(payload), encoding="utf-8")
    executor = make_executor(tmp_path)
    gate = executor.execution_gate()
    assert gate.passed is False
    assert "artifact_root_resumable" in gate.errors
    before = digest(path)
    summary = executor.execute()
    assert summary.execution_authorized is False
    assert summary.status == "BLOCKED_NOT_READY"
    assert digest(path) == before


@pytest.mark.parametrize(
    "mutator,needle",
    [
        (lambda payload: payload["manifest"].__setitem__("configuration_hash", "wrong"), "configuration hash"),
        (lambda payload: payload["manifest"].__setitem__("participant_revision", "wrong"), "participant revision"),
        (lambda payload: payload["manifest"].__setitem__("run_id", "wrong-run-id"), "run ID"),
    ],
)
def test_identity_mismatch_blocks_resume(tmp_path: Path, mutator, needle: str) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    path = existing[0]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutator(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    gate = make_executor(tmp_path).execution_gate()
    assert gate.passed is False
    assert "artifact_root_resumable" in gate.errors
    assert any(needle in error for error in gate.errors)


def test_resume_executes_only_missing_and_calls_metrics_once_after_180_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    before = {path: digest(path) for path in existing}
    calls = 0
    original = executor_module.calculate_compatibility_metrics

    def counted(report):
        nonlocal calls
        calls += 1
        return original(report)

    monkeypatch.setattr(executor_module, "calculate_compatibility_metrics", counted)
    summary = make_executor(tmp_path).execute()
    assert summary.status == "COMPLETED"
    assert summary.completed_runs == 170
    assert summary.failed_runs == 10
    assert summary.benchmark_runs_executed == 180
    assert summary.provider_operations_executed == 60
    assert summary.metric_results_generated > 0
    assert calls == 1
    assert len(list((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "raw").glob("*.json"))) == 180
    assert {path: digest(path) for path in existing} == before

    second = make_executor(tmp_path).execute()
    assert second.status == "COMPLETED"
    assert second.benchmark_runs_executed == 180
    assert calls == 1
    log = json.loads((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "execution_log.json").read_text(encoding="utf-8"))
    assert len({run["run_id"] for run in log["runs"]}) == 180


def test_interruption_after_resume_is_recoverable_and_metrics_wait(tmp_path: Path) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    before = {path: digest(path) for path in existing}



    class FailOnce(FixtureController):
        def __init__(self, lab):
            super().__init__(lab)
            self.calls = 0

        def reset(self):
            self.calls += 1
            if self.calls == 1:
                return FixtureResetResult(False, "interrupted after resumed trial")
            return super().reset()

    first = make_executor(tmp_path)
    controller = FailOnce(first.lab)
    interrupted = make_executor(tmp_path, lab=first.lab, fixture_controller=controller).execute()
    assert interrupted.status == "RUNNING"
    assert interrupted.metric_results_generated == 0
    assert len(list((tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "raw").glob("*.json"))) == 97

    resumed = make_executor(tmp_path).execute()
    assert resumed.status == "COMPLETED"
    assert resumed.completed_runs == 169
    assert resumed.failed_runs == 10
    assert resumed.invalidated_runs == 1
    assert len({path.name for path in (tmp_path / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID / "raw").glob("*.json")}) == 180
    assert {path: digest(path) for path in existing} == before


def test_resume_inspection_rejects_duplicate_manifest_run_ids(tmp_path: Path) -> None:
    _, existing = seed_interrupted_root(tmp_path)
    path = existing[1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    duplicate = path.with_name("duplicate.json")
    duplicate.write_text(json.dumps(payload), encoding="utf-8")
    executor = make_executor(tmp_path)
    with pytest.raises(ResumeValidationError, match="filename does not match manifest|duplicate terminal"):
        inspect_existing_run(
            executor.output_root,
            executor.plan_manifests(),
            expected_benchmark_run_id=EXPECTED_BENCHMARK_RUN_ID,
            expected_configuration_hash=EXPECTED_CONFIGURATION_HASH,
        )
