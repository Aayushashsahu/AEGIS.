#!/usr/bin/env python3
"""Explicit CLI boundary for one raw-first Bright Data collector trigger.

Without ``--execute`` this command performs local configuration validation only.
With ``--execute`` it allows one batch trigger, bounded result polling, raw
evidence persistence before normalisation, canonical Observation construction,
and canonical detection.  It never calls healing, approval, commit, rollback,
benchmark, NVIDIA, or Gemini paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import SQLiteAuditStore, _redact, _to_jsonable
from aegis.collector_trigger import (
    BRIGHT_DATA_API_TOKEN_ENV,
    DEFAULT_MAX_POLL_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    DEFAULT_TRIGGER_TIMEOUT_SECONDS,
    TriggerState,
    inspect_known_collection_once,
    resume_batch_collection_once,
    trigger_batch_collection_once,
)
from aegis.detection import evaluate_detection
from aegis.models import Observation
from scripts.mission033_lifecycle import mission033_contract


CANONICAL_COLLECTOR_ID = "c_mt09pib13nxqz1coi"
DEFAULT_OUTPUT_ROOT = ROOT / "experiments" / "mission_068_real_collector_trigger" / "runs"
ACTIVE_STATES = {"ACTIVE"}


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(_redact(_to_jsonable(payload)), sort_keys=True, indent=2) + "\n")


def _safe_id(value: str, *, name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise ValueError(f"{name} must be a safe opaque identifier")
    return value


def _read_state(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("state file must contain a JSON object")
    return payload


def _write_operational_state(path: Path, payload: Mapping[str, Any]) -> None:
    """Write mutable schedule state outside immutable evidence directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _raw_first_sink(directory: Path) -> tuple[Any, list[dict[str, object]]]:
    """Return a controlled writer that persists each response before transport parsing."""

    directory.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, object]] = []

    def sink(response: Any) -> None:
        if response.body is None:
            return
        filename = f"{len(artifacts) + 1:03d}_{response.stage.replace('/', '_')}.bin"
        path = directory / filename
        with path.open("xb") as handle:
            handle.write(response.body)
        artifacts.append({"path": str(path.relative_to(ROOT)), **response.safe_metadata()})

    return sink, artifacts


def local_preflight(*, collector_id: str, target_url: str, output_dir: Path, operation_id: str, correlation_id: str, state_path: Path | None, state: Mapping[str, Any] | None, allow_untracked_run: bool) -> dict[str, Any]:
    tracked_collection = state.get("provider_collection_id") if isinstance(state, Mapping) else None
    tracked_collection_valid = isinstance(tracked_collection, str) and tracked_collection.startswith("j_")
    checks = {
        "exact_canonical_collector": collector_id == CANONICAL_COLLECTOR_ID,
        "credential_configured": bool(os.environ.get(BRIGHT_DATA_API_TOKEN_ENV, "").strip()),
        "target_is_http": target_url.startswith(("https://", "http://")),
        "fresh_output_directory": not output_dir.exists(),
        "raw_first_evidence_destination": str(output_dir.resolve()).startswith(str(DEFAULT_OUTPUT_ROOT.resolve())),
        "single_trigger_budget": True,
        "trigger_retry_budget_zero": True,
        "healing_disabled": True,
        "approval_disabled": True,
        "commit_disabled": True,
        "rollback_disabled": True,
        "correlation_id_valid": bool(correlation_id.strip()),
        "operation_id_valid": bool(operation_id.strip()),
        "state_path_present": state_path is not None,
        "execution_authorized_by_tracked_state_or_explicit_first_run": tracked_collection_valid or allow_untracked_run,
    }
    return {
        "schema_version": "mission-068-trigger-preflight-v1",
        "collector_id": collector_id,
        "target_url_sha256": hashlib.sha256(target_url.encode("utf-8")).hexdigest(),
        "operation_id": operation_id,
        "correlation_id": correlation_id,
        "checks": checks,
        "all_pass": all(checks.values()),
        "provider_trigger_attempts": 0,
        "provider_poll_requests": 0,
        "retries": 0,
        "key_exposed": False,
    }


