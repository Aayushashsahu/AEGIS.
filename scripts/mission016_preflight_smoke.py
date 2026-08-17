from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
EXPECTED_CONFIG_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
FLOOR_RUN_ID = "mission_016_floor_59a11e27a71f"
FLOOR_RUN_ROOT = ROOT / "benchmarks/runs" / FLOOR_RUN_ID
HISTORICAL_FLOOR_RUN_ID = "mission_016_floor_f48ec5c5792b"
HISTORICAL_FLOOR_RUN_ROOT = ROOT / "benchmarks/runs" / HISTORICAL_FLOOR_RUN_ID
SMOKE_ROOT = FLOOR_RUN_ROOT / "baseline_b_execution_readiness_smoke"
EXPECTED_SEED = 12345
EXPECTED_MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")
EXPECTED_MODEL = "gemini-3.6-flash"
EXPECTED_REVISIONS = {
    "BASELINE_A": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
    "BASELINE_B": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
    "AEGIS": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
}
SOURCE_FILES = {
    "BASELINE_A": "src/aegis/baseline_participants.py",
    "BASELINE_B": "src/aegis/baseline_participants.py",
    "AEGIS": "src/aegis/benchmark_runner.py",
}
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

sys.path.insert(0, str(ROOT / "src"))

from aegis.baseline_participants import BASELINE_B_MODEL_ID, BASELINE_B_REPAIR_PROMPT_TEMPLATE, BASELINE_B_SYSTEM_PROMPT
from aegis.benchmark_config import load_benchmark_config, validate_config
from aegis.benchmark_runner import BenchmarkRunner, ParticipantRunEvidence, RunnerDryRunStatus
from aegis.mutation_lab import MutationLab, baseline_fixture


class GeminiApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightResult:
    passed: bool
    checks: Mapping[str, Any]
    errors: tuple[str, ...]

    def to_dict(self) -> Mapping[str, Any]:
        return {"passed": self.passed, "checks": self.checks, "errors": self.errors}


