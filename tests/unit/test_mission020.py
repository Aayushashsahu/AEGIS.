from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_lifecycle import BenchmarkArtifactLayout, BenchmarkLifecyclePhase, deterministic_benchmark_run_id
from aegis.benchmark_runner import BenchmarkRunner

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
SMOKE_RUN_ID = "mission_016_floor_59a11e27a71f"
SMOKE_ROOT = ROOT / "benchmarks/runs" / SMOKE_RUN_ID
HISTORICAL_ROOT = ROOT / "benchmarks/runs" / "mission_016_floor_f48ec5c5792b"
CONFIG_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"

_PREFLIGHT_SPEC = importlib.util.spec_from_file_location("mission016_preflight_smoke_m020", ROOT / "scripts/mission016_preflight_smoke.py")
assert _PREFLIGHT_SPEC is not None and _PREFLIGHT_SPEC.loader is not None
preflight = importlib.util.module_from_spec(_PREFLIGHT_SPEC)
sys.modules[_PREFLIGHT_SPEC.name] = preflight
_PREFLIGHT_SPEC.loader.exec_module(preflight)


def _digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_existing_mission019_smoke_evidence_is_validated_without_recreation() -> None:
    before = _digest(SMOKE_ROOT)
    result, config = preflight.run_preflight()
    assert result.passed is True
    assert config.configuration_hash == CONFIG_HASH
    assert result.checks["smoke_evidence"]["pass"] is True
    assert result.checks["artifact_paths"]["preflight_smoke_root_present"] is True
    assert result.checks["artifact_paths"]["benchmark_run_root_absent"] is True
    assert _digest(SMOKE_ROOT) == before


def test_preflight_does_not_call_gemini_when_existing_smoke_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_run(_config):
        raise AssertionError("Mission 020 must not rerun Gemini when smoke evidence is valid")

    monkeypatch.setattr(preflight, "run_baseline_b_smoke", must_not_run)
    result, _ = preflight.run_preflight()
    assert result.passed is True
    assert result.checks["smoke_evidence"]["status"] == "VALID"


def test_corrupt_smoke_evidence_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    isolated_root = tmp_path / SMOKE_RUN_ID
    shutil.copytree(SMOKE_ROOT, isolated_root)
    smoke_path = isolated_root / "baseline_b_execution_readiness_smoke/smoke.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    smoke["status"] = "FAIL"
    smoke_path.write_text(json.dumps(smoke), encoding="utf-8")
    monkeypatch.setattr(preflight, "PREFLIGHT_SMOKE_ROOT", isolated_root)
    monkeypatch.setattr(preflight, "FLOOR_RUN_ROOT", isolated_root)
    monkeypatch.setattr(preflight, "SMOKE_ROOT", isolated_root / "baseline_b_execution_readiness_smoke")
    result, _ = preflight.run_preflight()
    assert result.passed is False
    assert result.checks["smoke_evidence"]["pass"] is False
    assert "smoke_status" in result.checks["smoke_evidence"]["errors"]


def test_deterministic_benchmark_run_id_is_distinct_from_smoke_run_id() -> None:
    revisions = dict(preflight.EXPECTED_REVISIONS)
    run_id_one = deterministic_benchmark_run_id(CONFIG_HASH, "mission-020-floor-v1", revisions)
    run_id_two = deterministic_benchmark_run_id(CONFIG_HASH, "mission-020-floor-v1", dict(reversed(tuple(revisions.items()))))
    assert run_id_one == run_id_two
    assert run_id_one.startswith("mission_020_floor_")
    assert run_id_one != SMOKE_RUN_ID
    assert run_id_one == preflight.BENCHMARK_RUN_ID


def test_benchmark_artifact_root_cannot_overlap_smoke_root(tmp_path: Path) -> None:
    config = load_benchmark_config(CONFIG_PATH)
    future_root = tmp_path / preflight.BENCHMARK_RUN_ID
    layout = BenchmarkArtifactLayout(preflight.BENCHMARK_RUN_ID, tmp_path, SMOKE_ROOT)
    layout.validate_absent()
    runner = BenchmarkRunner(
        config,
        lifecycle_phase=BenchmarkLifecyclePhase.BENCHMARK_EXECUTION,
        artifact_root=str(future_root),
        forbidden_artifact_roots=(str(SMOKE_ROOT),),
    )
    assert runner.lifecycle_phase is BenchmarkLifecyclePhase.BENCHMARK_EXECUTION
    assert runner.build_input("BASELINE_A", "M001", 12345).artifact_root == str(future_root)
    with pytest.raises(ValueError):
        BenchmarkRunner(config, artifact_root=str(SMOKE_ROOT / "raw"), forbidden_artifact_roots=(str(SMOKE_ROOT),))


def test_lifecycle_phases_are_explicit() -> None:
    config = load_benchmark_config(CONFIG_PATH)
    preflight_runner = BenchmarkRunner(config, lifecycle_phase=BenchmarkLifecyclePhase.PREFLIGHT)
    smoke_runner = BenchmarkRunner(config, lifecycle_phase=BenchmarkLifecyclePhase.SMOKE)
    assert preflight_runner.lifecycle_phase is BenchmarkLifecyclePhase.PREFLIGHT
    assert smoke_runner.lifecycle_phase is BenchmarkLifecyclePhase.SMOKE
    assert preflight.BENCHMARK_RUN_ROOT != SMOKE_ROOT


def test_historical_artifacts_remain_byte_identical_and_counters_stay_zero() -> None:
    smoke_before = _digest(SMOKE_ROOT)
    historical_before = _digest(HISTORICAL_ROOT)
    smoke_log = json.loads((SMOKE_ROOT / "execution_log.json").read_text(encoding="utf-8"))
    root_log = json.loads((SMOKE_ROOT / "execution_log.json").read_text(encoding="utf-8"))
    assert root_log["benchmark_runs_executed"] == 0
    assert root_log["provider_operations_executed"] == 0
    assert root_log["healing_operations_executed"] == 0
    assert root_log["metric_results_generated"] == 0
    assert root_log["execution_authorized"] is False
    assert smoke_log["status"] == "BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK"
    assert _digest(SMOKE_ROOT) == smoke_before
    assert _digest(HISTORICAL_ROOT) == historical_before
