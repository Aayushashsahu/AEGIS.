#!/usr/bin/env python3
"""Mission 028 provider-free pre-execution gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.mission028_execution import preflight, validate_benchmark_rate_policy


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Mission 028 before trial 1")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--output", default="experiments/mission_028_preflight.json", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    gate, config, run_id = preflight(root)
    payload = {
        "mission": "028",
        "status": "PREFLIGHT_PASS" if gate.passed else "STOPPED_PREFLIGHT",
        "notice": "NO TRIAL EXECUTED",
        "benchmark_run_id": run_id,
        "configuration_hash": config.configuration_hash,
        "attempt_id": "mission-028-nvidia-comparative-benchmark-v1",
        "rate_policy": validate_benchmark_rate_policy(config),
        "gate": gate.to_dict(),
        "execution_authorized": False,
        "benchmark_runs_executed": 0,
        "provider_operations_executed": 0,
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
    }
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2))
    return 0 if gate.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
