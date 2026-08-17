from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aegis.benchmark_config import default_validation_config, run_dry_run


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks" / "configs" / "mission_011_validation_floor.json"
DRY_RUN_PATH = ROOT / "benchmarks" / "configs" / "mission_011_dry_run.json"
PLAN_PATH = ROOT / "benchmarks" / "configs" / "mission_011_execution_plan.json"


def git_revision() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()


def main() -> None:
    revision = git_revision()
    config = default_validation_config(code_revision=revision, repository_state="DIRTY_USER_FILES_PRESERVED")
    first = run_dry_run(config, repository_root=ROOT)
    second = run_dry_run(config, repository_root=ROOT)
    if first.to_json() != second.to_json():
        raise SystemExit("Mission 011 reproducibility check failed: dry-run outputs differ")
    if first.execution_plan != second.execution_plan:
        raise SystemExit("Mission 011 reproducibility check failed: plans differ")
    if not first.valid:
        raise SystemExit(f"Mission 011 configuration validation failed: {first.validation.errors}")

    CONFIG_PATH.write_text(config.to_json(), encoding="utf-8")
    DRY_RUN_PATH.write_text(first.to_json(), encoding="utf-8")
    plan = {
        "plan_version": "mission-011-execution-plan-v1",
        "benchmark_id": config.benchmark_id,
        "configuration_hash": config.configuration_hash,
        "validation_only": True,
        "execution_authorized": False,
        "expected_run_count": first.expected_run_count,
        "mutation_count": first.mutation_count,
        "seed_count": first.seed_count,
        "baseline_count": first.baseline_count,
        "execution": "NOT_EXECUTED",
        "steps": first.to_dict()["execution_plan"],
    }
    PLAN_PATH.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
