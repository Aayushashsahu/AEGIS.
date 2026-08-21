"""Mission 048: one owner-authorized, evidence-preserving collector rerun."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.bounded_rerun_preflight import BoundedRerunPreflightEvidence, evaluate_bounded_rerun_preflight
from aegis.one_shot_rerun import DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS, DEFAULT_RERUN_WAIT_SECONDS, OneShotRerunResult, rerun_collector_once
from aegis.operation_correlation import append_correlation_record, build_operation_correlation


ROOT = Path(__file__).resolve().parents[1]
MISSION_DIR = ROOT / "experiments" / "mission_048_evidence_preserving_rerun"
AUTHORIZATION_PATH = MISSION_DIR / "authorization.json"
RAW_RESPONSE_PATH = MISSION_DIR / "raw_response.bin"
CORRELATION_DIR = MISSION_DIR / "correlation_records"
MISSION048A_SUMMARY_PATH = ROOT / "experiments" / "mission_048a_current_operation_inspection" / "summary.json"
TARGET_URL = "https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target"
CORRELATION_ID = "mission048-rerun-c_mt09pib13nxqz1coi"
OPERATION_ID = "mission048-rerun-20260821T025232Z"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2) + "\n")


def _historical_evidence_intact() -> bool:
    protected = (
        ROOT / "benchmarks" / "runs" / "mission_028_recovery_floor_4812160675146552" / "execution_log.json",
        ROOT / "experiments" / "mission_029" / "demo_manifest.json",
        ROOT / "experiments" / "mission_030" / "live_heal_result.json",
        ROOT / "experiments" / "mission_033_live_bright_data_success" / "approval.json",
        ROOT / "experiments" / "mission_041a_post_approval_progress" / "progress_check.json",
        ROOT / "experiments" / "mission_041_post_heal_rerun" / "post_heal_output.json",
        ROOT / "experiments" / "mission_044_final_template_snapshot" / "summary.json",
        ROOT / "experiments" / "mission_046_dashboard_forensics" / "summary.json",
    )
    return all(path.is_file() for path in protected)


def _operation_evidence() -> tuple[str, bool]:
    """Read the immutable Mission 048A conclusion without contacting Bright Data."""

    summary = _read_json(MISSION048A_SUMMARY_PATH)
    if summary.get("collector_id") != MISSION034_COLLECTOR_ID:
        return "UNKNOWN", True
    if summary.get("current_operation_lookup") != "NOT_DOCUMENTED":
        return "UNKNOWN", True
    return "UNKNOWN", summary.get("conflicting_operation") == "YES"


def preflight() -> dict[str, Any]:
    """Check only local configuration and immutable evidence; never contact a provider."""

    authorization = _read_json(AUTHORIZATION_PATH)
    budget = authorization.get("operation_budget")
    execution_contract = authorization.get("execution_contract")
    operation_state, known_conflict = _operation_evidence()
    policy = evaluate_bounded_rerun_preflight(BoundedRerunPreflightEvidence(
        collector_id=authorization.get("collector_id", "") if isinstance(authorization.get("collector_id"), str) else "",
        current_operation_state=operation_state,
        known_conflict=known_conflict,
        rerun_budget=budget.get("documented_collector_rerun", -1) if isinstance(budget, dict) else -1,
        retry_budget=budget.get("retries", -1) if isinstance(budget, dict) else -1,
        approval_budget=budget.get("approval", -1) if isinstance(budget, dict) else -1,
        heal_budget=budget.get("heal", -1) if isinstance(budget, dict) else -1,
        commit_budget=budget.get("commit", -1) if isinstance(budget, dict) else -1,
        rollback_budget=budget.get("rollback", -1) if isinstance(budget, dict) else -1,
        historical_evidence_intact=_historical_evidence_intact(),
        response_capture_armed=callable(getattr(OneShotRerunResult, "preserve_raw_response", None)),
        correlation_id_generated=bool(CORRELATION_ID),
    ))
    checks = {
        "exact_collector": authorization.get("collector_id") == MISSION034_COLLECTOR_ID == "c_mt09pib13nxqz1coi",
        "authenticated_transport_configured": bool(os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "").strip()),
        "one_rerun_budget": isinstance(budget, dict) and budget.get("documented_collector_rerun") == 1,
        "zero_retry_budget": isinstance(budget, dict) and budget.get("retries") == 0,
        "bounded_policy_allows_rerun": policy.allows_single_bounded_rerun,
        "historical_evidence_paths_present": policy.checks["historical_evidence_intact"],
        "response_capture_capable": policy.checks["response_capture_armed"],
        "fresh_raw_response_path": not RAW_RESPONSE_PATH.exists(),
        "fresh_correlation_directory": not CORRELATION_DIR.exists(),
        "controlled_raw_response_path": isinstance(execution_contract, dict) and execution_contract.get("raw_response_path") == str(RAW_RESPONSE_PATH.relative_to(ROOT)),
        "controlled_correlation_path": isinstance(execution_contract, dict) and execution_contract.get("correlation_record_dir") == str(CORRELATION_DIR.relative_to(ROOT)),
        "authorized_operation_id": isinstance(execution_contract, dict) and execution_contract.get("aegis_operation_id") == OPERATION_ID,
    }
    return {
        "schema_version": "mission-048-preflight-v1",
        "collector_id": MISSION034_COLLECTOR_ID,
        "target_url": TARGET_URL,
        "correlation_id": CORRELATION_ID,
        "operation_id": OPERATION_ID,
        "current_operation_state": policy.current_operation_state,
        "known_conflict": policy.known_conflict,
        "conflict_absence_proven": policy.conflict_absence_proven,
        "preflight_decision": policy.preflight_decision,
        "preflight_reason": policy.preflight_reason,
        "policy_checks": policy.checks,
        "checks": checks,
        "all_pass": all(checks.values()),
        "provider_operations_attempted": 0,
        "retries": 0,
        "key_exposed": False,
    }


def _request_metadata(requested_at_utc: str) -> dict[str, Any]:
    return {
        "schema_version": "mission-048-run-request-v1",
        "requested_at_utc": requested_at_utc,
        "operation": "synchronous_collector_rerun",
        "collector_id": MISSION034_COLLECTOR_ID,
        "target_url": TARGET_URL,
        "correlation_id": CORRELATION_ID,
        "operation_id": OPERATION_ID,
        "retry_budget": 0,
        "http_timeout_seconds": DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS,
        "wait_seconds": DEFAULT_RERUN_WAIT_SECONDS,
        "key_exposed": False,
    }


def _persist_result(result: OneShotRerunResult, requested_at_utc: str) -> dict[str, Any]:
    raw_metadata: dict[str, Any] = result.to_safe_metadata()
    raw_metadata.update({"schema_version": "mission-048-raw-response-metadata-v1", "requested_at_utc": requested_at_utc})
    raw_evidence: dict[str, Any] | None = None
    if result.raw_response_bytes is not None:
        raw_evidence = result.preserve_raw_response(RAW_RESPONSE_PATH)
        raw_metadata["raw_response_evidence"] = raw_evidence
    _write_new_json(MISSION_DIR / "raw_response_metadata.json", raw_metadata)
    if result.raw_response_sha256 is not None:
        _write_new_json(MISSION_DIR / "raw_response_hash.json", {
            "schema_version": "mission-048-raw-response-hash-v1",
            "algorithm": "sha256",
            "sha256": result.raw_response_sha256,
            "bytes": len(result.raw_response_bytes) if result.raw_response_bytes is not None else None,
        })
    correlation = build_operation_correlation(
        aegis_operation_id=OPERATION_ID,
        collector_id=MISSION034_COLLECTOR_ID,
        target_url=TARGET_URL,
        started_at_utc=requested_at_utc,
        provider_run_id=result.response_id,
        template_version=None,
        operation_type=result.operation,
        correlation_id=CORRELATION_ID,
    )
    correlation_path = append_correlation_record(CORRELATION_DIR, correlation)
    _write_new_json(MISSION_DIR / "correlation.json", {
        "schema_version": "mission-048-correlation-reference-v1",
        "record_path": str(correlation_path.relative_to(ROOT)),
        "record": correlation.to_evidence_dict(),
    })
    return {"raw_evidence": raw_evidence, "correlation_path": str(correlation_path.relative_to(ROOT))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the one owner-authorized rerun after local preflight succeeds.")
    args = parser.parse_args()
    report = preflight()
    preflight_path = MISSION_DIR / "preflight.json"
    if preflight_path.exists():
        preflight_path = MISSION_DIR / "preflight_revalidation.json"
    if not report["all_pass"]:
        report["rerun"] = "NOT_ATTEMPTED"
        _write_new_json(preflight_path, report)
        print(json.dumps(report, sort_keys=True))
        return 2
    if not args.execute:
        report["rerun"] = "NOT_ATTEMPTED"
        _write_new_json(preflight_path, report)
        print(json.dumps(report, sort_keys=True))
        return 0
    report["rerun"] = "PENDING_AUTHORIZED_EXECUTION"
    _write_new_json(preflight_path, report)
    requested_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_new_json(MISSION_DIR / "run_request.json", _request_metadata(requested_at_utc))
    result = rerun_collector_once(
        os.environ[BRIGHT_DATA_DCA_TOKEN_ENV],
        collector_id=MISSION034_COLLECTOR_ID,
        target_url=TARGET_URL,
        correlation_id=CORRELATION_ID,
        wait_seconds=DEFAULT_RERUN_WAIT_SECONDS,
        http_timeout_seconds=DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS,
    )
    persisted = _persist_result(result, requested_at_utc)
    report.update({
        "rerun": "SUCCESS" if result.success else "FAILED",
        "provider_operations_attempted": 1,
        "rerun_result": result.to_evidence_dict(),
        "persisted": persisted,
    })
    print(json.dumps(report, sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
