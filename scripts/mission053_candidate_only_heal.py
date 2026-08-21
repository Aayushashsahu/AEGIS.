"""Execute one explicitly authorized Bright Data heal and stop at the candidate.

The command is unavailable unless ``--execute`` is passed after preflight. It
has no approval, rerun, commit, rollback, or retry capability. Provider output
is captured before normalization only when it contains no credential-like text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
MISSION_DIR = ROOT / "experiments" / "mission_053_candidate_only"
AUTHORIZATION_PATH = MISSION_DIR / "authorization.json"
MISSION052_DIR = ROOT / "experiments" / "mission_052"
TARGET_CONTRACT_PATH = ROOT / "experiments" / "mission_033_live_bright_data_success" / "target_contract.json"
PROMPT_PATH = MISSION052_DIR / "repair_prompt.txt"
FUTURE_PACKAGE_PATH = MISSION052_DIR / "future_bounded_experiment.json"
RAW_PATH = MISSION_DIR / "raw_provider_response.bin"
CLI_CREDENTIAL_ENV = "BRIGHTDATA_API_KEY"
COLLECTOR_ID = "c_mt09pib13nxqz1coi"
REQUIRED_FIELDS = ("title", "price", "availability")
SECRET_VALUE_RE = re.compile(r"\b(?:sk|nvapi|bdapi|bearer)[_-]?[A-Za-z0-9._-]{12,}\b", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|token|password|secret|cookie)", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): "[REDACTED]" if SECRET_KEY_RE.search(str(key)) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(_redact(dict(value)), indent=2, sort_keys=True) + "\n")


def _historical_evidence_intact() -> bool:
    required = (
        ROOT / "experiments" / "mission_033_live_bright_data_success" / "candidate_preview.json",
        ROOT / "experiments" / "mission_033_live_bright_data_success" / "approval.json",
        ROOT / "experiments" / "mission_041_post_heal_rerun" / "summary.json",
        ROOT / "experiments" / "mission_041_post_heal_rerun" / "post_heal_output.json",
        ROOT / "experiments" / "mission_048c_evidence_preserving_rerun" / "summary.json",
    )
    return all(path.is_file() for path in required)


def _fresh_paths_available() -> bool:
    return not any((MISSION_DIR / name).exists() for name in ("preflight.json", "heal_request.json", "heal_result.json", "candidate_preview.json", "summary.json", "artifact_hashes.json", RAW_PATH.name))


def _target_url() -> str:
    return str(_read_json(TARGET_CONTRACT_PATH)["target_url"])


def _prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_command(*, collector_id: str, target_url: str, prompt: str) -> list[str]:
    if collector_id != COLLECTOR_ID:
        raise ValueError("Mission 053 only allows the exact authorized collector")
    if len(prompt) > 1000:
        raise ValueError("Mission 053 prompt exceeds documented limit")
    command = [
        "npx", "-p", "@brightdata/cli", "bdata", "--timing", "scraper", "heal", collector_id, prompt,
        "--url", target_url, "--timeout", "900", "--max-retries", "0", "--json",
    ]
    if "--auto-approve" in command or "approve" in command or "run" in command:
        raise RuntimeError("Mission 053 forbids approval, rerun, and auto-approval")
    return command


def preflight() -> dict[str, Any]:
    """Evaluate all conditions without contacting Bright Data."""

    authorization = _read_json(AUTHORIZATION_PATH)
    package = _read_json(FUTURE_PACKAGE_PATH)
    prompt = _prompt()
    target_url = _target_url()
    checks = {
        "exact_collector": authorization.get("collector_id") == COLLECTOR_ID and package.get("collector") == COLLECTOR_ID,
        "exact_canonical_target": package.get("target") == target_url,
        "prompt_present": PROMPT_PATH.is_file(),
        "prompt_length": len(prompt) == int(authorization.get("prompt_expected_characters", -1)) == 368,
        "prompt_matches_prepared_artifact": _prompt_hash(prompt) == hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
        "authenticated_transport_configured": bool(os.environ.get(CLI_CREDENTIAL_ENV, "").strip()),
        "authorized_one_heal_budget": authorization.get("authorized_provider_operations") == {"heal": 1},
        "zero_retry_budget": authorization.get("retry_budget") == 0,
        "approval_and_rerun_prohibited": isinstance(authorization.get("prohibited_provider_operations"), Mapping) and authorization["prohibited_provider_operations"].get("approval") == 0 and authorization["prohibited_provider_operations"].get("rerun") == 0,
        "historical_evidence_intact": _historical_evidence_intact(),
        "fresh_controlled_paths": _fresh_paths_available(),
        "raw_capture_armed": True,
    }
    return {
        "schema_version": "mission-053-preflight-v1",
        "checked_at_utc": _now(),
        "collector_id": COLLECTOR_ID,
        "target_url": target_url,
        "prompt_sha256": _prompt_hash(prompt),
        "prompt_length": len(prompt),
        "checks": checks,
        "all_pass": all(checks.values()),
        "provider_requests_attempted": 0,
        "provider_mutations_attempted": 0,
        "retries": 0,
        "key_exposed": False,
    }


def _parse_json(stdout: bytes) -> Any:
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
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


def _provider_id(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    for key in ("operation_id", "response_id", "job_id", "id", "request_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _field_state(row: Mapping[str, Any], field: str) -> str:
    if field not in row:
        return "MISSING"
    value = row[field]
    if value is None:
        return "NULL"
    if isinstance(value, str) and not value.strip():
        return "EMPTY"
    return "PRESENT"


def _preview(payload: Any) -> list[Mapping[str, Any]] | None:
    if not isinstance(payload, Mapping):
        return None
    value = payload.get("preview_result")
    if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
        return list(value)
    return None


def _preserve_raw(raw: bytes) -> dict[str, Any]:
    sha256 = hashlib.sha256(raw).hexdigest()
    secret_like = bool(SECRET_VALUE_RE.search(raw.decode("utf-8", errors="ignore")))
    if raw and not secret_like:
        with RAW_PATH.open("xb") as handle:
            handle.write(raw)
        return {"preserved": True, "path": RAW_PATH.name, "sha256": sha256, "bytes": len(raw), "secret_like_content": False}
    return {"preserved": False, "sha256": sha256, "bytes": len(raw), "secret_like_content": secret_like, "reason": "empty_or_not_safe_to_persist"}


def execute_once() -> dict[str, Any]:
    report = preflight()
    _write_new_json(MISSION_DIR / "preflight.json", report)
    if not report["all_pass"]:
        summary = {"schema_version": "mission-053-summary-v1", "collector_id": COLLECTOR_ID, "heal": "NOT_ATTEMPTED", "reason": "PREFLIGHT_FAILED", "provider_mutations": 0, "retries": 0}
        _write_new_json(MISSION_DIR / "summary.json", summary)
        return summary

    prompt = _prompt()
    command = build_command(collector_id=COLLECTOR_ID, target_url=str(report["target_url"]), prompt=prompt)
    _write_new_json(MISSION_DIR / "heal_request.json", {
        "schema_version": "mission-053-heal-request-v1", "requested_at_utc": _now(), "collector_id": COLLECTOR_ID,
        "target_url": report["target_url"], "prompt_sha256": _prompt_hash(prompt), "prompt_length": len(prompt),
        "command_sha256": hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest(), "retry_budget": 0,
        "auto_approval_used": False, "approval_authorized": False, "rerun_authorized": False, "key_exposed": False,
    })
    started = time.monotonic()
    started_at = _now()
    try:
        completed = subprocess.run(command, check=False, capture_output=True, timeout=900)
        returncode, timed_out, stdout, stderr = completed.returncode, False, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        returncode, timed_out, stdout, stderr = None, True, exc.stdout or b"", exc.stderr or b""
    elapsed_ms = round((time.monotonic() - started) * 1000)
    raw = _preserve_raw(stdout)
    payload = _parse_json(stdout)
    status = payload.get("status") if isinstance(payload, Mapping) else None
    preview = _preview(payload)
    result = {
        "schema_version": "mission-053-heal-result-v1", "collector_id": COLLECTOR_ID, "target_url": report["target_url"],
        "started_at_utc": started_at, "completed_at_utc": _now(), "elapsed_ms": elapsed_ms, "returncode": returncode,
        "timed_out": timed_out, "http_status": "NOT_EXPOSED_BY_CLI", "provider_status": status or ("TIMED_OUT" if timed_out else "UNKNOWN"),
        "provider_operation_id": _provider_id(payload), "raw_provider_response": raw, "payload": payload,
        "stderr": stderr.decode("utf-8", errors="replace").strip(), "provider_mutations": 1, "retries": 0,
        "approval_executed": False, "rerun_executed": False, "commit_executed": False, "key_exposed": False,
    }
    _write_new_json(MISSION_DIR / "heal_result.json", result)
    if preview is not None:
        first = preview[0] if preview else {}
        states = {field: _field_state(first, field) for field in REQUIRED_FIELDS}
        complete = bool(preview) and all(state == "PRESENT" for state in states.values())
        _write_new_json(MISSION_DIR / "candidate_preview.json", {
            "schema_version": "mission-053-real-provider-candidate-preview-v1", "provenance": "REAL_PROVIDER", "verification_status": "UNVERIFIED",
            "collector_id": COLLECTOR_ID, "provider_status": result["provider_status"], "provider_operation_id": result["provider_operation_id"],
            "preview_result": preview, "field_states": states, "candidate": "COMPLETE" if complete else "INCOMPLETE",
            "approval_executed": False, "rerun_executed": False, "commit_executed": False,
        })
    candidate = "ABSENT" if preview is None else ("COMPLETE" if preview and all(_field_state(preview[0], field) == "PRESENT" for field in REQUIRED_FIELDS) else "INCOMPLETE")
    summary = {
        "schema_version": "mission-053-summary-v1", "collector_id": COLLECTOR_ID,
        "heal": "SUCCESS" if returncode == 0 and not timed_out else "FAILED", "provider_status": result["provider_status"],
        "candidate": candidate, "candidate_fields": list(preview[0].keys()) if preview else [], "approval": "NOT_AUTHORIZED", "rerun": "NOT_AUTHORIZED",
        "provider_mutations": 1, "retries": 0, "data_shipped": "NO", "next_step": "STOP_AFTER_CANDIDATE_ONLY",
    }
    _write_new_json(MISSION_DIR / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the one authorized Mission 053 candidate-only Bright Data heal.")
    parser.add_argument("--execute", action="store_true", help="Required explicit opt-in after preflight.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(preflight(), sort_keys=True))
        return 0
    result = execute_once()
    print(json.dumps(_redact(result), sort_keys=True))
    return 0 if result["heal"] == "SUCCESS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
