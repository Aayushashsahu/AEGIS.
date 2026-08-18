#!/usr/bin/env python3
"""Build the static, read-only evidence contract consumed by AEGIS Judge Mode.

This command never invokes Bright Data, NVIDIA, Gemini, a benchmark executor,
approval, commit, or rollback. It validates the immutable Mission 029 bundle,
summarizes the preserved Mission 028 recovery run, and materializes one
explicit TEST_DOUBLE replay by calling AEGIS's deterministic verification,
risk, and commit-gate modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from aegis.audit_store import _redact, _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.mission030_evidence import Mission029ArtifactLoader
from aegis.risk import RiskGovernor
from aegis.verification import verify_candidate
from aegis.verification_double import VerificationFixture, build_verification_fixture


ROOT = Path(__file__).resolve().parents[1]
MISSION_029_FILES = Mission029ArtifactLoader.FILES
RECOVERY_RUN_ID = "mission_028_recovery_floor_4812160675146552"
SENSITIVE_KEYS = {"authorization", "cookie", "password", "api_key", "apikey", "token", "secret"}


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _assert_redacted(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                raise ValueError(f"sensitive field present in snapshot input: {source}")
            _assert_redacted(nested, source=source)
    elif isinstance(value, list):
        for nested in value:
            _assert_redacted(nested, source=source)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_dict(stage: Any) -> dict[str, Any]:
    return {
        "id": stage.stage_id,
        "label": stage.label,
        "status": stage.status,
        "artifact": stage.evidence_file,
        "record_id": stage.record_id,
        "detail": stage.detail,
        "provenance": stage.provenance,
    }


def _build_live_lane(root: Path) -> dict[str, Any]:
    evidence_root = root / "experiments" / "mission_029"
    normalized = Mission029ArtifactLoader(evidence_root).load()
    raw = {key: _read_object(evidence_root / filename) for key, filename in MISSION_029_FILES.items()}
    for name, payload in raw.items():
        _assert_redacted(payload, source=f"mission_029/{name}")
    mission030 = _read_object(root / "experiments" / "mission_030" / "live_heal_result.json")
    _assert_redacted(mission030, source="mission_030/live_heal_result.json")
    prompt = mission030.get("prompt", {})
    handle = mission030.get("heal_handle", {})
    if not isinstance(prompt, Mapping) or not isinstance(handle, Mapping):
        raise ValueError("Mission 030 terminal heal evidence is malformed")
    if mission030.get("status") != "HEAL_FAILED_BEFORE_CANDIDATE" or mission030.get("candidate_created") is not False:
        raise ValueError("Mission 030 evidence is not the expected terminal no-candidate state")
    if prompt.get("prompt_length") != 676 or prompt.get("limit") != 1000 or prompt.get("within_limit") is not True:
        raise ValueError("Mission 030 prompt-compatibility evidence did not validate")
    source_hashes = {
        f"mission_029/{filename}": _sha256(evidence_root / filename)
        for filename in MISSION_029_FILES.values()
    }
    source_hashes["mission_030/live_heal_result.json"] = _sha256(root / "experiments" / "mission_030" / "live_heal_result.json")
    return {
        "mode": "LIVE_HISTORICAL_EVIDENCE",
        "mission": normalized.mission,
        "terminal_status": mission030["status"],
        "collector": {
            "id": normalized.collector_id,
            "target_url": normalized.target_url,
            "row_count": normalized.row_count,
            "collection_mode": normalized.collection_mode,
            "latency_ms": normalized.collection_latency_ms,
            "provider_operation_ids": dict(normalized.provider_operation_ids),
        },
        "corruption": {
            "provenance": "DEMO_CONTROLLED",
            "mutation_id": raw["mutation"].get("mutation_id"),
            "severity": raw["detection"].get("severity"),
            "field": raw["mutation"].get("field"),
            "expected_value": raw["mutation"].get("expected_value_from_preserved_live_output"),
            "observed_value": raw["mutation"].get("observed_corrupted_value"),
            "external_website_modified": raw["mutation"].get("external_website_modified"),
            "collector_modified": raw["mutation"].get("collector_modified"),
        },
        "stages": [_stage_dict(stage) for stage in normalized.stages],
        "provider_heal": {
            "provenance": "REAL_PROVIDER_EVIDENCE",
            "repair_request_id": mission030.get("repair_request_id"),
            "heal_id": handle.get("heal_id"),
            "status": handle.get("status"),
            "provider_status": handle.get("provider_status"),
            "error_code": handle.get("error_code"),
            "latency_ms": handle.get("latency_ms"),
            "transport_prompt": {
                "policy_version": prompt.get("policy_version"),
                "length": prompt.get("prompt_length"),
                "limit": prompt.get("limit"),
                "hash": prompt.get("prompt_hash"),
                "within_limit": prompt.get("within_limit"),
            },
            "candidate_created": False,
            "verification_invoked": False,
            "risk_governor_invoked": False,
            "production_commit_performed": False,
            "data_shipped": False,
        },
        "artifact_hashes": source_hashes,
    }


def _build_controlled_replay() -> dict[str, Any]:
    context = build_verification_fixture(VerificationFixture.SILENT_CORRUPTION)
    verification = verify_candidate(context)
    risk = RiskGovernor().decide(verification, context.candidate, correlation_id=context.correlation_id)
    commit = CommitGate().evaluate(
        context.candidate,
        verification,
        risk,
        context.contract,
        known_good_version=None,
        authorization=None,
        correlation_id=context.correlation_id,
        quarantine_record=None,
    )
    eligibility = OutputEligibilityBoundary.evaluate(commit)
    candidate_row = dict(context.candidate_output[0])
    expected_price = context.semantic_expectations.get("price")
    if candidate_row.get("price") == expected_price:
        raise ValueError("silent-corruption replay requires a visibly incorrect but valid-looking price")
    return {
        "mode": "TEST_DOUBLE_CONTROLLED_REPLAY",
        "fixture": VerificationFixture.SILENT_CORRUPTION.value,
        "disclaimer": "This is a deterministic TEST_DOUBLE verification fixture. It is not a Bright Data candidate and was not produced by a live provider heal.",
        "candidate": {
            "id": "replay_candidate_mission031_silent_corruption",
            "provenance": context.candidate.provenance.value,
            "provider_status": context.candidate.provider_status,
            "verification_status_before_review": context.candidate.verification_status.value,
            "row": candidate_row,
        },
        "ai_proposal": dict(context.model_opinion),
        "expected_value": {"field": "price", "value": expected_price},
        "observed_value": {"field": "price", "value": candidate_row.get("price")},
        "verification": {
            "id": "verification_mission031_silent_corruption",
            "overall_status": verification.overall_status.value,
            "eligible_for_future_commit": verification.eligible_for_future_commit,
            "checks": [
                {
                    "channel": check.channel.value,
                    "status": check.status.value,
                    "category": check.category,
                    "message": check.message,
                    "affected_fields": list(check.affected_fields),
                    "critical": check.critical,
                    "evidence_refs": list(check.evidence_refs),
                }
                for check in verification.checks
            ],
        },
        "risk": {
            "decision": risk.decision.value,
            "reason_code": risk.reason_code,
            "provenance": "DETERMINISTIC_TEST_DOUBLE",
        },
        "commit": {
            "eligibility": commit.eligibility.value,
            "reason_code": commit.reason_code,
            "output_eligible": eligibility.eligible,
            "data_shipped": False,
        },
    }


def _build_benchmark_summary(root: Path) -> dict[str, Any]:
    run_root = root / "benchmarks" / "runs" / RECOVERY_RUN_ID
    execution = _read_object(run_root / "execution_log.json")
    report = _read_object(run_root / "reports" / "mission-022-metric-boundary-compatibility.json")
    config = _read_object(run_root / "frozen_config.json")
    if execution.get("benchmark_run_id") != RECOVERY_RUN_ID or execution.get("status") != "COMPLETED":
        raise ValueError("Mission 028 recovery execution log does not match expected terminal identity")
    records = [
        record["metric_input"]
        for record in report.get("records", [])
        if isinstance(record, Mapping) and isinstance(record.get("metric_input"), Mapping)
    ]
    aegis_records = [record for record in records if record.get("participant_id") == "AEGIS"]
    anomalous_records = [record for record in aegis_records if record.get("mutation_id") not in {"M001"}]
    l5_records = [record for record in aegis_records if record.get("mutation_id") in {"M005", "M006"}]
    detected = sum(record.get("detected") is True for record in anomalous_records)
    l5_detected = sum(record.get("detected") is True for record in l5_records)
    l5_shipped = sum(record.get("output_eligible") is True for record in l5_records)
    config_text = json.dumps(config, sort_keys=True)
    if "openai/gpt-oss-20b" not in config_text or "NVIDIA_PROVIDER_LIMIT_UNKNOWN" not in config_text:
        raise ValueError("frozen NVIDIA configuration no longer contains required provenance markers")
    return {
        "mode": "REPRODUCIBLE_BENCHMARK_EVIDENCE",
        "run_id": RECOVERY_RUN_ID,
        "configuration_hash": execution.get("configuration_hash"),
        "protocol": {
            "participants": ["BASELINE_A", "BASELINE_B / NVIDIA NIM", "AEGIS / TEST_DOUBLE"],
            "mutation_classes": list(config.get("mutation_class_ids", [])),
            "trials_per_mutation": 10,
            "seed": 12345,
            "nvidia_model": "openai/gpt-oss-20b",
            "nvidia_throttle": "6 RPM benchmark-side; 10 second minimum interval; concurrency 1",
            "nvidia_provider_limit": "UNKNOWN",
        },
        "execution": {
            "planned_opportunities": execution.get("planned_runs"),
            "completed_opportunities": execution.get("completed_runs"),
            "failed_opportunities": execution.get("failed_runs"),
            "provider_operations": execution.get("provider_operations_executed"),
            "healing_operations": execution.get("healing_operations_executed"),
            "metric_results_generated": execution.get("metric_results_generated"),
        },
        "controlled_aegis_metrics": {
            "provenance": "TEST_DOUBLE_CONTROLLED_HARNESS",
            "metric_input_count": len(aegis_records),
            "detection_rate": {"numerator": detected, "denominator": len(anomalous_records)},
            "l5_detection_rate": {"numerator": l5_detected, "denominator": len(l5_records)},
            "l5_bad_data_shipped": {"numerator": l5_shipped, "denominator": len(l5_records)},
            "caveat": "These AEGIS metrics measure the controlled TEST_DOUBLE harness only. They are not live Bright Data reliability metrics and Baseline A/B are not included in their denominator.",
        },
    }


def build_snapshot(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    snapshot = {
        "schema_version": "mission-031-judge-mode-snapshot-v1",
        "read_only": True,
        "provider_operations_executed_by_builder": 0,
        "live_lane": _build_live_lane(root),
        "controlled_replay": _build_controlled_replay(),
        "benchmark": _build_benchmark_summary(root),
        "safety": {
            "approval_operations": 0,
            "production_commits": 0,
            "rollbacks": 0,
            "benchmark_runs_executed_by_builder": 0,
            "gemini_invocations": 0,
            "nvidia_invocations": 0,
            "claim": "AI proposes. Evidence decides.",
        },
    }
    return _redact(_to_jsonable(snapshot))


def write_snapshot(root: Path = ROOT, output: Path | None = None) -> Path:
    destination = output or root / "experiments" / "mission_031" / "judge_mode_snapshot.json"
    snapshot = build_snapshot(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the provider-free AEGIS Judge Mode evidence snapshot")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = write_snapshot(args.root.resolve(), args.output.resolve() if args.output else None)
    print(json.dumps({"status": "SNAPSHOT_BUILT", "output": str(output), "provider_operations_executed": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
