#!/usr/bin/env python3
"""Verify the preserved Mission 033 provider preview without approving it.

This projector consumes only recorded evidence. It never calls Bright Data and
cannot invoke the approval command returned as untrusted provider data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import _redact, _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.healing import RepairCandidate
from aegis.models import ProviderProvenance
from aegis.risk import RiskGovernor
from aegis.verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate
from scripts.mission033_lifecycle import FIELDS, _observation_from_run, _read_json, _write_json, mission033_contract


MISSION_DIR_NAME = "mission_033_live_bright_data_success"


def _canonical_row(row: Mapping[str, Any]) -> dict[str, Any]:
    price = row.get("price")
    normalized_price = (
        {key: price[key] for key in ("currency", "value") if key in price}
        if isinstance(price, Mapping)
        else price
    )
    return {"title": row.get("title"), "price": normalized_price, "availability": row.get("availability")}


def project_candidate_verification(evidence_root: Path) -> dict[str, Any]:
    """Record canonical verification, risk, and blocked-approval decisions."""

    heal_envelope = _read_json(evidence_root / "provider_operations" / "operation_001_heal.json")
    heal_payload = heal_envelope.get("stdout")
    if not isinstance(heal_payload, Mapping) or heal_payload.get("status") != "awaiting_approval":
        raise RuntimeError("Mission 033 requires a preserved real awaiting_approval provider candidate.")
    preview = heal_payload.get("preview_result")
    if not isinstance(preview, list) or not all(isinstance(row, Mapping) for row in preview):
        raise RuntimeError("Mission 033 provider candidate is missing a structured preview_result.")
    repair_request = _read_json(evidence_root / "repair_request.json")
    target_contract = _read_json(evidence_root / "target_contract.json")
    target_url = str(target_contract["target_url"])
    candidate_id = f"candidate_m033_{hashlib.sha256((str(heal_envelope['operation_id']) + str(heal_envelope['command_sha256'])).encode('utf-8')).hexdigest()[:16]}"
    candidate = RepairCandidate(
        candidate_id=candidate_id,
        repair_request_id=str(repair_request["repair_request_id"]),
        collector_reference=str(heal_envelope["collector_id"]),
        provider_operation_reference=str(heal_envelope["operation_id"]),
        provider_status=str(heal_payload["status"]),
        preview_result=preview,
        diff_summary=str(heal_payload.get("diff_summary", "")),
        approval_command=str(heal_payload.get("next_step", "")) or None,
        raw_evidence_ref="evidence://mission-033/provider-operations/operation_001_heal.json",
        provenance=ProviderProvenance.BRIGHT_DATA,
        latency_ms=int(heal_envelope["elapsed_ms"]),
    )
    initial_run = _read_json(evidence_root / "initial_run.json")
    baseline = _observation_from_run(initial_run, target_url=target_url, target_version="v1")
    normalized_history = replace(baseline, output=tuple(_canonical_row(row) for row in baseline.output), schema=FIELDS, row_count=len(baseline.output))
    candidate_rows = tuple(_canonical_row(row) for row in preview)
    expected = {
        "title": "AEGIS Verification Widget",
        "price": {"currency": "USD", "value": 599},
        "availability": "Available",
    }
    independent_evidence = IndependentEvidence(
        evidence_id="independent_m033_owned_target_contract_v2",
        source="AEGIS-owned public target contract and direct v2 target snapshot",
        rows=(expected,),
        provenance=VerificationProvenance.DETERMINISTIC,
        source_group="AEGIS_OWNED_TARGET_DIRECT_FETCH",
        evidence_refs=(
            "evidence://mission-033/target-contract.json",
            "evidence://mission-033/independent-target-snapshot.html",
        ),
        correlation_id=f"mission033-owned-target-{heal_envelope['operation_id']}",
    )
    verification = verify_candidate(VerificationContext(
        candidate=candidate,
        contract=mission033_contract(),
        candidate_output=candidate_rows,
        history=(normalized_history,),
        independent_evidence=independent_evidence,
        correlation_id=f"mission033-{heal_envelope['operation_id']}",
        evidence_refs=(
            "evidence://mission-033/initial-run",
            "evidence://mission-033/post-drift-run",
            "evidence://mission-033/provider-candidate",
        ),
        semantic_expectations=expected,
        history_source_group="BRIGHT_DATA_LIVE_COLLECTION",
    ))
    risk = RiskGovernor().decide(verification, candidate, correlation_id=verification.correlation_id)
    commit = CommitGate().evaluate(
        candidate,
        verification,
        risk,
        mission033_contract(),
        known_good_version=None,
        authorization=None,
        correlation_id=verification.correlation_id,
    )
    output = OutputEligibilityBoundary.evaluate(commit)
    candidate_record = {
        "schema_version": "mission-033-real-provider-candidate-v1",
        "provenance": "REAL_PROVIDER",
        "candidate_id": candidate.candidate_id,
        "collector_id": candidate.collector_reference,
        "provider_status": candidate.provider_status,
        "candidate_state": candidate.verification_status.value,
        "preview_result": candidate.preview_result,
        "diff_summary": candidate.diff_summary,
        "provider_approval_command_present": bool(candidate.approval_command),
        "provider_approval_executed": False,
        "raw_evidence_ref": candidate.raw_evidence_ref,
        "latency_ms": candidate.latency_ms,
    }
    approval = {
        "schema_version": "mission-033-provider-approval-boundary-v1",
        "status": "NOT_AUTHORIZED_NOT_EXECUTED",
        "collector_id": candidate.collector_reference,
        "candidate_id": candidate.candidate_id,
        "provider_status": candidate.provider_status,
        "provider_approval_command_returned": bool(candidate.approval_command),
        "provider_approval_executed": False,
        "reason": "Mission 033 authorizes exactly one heal request but no provider approval, activation, or production commit.",
    }
    post_heal = {
        "schema_version": "mission-033-post-heal-run-boundary-v1",
        "status": "NOT_EXECUTED_APPROVAL_REQUIRED",
        "collector_id": candidate.collector_reference,
        "reason": "The candidate remains awaiting provider approval. No provider approval and no third collector run are authorized by the bounded Mission 033 budget.",
        "same_collector_run_after_approval": False,
        "corrected_live_output_claimed": False,
    }
    _write_json(evidence_root / "candidate_preview.json", candidate_record)
    _write_json(evidence_root / "verification.json", verification)
    _write_json(evidence_root / "risk_decision.json", risk)
    _write_json(evidence_root / "commit_decision.json", commit)
    _write_json(evidence_root / "output_eligibility.json", output)
    _write_json(evidence_root / "approval.json", approval)
    _write_json(evidence_root / "post_heal_run.json", post_heal)
    return {
        "candidate": candidate,
        "verification": verification,
        "risk": risk,
        "commit": commit,
        "output": output,
        "approval": approval,
        "post_heal": post_heal,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the preserved Mission 033 provider candidate without approval")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = project_candidate_verification(args.root.resolve() / "experiments" / MISSION_DIR_NAME)
    print(json.dumps(_redact(_to_jsonable(result)), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