class GeminiApiCaller:
    """Minimal official Gemini Developer API caller using the approved model only."""

    def __init__(self, api_key: str, *, model_id: str = EXPECTED_MODEL, timeout_seconds: int = 300) -> None:
        self._api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        query = urlencode({"key": self._api_key})
        url = f"{GEMINI_BASE_URL}{path}?{query}"
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise GeminiApiError(f"Gemini API HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise GeminiApiError(f"Gemini API transport failure: {exc.reason}") from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise GeminiApiError("Gemini API returned non-JSON content") from exc
        if not isinstance(parsed, Mapping):
            raise GeminiApiError("Gemini API returned a non-object response")
        return parsed

    def list_models(self) -> tuple[str, ...]:
        payload = self._request("GET", "/models")
        models = payload.get("models", ())
        names = []
        if isinstance(models, list):
            for item in models:
                if isinstance(item, Mapping) and isinstance(item.get("name"), str):
                    names.append(item["name"])
        return tuple(sorted(names))

    def __call__(self, system_prompt: str, repair_prompt: str) -> Mapping[str, Any]:
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": repair_prompt}]}],
            "generationConfig": {"maxOutputTokens": 8192},
        }
        return self._request("POST", f"/models/{self.model_id}:generateContent", payload)


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _revision_matches(revision: str, path: str) -> bool:
    result = subprocess.run(["git", "diff", "--quiet", revision, "--", path], cwd=ROOT)
    return result.returncode == 0


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _serialize(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def run_preflight() -> tuple[PreflightResult, Any]:
    config = load_benchmark_config(CONFIG_PATH)
    validation = validate_config(config)
    runner = BenchmarkRunner(config)
    dry_run = runner.dry_run() if validation.valid else None
    lab = MutationLab()
    shared = [runner.build_input(participant, "M001", EXPECTED_SEED).shared_metadata() for participant in ("BASELINE_A", "BASELINE_B", "AEGIS")]
    checks: dict[str, Any] = {
        "configuration_hash": {"expected": EXPECTED_CONFIG_HASH, "actual": config.configuration_hash, "pass": config.configuration_hash == EXPECTED_CONFIG_HASH},
        "configuration_validation": {"status": validation.status.value, "pass": validation.valid, "errors": validation.errors},
        "code_revision": {
            "current_commit": _git("rev-parse", "HEAD"),
            "participants": {
                participant: {
                    "expected_revision": EXPECTED_REVISIONS[participant],
                    "source_file": SOURCE_FILES[participant],
                    "pass": _revision_matches(EXPECTED_REVISIONS[participant], SOURCE_FILES[participant]),
                }
                for participant in EXPECTED_REVISIONS
            },
        },
        "fixture_version": {"expected": "1", "actual": config.fixture_version, "pass": config.fixture_id == "gpu-price-staging" and config.fixture_version == "1"},
        "mutation_set": {"expected": EXPECTED_MUTATIONS, "actual": config.mutation_class_ids, "pass": tuple(config.mutation_class_ids) == EXPECTED_MUTATIONS},
        "seed": {"expected": EXPECTED_SEED, "actual": config.seeds, "pass": tuple(config.seeds) == (EXPECTED_SEED,)},
        "participants_ready": {
            "pass": bool(dry_run) and all(report.ready for report in dry_run.participant_readiness.values()),
            "reports": {} if dry_run is None else {key: _serialize(value) for key, value in dry_run.participant_readiness.items()},
        },
        "fairness": {
            "pass": shared[0] == shared[1] == shared[2] and all(item["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED" for item in shared),
            "shared_metadata": shared[0],
        },
        "metric_formula_version": {"expected": "mission-010-metrics-v1", "actual": config.metric_formula_version, "pass": config.metric_formula_version == "mission-010-metrics-v1"},
        "artifact_paths": {
            "pass": all((ROOT / path).is_dir() for path in ("benchmarks/configs", "benchmarks/manifests", "benchmarks/runs", "benchmarks/results", "benchmarks/reports")),
            "paths": [str(ROOT / path) for path in ("benchmarks/configs", "benchmarks/manifests", "benchmarks/runs", "benchmarks/results", "benchmarks/reports")],
            "floor_run_absent": not FLOOR_RUN_ROOT.exists(),
            "corrected_floor_run_id": FLOOR_RUN_ID,
            "historical_floor_run_id": HISTORICAL_FLOOR_RUN_ID,
            "historical_floor_run_preserved": HISTORICAL_FLOOR_RUN_ROOT.is_dir(),
        },
        "clean_fixture_state": {"pass": lab.fixture == baseline_fixture(), "provenance": "TEST_DOUBLE_IMMUTABLE_FIXTURE"},
        "dry_run": {"status": None if dry_run is None else dry_run.status.value, "pass": bool(dry_run) and dry_run.status is RunnerDryRunStatus.READY_TO_EXECUTE},
    }
    errors = []
    for name, check in checks.items():
        if name == "code_revision":
            if not all(item["pass"] for item in check["participants"].values()):
                errors.append("participant source revision drift detected")
        elif name == "participants_ready":
            if not check["pass"]:
                errors.append("not all participants are READY")
        elif name == "fairness":
            if not check["pass"]:
                errors.append("fairness validation failed")
        elif name == "artifact_paths":
            if not check["pass"] or not check["floor_run_absent"]:
                errors.append("artifact path validation failed or corrected floor run already exists")
            if not check["historical_floor_run_preserved"]:
                errors.append("historical Mission 016 floor run is missing")
        elif not check.get("pass", False):
            errors.append(f"preflight check failed: {name}")
    return PreflightResult(not errors, checks, tuple(errors)), config


def _candidate_text(response: Mapping[str, Any]) -> str:
    candidates = response.get("candidates", ())
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, Mapping):
        return ""
    content = first.get("content", {})
    if not isinstance(content, Mapping):
        return ""
    parts = content.get("parts", ())
    if not isinstance(parts, list):
        return ""
    return "\n".join(str(part["text"]) for part in parts if isinstance(part, Mapping) and isinstance(part.get("text"), str))


def run_baseline_b_smoke(config: Any) -> Mapping[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    checks: dict[str, Any] = {
        "api_key_available": bool(api_key),
        "configured_model": {"expected": EXPECTED_MODEL, "actual": BASELINE_B_MODEL_ID, "pass": BASELINE_B_MODEL_ID == EXPECTED_MODEL},
        "exact_system_prompt_loaded": BASELINE_B_SYSTEM_PROMPT == str(config.baselines[1].metadata.get("system_prompt", "")),
        "exact_repair_prompt_loaded": BASELINE_B_REPAIR_PROMPT_TEMPLATE == str(config.baselines[1].metadata.get("repair_prompt_template", "")),
        "tools_disabled": False,
        "aegis_verification_not_invoked": False,
        "risk_governor_not_invoked": False,
        "commit_gate_not_invoked": False,
        "evaluator_ground_truth_runtime_payload": "NOT_PROVIDED",
        "model_reachable": False,
        "model_call_produced_candidate": False,
        "candidate_received": False,
        "candidate_selected": False,
        "candidate_accepted": False,
        "candidate_present_in_raw_evidence": False,
        "candidate_application_bounded": False,
        "first_candidate_policy_executable": False,
        "normalized_participant_evidence": False,
    }
    if not api_key:
        return {"name": "BASELINE_B_EXECUTION_READINESS_SMOKE", "status": "FAIL", "checks": checks, "errors": ["GEMINI_API_KEY is unavailable"]}

    caller = GeminiApiCaller(api_key)
    try:
        models = caller.list_models()
        exact_name = f"models/{EXPECTED_MODEL}"
        checks["model_list_contains_exact_id"] = exact_name in models
        if exact_name not in models:
            return {
                "name": "BASELINE_B_EXECUTION_READINESS_SMOKE",
                "status": "FAIL",
                "checks": checks,
                "errors": [f"approved model {EXPECTED_MODEL} is not listed by the official Gemini API"],
                "listed_model_count": len(models),
                "listed_approved_model_names": [name for name in models if EXPECTED_MODEL in name],
            }

        captured: list[tuple[str, str, Mapping[str, Any]]] = []

        def injected_caller(system_prompt: str, repair_prompt: str) -> Mapping[str, Any]:
            response = caller(system_prompt, repair_prompt)
            captured.append((system_prompt, repair_prompt, response))
            return response

        from aegis.benchmark_runner import BaselineBAdapter

        spec = next(spec for spec in config.baselines if spec.baseline_id == "BASELINE_B")
        adapter = BaselineBAdapter(spec, MutationLab(), model_caller=injected_caller)
        adapter._benchmark_config = config
        input_record = BenchmarkRunner(config).build_input("BASELINE_B", "M001", EXPECTED_SEED)
        prepared = adapter.prepare(input_record)
        evidence: ParticipantRunEvidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
        checks["model_reachable"] = True
        checks["model_call_produced_candidate"] = bool(captured and _candidate_text(captured[0][2]))
        checks["tools_disabled"] = adapter.configuration.tools_enabled is False
        application = evidence.candidate_application if isinstance(evidence.candidate_application, Mapping) else {}
        checks["candidate_received"] = evidence.candidate_received is True
        checks["candidate_selected"] = evidence.candidate_selected is True
        checks["candidate_accepted"] = evidence.candidate_accepted is True
        checks["candidate_present_in_raw_evidence"] = evidence.candidate != "NOT_APPLICABLE"
        checks["candidate_application_bounded"] = application.get("application_mode") == "SAFE_TEST_DOUBLE_BOUNDARY" and application.get("generated_code_executed") is False
        checks["aegis_verification_not_invoked"] = evidence.verification_status == "NOT_APPLICABLE" and application.get("aegis_verification_invoked") is False
        checks["risk_governor_not_invoked"] = evidence.risk_decision == "NOT_APPLICABLE" and application.get("risk_governor_invoked") is False
        checks["commit_gate_not_invoked"] = application.get("commit_gate_invoked") is False
        checks["normalized_participant_evidence"] = evidence.participant_id == "BASELINE_B" and evidence.provenance == "MODEL_ASSISTED" and evidence.llm_calls == 1
        checks["first_candidate_policy_executable"] = evidence.failure_state == "COMPLETED" and evidence.output_eligible is True and evidence.candidate_accepted is True
        prompt_text = "\n".join(item for pair in captured for item in pair[:2])
        checks["no_evaluator_ground_truth_in_prompt"] = "expected_correct_state" not in prompt_text and "expected_corrupted_state" not in prompt_text and "MutationGroundTruth" not in prompt_text
        smoke = {
            "name": "BASELINE_B_EXECUTION_READINESS_SMOKE",
            "status": "PASS" if all(value is True for value in checks.values() if isinstance(value, bool)) else "FAIL",
            "checks": checks,
            "adapter_evidence": _serialize(evidence),
            "captured_prompt_hashes": {
                "system_prompt_sha256": __import__("hashlib").sha256(captured[0][0].encode()).hexdigest() if captured else None,
                "repair_prompt_sha256": __import__("hashlib").sha256(captured[0][1].encode()).hexdigest() if captured else None,
            },
            "model_response": captured[0][2] if captured else None,
            "model_response_text": _candidate_text(captured[0][2]) if captured else "",
            "provider_operation_count": 1,
            "runtime_ground_truth_payload": "NOT_PROVIDED",
            "errors": [],
        }
        if smoke["status"] != "PASS":
            smoke["errors"] = [name for name, value in checks.items() if value is False]
        return smoke
    except GeminiApiError as exc:
        checks["model_reachable"] = False
        return {"name": "BASELINE_B_EXECUTION_READINESS_SMOKE", "status": "FAIL", "checks": checks, "errors": [str(exc)], "provider_operation_count": 1}
    except Exception as exc:
        return {"name": "BASELINE_B_EXECUTION_READINESS_SMOKE", "status": "FAIL", "checks": checks, "errors": [f"smoke adapter failure: {type(exc).__name__}: {exc}"], "provider_operation_count": 1}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_serialize(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    preflight, config = run_preflight()
    FLOOR_RUN_ROOT.mkdir(parents=True, exist_ok=False)
    write_json(FLOOR_RUN_ROOT / "frozen_config.json", config.to_dict())
    write_json(FLOOR_RUN_ROOT / "preflight.json", {"mission": "016", "run_id": FLOOR_RUN_ID, "result": preflight.to_dict(), "current_commit": _git("rev-parse", "HEAD"), "repository_status": _git("status", "--short")})
    if not preflight.passed:
        write_json(FLOOR_RUN_ROOT / "execution_log.json", {"status": "STOPPED_PREFLIGHT", "benchmark_runs_executed": 0, "provider_operations_executed": 0, "healing_operations_executed": 0, "metric_results_generated": 0, "execution_authorized": False, "errors": preflight.errors})
        print(json.dumps({"status": "STOPPED_PREFLIGHT", "errors": preflight.errors}, indent=2))
        return 2
    smoke = run_baseline_b_smoke(config)
    write_json(SMOKE_ROOT / "smoke.json", smoke)
    write_json(SMOKE_ROOT / "execution_log.json", {"status": smoke["status"], "provider_operation_count": smoke.get("provider_operation_count", 0), "benchmark_runs_executed": 0, "healing_operations_executed": 0, "metric_results_generated": 0, "execution_authorized": False})
    if smoke["status"] != "PASS":
        write_json(FLOOR_RUN_ROOT / "execution_log.json", {"status": "STOPPED_BASELINE_B_SMOKE", "benchmark_runs_executed": 0, "provider_operations_executed": smoke.get("provider_operation_count", 0), "healing_operations_executed": 0, "metric_results_generated": 0, "execution_authorized": False, "errors": smoke.get("errors", [])})
        print(json.dumps({"status": "STOPPED_BASELINE_B_SMOKE", "errors": smoke.get("errors", []), "checks": smoke.get("checks", {})}, indent=2))
        return 3
    write_json(FLOOR_RUN_ROOT / "execution_log.json", {
        "status": "BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK",
        "benchmark_runs_executed": 0,
        "provider_operations_executed": smoke.get("provider_operation_count", 0),
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
        "execution_authorized": False,
    })
    print(json.dumps({"status": "BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK", "smoke_status": smoke["status"], "benchmark_runs_executed": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
