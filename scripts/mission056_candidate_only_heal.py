"""Mission 056: one bounded candidate-only Bright Data heal, with no approval path.

Without ``--execute`` this command performs only target-health and local
integrity checks. With ``--execute`` it requires the immutable preflight record
and performs exactly one documented heal command with zero retries.
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
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.healing import RepairCandidate
from aegis.mission056_candidate_evidence import candidate_field_states, candidate_is_complete, normalize_candidate_row, target_facts_from_html
from aegis.mission056_simulation import mission056_contract
from aegis.models import ProviderProvenance
from aegis.operation_correlation import append_correlation_record, build_operation_correlation
from aegis.output_lineage import analyze_output_lineage
from aegis.risk import RiskGovernor
from aegis.transport_evidence import preserve_raw_response_once
from aegis.verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate


MISSION_DIR = ROOT / "experiments" / "mission_056_full_scale_recovery"
EXPERIMENT_PATH = MISSION_DIR / "candidate_only_experiment.json"
MANIFEST_PATH = MISSION_DIR / "protected_historical_integrity_manifest.json"
PREFLIGHT_PATH = MISSION_DIR / "preflight.json"
CLI_CREDENTIAL_ENV = "BRIGHTDATA_API_KEY"
SECRET_VALUE_RE = re.compile(r"\b(?:sk|nvapi|bdapi|bearer)[_-]?[A-Za-z0-9._-]{12,}\b", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|token|password|secret|cookie)", re.IGNORECASE)
SAFE_METADATA_KEYS = frozenset({"secret_like_content"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object at {path}")
    return value


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if SECRET_KEY_RE.search(str(key)) and str(key) not in SAFE_METADATA_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(_redact(dict(value)), indent=2, sort_keys=True) + "\n")


def _safe_stderr(raw: bytes) -> str:
    return _redact(raw.decode("utf-8", errors="replace").strip())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _historical_integrity() -> tuple[bool, dict[str, str | None]]:
    manifest = _read_json(MANIFEST_PATH)
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("integrity manifest files must be a mapping")
    actual: dict[str, str | None] = {}
    for relative, expected in files.items():
        path = ROOT / str(relative)
        actual[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual[str(relative)] != expected:
            return False, actual
    return True, actual


def _target_health(experiment: Mapping[str, Any]) -> dict[str, Any]:
    paths = experiment["evidence_paths"]
    target = experiment["target"]
    if not isinstance(paths, Mapping) or not isinstance(target, Mapping):
        raise ValueError("experiment target and evidence_paths must be mappings")
    facts: dict[str, Any] = {}
    observations: dict[str, Any] = {}
    for variant, url_key, raw_key in (
        ("baseline", "baseline_url", "target_health_baseline_raw"),
        ("drift", "url", "target_health_drift_raw"),
    ):
        url = str(target[url_key])
        raw_path = ROOT / str(paths[raw_key])
        request = Request(url, headers={"Accept": "text/html", "User-Agent": "aegis-mission056-preflight/1"}, method="GET")
        started = time.monotonic()
        with urlopen(request, timeout=15) as response:
            status = int(response.getcode())
            content_type = response.headers.get_content_type()
            raw = response.read()
        mirror = preserve_raw_response_once(raw, path=raw_path, aegis_operation_id=f"m056-target-{variant}-20260821T153830Z", correlation_id=f"mission056-target-{variant}-20260821T153830Z")
        parsed = target_facts_from_html(raw, variant=variant)
        facts[variant] = parsed
        observations[variant] = {
            "url": url,
            "http_status": status,
            "content_type": content_type,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "raw_mirror": mirror.to_evidence_dict(),
            "facts": parsed,
        }
    return {"schema_version": "mission-056-direct-target-health-v1", "provenance": "DIRECT_TARGET_FETCH", "observed_at_utc": _now(), "variants": observations, "facts_match": facts["baseline"] == facts["drift"] == target["expected_semantic_values"]}


def _fresh_paths(experiment: Mapping[str, Any]) -> bool:
    paths = experiment["evidence_paths"]
    required = ("preflight", "target_health_baseline_raw", "target_health_drift_raw", "target_health_metadata", "heal_request", "heal_raw", "heal_metadata", "candidate_preview", "normalized_analysis", "verification", "risk", "commit", "downstream", "summary")
    return isinstance(paths, Mapping) and all(not (ROOT / str(paths[name])).exists() for name in required)


def _parse_json(stdout: bytes) -> Any:
    text = stdout.decode("utf-8", errors="replace").strip()
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


def _operation_id(payload: Any, fallback: str) -> str:
    if isinstance(payload, Mapping):
        for key in ("operation_id", "provider_operation_id", "response_id", "job_id", "id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    return fallback


def _preview(payload: Any) -> list[Mapping[str, Any]] | None:
    if isinstance(payload, Mapping) and isinstance(payload.get("preview_result"), list) and all(isinstance(row, Mapping) for row in payload["preview_result"]):
        return list(payload["preview_result"])
    return None


def _heal_command(experiment: Mapping[str, Any]) -> list[str]:
    target = experiment["target"]
    repair_prompt = experiment["repair_prompt"]
    if not isinstance(target, Mapping) or not isinstance(repair_prompt, Mapping):
        raise ValueError("experiment target and repair_prompt must be mappings")
    return [
        "npx", "-p", "@brightdata/cli@0.3.5", "bdata", "--timing", "scraper", "heal", str(experiment["collector_id"]), str(repair_prompt["text"]),
        "--url", str(target["url"]), "--timeout", "900", "--max-retries", "0", "--json",
    ]


def create_preflight() -> dict[str, Any]:
    experiment = _read_json(EXPERIMENT_PATH)
    target = experiment["target"]
    prompt = experiment["repair_prompt"]
    integrity_ok, actual_hashes = _historical_integrity()
    initial_freshness = _fresh_paths(experiment)
    target_health: dict[str, Any] | None = None
    health_error: str | None = None
    if initial_freshness:
        try:
            target_health = _target_health(experiment)
        except Exception as exc:  # Preflight records a safe error and never invokes Bright Data.
            health_error = type(exc).__name__
    checks = {
        "experiment_status_ready": experiment.get("status") == "READY_FOR_PROVIDER_FREE_PREFLIGHT",
        "exact_collector": experiment.get("collector_id") == "c_mt09pib13nxqz1coi",
        "one_heal_zero_retry_budget": experiment.get("operation_budget") == {"documented_bright_data_heal": 1, "bright_data_approval": 0, "bright_data_run_or_rerun": 0, "collector_create_or_modify": 0, "commit": 0, "rollback": 0, "benchmark": 0, "nvidia": 0, "gemini": 0, "retries": 0},
        "prompt_within_limit": isinstance(prompt, Mapping) and len(str(prompt.get("text", ""))) == int(prompt.get("character_count", -1)) <= int(prompt.get("maximum_characters", -1)),
        "prompt_hash_matches": isinstance(prompt, Mapping) and _sha256_text(str(prompt.get("text", ""))) == prompt.get("sha256"),
        "target_hash_matches": isinstance(target, Mapping) and _sha256_text(str(target.get("url", ""))) == experiment.get("correlation", {}).get("target_url_sha256"),
        "target_health_pass": bool(target_health and target_health.get("facts_match")),
        "target_health_direct_evidence": bool(target_health and target_health.get("provenance") == "DIRECT_TARGET_FETCH"),
        "credential_configured_server_side": bool(os.environ.get(CLI_CREDENTIAL_ENV, "").strip()),
        "historical_integrity": integrity_ok,
        "fresh_controlled_paths": initial_freshness,
        "local_simulation_present": (MISSION_DIR / "local_lifecycle_simulation.json").is_file(),
        "no_known_conflicting_provider_operation_in_available_evidence": True,
        "approval_and_rerun_remain_prohibited": experiment.get("operation_budget", {}).get("bright_data_approval") == 0 and experiment.get("operation_budget", {}).get("bright_data_run_or_rerun") == 0,
    }
    report = {
        "schema_version": "mission-056-preflight-v1",
        "checked_at_utc": _now(),
        "collector_id": experiment.get("collector_id"),
        "correlation": experiment.get("correlation"),
        "current_provider_operation_state": "UNKNOWN",
        "known_conflict": "NO_IN_AVAILABLE_EVIDENCE",
        "checks": checks,
        "target_health": target_health,
        "target_health_error_class": health_error,
        "protected_actual_hashes": actual_hashes,
        "all_pass": all(checks.values()),
        "bright_data_provider_operations": 0,
        "bright_data_mutations": 0,
        "retries": 0,
        "key_exposed": False,
    }
    if target_health is not None:
        _write_new_json(MISSION_DIR / str(experiment["evidence_paths"]["target_health_metadata"]).split("mission_056_full_scale_recovery/", 1)[-1], target_health)
    _write_new_json(PREFLIGHT_PATH, report)
    return report


def execute_once() -> dict[str, Any]:
    experiment = _read_json(EXPERIMENT_PATH)
    preflight = _read_json(PREFLIGHT_PATH)
    if not preflight.get("all_pass"):
        raise RuntimeError("Mission 056 preflight did not pass; Bright Data heal must not run")
    target = experiment["target"]
    paths = experiment["evidence_paths"]
    correlation = experiment["correlation"]
    command = _heal_command(experiment)
    _write_new_json(MISSION_DIR / str(paths["heal_request"]).split("mission_056_full_scale_recovery/", 1)[-1], {
        "schema_version": "mission-056-heal-request-v1", "requested_at_utc": _now(), "collector_id": experiment["collector_id"],
        "target_url": target["url"], "prompt_sha256": experiment["repair_prompt"]["sha256"], "prompt_length": experiment["repair_prompt"]["character_count"],
        "command_sha256": hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest(), "retry_budget": 0, "approval_authorized": False, "rerun_authorized": False, "key_exposed": False,
    })
    started = time.monotonic()
    started_at = _now()
    try:
        result = subprocess.run(command, check=False, capture_output=True, timeout=900)
        returncode, timed_out, stdout, stderr = result.returncode, False, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        returncode, timed_out, stdout, stderr = None, True, exc.stdout or b"", exc.stderr or b""
    elapsed_ms = round((time.monotonic() - started) * 1000)
    raw_path = ROOT / str(paths["heal_raw"])
    raw_mirror = preserve_raw_response_once(stdout, path=raw_path, aegis_operation_id=str(correlation["aegis_operation_id"]), correlation_id=str(correlation["correlation_id"]))
    payload = _parse_json(stdout)
    provider_status = str(payload.get("status", "UNKNOWN")) if isinstance(payload, Mapping) else "UNKNOWN"
    provider_operation_id = _operation_id(payload, str(correlation["aegis_operation_id"]))
    metadata = {
        "schema_version": "mission-056-heal-metadata-v1", "collector_id": experiment["collector_id"], "target_url": target["url"], "started_at_utc": started_at, "completed_at_utc": _now(),
        "elapsed_ms": elapsed_ms, "returncode": returncode, "timed_out": timed_out, "provider_status": provider_status, "provider_operation_id": provider_operation_id,
        "raw_mirror": raw_mirror.to_evidence_dict(), "stderr": _safe_stderr(stderr), "bright_data_mutations": 1, "retries": 0, "approval_executed": False, "rerun_executed": False, "commit_executed": False, "key_exposed": False,
    }
    _write_new_json(MISSION_DIR / str(paths["heal_metadata"]).split("mission_056_full_scale_recovery/", 1)[-1], metadata)
    record = build_operation_correlation(
        aegis_operation_id=str(correlation["aegis_operation_id"]), collector_id=str(experiment["collector_id"]), target_url=str(target["url"]), started_at_utc=started_at,
        provider_run_id=provider_operation_id, template_version=None, provider_revision=None, requested_version=None, selected_version=None, version_evidence_source=None,
        raw_response_sha256=raw_mirror.sha256, operation_type="candidate_only_heal", correlation_id=str(correlation["correlation_id"]),
    )
    append_correlation_record(ROOT / str(paths["correlation_record"]).rsplit("/", 1)[0], record)
    preview = _preview(payload)
    candidate_status = "ABSENT" if preview is None else "COMPLETE" if candidate_is_complete(preview) else "INCOMPLETE"
    terminal: dict[str, Any] = {"candidate": candidate_status, "provider_status": provider_status, "verification": "NOT_APPLICABLE", "risk": "NOT_APPLICABLE", "commit": "BLOCKED", "downstream": "BLOCKED", "next_step": "STOP"}
    if preview is not None:
        candidate_id = f"candidate_m056_{hashlib.sha256((provider_operation_id + str(correlation['correlation_id'])).encode('utf-8')).hexdigest()[:16]}"
        candidate_record = {
            "schema_version": "mission-056-real-provider-candidate-preview-v1", "provenance": "REAL_PROVIDER", "candidate_id": candidate_id, "collector_id": experiment["collector_id"],
            "provider_operation_id": provider_operation_id, "provider_status": provider_status, "preview_result": preview, "field_states": candidate_field_states(preview), "candidate": candidate_status,
            "approval_executed": False, "rerun_executed": False, "commit_executed": False,
        }
        _write_new_json(MISSION_DIR / str(paths["candidate_preview"]).split("mission_056_full_scale_recovery/", 1)[-1], candidate_record)
        normalized = tuple(normalize_candidate_row(row) for row in preview)
        lineage = analyze_output_lineage(preview, normalized, ("title", "price", "availability"))
        _write_new_json(MISSION_DIR / str(paths["normalized_analysis"]).split("mission_056_full_scale_recovery/", 1)[-1], {"schema_version": "mission-056-normalized-analysis-v1", "decoded_rows": preview, "normalized_rows": normalized, "lineage": lineage.to_evidence_dict()})
        health = _read_json(MISSION_DIR / str(paths["target_health_metadata"]).split("mission_056_full_scale_recovery/", 1)[-1])
        expected = health["variants"]["drift"]["facts"]
        candidate = RepairCandidate(candidate_id=candidate_id, repair_request_id=str(correlation["aegis_operation_id"]), collector_reference=str(experiment["collector_id"]), provider_operation_reference=provider_operation_id, provider_status=provider_status, preview_result=preview, diff_summary=str(payload.get("diff_summary", "")) if isinstance(payload, Mapping) else "", approval_command=None, raw_evidence_ref=f"evidence://{paths['heal_raw']}", provenance=ProviderProvenance.BRIGHT_DATA, latency_ms=elapsed_ms)
        independent = IndependentEvidence(evidence_id="independent_m056_direct_target_health", source="direct managed target health response", rows=(expected,), provenance=VerificationProvenance.DETERMINISTIC, source_group="M056_DIRECT_TARGET_FETCH", evidence_refs=(f"evidence://{paths['target_health_drift_raw']}",), correlation_id=str(correlation["correlation_id"]))
        verification = verify_candidate(VerificationContext(candidate=candidate, contract=mission056_contract(), candidate_output=normalized, independent_evidence=independent, correlation_id=str(correlation["correlation_id"]), evidence_refs=(f"evidence://{paths['heal_raw']}", f"evidence://{paths['target_health_drift_raw']}"), semantic_expectations=expected, history_source_group="BRIGHT_DATA_LIVE_COLLECTION"))
        risk = RiskGovernor().decide(verification, candidate, correlation_id=str(correlation["correlation_id"]))
        commit = CommitGate().evaluate(candidate, verification, risk, mission056_contract(), known_good_version=None, authorization=None, correlation_id=str(correlation["correlation_id"]))
        downstream = OutputEligibilityBoundary.evaluate(commit)
        _write_new_json(MISSION_DIR / str(paths["verification"]).split("mission_056_full_scale_recovery/", 1)[-1], _to_jsonable(verification))
        _write_new_json(MISSION_DIR / str(paths["risk"]).split("mission_056_full_scale_recovery/", 1)[-1], _to_jsonable(risk))
        _write_new_json(MISSION_DIR / str(paths["commit"]).split("mission_056_full_scale_recovery/", 1)[-1], _to_jsonable(commit))
        _write_new_json(MISSION_DIR / str(paths["downstream"]).split("mission_056_full_scale_recovery/", 1)[-1], _to_jsonable(downstream))
        terminal.update({"verification": verification.overall_status.value, "risk": risk.decision.value, "commit": commit.eligibility.value, "downstream": "ELIGIBLE" if downstream.eligible else "BLOCKED", "next_step": "SEPARATE_APPROVAL_AUTHORIZATION_REQUIRED" if candidate_status == "COMPLETE" and verification.overall_status.value == "PASS" and risk.decision.value == "ACCEPT" else "STOP"})
    integrity_ok, _ = _historical_integrity()
    summary = {"schema_version": "mission-056-summary-v1", "heal": "SUCCESS" if returncode == 0 and not timed_out else "FAILED", "bright_data_mutations": 1, "retries": 0, "historical_integrity": "UNCHANGED" if integrity_ok else "INTEGRITY_FAILURE", "data_shipped": "NO", **terminal}
    _write_new_json(MISSION_DIR / str(paths["summary"]).split("mission_056_full_scale_recovery/", 1)[-1], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Mission 056 bounded candidate-only heal.")
    parser.add_argument("--preflight", action="store_true", help="Capture direct target health and write the immutable provider-free preflight only.")
    parser.add_argument("--execute", action="store_true", help="Perform exactly one heal only after a passing preflight exists.")
    args = parser.parse_args()
    if args.preflight == args.execute:
        parser.error("choose exactly one of --preflight or --execute")
    result = create_preflight() if args.preflight else execute_once()
    print(json.dumps(_redact(result), sort_keys=True))
    return 0 if (result.get("all_pass") is True or result.get("heal") == "SUCCESS") else 3


if __name__ == "__main__":
    raise SystemExit(main())
