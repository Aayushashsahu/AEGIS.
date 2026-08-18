#!/usr/bin/env python3
"""Run or safely resume the explicitly authorized Mission 028 benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.mission028_execution import (
    build_mission028_executor,
    build_nvidia_caller,
    load_mission028_config,
    mission028_run_id,
)
from aegis.nvidia_provider import load_nvidia_api_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute Mission 028 NVIDIA comparative benchmark")
    parser.add_argument("--run", action="store_true", help="explicitly authorize the Mission 028 run")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--preflight", default="experiments/mission_028_preflight.json", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.run:
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "--run is required; no benchmark executed"}, indent=2))
        return 2

    config = load_mission028_config(root)
    run_id = mission028_run_id(config)
    preflight_path = args.preflight if args.preflight.is_absolute() else root / args.preflight
    if not preflight_path.is_file():
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "Mission 028 preflight evidence is missing", "benchmark_run_id": run_id}, indent=2))
        return 2
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if (
        preflight.get("status") != "PREFLIGHT_PASS"
        or preflight.get("configuration_hash") != config.configuration_hash
        or preflight.get("benchmark_run_id") != run_id
    ):
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "Mission 028 preflight identity or status is invalid", "benchmark_run_id": run_id}, indent=2))
        return 2

    api_key = load_nvidia_api_key()
    if not api_key:
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "NVIDIA API key is required for the explicit run", "benchmark_run_id": run_id}, indent=2))
        return 2

    caller = build_nvidia_caller(config, api_key=api_key)
    output_root = root / "benchmarks/runs" / run_id
    executor = build_mission028_executor(root, output_root=output_root, model_caller=caller)
    summary = executor.execute()
    payload = {
        "mission": "028",
        "summary": summary.to_dict(),
        "nvidia_caller": caller.redacted_metadata(),
        "rate_policy": {
            "benchmark_requests_per_minute": 6,
            "benchmark_min_interval_seconds": 10,
            "concurrency_limit": 1,
            "provider_limit": "UNKNOWN",
        },
        "gemini_invoked": False,
        "bright_data_invoked": False,
        "healing_operations_executed": 0,
    }
    evidence_path = root / "experiments/mission_028_execution_summary.json"
    evidence_path.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2))
    return 0 if summary.status == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
