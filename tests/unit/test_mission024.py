from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_executor import BenchmarkExecutor, EXPECTED_BENCHMARK_RUN_ID, EXPECTED_CONFIGURATION_HASH
from aegis.smoke_evidence import resolve_immutable_smoke_evidence, validate_immutable_smoke_evidence

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
BENCHMARK_ROOT = ROOT / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID


def _load_preflight():
    name = "mission016_preflight_smoke_m024"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/mission016_preflight_smoke.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_preflight_and_executor_share_canonical_paths_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    preflight = _load_preflight()
    paths = resolve_immutable_smoke_evidence(ROOT)
    before = _digest(paths.smoke_root)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("Mission 024 must not rerun smoke/Gemini")

    monkeypatch.setattr(preflight, "run_baseline_b_smoke", must_not_run)
    preflight_result, config = preflight.run_preflight()
    preflight_validation = validate_immutable_smoke_evidence(ROOT)

    executor = BenchmarkExecutor(
        config,
        repository_root=ROOT,
        output_root=BENCHMARK_ROOT,
        model_caller=lambda _system, _repair: {"candidates": []},
    )
    gate = executor.execution_gate()

    assert preflight_result.passed is True
    assert config.configuration_hash == EXPECTED_CONFIGURATION_HASH
    assert preflight_validation.passed is True
    assert preflight_validation.status == "VALID"
    assert preflight_validation.checks["candidate_accepted"] is True
    assert preflight_validation.checks["bounded_application"] is True
    assert preflight_validation.checks["runtime_ground_truth_not_provided"] is True
    assert preflight.SMOKE_EVIDENCE_PATHS.to_dict() == paths.to_dict()
    assert executor.smoke_evidence_paths.to_dict() == paths.to_dict()
    assert executor._validate_immutable_smoke_evidence() == preflight_validation.to_dict()

    assert gate.passed is True
    assert gate.execution_authorized is False
    assert gate.checks["smoke_evidence"] is True
    assert gate.checks["planned_run_count"] is True
    assert gate.checks["artifact_root_absent"] is True
    assert gate.checks["smoke_evidence_detail"]["status"] == "VALID"
    assert not BENCHMARK_ROOT.exists()
    assert _digest(paths.smoke_root) == before


def test_canonical_resolver_returns_exact_five_evidence_files() -> None:
    paths = resolve_immutable_smoke_evidence(ROOT)
    assert paths.smoke_root == ROOT / "benchmarks/runs/mission_016_floor_59a11e27a71f"
    assert paths.baseline_b_smoke_root == paths.smoke_root / "baseline_b_execution_readiness_smoke"
    assert paths.smoke == paths.baseline_b_smoke_root / "smoke.json"
    assert paths.smoke_log == paths.baseline_b_smoke_root / "execution_log.json"
    assert paths.preflight == paths.smoke_root / "preflight.json"
    assert paths.root_execution_log == paths.smoke_root / "execution_log.json"
    assert paths.frozen_config == paths.smoke_root / "frozen_config.json"
    assert all(path.is_file() for path in (paths.smoke, paths.smoke_log, paths.preflight, paths.root_execution_log, paths.frozen_config))

    root_log = json.loads(paths.root_execution_log.read_text(encoding="utf-8"))
    assert root_log["benchmark_runs_executed"] == 0
    assert root_log["provider_operations_executed"] == 0
    assert root_log["healing_operations_executed"] == 0
    assert root_log["metric_results_generated"] == 0
    assert root_log["execution_authorized"] is False
