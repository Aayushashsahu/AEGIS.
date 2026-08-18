#!/usr/bin/env python3
"""Execute or safely resume the Mission 028 recovery benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.mission028_execution import (
    MISSION_028_INVALIDATED_RUN_ID,
    MISSION_028_RECOVERY_ATTEMPT_ID,
    MISSION_028_RECOVERY_RUN_ID_PREFIX,
    build_mission028_executor,
    build_nvidia_caller,
    load_mission028_config,
    recovery_run_id,
)
from aegis.nvidia_provider import load_nvidia_api_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute Mission 028 clean recovery benchmark")
    parser.add_argument("--run", action="store_true", help="explicitly authorize the recovery run")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--preflight", default="experiments/mission_028_recovery_preflight.json", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config = load_mission028_config(root)
    run_id = recovery_run_id(config)
    if run_id == MISSION_028_INVALIDATED_RUN_ID:
        raise RuntimeError("recovery run ID must not reuse the invalidated first attempt")
    if not args.run:
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "--run is required; no recovery benchmark executed", "benchmark_run_id": run_id}, indent=2))
        return 2
    preflight_path = args.preflight if args.preflight.is_absolute() else root / args.preflight
    if not preflight_path.is_file():
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "recovery preflight evidence is missing", "benchmark_run_id": run_id}, indent=2))
        return 2
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "RECOVERY_PREFLIGHT_PASS" or preflight.get("benchmark_run_id") != run_id or preflight.get("invalidated_first_attempt_run_id") != MISSION_028_INVALIDATED_RUN_ID:
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "recovery preflight identity or status is invalid", "benchmark_run_id": run_id}, indent=2))
        return 2
    api_key = load_nvidia_api_key()
    if not api_key:
        print(json.dumps({"status": "BLOCKED_NOT_READY", "error": "NVIDIA API key is required for recovery execution", "benchmark_run_id": run_id}, indent=2))
        return 2
    output_root = root / "benchmarks/runs" / run_id
    caller = build_nvidia_caller(config, api_key=api_key)
    executor = build_mission028_executor(
        root,
        output_root=output_root,
        model_caller=caller,
        attempt_id=MISSION_028_RECOVERY_ATTEMPT_ID,
        run_id_prefix=MISSION_028_RECOVERY_RUN_ID_PREFIX,
    )
    summary = executor.execute()
    payload = {
        "mission": "028",
        "attempt_kind": "RECOVERY",
        "invalidated_first_attempt_run_id": MISSION_028_INVALIDATED_RUN_ID,
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
        "artifact_root_preservation_fix": "runs_root_explicit_and_test_cleanup_temp_only",
    }
    evidence_path = root / "experiments/mission_028_recovery_execution_summary.json"
    evidence_path.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2))
    return 0 if summary.status == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
