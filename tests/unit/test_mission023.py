from __future__ import annotations

import json
from pathlib import Path

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_executor import (
    EXPECTED_BENCHMARK_RUN_ID,
    EXPECTED_CONFIGURATION_HASH,
    EXPECTED_SMOKE_RUN_ID,
    BenchmarkExecutor,
)
from aegis.benchmark_lifecycle import BASELINE_B_SMOKE_SUBROOT, BenchmarkArtifactLayout

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
SMOKE_ROOT = ROOT / "benchmarks/runs" / EXPECTED_SMOKE_RUN_ID
BASELINE_B_SMOKE_ROOT = SMOKE_ROOT / BASELINE_B_SMOKE_SUBROOT
BENCHMARK_ROOT = ROOT / "benchmarks/runs" / EXPECTED_BENCHMARK_RUN_ID


def test_canonical_smoke_paths_are_explicit_and_gate_passes_without_execution() -> None:
    config = load_benchmark_config(CONFIG_PATH)
    executor = BenchmarkExecutor(
        config,
        repository_root=ROOT,
        output_root=BENCHMARK_ROOT,
        model_caller=lambda _system, _repair: {"candidates": []},
    )

    assert executor.layout.smoke_root == SMOKE_ROOT
    assert executor.layout.smoke_evidence_root == BASELINE_B_SMOKE_ROOT
    assert executor.layout.root == BENCHMARK_ROOT
    assert executor.layout.baseline_b_smoke_root == BASELINE_B_SMOKE_ROOT

    required = {
        "smoke": BASELINE_B_SMOKE_ROOT / "smoke.json",
        "smoke_execution_log": BASELINE_B_SMOKE_ROOT / "execution_log.json",
        "preflight": SMOKE_ROOT / "preflight.json",
        "root_execution_log": SMOKE_ROOT / "execution_log.json",
        "frozen_config": SMOKE_ROOT / "frozen_config.json",
    }
    assert all(path.is_file() for path in required.values())

    smoke = executor._validate_immutable_smoke_evidence()
    assert smoke["pass"] is True
    assert smoke["status"] == "VALID"
    assert smoke["checks"]["smoke_status"] is True
    assert smoke["checks"]["candidate_accepted"] is True
    assert smoke["checks"]["bounded_application"] is True
    assert smoke["checks"]["runtime_ground_truth_not_provided"] is True
    assert smoke["checks"]["preflight_passed"] is True
    assert smoke["checks"]["frozen_config_hash"] is True

    gate = executor.execution_gate()
    assert gate.passed is True
    assert gate.configuration_hash == EXPECTED_CONFIGURATION_HASH
    assert gate.benchmark_run_id == EXPECTED_BENCHMARK_RUN_ID
    assert gate.checks["smoke_evidence"] is True
    assert gate.checks["participants_ready"] is True
    assert gate.checks["fairness"] is True
    assert gate.checks["planned_run_count"] is True
    assert gate.checks["artifact_root_absent"] is True
    assert gate.checks["smoke_evidence_detail"]["status"] == "VALID"

    assert not BENCHMARK_ROOT.exists()
    root_log = json.loads((SMOKE_ROOT / "execution_log.json").read_text(encoding="utf-8"))
    assert root_log["benchmark_runs_executed"] == 0
    assert root_log["provider_operations_executed"] == 0
    assert root_log["healing_operations_executed"] == 0
    assert root_log["metric_results_generated"] == 0
    assert root_log["execution_authorized"] is False


def test_three_argument_layout_defaults_to_canonical_baseline_b_subroot(tmp_path: Path) -> None:
    smoke_root = tmp_path / EXPECTED_SMOKE_RUN_ID
    layout = BenchmarkArtifactLayout(EXPECTED_BENCHMARK_RUN_ID, tmp_path, smoke_root)
    assert layout.smoke_root == smoke_root
    assert layout.baseline_b_smoke_root == smoke_root / BASELINE_B_SMOKE_SUBROOT
    assert layout.smoke_evidence_root == smoke_root / BASELINE_B_SMOKE_SUBROOT
