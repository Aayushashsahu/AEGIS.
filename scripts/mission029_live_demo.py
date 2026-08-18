#!/usr/bin/env python3
"""Mission 029 live Bright Data demonstration.

This script performs at most one fresh collector create, one collector run, and
one approval-gated healing request. It never approves, commits, or activates a
provider candidate. Re-running after a complete evidence bundle replays the
preserved result without another provider operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from aegis.adapter import BrightDataCliAdapter, CommandResult, _last_object, subprocess_runner
from aegis.audit_store import _redact, _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary, QuarantineLedger
from aegis.contracts import default_extraction_contract
from aegis.diagnosis import DiagnosisContext, DeterministicDiagnostician, build_repair_request
from aegis.healing import HealHandle, HealOperationResult, HealState, RepairCandidate, VerificationStatus
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    CollectorHandle,
    Observation,
    ProviderProvenance,
    utc_now,
)
from aegis.risk import RiskGovernor, RiskDecisionType
from aegis.verification import VerificationContext, verify_candidate

TARGET_URL = "https://news.ycombinator.com"
DESCRIPTION = "Extract top stories: title, url, points, author, comment count"
SELECTED_FIELDS = ("title", "url", "points", "author", "comment_count")
DEMO_MUTATION_ID = "DEMO_MUTATION"
EVIDENCE_ROOT_NAME = "mission_029"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_redact(_to_jsonable(value)), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        for key in ("rows", "items", "results", "data", "output", "preview_result"):
            nested = value.get(key)
            if isinstance(nested, (list, tuple)) and all(isinstance(row, Mapping) for row in nested):
                return tuple(nested)
        return (value,) if value else ()
    if isinstance(value, (list, tuple)) and all(isinstance(row, Mapping) for row in value):
        return tuple(value)
    return ()


def _normalize_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    return tuple({field: row.get(field) for field in SELECTED_FIELDS} for row in rows)


def validate_demo_target(target_url: str = TARGET_URL, fields: Sequence[str] = SELECTED_FIELDS) -> None:
    if not target_url.startswith("https://") or target_url != TARGET_URL:
        raise ValueError("Mission 029 target must be the approved public HTTPS Hacker News URL")
    if tuple(fields) != SELECTED_FIELDS:
        raise ValueError("Mission 029 target fields must remain the frozen selected schema")


def apply_demo_mutation(rows: Sequence[Mapping[str, Any]]) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    """Apply DEMO_MUTATION only to a copied AEGIS evidence snapshot."""

    original = [dict(row) for row in rows]
    mutation_index = next((index for index, row in enumerate(original) if isinstance(row.get("points"), (int, float)) and not isinstance(row.get("points"), bool)), None)
    mutation_field = "points"
    if mutation_index is None:
        mutation_field = "comment_count"
        mutation_index = next((index for index, row in enumerate(original) if isinstance(row.get(mutation_field), (int, float)) and not isinstance(row.get(mutation_field), bool)), None)
    if mutation_index is None:
        raise ValueError("live output contained no numeric field suitable for DEMO_MUTATION")
    expected_value = original[mutation_index][mutation_field]
    mutated = [dict(row) for row in original]
    mutated[mutation_index][mutation_field] = -1
    return tuple(mutated), {
        "mutation_id": DEMO_MUTATION_ID,
        "reversible": True,
        "boundary": "AEGIS_EVIDENCE_ONLY",
        "external_website_modified": False,
        "collector_modified": False,
        "row_index": mutation_index,
        "field": mutation_field,
        "expected_value_from_preserved_live_output": expected_value,
        "observed_corrupted_value": -1,
        "ground_truth": "non_negative_numeric",
        "original_output_ref": "collection_output_provider_raw.json",
    }


def _provider_operation_type(command: Sequence[str]) -> str:
    if "create" in command:
        return "collector_create"
    if "run" in command:
        return "collector_run"
    if "heal" in command:
        return "healing_request"
    return "provider_operation"


class RecordingRunner:
    """Record provider command envelopes without storing credentials."""

    def __init__(self, operation_root: Path, runner: Any = subprocess_runner) -> None:
        self.operation_root = operation_root
        self.operation_root.mkdir(parents=True, exist_ok=True)
        self._runner = runner
        self.next_index = len(tuple(operation_root.glob("operation_*.json"))) + 1

    def __call__(self, command: Sequence[str]) -> CommandResult:
        result = self._runner(command)
        operation_id = f"operation_{self.next_index:03d}"
        self.next_index += 1
        record = {
            "operation_id": operation_id,
            "operation_type": _provider_operation_type(command),
            "command": list(command),
            "returncode": result.returncode,
            "latency_ms": result.latency_ms,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        _write_json(self.operation_root / f"{operation_id}.json", record)
        return result


def _load_collector(evidence_root: Path) -> CollectorHandle | None:
    path = evidence_root / "collector_handle.json"
    if not path.is_file():
        return None
    payload = _read_json(path)
    return CollectorHandle(
        collector_id=str(payload["collector_id"]),
        provider=ProviderProvenance.BRIGHT_DATA,
        provider_reference=payload.get("provider_reference"),
    )


def _load_collection(evidence_root: Path) -> CollectionResult | None:
    handle_path = evidence_root / "collection_handle.json"
    output_path = evidence_root / "collection_output_normalized.json"
    if not handle_path.is_file() or not output_path.is_file():
        return None
    payload = _read_json(handle_path)
    handle = CollectionHandle(
        collection_id=str(payload["collection_id"]),
        collector_id=str(payload["collector_id"]),
        correlation_id=str(payload.get("correlation_id", "")),
        status=CollectionState.COMPLETED,
        mode=CollectionMode(str(payload.get("mode", CollectionMode.REALTIME.value))),
        provider_operation_ids=payload.get("provider_operation_ids", {}),
        provider_status=str(payload.get("provider_status", "COMPLETED")),
        latency_ms=payload.get("latency_ms"),
        output_schema=tuple(payload.get("output_schema", SELECTED_FIELDS)),
        provider_provenance=ProviderProvenance.BRIGHT_DATA,
        evidence_refs=tuple(payload.get("evidence_refs", ())),
    )
    return CollectionResult(handle=handle, output=tuple(_read_json(output_path)), received_at=utc_now())


def _load_candidate(evidence_root: Path) -> RepairCandidate | None:
    path = evidence_root / "repair_candidate.json"
    if not path.is_file():
        return None
    payload = _read_json(path)
    return RepairCandidate(
        candidate_id=str(payload["candidate_id"]),
        repair_request_id=str(payload["repair_request_id"]),
        collector_reference=str(payload["collector_reference"]),
        provider_operation_reference=payload.get("provider_operation_reference"),
        provider_status=str(payload.get("provider_status", "")),
        preview_result=payload.get("preview_result"),
        diff_summary=str(payload.get("diff_summary", "")),
        approval_command=payload.get("approval_command"),
        raw_evidence_ref=str(payload["raw_evidence_ref"]),
        provenance=ProviderProvenance(str(payload.get("provenance", ProviderProvenance.BRIGHT_DATA.value))),
        latency_ms=payload.get("latency_ms"),
        verification_status=VerificationStatus.UNVERIFIED,
    )


def _artifact_hashes(evidence_root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(evidence_root)): _sha256(path)
        for path in sorted(evidence_root.rglob("*"))
        if path.is_file() and path.name not in {"demo_manifest.json", "artifact_hashes.json"}
    }


def run_demo(root: Path, *, live: bool) -> dict[str, Any]:
    evidence_root = root / "experiments" / EVIDENCE_ROOT_NAME
    evidence_root.mkdir(parents=True, exist_ok=True)
    validate_demo_target()
    manifest_path = evidence_root / "demo_manifest.json"
    if manifest_path.is_file():
        existing = _read_json(manifest_path)
        existing["replay"] = True
        return existing
    if not live:
        return {
            "status": "BLOCKED_NOT_READY",
            "message": "Pass --live to authorize the bounded collector create/run/heal demonstration.",
            "provider_operations_executed": 0,
            "production_commit_performed": False,
        }

    operation_root = evidence_root / "provider_operations"
    runner = RecordingRunner(operation_root)
    adapter = BrightDataCliAdapter(runner=runner)
    try:
        collector = _load_collector(evidence_root)
        if collector is None:
            request = __import__("aegis.models", fromlist=["CollectorRequest"]).CollectorRequest(
                target_url=TARGET_URL,
                extraction_prompt=DESCRIPTION,
                provider=ProviderProvenance.BRIGHT_DATA,
            )
            collector = adapter.create_collector(request)
            if not collector.collector_id.startswith("c_"):
                raise RuntimeError("fresh Bright Data collector ID was not a c_* value")
            _write_json(evidence_root / "collector_handle.json", collector)
            create_record = _last_object(next(iter(sorted(operation_root.glob("operation_*.json"))), Path("/dev/null")).read_text(encoding="utf-8")) if False else None
            _write_json(evidence_root / "collector_creation_evidence.json", {
                "collector_id": collector.collector_id,
                "provider": "BRIGHT_DATA",
                "target_url": TARGET_URL,
                "description": DESCRIPTION,
                "provider_reference": collector.provider_reference,
                "fresh_collector_required": True,
                "evidence_refs": (f"evidence://bright-data/cli/create/{collector.collector_id}",),
            })

        collection = _load_collection(evidence_root)
        if collection is None:
            raw_handle = adapter.run_collector(collector, target_url=TARGET_URL, mode=CollectionMode.REALTIME)
            while True:
                current = adapter.poll_collection(raw_handle)
                if current.status in {CollectionState.COMPLETED, CollectionState.FAILED, CollectionState.TIMED_OUT}:
                    break
                time.sleep(2)
            if current.status is not CollectionState.COMPLETED:
                _write_json(evidence_root / "collection_failure.json", current)
                raise RuntimeError(f"Bright Data collector run ended {current.status.value}")
            raw_result = adapter.retrieve_output(current)
            raw_rows = tuple(raw_result.output)
            _write_json(evidence_root / "collection_output_provider_raw.json", raw_rows)
            normalized_rows = _normalize_rows(raw_rows)
            normalized_handle = replace(current, output_schema=SELECTED_FIELDS)
            collection = CollectionResult(handle=normalized_handle, output=normalized_rows, received_at=raw_result.received_at)
            _write_json(evidence_root / "collection_handle.json", collection.handle)
            _write_json(evidence_root / "collection_output_normalized.json", collection.output)
            _write_json(evidence_root / "collection_summary.json", {
                "collector_id": collector.collector_id,
                "collection_id": collection.handle.collection_id,
                "provider_operation_ids": collection.handle.provider_operation_ids,
                "mode": collection.handle.mode,
                "provider_status": collection.handle.provider_status,
                "row_count": len(collection.output),
                "schema": SELECTED_FIELDS,
                "latency_ms": collection.handle.latency_ms,
                "evidence_refs": collection.handle.evidence_refs,
            })

        original_observation = Observation.from_result(collection, {"target_url": TARGET_URL})
        _write_json(evidence_root / "observation_original.json", original_observation)
        original_rows = [dict(row) for row in collection.output]
        mutated_rows, mutation = apply_demo_mutation(original_rows)
        mutation_index = int(mutation["row_index"])
        mutation_field = str(mutation["field"])
        mutated_observation = Observation(
            collection_id=collection.handle.collection_id,
            collector_id=collection.handle.collector_id,
            provider_operation_ids=collection.handle.provider_operation_ids,
            input={"target_url": TARGET_URL},
            output=mutated_rows,
            schema=SELECTED_FIELDS,
            row_count=len(mutated_rows),
            latency_ms=collection.handle.latency_ms,
            collection_mode=collection.handle.mode,
            provider_provenance=ProviderProvenance.BRIGHT_DATA,
            evidence_refs=tuple(sorted(set(collection.handle.evidence_refs) | {"evidence://mission-029/demo-mutation"})),
        )
        _write_json(evidence_root / "demo_mutation.json", mutation)
        _write_json(evidence_root / "observation_mutated.json", mutated_observation)

        contract = default_extraction_contract()
        detection = __import__("aegis.detection", fromlist=["evaluate_detection"]).evaluate_detection(mutated_observation, contract)
        _write_json(evidence_root / "detection_result.json", detection)
        correlation_id = collection.handle.correlation_id
        diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(
            observation=mutated_observation,
            detection=detection,
            contract=contract,
            detection_id=f"detection_{mutated_observation.observation_id}",
            evidence_refs=("evidence://mission-029/demo-mutation",),
            correlation_id=correlation_id,
        ))
        if diagnosis is None:
            raise RuntimeError("DEMO_MUTATION did not produce a deterministic diagnosis")
        _write_json(evidence_root / "diagnosis.json", diagnosis)
        repair_request = build_repair_request(
            diagnosis,
            observation=mutated_observation,
            contract=contract,
            target_input={"target_url": TARGET_URL},
            mutation_context=mutation,
        )
        _write_json(evidence_root / "repair_request.json", repair_request)

        candidate = _load_candidate(evidence_root)
        if candidate is None:
            heal_handle = adapter.request_healing(repair_request, timeout_seconds=900)
            while True:
                current_heal = adapter.poll_healing(heal_handle)
                if current_heal.status in {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT}:
                    if current_heal.status is HealState.AWAITING_APPROVAL:
                        current_heal = adapter.poll_healing(current_heal)
                    break
                time.sleep(2)
            if current_heal.status not in {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY}:
                _write_json(evidence_root / "healing_failure.json", current_heal)
                raise RuntimeError(f"Bright Data healing ended {current_heal.status.value}")
            heal_result = adapter.retrieve_heal_result(current_heal)
            if heal_result.candidate is None:
                raise RuntimeError("Bright Data healing returned no RepairCandidate")
            candidate = heal_result.candidate
            _write_json(evidence_root / "heal_handle.json", heal_result.handle)
            _write_json(evidence_root / "heal_provider_envelope.json", heal_result.envelope)
            _write_json(evidence_root / "repair_candidate.json", candidate)
            _write_json(evidence_root / "healing_summary.json", {
                "collector_id": collector.collector_id,
                "heal_id": heal_result.handle.heal_id,
                "status": heal_result.handle.status,
                "provider_operation_reference": candidate.provider_operation_reference,
                "provider_status": candidate.provider_status,
                "diff_summary": candidate.diff_summary,
                "approval_command_present": bool(candidate.approval_command),
                "approval_command_executed": False,
                "production_commit_performed": False,
                "latency_ms": candidate.latency_ms,
            })

        candidate_rows = _normalize_rows(_rows(candidate.preview_result))
        verification = verify_candidate(VerificationContext(
            candidate=candidate,
            contract=contract,
            candidate_output=candidate_rows,
            history=(original_observation,),
            independent_evidence=None,
            correlation_id=correlation_id,
            evidence_refs=("evidence://mission-029/verification",),
            unaffected_fields=tuple(field for field in SELECTED_FIELDS if field not in diagnosis.affected_fields),
            history_source_group="BRIGHT_DATA_LIVE_COLLECTION",
        ))
        _write_json(evidence_root / "verification_result.json", verification)
        risk = RiskGovernor().decide(verification, candidate, correlation_id=correlation_id)
        _write_json(evidence_root / "risk_decision.json", risk)
        quarantine_record = None
        quarantine_ledger = QuarantineLedger()
        if risk.decision is RiskDecisionType.QUARANTINE:
            quarantine_ledger = quarantine_ledger.record_for_decision(candidate, verification, risk)
            quarantine_record = quarantine_ledger.records[-1]
            _write_json(evidence_root / "quarantine_record.json", quarantine_record)
        commit_decision = CommitGate().evaluate(
            candidate,
            verification,
            risk,
            contract,
            known_good_version=None,
            authorization=None,
            correlation_id=correlation_id,
            quarantine_record=quarantine_record,
        )
        _write_json(evidence_root / "commit_decision.json", commit_decision)
        eligibility = OutputEligibilityBoundary.evaluate(commit_decision, quarantine_record=quarantine_record)
        _write_json(evidence_root / "output_eligibility.json", eligibility)
        provider_files = sorted(operation_root.glob("operation_*.json"))
        counts: dict[str, int] = {}
        for path in provider_files:
            operation_type = str(_read_json(path).get("operation_type", "provider_operation"))
            counts[operation_type] = counts.get(operation_type, 0) + 1
        status = "QUARANTINED" if risk.decision is RiskDecisionType.QUARANTINE else "REJECTED" if risk.decision is RiskDecisionType.REJECT else "ELIGIBLE_BUT_COMMIT_NOT_PERFORMED"
        manifest = {
            "mission": "029",
            "status": status,
            "target_url": TARGET_URL,
            "collector_id": collector.collector_id,
            "observation_id": mutated_observation.observation_id,
            "detection_id": f"detection_{mutated_observation.observation_id}",
            "diagnosis_id": diagnosis.diagnosis_id,
            "repair_request_id": repair_request.repair_request_id,
            "candidate_id": candidate.candidate_id,
            "verification_id": verification.verification_id,
            "risk_decision_id": risk.decision_id,
            "commit_decision_id": commit_decision.decision_id,
            "row_count": len(collection.output),
            "detection": {"detected": detection.detected, "severity": detection.severity, "affected_fields": detection.affected_fields},
            "diagnosis": {"failure_class": diagnosis.failure_class, "certainty": diagnosis.certainty, "rationale": diagnosis.rationale},
            "candidate_state": candidate.verification_status,
            "verification_status": verification.overall_status,
            "risk_decision": risk.decision,
            "risk_reason": risk.reason_code,
            "commit_eligibility": commit_decision.eligibility,
            "data_shipped": False,
            "production_commit_performed": False,
            "provider_operation_counts": counts,
            "provider_operations_executed": sum(counts.values()),
            "approval_command_executed": False,
            "gemini_invoked": False,
            "nvidia_benchmark_invoked": False,
            "benchmark_invoked": False,
            "demo_mutation": mutation,
            "evidence_root": str(evidence_root.relative_to(root)),
        }
        _write_json(manifest_path, manifest)
        _write_json(evidence_root / "artifact_hashes.json", _artifact_hashes(evidence_root))
        return manifest
    finally:
        adapter.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded Mission 029 Bright Data live demonstration")
    parser.add_argument("--live", action="store_true", help="authorize at most one create, one run, and one heal")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    try:
        manifest = run_demo(args.root.resolve(), live=args.live)
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "provider_credentials_echoed": False}, sort_keys=True))
        return 2
    print(json.dumps(_redact(_to_jsonable(manifest)), sort_keys=True, indent=2))
    return 0 if manifest.get("status") not in {"FAILED", "BLOCKED_NOT_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
