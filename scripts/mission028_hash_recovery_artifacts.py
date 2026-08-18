#!/usr/bin/env python3
"""Hash and validate the preserved Mission 028 recovery artifact root."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.benchmark_resume import inspect_existing_run
from aegis.mission028_execution import load_mission028_config, build_mission028_executor, recovery_run_id


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash Mission 028 recovery artifacts")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--output", default="experiments/mission_028_recovery_artifact_hashes.json", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config = load_mission028_config(root)
    run_id = recovery_run_id(config)
    run_root = root / "benchmarks/runs" / run_id
    executor = build_mission028_executor(root, output_root=run_root, model_caller=object(), attempt_id="mission-028-nvidia-comparative-benchmark-recovery-v1", run_id_prefix="mission_028_recovery_floor")
    manifests = executor.plan_manifests()
    inspection = inspect_existing_run(run_root, manifests, expected_benchmark_run_id=run_id, expected_configuration_hash=config.configuration_hash, expected_participant_revisions={spec.baseline_id: spec.implementation_revision for spec in config.baselines})
    raw_paths = sorted((run_root / "raw").glob("*.json"))
    states = Counter(artifact.state for artifact in inspection.artifacts_by_run_id.values())
    hashes = {str(path.relative_to(root)): sha256(path) for path in sorted(run_root.rglob("*")) if path.is_file()}
    raw_hashes = {path: digest for path, digest in hashes.items() if path.startswith(f"benchmarks/runs/{run_id}/raw/")}
    payload = {
        "run_id": run_id,
        "configuration_hash": config.configuration_hash,
        "raw_artifact_count": len(raw_paths),
        "unique_terminal_run_ids": len(inspection.artifacts_by_run_id),
        "missing_count": inspection.missing_count,
        "terminal_counts": dict(states),
        "raw_artifact_hashes": raw_hashes,
        "all_run_artifact_hashes": hashes,
        "metrics_sha256": hashes.get(f"benchmarks/runs/{run_id}/metrics/mission-010-metrics.json"),
        "execution_log_sha256": hashes.get(f"benchmarks/runs/{run_id}/execution_log.json"),
        "preservation_status": "PASS" if len(raw_paths) == 180 and inspection.missing_count == 0 and len(inspection.artifacts_by_run_id) == 180 else "FAIL",
    }
    if payload["preservation_status"] != "PASS":
        raise RuntimeError(json.dumps(payload, sort_keys=True))
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("run_id", "raw_artifact_count", "unique_terminal_run_ids", "missing_count", "terminal_counts", "metrics_sha256", "execution_log_sha256", "preservation_status")}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