def _result_evidence(*, result, target_url: str, correlation_id: str, raw_artifacts: tuple[dict[str, object], ...], output_dir: Path) -> dict[str, Any]:
    safe = result.to_safe_metadata()
    safe["raw_evidence"] = list(raw_artifacts)
    safe["raw_evidence_preserved_before_normalization"] = bool(raw_artifacts)
    if result.state is not TriggerState.COMPLETED:
        safe.update({
            "observation": "NOT_CREATED",
            "detection": "NOT_CREATED",
            "verification": {"status": "NOT_APPLICABLE", "reason": "collector result did not complete"},
            "risk": {"status": "NOT_APPLICABLE", "reason": "collector result did not complete"},
            "commit": {"status": "BLOCKED", "reason": "collection did not produce a complete observation"},
        })
        return safe
    evidence_refs = tuple(
        f"evidence://{(Path(str(item['path'])) if Path(str(item['path'])).is_absolute() else ROOT / Path(str(item['path']))).resolve().relative_to(ROOT)}"
        for item in raw_artifacts
    )
    collection = result.to_collection_result(evidence_refs=evidence_refs)
    observation = Observation.from_result(collection, {"target_url": target_url, "correlation_id": correlation_id})
    detection = evaluate_detection(observation, mission033_contract())
    audit_path = output_dir / "audit.sqlite"
    with SQLiteAuditStore(audit_path) as audit:
        observation_event = audit.append_observation(
            observation,
            aggregate_id=collection.handle.collection_id,
            correlation_id=correlation_id,
            provenance="REAL_PROVIDER",
            evidence_refs=evidence_refs,
        )
        detection_event = audit.append_detection(
            detection,
            aggregate_id=collection.handle.collection_id,
            correlation_id=correlation_id,
            provenance="AEGIS_DETERMINISTIC",
            evidence_refs=tuple(detection.evidence_refs),
        )
    safe.update({
        "observation": _to_jsonable(observation),
        "detection": _to_jsonable(detection),
        "audit": {
            "store": str(audit_path.relative_to(ROOT)) if audit_path.is_relative_to(ROOT) else str(audit_path),
            "observation_event_id": observation_event.event_id,
            "detection_event_id": detection_event.event_id,
        },
        "verification": {"status": "NOT_APPLICABLE", "reason": "A collection output is an observation, not a repaired candidate."},
        "risk": {"status": "NOT_APPLICABLE", "reason": "No candidate verification exists for a direct collection result."},
        "commit": {"status": "BLOCKED", "reason": "No repair candidate, verification result, or separate commit authorization exists."},
    })
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Perform the one bounded trigger after local and active-run preflight passes.")
    parser.add_argument("--collector-id", default=CANONICAL_COLLECTOR_ID)
    parser.add_argument("--target-url", default=os.environ.get("AEGIS_TRIGGER_TARGET_URL"))
    parser.add_argument("--resume-collection-id", default=None, help="Resume bounded dataset retrieval for one known provider collection ID; never triggers a new collection.")
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--state-path", type=Path, default=None, help="Mutable operational state outside immutable evidence; required for scheduled execution.")
    parser.add_argument("--allow-untracked-run", action="store_true", help="Allow one manual validation when no prior tracked provider collection exists. Never use this for scheduled execution.")
    args = parser.parse_args()
    if not args.target_url:
        parser.error("--target-url or AEGIS_TRIGGER_TARGET_URL is required")
    try:
        operation_id = _safe_id(args.operation_id, name="operation_id")
        correlation_id = _safe_id(args.correlation_id, name="correlation_id")
    except ValueError as error:
        parser.error(str(error))
    output_dir = (args.output_dir or (DEFAULT_OUTPUT_ROOT / operation_id)).resolve()
    try:
        state = _read_state(args.state_path) if args.state_path else None
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(f"invalid --state-path: {error}")
    preflight = local_preflight(
        collector_id=args.collector_id,
        target_url=args.target_url,
        output_dir=output_dir,
        operation_id=operation_id,
        correlation_id=correlation_id,
        state_path=args.state_path,
        state=state,
        allow_untracked_run=args.allow_untracked_run or bool(args.resume_collection_id),
    )
    if args.resume_collection_id:
        preflight["resume_collection_id"] = args.resume_collection_id
        preflight["trigger_budget"] = 0
    if not preflight["all_pass"] or not args.execute:
        print(json.dumps(preflight, sort_keys=True))
        return 0 if preflight["all_pass"] else 2

    if not args.resume_collection_id and state and isinstance(state.get("provider_collection_id"), str):
        known = inspect_known_collection_once(os.environ[BRIGHT_DATA_API_TOKEN_ENV], collection_id=state["provider_collection_id"])
        preflight["known_collection_status"] = _to_jsonable(known)
        if known.is_active or known.state == "UNKNOWN":
            preflight["trigger"] = "NOT_ATTEMPTED"
            preflight["stop_reason"] = "KNOWN_COLLECTION_ACTIVE" if known.is_active else "KNOWN_COLLECTION_STATUS_UNRESOLVED"
            print(json.dumps(_redact(_to_jsonable(preflight)), sort_keys=True))
            return 2

    requested_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_new_json(output_dir / "run_request.json", {
        "schema_version": "mission-068-trigger-request-v1",
        "requested_at_utc": requested_at,
        "collector_id": args.collector_id,
        "target_url_sha256": preflight["target_url_sha256"],
        "operation_id": operation_id,
        "correlation_id": correlation_id,
        "trigger_budget": 0 if args.resume_collection_id else 1,
        "resume_collection_id": args.resume_collection_id,
        "retry_budget": 0,
        "healing": "DISABLED",
        "approval": "DISABLED",
        "commit": "DISABLED",
        "rollback": "DISABLED",
        "key_exposed": False,
    })
    raw_sink, raw_artifacts = _raw_first_sink(output_dir / "raw")
    if args.resume_collection_id:
        result = resume_batch_collection_once(
            os.environ[BRIGHT_DATA_API_TOKEN_ENV],
            collector_id=args.collector_id,
            target_url=args.target_url,
            correlation_id=correlation_id,
            collection_id=args.resume_collection_id,
            poll_timeout_seconds=DEFAULT_POLL_TIMEOUT_SECONDS,
            poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
            max_poll_attempts=DEFAULT_MAX_POLL_ATTEMPTS,
            raw_response_sink=raw_sink,
        )
    else:
        result = trigger_batch_collection_once(
            os.environ[BRIGHT_DATA_API_TOKEN_ENV],
            collector_id=args.collector_id,
            target_url=args.target_url,
            correlation_id=correlation_id,
            trigger_timeout_seconds=DEFAULT_TRIGGER_TIMEOUT_SECONDS,
            poll_timeout_seconds=DEFAULT_POLL_TIMEOUT_SECONDS,
            poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
            max_poll_attempts=DEFAULT_MAX_POLL_ATTEMPTS,
            raw_response_sink=raw_sink,
        )
    evidence = _result_evidence(
        result=result,
        target_url=args.target_url,
        correlation_id=correlation_id,
        raw_artifacts=tuple(raw_artifacts),
        output_dir=output_dir,
    )
    _write_new_json(output_dir / "result.json", evidence)
    if args.state_path and result.collection_id:
        _write_operational_state(args.state_path, {"provider_collection_id": result.collection_id, "last_state": result.state.value, "updated_at_utc": requested_at})
    print(json.dumps({"operation_id": operation_id, "state": result.state.value, "provider_collection_id": result.collection_id, "trigger_attempts": result.trigger_attempts, "raw_evidence_count": len(raw_artifacts), "retries": 0, "healing": "DISABLED", "approval": "DISABLED", "commit": "BLOCKED"}, sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
