#!/usr/bin/env python3
"""Project preserved Mission 033 provider evidence through canonical AEGIS logic.

This script is provider-free: it consumes the already preserved v1 and v2 run
envelopes, constructs an UNTRUSTED_UNTIL_VERIFIED Observation, runs canonical
detection and diagnosis, and emits one compact transport prompt. It never runs,
approves, commits, or rolls back a Bright Data scraper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import _redact, _to_jsonable
from aegis.detection import evaluate_detection
from aegis.diagnosis import DiagnosisContext, build_repair_request, diagnose_deterministically
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    ExtractionContract,
    FieldContract,
    Observation,
    ProviderProvenance,
)


MISSION_DIR_NAME = "mission_033_live_bright_data_success"
FIELDS = ("title", "price", "availability")
RESPONSE_ID_RE = re.compile(r"response_id:\s*([A-Za-z0-9_-]+)")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_redact(_to_jsonable(value)), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def mission033_contract() -> ExtractionContract:
    """Return the frozen three-field contract for the AEGIS-owned public target."""

    return ExtractionContract(
        contract_id="mission-033-owned-product-v1",
        fields=(
            FieldContract("title", expected_types=(str,)),
            FieldContract("price", expected_types=(dict, MappingProxyType)),
            FieldContract("availability", expected_types=(str,)),
        ),
        min_rows=1,
        expected_schema=FIELDS,
    )


def _response_id(envelope: Mapping[str, Any]) -> str:
    stderr = str(envelope.get("stderr", ""))
    match = RESPONSE_ID_RE.search(stderr)
    return match.group(1) if match else str(envelope.get("operation_id", "mission033-run"))


def _rows(envelope: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    raw = envelope.get("stdout")
    if not isinstance(raw, list) or not all(isinstance(row, Mapping) for row in raw):
        raise ValueError("Mission 033 provider run must preserve a list of mapping rows.")
    return tuple({field: row[field] for field in FIELDS if field in row} for row in raw)


def _observation_from_run(envelope: Mapping[str, Any], *, target_url: str, target_version: str) -> Observation:
    collector_id = str(envelope["collector_id"])
    handle = CollectionHandle(
        collection_id=_response_id(envelope),
        collector_id=collector_id,
        correlation_id=f"mission033-{target_version}-{_response_id(envelope)}",
        status=CollectionState.COMPLETED,
        mode=CollectionMode.REALTIME,
        provider_operation_ids={"response_id": _response_id(envelope), "operation_id": str(envelope["operation_id"])},
        provider_status=str(envelope["status"]),
        latency_ms=int(envelope["elapsed_ms"]),
        output_schema=FIELDS,
        provider_provenance=ProviderProvenance.BRIGHT_DATA,
        evidence_refs=(
            f"evidence://mission-033/{envelope['operation_id']}",
            "evidence://mission-033/target-contract",
        ),
    )
    return Observation.from_result(
        CollectionResult(handle=handle, output=_rows(envelope)),
        {"target_url": target_url, "target_version": target_version},
    )


def build_provider_prompt(repair_request: Any) -> str:
    """Create the bounded provider-only wording from an AEGIS RepairRequest.

    This is a transport compaction, not a second diagnosis. It deliberately
    excludes verification, risk, approval, commit, benchmark, and AEGIS-policy
    instructions because Bright Data only needs the extraction correction.
    """

    expected = set(FIELDS)
    affected = tuple(field for field in FIELDS if field in set(repair_request.affected_fields))
    if set(affected) != expected:
        raise ValueError("Mission 033 provider prompt requires all three observed missing contract fields.")
    prompt = (
        "The page markup changed and the current run returns only the input URL. "
        "Restore title, price, and availability from the current semantic labels: "
        "Item name, Current price, and Stock state. Preserve the existing output schema. "
        "Return title as text, price with USD currency and numeric value 599, and availability as Available."
    )
    forbidden = ("approve", "commit", "verification", "risk", "benchmark", "aegis")
    if len(prompt) > 1000 or any(term in prompt.lower() for term in forbidden):
        raise ValueError("Mission 033 provider prompt violates the documented transport boundary.")
    return prompt


def project_lifecycle(evidence_root: Path) -> dict[str, Any]:
    """Write canonical pre-heal lifecycle artifacts from preserved real evidence."""

    contract_payload = _read_json(evidence_root / "target_contract.json")
    target_url = str(contract_payload["target_url"])
    initial_run = _read_json(evidence_root / "initial_run.json")
    drifted_run = _read_json(evidence_root / "provider_operations" / "operation_002_run.json")
    baseline = _observation_from_run(initial_run, target_url=target_url, target_version="v1")
    observation = _observation_from_run(drifted_run, target_url=target_url, target_version="v2")
    detection = evaluate_detection(observation, mission033_contract())
    context = DiagnosisContext(
        observation=observation,
        detection=detection,
        contract=mission033_contract(),
        detection_id=f"detection_{observation.observation_id}",
        evidence_refs=(
            "evidence://mission-033/initial-run",
            "evidence://mission-033/post-drift-run",
            "evidence://mission-033/target-v2",
        ),
        correlation_id=observation.collection_id,
    )
    diagnosis = diagnose_deterministically(context)
    if diagnosis is None:
        raise RuntimeError("Mission 033 post-drift provider output did not produce a canonical diagnosis.")
    repair_request = build_repair_request(
        diagnosis,
        observation=observation,
        contract=mission033_contract(),
        target_input={"target_url": target_url},
        mutation_context={
            "mutation_id": "M033_OWNED_TARGET_V2_MARKUP_DRIFT",
            "boundary": "OWNED_PUBLIC_TARGET",
            "same_url": True,
            "external_provider_output_modified": False,
            "baseline_run_artifact": "initial_run.json",
            "drifted_run_artifact": "provider_operations/operation_002_run.json",
        },
    )
    prompt = build_provider_prompt(repair_request)
    observation_payload = {
        "schema_version": "mission-033-corruption-observation-v1",
        "provenance": "REAL_PROVIDER",
        "collector_id": observation.collector_id,
        "target_url": target_url,
        "same_url": True,
        "baseline_target_version": "v1",
        "drifted_target_version": "v2",
        "baseline_provider_response_id": _response_id(initial_run),
        "drifted_provider_response_id": _response_id(drifted_run),
        "baseline_rows": _rows(initial_run),
        "drifted_rows": _rows(drifted_run),
        "expected_fields": FIELDS,
        "observed_missing_fields": tuple(field for field in FIELDS if field not in _rows(drifted_run)[0]),
        "provider_output_fabricated": False,
        "controlled_target_change": "v1 semantic CSS elements changed to v2 definition-list labels; visible business facts remained unchanged.",
    }
    heal_request = {
        "schema_version": "mission-033-heal-request-v1",
        "status": "READY_FOR_ONE_AUTHORIZED_HEAL",
        "provenance": "AEGIS_DETERMINISTIC_PROJECTION",
        "collector_id": repair_request.collector_reference,
        "target_url": target_url,
        "repair_request_id": repair_request.repair_request_id,
        "diagnosis_id": diagnosis.diagnosis_id,
        "prompt": prompt,
        "prompt_length": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "within_documented_limit": len(prompt) <= 1000,
        "auto_approve": False,
        "retries": 0,
        "approval_authorized": False,
        "provider_command_authorized": "bdata scraper heal <collector_id> <prompt> --url <target_url> --max-retries 0 --json",
    }
    _write_json(evidence_root / "observation.json", observation)
    _write_json(evidence_root / "corruption_observation.json", observation_payload)
    _write_json(evidence_root / "detection.json", detection)
    _write_json(evidence_root / "diagnosis.json", diagnosis)
    _write_json(evidence_root / "repair_request.json", repair_request)
    _write_json(evidence_root / "heal_request.json", heal_request)
    return {
        "observation": observation,
        "detection": detection,
        "diagnosis": diagnosis,
        "repair_request": repair_request,
        "heal_request": heal_request,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Project Mission 033 evidence through canonical AEGIS pre-heal logic")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = project_lifecycle(args.root.resolve() / "experiments" / MISSION_DIR_NAME)
    print(json.dumps(_redact(_to_jsonable(result)), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
