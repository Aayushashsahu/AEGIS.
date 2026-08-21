"""Mission 048C: one explicit rerun with raw-response-first local evidence."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.bounded_rerun_preflight import BoundedRerunPreflightEvidence, evaluate_bounded_rerun_preflight
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.healing import RepairCandidate
from aegis.models import ProviderProvenance
from aegis.one_shot_rerun import DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS, DEFAULT_RERUN_WAIT_SECONDS, OneShotRerunResult, rerun_collector_once
from aegis.operation_correlation import append_correlation_record, build_operation_correlation
from aegis.output_lineage import analyze_output_lineage
from aegis.risk import RiskGovernor
from aegis.verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate
from scripts.mission033_lifecycle import FIELDS, _observation_from_run, mission033_contract
from scripts.mission033_verify_candidate import _canonical_row


ROOT = Path(__file__).resolve().parents[1]
MISSION_DIR = ROOT / "experiments" / "mission_048c_evidence_preserving_rerun"
AUTHORIZATION_PATH = MISSION_DIR / "authorization.json"
RAW_RESPONSE_PATH = MISSION_DIR / "raw_response.bin"
CORRELATION_DIR = MISSION_DIR / "correlation_records"
MISSION033_DIR = ROOT / "experiments" / "mission_033_live_bright_data_success"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _historical_evidence_intact() -> bool:
    protected = (
        ROOT / "benchmarks" / "runs" / "mission_028_recovery_floor_4812160675146552" / "execution_log.json",
        ROOT / "experiments" / "mission_029" / "demo_manifest.json",
        ROOT / "experiments" / "mission_030" / "live_heal_result.json",
        ROOT / "experiments" / "mission_033_live_bright_data_success" / "approval.json",
        ROOT / "experiments" / "continuation_forensics_2026-08-20" / "provider_timeline.md",
        ROOT / "experiments" / "mission_041a_post_approval_progress" / "progress_check.json",
        ROOT / "experiments" / "mission_041_post_heal_rerun" / "post_heal_output.json",
        ROOT / "experiments" / "mission_044_final_template_snapshot" / "summary.json",
        ROOT / "experiments" / "mission_046_dashboard_forensics" / "summary.json",
        ROOT / "experiments" / "mission_048_evidence_preserving_rerun" / "summary.json",
        ROOT / "experiments" / "mission_048a_current_operation_inspection" / "summary.json",
        ROOT / "experiments" / "mission_048b_preflight_policy_amendment" / "summary.json",
    )
    return all(path.is_file() for path in protected)


def _field_state(row: Mapping[str, Any], field: str) -> str:
    value: Any = row
    for segment in field.split("."):
        if not isinstance(value, Mapping) or segment not in value:
            return "MISSING"
        value = value[segment]
    if value is None:
        return "NULL"
    if isinstance(value, str) and not value.strip():
        return "EMPTY"
    return "PRESENT"


def _next_preflight_path() -> Path:
    primary = MISSION_DIR / "preflight.json"
    if not primary.exists():
        return primary
    index = 1
    while True:
        suffix = "preflight_revalidation.json" if index == 1 else f"preflight_revalidation_{index}.json"
        candidate = MISSION_DIR / suffix
        if not candidate.exists():
            return candidate
        index += 1


def preflight() -> dict[str, Any]:
    """Provider-free validation only; this function never contacts Bright Data."""

    authorization = _read_json(AUTHORIZATION_PATH)
    budget = authorization.get("operation_budget")
    policy_input = authorization.get("current_operation_policy")
    correlation = authorization.get("correlation")
    contract = authorization.get("evidence_contract")
    policy = evaluate_bounded_rerun_preflight(BoundedRerunPreflightEvidence(
        collector_id=authorization.get("collector_id", "") if isinstance(authorization.get("collector_id"), str) else "",
        current_operation_state=policy_input.get("current_operation_state", "") if isinstance(policy_input, dict) else "",
        known_conflict=isinstance(policy_input, dict) and policy_input.get("known_conflict") == "YES",
        rerun_budget=budget.get("documented_collector_rerun", -1) if isinstance(budget, dict) else -1,
        retry_budget=budget.get("retries", -1) if isinstance(budget, dict) else -1,
        approval_budget=budget.get("approval", -1) if isinstance(budget, dict) else -1,
        heal_budget=budget.get("heal", -1) if isinstance(budget, dict) else -1,
        commit_budget=budget.get("commit", -1) if isinstance(budget, dict) else -1,
        rollback_budget=budget.get("rollback", -1) if isinstance(budget, dict) else -1,
        historical_evidence_intact=_historical_evidence_intact(),
        response_capture_armed=callable(getattr(OneShotRerunResult, "preserve_raw_response", None)),
        correlation_id_generated=isinstance(correlation, dict) and isinstance(correlation.get("aegis_correlation_id"), str) and correlation["aegis_correlation_id"].startswith("mission048c-"),
    ))
    checks = {
        "amended_policy_allows": policy.allows_single_bounded_rerun,
        "authenticated_transport_configured": bool(os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "").strip()),
        "append_only_preflight_path_available": True,
        "fresh_run_request_path": not (MISSION_DIR / "run_request.json").exists(),
        "fresh_raw_response_path": not RAW_RESPONSE_PATH.exists(),
        "fresh_correlation_directory": not CORRELATION_DIR.exists(),
        "controlled_raw_path": isinstance(contract, dict) and contract.get("raw_response_path") == str(RAW_RESPONSE_PATH.relative_to(ROOT)),
        "controlled_correlation_path": isinstance(contract, dict) and contract.get("correlation_record_dir") == str(CORRELATION_DIR.relative_to(ROOT)),
        "stop_after_provider_operation": isinstance(contract, dict) and contract.get("stop_after_provider_operation") is True,
    }
    return {
        "schema_version": "mission-048c-preflight-v1",
        "collector_id": MISSION034_COLLECTOR_ID,
        "target_url": authorization.get("target_url"),
        "correlation_id": correlation.get("aegis_correlation_id") if isinstance(correlation, dict) else None,
        "operation_id": correlation.get("aegis_operation_id") if isinstance(correlation, dict) else None,
        "current_operation_state": policy.current_operation_state,
        "known_conflict": policy.known_conflict,
        "conflict_absence_proven": policy.conflict_absence_proven,
        "preflight_policy_version": policy_input.get("preflight_policy_version") if isinstance(policy_input, dict) else None,
        "preflight_decision": policy.preflight_decision,
        "preflight_reason": policy.preflight_reason,
        "policy_checks": policy.checks,
        "checks": checks,
        "all_pass": policy.allows_single_bounded_rerun and all(checks.values()),
        "provider_operations_attempted": 0,
        "retries": 0,
        "key_exposed": False,
    }


def _persist_raw_first(result: OneShotRerunResult) -> dict[str, Any] | None:
    if result.raw_response_bytes is None:
        return None
    raw_evidence = result.preserve_raw_response(RAW_RESPONSE_PATH)
    _write_new_json(MISSION_DIR / "raw_response_hash.json", {
        "schema_version": "mission-048c-raw-response-hash-v1",
        "algorithm": "sha256",
        "sha256": result.raw_response_sha256,
        "bytes": len(result.raw_response_bytes),
    })
    return raw_evidence


def _verify(rows: tuple[dict[str, Any], ...], result: OneShotRerunResult, correlation_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    target_contract = _read_json(MISSION033_DIR / "target_contract.json")
    initial_run = _read_json(MISSION033_DIR / "initial_run.json")
    baseline = _observation_from_run(initial_run, target_url=str(target_contract["target_url"]), target_version="v1")
    normalized_history = replace(baseline, output=tuple(_canonical_row(row) for row in baseline.output), schema=FIELDS, row_count=len(baseline.output))
    expected = {"title": "AEGIS Verification Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"}
    candidate = RepairCandidate(
        candidate_id="candidate_m048c_real_rerun",
        repair_request_id="repair_m033_compatible",
        collector_reference=MISSION034_COLLECTOR_ID,
        provider_operation_reference=result.response_id or correlation_id,
        provider_status="COMPLETED",
        preview_result=list(rows),
        diff_summary="Actual Mission 048C post-approval rerun output",
        approval_command=None,
        raw_evidence_ref="evidence://mission-048c/raw-response.bin",
        provenance=ProviderProvenance.BRIGHT_DATA,
        latency_ms=result.elapsed_ms,
    )
    independent = IndependentEvidence(
        evidence_id="independent_m033_owned_target_contract_v2",
        source="AEGIS-owned public target contract and direct v2 target snapshot",
        rows=(expected,),
        provenance=VerificationProvenance.DETERMINISTIC,
        source_group="AEGIS_OWNED_TARGET_DIRECT_FETCH",
        evidence_refs=("evidence://mission-033/target-contract.json", "evidence://mission-033/independent-target-snapshot.html"),
        correlation_id=correlation_id,
    )
    verification = verify_candidate(VerificationContext(
        candidate=candidate,
        contract=mission033_contract(),
        candidate_output=tuple(_canonical_row(row) for row in rows),
        history=(normalized_history,),
        independent_evidence=independent,
        correlation_id=correlation_id,
        evidence_refs=("evidence://mission-048c/raw-response.bin", "evidence://mission-033/target-contract.json"),
        semantic_expectations=expected,
        history_source_group="BRIGHT_DATA_LIVE_COLLECTION",
    ))
    risk = RiskGovernor().decide(verification, candidate, correlation_id=correlation_id)
    commit = CommitGate().evaluate(candidate, verification, risk, mission033_contract(), known_good_version=None, authorization=None, correlation_id=correlation_id)
    eligibility = OutputEligibilityBoundary.evaluate(commit)
    from aegis.audit_store import _to_jsonable
    return _to_jsonable(verification), _to_jsonable(risk), {"commit": _to_jsonable(commit), "eligibility": _to_jsonable(eligibility)}


def _analyze(result: OneShotRerunResult, correlation_id: str) -> dict[str, Any]:
    rows = result.rows
    normalized_rows = tuple(_canonical_row(row) for row in rows)
    lineage = analyze_output_lineage(rows, normalized_rows, ("title", "price", "availability"))
    first_row: Mapping[str, Any] = rows[0] if rows else {}
    raw_states = {field: _field_state(first_row, field) for field in ("input.url", "title", "price", "availability")}
    first_loss = "UNKNOWN"
    if lineage.required_fields_dropped_by_normalization:
        first_loss = "AEGIS_NORMALIZATION"
    elif lineage.required_fields_missing_from_provider or lineage.required_fields_missing_in_any_provider_row:
        first_loss = "PROVIDER_RESPONSE"
    return {
        "schema_version": "mission-048c-normalized-analysis-v1",
        "decoded_rows": list(rows),
        "normalized_rows": list(normalized_rows),
        "lineage": lineage.to_evidence_dict(),
        "first_field_loss_point": first_loss,
        "raw_field_states": raw_states,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the one owner-authorized Mission 048C rerun after preflight.")
    args = parser.parse_args()
    report = preflight()
    preflight_path = _next_preflight_path()
    _write_new_json(preflight_path, {**report, "rerun": "PENDING_AUTHORIZED_EXECUTION" if report["all_pass"] else "NOT_ATTEMPTED"})
    if not report["all_pass"] or not args.execute:
        print(json.dumps(report, sort_keys=True))
        return 2 if not report["all_pass"] else 0
    requested_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_new_json(MISSION_DIR / "run_request.json", {
        "schema_version": "mission-048c-run-request-v1",
        "requested_at_utc": requested_at_utc,
        "collector_id": report["collector_id"],
        "target_url": report["target_url"],
        "correlation_id": report["correlation_id"],
        "operation_id": report["operation_id"],
        "authorized_provider_operations": 1,
        "retry_budget": 0,
        "key_exposed": False,
    })
    result = rerun_collector_once(
        os.environ[BRIGHT_DATA_DCA_TOKEN_ENV], collector_id=MISSION034_COLLECTOR_ID,
        target_url=str(report["target_url"]), correlation_id=str(report["correlation_id"]),
        wait_seconds=DEFAULT_RERUN_WAIT_SECONDS, http_timeout_seconds=DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS,
    )
    raw_evidence = _persist_raw_first(result)
    safe_metadata = result.to_safe_metadata()
    safe_metadata.update({"schema_version": "mission-048c-raw-response-metadata-v1", "requested_at_utc": requested_at_utc, "raw_response_evidence": raw_evidence})
    _write_new_json(MISSION_DIR / "raw_response_metadata.json", safe_metadata)
    correlation = build_operation_correlation(
        aegis_operation_id=str(report["operation_id"]), collector_id=MISSION034_COLLECTOR_ID,
        target_url=str(report["target_url"]), started_at_utc=requested_at_utc,
        provider_run_id=result.response_id, template_version=None, operation_type=result.operation,
        correlation_id=str(report["correlation_id"]),
    )
    correlation_path = append_correlation_record(CORRELATION_DIR, correlation)
    _write_new_json(MISSION_DIR / "correlation.json", {"schema_version": "mission-048c-correlation-v1", "record_path": str(correlation_path.relative_to(ROOT)), "record": correlation.to_evidence_dict()})
    if result.success:
        analysis = _analyze(result, str(report["correlation_id"]))
        _write_new_json(MISSION_DIR / "normalized_analysis.json", analysis)
        _write_new_json(MISSION_DIR / "comparison.json", {"schema_version": "mission-048c-comparison-v1", "raw_field_states": analysis["raw_field_states"], "lineage": analysis["lineage"], "first_field_loss_point": analysis["first_field_loss_point"]})
        verification, risk, commit = _verify(result.rows, result, str(report["correlation_id"]))
        _write_new_json(MISSION_DIR / "verification.json", verification)
        _write_new_json(MISSION_DIR / "risk_decision.json", risk)
        _write_new_json(MISSION_DIR / "commit_decision.json", commit)
    print(json.dumps({"attempted": result.attempted, "success": result.success, "http_status": result.http_status, "raw_response_preserved": raw_evidence is not None}, sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
