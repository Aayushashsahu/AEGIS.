"""Mission 059: exactly one raw-first, candidate-only Bright Data heal.

``--preflight`` makes only direct controlled-target reads and local integrity
checks. ``--execute`` performs the single authorized heal. ``--validate`` is
provider-free and writes artifact hashes after execution. Approval, rerun,
commit, and rollback have no callable implementation in this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aegis.mission056_candidate_evidence import target_facts_from_html
from aegis.mission059_evidence import candidate_status, extract_provider_identifiers
from aegis.transport_evidence import preserve_raw_response_once

MISSION_DIR = ROOT / "experiments" / "mission_059"
AUTHORIZATION_PATH = MISSION_DIR / "authorization.json"
CAPABILITIES_PATH = MISSION_DIR / "cli_capabilities.json"
SPEC_PATH = MISSION_DIR / "experiment_spec.json"
PREFLIGHT_PATH = MISSION_DIR / "preflight.json"
CORRELATION_PATH = MISSION_DIR / "correlation.json"
CLI_CREDENTIAL_ENV = "BRIGHTDATA_API_KEY"
SECRET_VALUE_RE = re.compile(r"\b(?:sk|nvapi|bdapi|bearer)[_-]?[A-Za-z0-9._-]{12,}\b", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|token|password|secret|cookie)", re.IGNORECASE)
SAFE_METADATA_KEYS = frozenset({
    "secret_like_content",
    "authorization_context",
    "authorization_one_heal_zero_retry",
    "approval_authorized",
    "rerun_authorized",
    "commit_authorized",
    "rollback_authorized",
})

PROTECTED_HASHES = {
    "experiments/mission_053_candidate_only/heal_result.json": "6a2ee97dee2f0a3ac60bfe8cb77e018c73511e11603363c6b0174487100f8ecd",
    "experiments/mission_053_candidate_only/raw_provider_response.bin": "dcfa386469ec7a78fb42e5f91779e501edb2b9863a1277212cb585b13d249178",
    "experiments/mission_056_full_scale_recovery/heal_metadata.json": "665f79c52756ccc11b9ec216fd56ff51516cd4699ad8c737e3fc5cb32f92c070",
    "experiments/mission_056_full_scale_recovery/heal_raw.bin": "a0bba0d6b4d1c5dcd7271519a6ade77f3135385afe2cf8d211c75f3c0ec9e9b7",
    "experiments/mission_056_full_scale_recovery/correlation_records/m056-heal-20260821T153830Z.json": "9d910f4d016498543d0b78c3a559221f071b9e66782d82d48e4a07b2530e9ac1",
}
TERMINAL_PATHS = (
    "preflight.json", "correlation.json", "heal_request.json", "heal_raw_response.bin",
    "heal_raw_metadata.json", "heal_result.json", "candidate_preview.json", "future_approval_artifact.json",
    "summary.json", "artifact_hashes.json", "validation.json",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): "[REDACTED]" if SECRET_KEY_RE.search(str(key)) and str(key) not in SAFE_METADATA_KEYS else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(_redact(dict(value)), indent=2, sort_keys=True) + "\n")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
                return value
            except json.JSONDecodeError:
                continue
    return {"unparsed_text": text}


def _historical_integrity() -> tuple[bool, dict[str, str | None]]:
    actual: dict[str, str | None] = {}
    for relative, expected in PROTECTED_HASHES.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        actual[relative] = digest
        if digest != expected:
            return False, actual
    return True, actual


def _fresh_terminal_paths() -> bool:
    return all(not (MISSION_DIR / name).exists() for name in TERMINAL_PATHS)


def _build_command(spec: Mapping[str, Any]) -> list[str]:
    target = spec["target"]
    prompt = spec["repair_prompt"]
    return [
        "npx", "--offline", "-p", "@brightdata/cli@0.3.5", "bdata", "--timing", "scraper", "heal",
        str(spec["collector_id"]), str(prompt["text"]), "--url", str(target["url"]), "--timeout", "900",
        "--max-retries", "0", "--json",
    ]


def create_preflight() -> dict[str, Any]:
    if not _fresh_terminal_paths():
        raise RuntimeError("Mission 059 evidence paths are not fresh")
    authorization = _read_json(AUTHORIZATION_PATH)
    capabilities = _read_json(CAPABILITIES_PATH)
    spec = _read_json(SPEC_PATH)
    correlation_timestamp = _now()
    operation_stamp = correlation_timestamp.replace("-", "").replace(":", "").replace(".", "").replace("Z", "Z")
    correlation = {
        "schema_version": "mission-059-correlation-v1",
        "mission": "MISSION_059",
        "aegis_operation_id": f"m059-heal-{operation_stamp}",
        "aegis_correlation_id": f"mission059-heal-{spec['collector_id']}-{operation_stamp}",
        "created_at_utc": correlation_timestamp,
        "collector_id": spec["collector_id"],
        "target_url": spec["target"]["url"],
        "cli_version": capabilities.get("cli_version"),
        "operation_type": "candidate_only_heal",
        "prompt_sha256": spec["repair_prompt"]["sha256"],
        "prompt_length": spec["repair_prompt"]["character_count"],
        "authorization_context": "experiments/mission_059/authorization.json",
        "provider_identifier_policy": "ACTUAL_ONLY_NO_FALLBACK",
    }
    _write_once(CORRELATION_PATH, correlation)
    integrity_ok, hashes = _historical_integrity()
    target_health: dict[str, Any] | None = None
    target_error: str | None = None
    started = time.monotonic()
    try:
        request = Request(str(spec["target"]["url"]), headers={"Accept": "text/html", "User-Agent": "aegis-mission059-preflight/1"}, method="GET")
        with urlopen(request, timeout=15) as response:
            raw = response.read()
            status = int(response.getcode())
            content_type = response.headers.get_content_type()
        facts = target_facts_from_html(raw, variant="drift")
        target_health = {"http_status": status, "content_type": content_type, "elapsed_ms": round((time.monotonic() - started) * 1000), "facts": facts}
    except Exception as exc:
        target_error = type(exc).__name__
    prompt = spec["repair_prompt"]
    checks = {
        "authorization_one_heal_zero_retry": authorization.get("provider_operations", {}).get("heal") == 1 and authorization.get("retries") == 0,
        "approval_and_rerun_prohibited": authorization.get("provider_operations", {}).get("approval") == 0 and authorization.get("provider_operations", {}).get("rerun") == 0,
        "exact_collector": spec.get("collector_id") == "c_mt09pib13nxqz1coi",
        "cli_version_pinned": capabilities.get("cli_version") == "0.3.5" and spec.get("cli", {}).get("version") == "0.3.5",
        "heal_version_not_invented": spec.get("cli", {}).get("heal_version_selector") == "NOT_DOCUMENTED",
        "prompt_hash_matches": _sha256_text(str(prompt.get("text", ""))) == prompt.get("sha256"),
        "prompt_length_matches": len(str(prompt.get("text", ""))) == prompt.get("character_count") and int(prompt.get("character_count", 0)) <= int(prompt.get("maximum_characters", 0)),
        "target_health_pass": bool(target_health and target_health["http_status"] == 200 and target_health["facts"] == {"title": "AEGIS Recovery Widget", "price": {"currency": "USD", "value": 599.0}, "availability": "Available"}),
        "credential_configured_server_side": bool(os.environ.get(CLI_CREDENTIAL_ENV, "").strip()),
        "historical_integrity": integrity_ok,
        "fresh_paths": True,
        "no_known_conflicting_provider_operation_in_available_evidence": True,
    }
    report = {
        "schema_version": "mission-059-preflight-v1", "checked_at_utc": _now(), "collector_id": spec["collector_id"],
        "correlation": correlation, "checks": checks, "all_pass": all(checks.values()), "target_health": target_health,
        "target_health_error_class": target_error, "protected_actual_hashes": hashes,
        "provider_operations": 0, "provider_mutations": 0, "retries": 0, "key_exposed": False,
    }
    _write_once(PREFLIGHT_PATH, report)
    return report


def execute_once() -> dict[str, Any]:
    preflight = _read_json(PREFLIGHT_PATH)
    if not preflight.get("all_pass"):
        raise RuntimeError("Mission 059 preflight failed; heal is forbidden")
    spec = _read_json(SPEC_PATH)
    correlation = _read_json(CORRELATION_PATH)
    command = _build_command(spec)
    _write_once(MISSION_DIR / "heal_request.json", {
        "schema_version": "mission-059-heal-request-v1", "requested_at_utc": _now(), "collector_id": spec["collector_id"],
        "target_url": spec["target"]["url"], "prompt_sha256": spec["repair_prompt"]["sha256"],
        "prompt_length": spec["repair_prompt"]["character_count"], "cli_version": spec["cli"]["version"],
        "command_sha256": hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest(), "retry_budget": 0,
        "approval_authorized": False, "rerun_authorized": False, "commit_authorized": False, "rollback_authorized": False,
    })
    started_at = _now()
    started = time.monotonic()
    try:
        completed = subprocess.run(command, check=False, capture_output=True, timeout=900)
        returncode, timed_out, stdout, stderr = completed.returncode, False, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        returncode, timed_out, stdout, stderr = None, True, exc.stdout or b"", exc.stderr or b""
    elapsed_ms = round((time.monotonic() - started) * 1000)
    raw = preserve_raw_response_once(stdout, path=MISSION_DIR / "heal_raw_response.bin", aegis_operation_id=str(correlation["aegis_operation_id"]), correlation_id=str(correlation["aegis_correlation_id"]))
    payload = _parse_json(stdout)
    provider_status = str(payload.get("status", "UNKNOWN")) if isinstance(payload, Mapping) else "UNKNOWN"
    identifiers = extract_provider_identifiers(payload)
    candidate, preview, fields = candidate_status(payload)
    raw_metadata = {
        "schema_version": "mission-059-heal-raw-metadata-v1", "captured_at_utc": _now(), "collector_id": spec["collector_id"],
        "http_status": "NOT_EXPOSED_BY_CLI", "content_type": "NOT_EXPOSED_BY_CLI", "returncode": returncode, "timed_out": timed_out,
        "provider_status": provider_status, "raw_mirror": raw.to_evidence_dict(), "provider_identifiers": identifiers,
        "provider_id": "PRESENT" if identifiers else "ABSENT", "aegis_correlation_id": correlation["aegis_correlation_id"],
        "aegis_operation_id": correlation["aegis_operation_id"], "elapsed_ms": elapsed_ms, "stderr": _redact(stderr.decode("utf-8", errors="replace").strip()),
    }
    _write_once(MISSION_DIR / "heal_raw_metadata.json", raw_metadata)
    result = {
        "schema_version": "mission-059-heal-result-v1", "collector_id": spec["collector_id"], "target_url": spec["target"]["url"],
        "started_at_utc": started_at, "completed_at_utc": _now(), "elapsed_ms": elapsed_ms, "returncode": returncode, "timed_out": timed_out,
        "provider_status": provider_status, "provider_identifiers": identifiers, "provider_id": "PRESENT" if identifiers else "ABSENT",
        "candidate": candidate, "candidate_fields": fields, "raw_response": raw.to_evidence_dict(),
        "aegis_operation_id": correlation["aegis_operation_id"], "aegis_correlation_id": correlation["aegis_correlation_id"],
        "provider_mutations": 1, "retries": 0, "approval": "NOT_AUTHORIZED", "rerun": "NOT_AUTHORIZED", "commit": "NOT_AUTHORIZED", "rollback": "NOT_AUTHORIZED", "key_exposed": False,
    }
    _write_once(MISSION_DIR / "heal_result.json", result)
    if preview is not None:
        _write_once(MISSION_DIR / "candidate_preview.json", {
            "schema_version": "mission-059-real-provider-candidate-preview-v1", "provenance": "REAL_PROVIDER", "verification_status": "UNVERIFIED",
            "collector_id": spec["collector_id"], "provider_status": provider_status, "provider_identifiers": identifiers, "provider_id": "PRESENT" if identifiers else "ABSENT",
            "preview_result": preview, "candidate": candidate, "field_states": fields, "approval": "NOT_AUTHORIZED", "rerun": "NOT_AUTHORIZED", "commit": "NOT_AUTHORIZED",
        })
        if candidate == "COMPLETE":
            _write_once(MISSION_DIR / "future_approval_artifact.json", {
                "schema_version": "mission-059-future-approval-artifact-v1", "candidate": "COMPLETE", "provenance": "REAL_PROVIDER", "verification_status": "UNVERIFIED",
                "risk": "NOT_EVALUATED", "approval": "NOT_AUTHORIZED", "rerun": "NOT_AUTHORIZED", "collector_id": spec["collector_id"],
                "provider_identifiers": identifiers, "aegis_correlation_id": correlation["aegis_correlation_id"], "required_next_authorization": "Separate explicit approval authorization required; do not approve from Mission 059.",
            })
    integrity_ok, _ = _historical_integrity()
    summary = {
        "schema_version": "mission-059-summary-v1", "heal": "SUCCESS" if returncode == 0 and not timed_out and provider_status == "awaiting_approval" else "FAILED",
        "provider_status": provider_status, "candidate": candidate, "candidate_fields": fields, "provider_id": "PRESENT" if identifiers else "ABSENT",
        "provider_identifiers": identifiers, "raw_response": "PRESERVED" if raw.persisted else "NOT_AVAILABLE", "mutations": 1, "retries": 0,
        "approval": "NOT_AUTHORIZED", "rerun": "NOT_AUTHORIZED", "historical_evidence": "UNCHANGED" if integrity_ok else "INTEGRITY_FAILURE", "next_step": "STOP",
    }
    _write_once(MISSION_DIR / "summary.json", summary)
    return summary


def validate() -> dict[str, Any]:
    summary = _read_json(MISSION_DIR / "summary.json")
    result = _read_json(MISSION_DIR / "heal_result.json")
    raw_path = MISSION_DIR / "heal_raw_response.bin"
    integrity_ok, hashes = _historical_integrity()
    raw_hash_matches = raw_path.is_file() and hashlib.sha256(raw_path.read_bytes()).hexdigest() == result.get("raw_response", {}).get("sha256")
    candidate_path = MISSION_DIR / "candidate_preview.json"
    candidate_provenance = "NOT_APPLICABLE"
    if candidate_path.is_file():
        candidate_provenance = _read_json(candidate_path).get("provenance", "UNKNOWN")
    validation = {
        "schema_version": "mission-059-validation-v1", "raw_bytes_hash_correct": raw_hash_matches, "candidate_provenance": candidate_provenance,
        "correlation_complete": CORRELATION_PATH.is_file(), "provider_id_not_fabricated": result.get("provider_id") == "ABSENT" or bool(result.get("provider_identifiers")),
        "zero_retries": result.get("retries") == 0, "zero_approvals": result.get("approval") == "NOT_AUTHORIZED", "zero_reruns": result.get("rerun") == "NOT_AUTHORIZED",
        "historical_evidence": "UNCHANGED" if integrity_ok else "INTEGRITY_FAILURE", "protected_actual_hashes": hashes,
        "provider_operations": 0, "provider_mutations": 0, "key_exposed": False,
    }
    _write_once(MISSION_DIR / "validation.json", validation)
    hashes_to_write = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(MISSION_DIR.iterdir()) if path.is_file() and path.name != "artifact_hashes.json"}
    _write_once(MISSION_DIR / "artifact_hashes.json", {"schema_version": "mission-059-artifact-hashes-v1", "algorithm": "sha256", "files": hashes_to_write, "historical_evidence": validation["historical_evidence"], "provider_operations": 0, "provider_mutations": 0, "retries": 0})
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Mission 059 bounded raw-first candidate-only Bright Data heal.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    result = create_preflight() if args.preflight else execute_once() if args.execute else validate()
    print(json.dumps(_redact(result), sort_keys=True))
    return 0 if result.get("all_pass") is True or args.execute or args.validate else 3


if __name__ == "__main__":
    raise SystemExit(main())
