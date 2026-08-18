#!/usr/bin/env python3
"""Finalize the single-attempt Mission 029 provider failure without a retry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aegis.audit_store import _redact, _to_jsonable


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(_redact(_to_jsonable(value)), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "experiments" / "mission_029"
    failure = json.loads((evidence / "healing_failure.json").read_text(encoding="utf-8"))
    reconciled_summary = evidence / "collection_summary_reconciled.json"
    collection = json.loads((reconciled_summary if reconciled_summary.is_file() else evidence / "collection_summary.json").read_text(encoding="utf-8"))
    observation = json.loads((evidence / "observation_mutated.json").read_text(encoding="utf-8"))
    detection = json.loads((evidence / "detection_result.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence / "diagnosis.json").read_text(encoding="utf-8"))
    repair_request = json.loads((evidence / "repair_request.json").read_text(encoding="utf-8"))
    termination = {
        "termination_id": "mission029_healing_provider_failure",
        "stage": "BRIGHT_DATA_HEALING",
        "status": "FAILED_BEFORE_CANDIDATE",
        "provider_failure": failure,
        "candidate_created": False,
        "verification_invoked": False,
        "risk_governor_invoked": False,
        "commit_gate_invoked": False,
        "approval_command_present": False,
        "approval_command_executed": False,
        "production_commit_performed": False,
        "data_shipped": False,
        "retry_performed": False,
        "reason": "The single authorized Bright Data healing request was rejected before candidate creation because the provider limit was 1000 prompt characters and the bounded repair prompt measured 1187 characters.",
        "correlation_id": failure["correlation_id"],
        "evidence_chain": {
            "collector_id": collection["collector_id"],
            "observation_id": observation["observation_id"],
            "detection_id": f"detection_{observation['observation_id']}",
            "diagnosis_id": diagnosis["diagnosis_id"],
            "repair_request_id": repair_request["repair_request_id"],
            "heal_id": failure["heal_id"],
            "candidate_id": None,
            "verification_id": None,
            "risk_decision_id": None,
            "commit_decision_id": None,
        },
    }
    write_json(evidence / "pipeline_termination.json", termination)
    operations = sorted((evidence / "provider_operations").glob("operation_*.json"))
    manifest = {
        "mission": "029",
        "status": "TERMINATED_PROVIDER_FAILURE",
        "target_url": "https://news.ycombinator.com",
        "collector_id": collection["collector_id"],
        "row_count": collection["row_count"],
        "collection_mode": collection["mode"],
        "detection": {
            "detected": detection["detected"],
            "severity": detection["severity"],
            "affected_fields": detection["affected_fields"],
        },
        "diagnosis": {
            "failure_class": diagnosis["failure_class"],
            "certainty": diagnosis["certainty"],
        },
        "healing": {
            "status": failure["status"],
            "error_code": failure["error_code"],
            "latency_ms": failure["latency_ms"],
            "candidate_created": False,
        },
        "provider_operation_counts": {
            "collector_create": 1,
            "collector_run": 1,
            "healing_request": 1,
            "total": len(operations),
        },
        "approval_command_executed": False,
        "production_commit_performed": False,
        "data_shipped": False,
        "gemini_invoked": False,
        "nvidia_benchmark_invoked": False,
        "benchmark_invoked": False,
        "replay_only": True,
        "termination_ref": "pipeline_termination.json",
    }
    write_json(evidence / "demo_manifest.json", manifest)
    hashes = {
        str(path.relative_to(evidence)): digest(path)
        for path in sorted(evidence.rglob("*"))
        if path.is_file() and path.name != "artifact_hashes.json"
    }
    write_json(evidence / "artifact_hashes.json", hashes)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
