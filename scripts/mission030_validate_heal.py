"""Mission 030: one bounded Bright Data compact-prompt heal validation.

The script consumes immutable Mission 029 evidence, writes new Mission 030
evidence only, and performs no provider activity unless explicitly invoked with
``--live``. A completed terminal result is replayed locally on subsequent runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from aegis.adapter import (
    BrightDataCliAdapter,
    BrightDataHealPrompt,
    CommandResult,
    build_bright_data_heal_prompt,
    subprocess_runner,
)
from aegis.audit_store import _redact, _to_jsonable
from aegis.diagnosis import (
    DiagnosisProvenance,
    FailureClass,
    RepairRequest,
    RepairRequestStatus,
)
from aegis.healing import HealState
from aegis.models import ExtractionContract, FieldContract

MISSION_029_ROOT = Path("experiments/mission_029")
MISSION_030_ROOT = Path("experiments/mission_030")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_redact(_to_jsonable(value)), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object artifact: {path}")
    return payload


def _types(values: Sequence[object]) -> tuple[type, ...]:
    known = {"str": str, "int": int, "float": float, "bool": bool}
    parsed: list[type] = []
    for value in values:
        text = str(value).replace("<class '", "").replace("'>", "")
        if text in known:
            parsed.append(known[text])
    return tuple(parsed) or (str,)


def load_mission029_repair_request(root: Path) -> RepairRequest:
    """Rehydrate the immutable Mission 029 request without changing it."""

    payload = _read_json(root / MISSION_029_ROOT / "repair_request.json")
    raw_contract = payload["extraction_contract"]
    if not isinstance(raw_contract, Mapping):
        raise ValueError("Mission 029 RepairRequest contains no extraction contract")
    fields = tuple(
        FieldContract(
            name=str(field["name"]),
            required=bool(field.get("required", True)),
            expected_types=_types(field.get("expected_types", ())),
            allow_null=bool(field.get("allow_null", False)),
        )
        for field in raw_contract["fields"]
    )
    contract = ExtractionContract(
        contract_id=str(raw_contract["contract_id"]),
        fields=fields,
        min_rows=int(raw_contract.get("min_rows", 1)),
        max_rows=raw_contract.get("max_rows"),
        expected_row_count=raw_contract.get("expected_row_count"),
        row_count_tolerance=int(raw_contract.get("row_count_tolerance", 0)),
        numeric_bounds={key: tuple(value) for key, value in dict(raw_contract.get("numeric_bounds", {})).items()},
        invariants=tuple(str(value) for value in raw_contract.get("invariants", ())),
        expected_schema=tuple(str(value) for value in raw_contract.get("expected_schema", ())),
    )
    return RepairRequest(
        repair_request_id=str(payload["repair_request_id"]),
        collector_reference=str(payload["collector_reference"]),
        observation_id=str(payload["observation_id"]),
        diagnosis_id=str(payload["diagnosis_id"]),
        detection_id=str(payload["detection_id"]),
        correlation_id=str(payload["correlation_id"]),
        affected_fields=tuple(str(value) for value in payload.get("affected_fields", ())),
        failure_class=FailureClass(str(payload.get("failure_class", FailureClass.UNKNOWN.value))),
        severity=str(payload.get("severity", "UNKNOWN")),
        extraction_contract=contract,
        evidence_references=tuple(str(value) for value in payload.get("evidence_references", ())),
        target_input=dict(payload.get("target_input", {})),
        repair_objective=str(payload["repair_objective"]),
        constraints=tuple(str(value) for value in payload.get("constraints", ())),
        mutation_context=dict(payload.get("mutation_context", {})),
        provenance=DiagnosisProvenance(str(payload.get("provenance", DiagnosisProvenance.DETERMINISTIC.value))),
        timestamp=payload.get("timestamp"),
        status=RepairRequestStatus(str(payload.get("status", RepairRequestStatus.REPAIR_REQUESTED.value))),
    )


def prompt_projection_record(prompt: BrightDataHealPrompt) -> dict[str, Any]:
    return {
        "policy_version": prompt.policy_version,
        "prompt_text": prompt.prompt_text,
        "prompt_length": prompt.prompt_length,
        "prompt_hash": prompt.prompt_hash,
        "limit": prompt.limit,
        "within_limit": prompt.within_limit,
    }


class RecordingHealRunner:
    """Persist the one permitted provider envelope without credentials."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def __call__(self, command: Sequence[str]) -> CommandResult:
        if any(self.root.glob("operation_*.json")):
            raise RuntimeError("Mission 030 permits exactly one Bright Data heal operation")
        result = subprocess_runner(command)
        _write_json(
            self.root / "operation_001.json",
            {
                "operation_id": "mission030_heal_001",
                "operation_type": "healing_request",
                "command": list(command),
                "returncode": result.returncode,
                "latency_ms": result.latency_ms,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path, *, live: bool) -> dict[str, Any]:
    evidence_root = root / MISSION_030_ROOT
    terminal_path = evidence_root / "live_heal_result.json"
    if terminal_path.exists():
        result = dict(_read_json(terminal_path))
        result["replay_only"] = True
        return result

    request = load_mission029_repair_request(root)
    prompt = build_bright_data_heal_prompt(request)
    preflight = {
        "mission": "MISSION_030",
        "source_repair_request": str(MISSION_029_ROOT / "repair_request.json"),
        "collector_id": request.collector_reference,
        "repair_request_id": request.repair_request_id,
        "prompt": prompt_projection_record(prompt),
        "bright_data_create_operations": 0,
        "bright_data_run_operations": 0,
        "bright_data_heal_operations": 0,
        "approval_operations": 0,
        "production_commits": 0,
    }
    _write_json(evidence_root / "preflight.json", preflight)
    if not prompt.within_limit:
        result = {**preflight, "status": "HEAL_BLOCKED_PROVIDER_PROMPT_LIMIT", "provider_called": False}
        _write_json(terminal_path, result)
        return result
    if not live:
        return {**preflight, "status": "PREFLIGHT_PASS", "provider_called": False}

    runner = RecordingHealRunner(evidence_root / "provider_operations")
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request, timeout_seconds=900)
        while handle.status not in {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT}:
            time.sleep(1)
            handle = adapter.poll_healing(handle)
        if handle.status is HealState.AWAITING_APPROVAL:
            handle = adapter.poll_healing(handle)
        candidate = None
        envelope = None
        if handle.status in {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY}:
            outcome = adapter.retrieve_heal_result(handle)
            candidate = outcome.candidate
            envelope = outcome.envelope
        result = {
            **preflight,
            "status": "CANDIDATE_UNVERIFIED" if candidate is not None else "HEAL_FAILED_BEFORE_CANDIDATE",
            "provider_called": True,
            "bright_data_heal_operations": 1,
            "heal_handle": handle,
            "candidate_created": candidate is not None,
            "candidate_status": "UNVERIFIED" if candidate is not None else "NOT_CREATED",
            "candidate": candidate,
            "provider_envelope": envelope,
            "verification_invoked": False,
            "risk_governor_invoked": False,
            "commit_gate_invoked": False,
            "approval_command_executed": False,
            "production_commit_performed": False,
            "data_shipped": False,
        }
        _write_json(terminal_path, result)
    _write_json(
        evidence_root / "artifact_hashes.json",
        {
            str(path.relative_to(evidence_root)): _sha256(path)
            for path in sorted(evidence_root.rglob("*.json"))
            if path.name != "artifact_hashes.json"
        },
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="perform the one owner-authorized Bright Data heal")
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), live=args.live), sort_keys=True, indent=2, default=str))


if __name__ == "__main__":
    main()
