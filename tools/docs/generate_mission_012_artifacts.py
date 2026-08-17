from __future__ import annotations

import json
from pathlib import Path

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_runner import BenchmarkRunner


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks" / "configs" / "mission_011_validation_floor.json"
DRY_RUN_PATH = ROOT / "benchmarks" / "configs" / "mission_012_runner_dry_run.json"
PLAN_PATH = ROOT / "benchmarks" / "configs" / "mission_012_execution_plan.json"
READINESS_PATH = ROOT / "benchmarks" / "configs" / "mission_012_participant_readiness.json"


def main() -> None:
    config = load_benchmark_config(CONFIG_PATH)
    runner = BenchmarkRunner(config)
    first = runner.dry_run()
    second = BenchmarkRunner(config).dry_run()
    if first.to_json() != second.to_json():
        raise SystemExit("Mission 012 reproducibility check failed: dry-run outputs differ")
    if first.plan != second.plan:
        raise SystemExit("Mission 012 reproducibility check failed: execution plans differ")
    if first.status.value != "BLOCKED_NOT_READY":
        raise SystemExit(f"Mission 012 expected BLOCKED_NOT_READY, got {first.status.value}")
    if first.benchmark_runs_executed != 0 or first.provider_operations_executed != 0 or first.healing_operations_executed != 0:
        raise SystemExit("Mission 012 zero-execution invariant failed")
    if first.metric_results_generated != 0 or first.execution_authorized:
        raise SystemExit("Mission 012 metric/execution authorization invariant failed")

    DRY_RUN_PATH.write_text(first.to_json(), encoding="utf-8")
    plan = {
        "runner_version": "mission-012-runner-v1",
        "status": first.status.value,
        "validation_only": True,
        "execution_authorized": False,
        "benchmark_id": config.benchmark_id,
        "configuration_hash": config.configuration_hash,
        "expected_run_count": first.expected_run_count,
        "participant_count": first.participant_count,
        "mutation_count": first.mutation_count,
        "seed_count": first.seed_count,
        "execution": "NOT_EXECUTED",
        "steps": [item.to_dict() for item in first.plan],
    }
    PLAN_PATH.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    readiness = {
        "runner_version": "mission-012-runner-v1",
        "validation_only": True,
        "configuration_hash": config.configuration_hash,
        "participants": first.to_dict()["participant_readiness"],
        "benchmark_runs_executed": 0,
        "provider_operations_executed": 0,
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
    }
    READINESS_PATH.write_text(json.dumps(readiness, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
