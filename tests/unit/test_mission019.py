from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from aegis.baseline_participants import BaselineBConfiguration, BaselineBUnavailable, apply_first_candidate
from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_runner import BaselineBAdapter, BenchmarkRunner
from aegis.mutation_lab import MutationLab, baseline_fixture

ROOT = Path(__file__).resolve().parents[2]
_PREFLIGHT_SPEC = importlib.util.spec_from_file_location("mission016_preflight_smoke_m019", ROOT / "scripts/mission016_preflight_smoke.py")
assert _PREFLIGHT_SPEC is not None and _PREFLIGHT_SPEC.loader is not None
preflight = importlib.util.module_from_spec(_PREFLIGHT_SPEC)
sys.modules[_PREFLIGHT_SPEC.name] = preflight
_PREFLIGHT_SPEC.loader.exec_module(preflight)
CONFIG = load_benchmark_config(ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json")


def _candidate(text: str) -> dict[str, object]:
    return {"content": {"parts": [{"text": text}]}}


def _evidence(response: dict[str, object] | None, *, caller_enabled: bool = True):
    spec = next(item for item in CONFIG.baselines if item.baseline_id == "BASELINE_B")
    calls: list[tuple[str, str]] = []

    def caller(system_prompt: str, repair_prompt: str):
        calls.append((system_prompt, repair_prompt))
        return response or {}

    adapter = BaselineBAdapter(spec, MutationLab(), model_caller=caller if caller_enabled else None)
    adapter._benchmark_config = CONFIG
    input_record = BenchmarkRunner(CONFIG).build_input("BASELINE_B", "M001", 12345)
    prepared = adapter.prepare(input_record)
    evidence = adapter.run_mutation(prepared)
    return evidence, calls, input_record


def test_candidate_received_selected_and_accepted_are_explicit() -> None:
    response = {"candidates": [_candidate("first candidate"), _candidate("second candidate")]}
    evidence, calls, input_record = _evidence(response)
    assert len(calls) == 1
    assert evidence.candidate_received is True
    assert evidence.candidate_selected is True
    assert evidence.candidate_accepted is True
    assert evidence.failure_state == "COMPLETED"
    assert evidence.output_eligible is True
    assert evidence.verification_status == "NOT_APPLICABLE"
    assert evidence.risk_decision == "NOT_APPLICABLE"
    assert evidence.llm_calls == 1
    assert evidence.provenance == "MODEL_ASSISTED"
    assert evidence.to_dict()["candidate"] == _candidate("first candidate")
    assert evidence.candidate_application["application_mode"] == "SAFE_TEST_DOUBLE_BOUNDARY"
    assert evidence.candidate_application["generated_code_executed"] is False
    assert evidence.candidate_application["aegis_verification_invoked"] is False
    assert evidence.candidate_application["risk_governor_invoked"] is False
    assert evidence.candidate_application["commit_gate_invoked"] is False
    assert input_record.trial_metadata["ground_truth_runtime_payload"] == "NOT_PROVIDED"
    assert any(ref.endswith("#candidate-accepted") for ref in evidence.evidence_refs)


def test_multiple_candidates_accept_only_the_first() -> None:
    evidence, _, _ = _evidence({"candidates": [_candidate("first"), _candidate("second")]})
    assert evidence.to_dict()["candidate"] == _candidate("first")
    assert evidence.candidate_application["candidate_index"] == 0
    assert evidence.candidate_application["candidate_count_seen"] == 2
    assert evidence.candidate_accepted is True


def test_candidate_missing_remains_failed_and_ineligible() -> None:
    evidence, _, _ = _evidence({"candidates": []})
    assert evidence.candidate_received is False
    assert evidence.candidate_selected is False
    assert evidence.candidate_accepted is False
    assert evidence.failure_state == "MODEL_CANDIDATE_NOT_RECEIVED"
    assert evidence.output_eligible is False
    assert evidence.llm_calls == 1


def test_model_unavailable_remains_honest_and_unavailable() -> None:
    evidence, calls, _ = _evidence(None, caller_enabled=False)
    assert calls == []
    assert evidence.failure_state == "MODEL_CALL_NOT_EXECUTED_IN_VALIDATION_ONLY_MISSION"
    assert evidence.output_eligible == "NOT_APPLICABLE"
    assert evidence.candidate_received is False
    assert evidence.candidate_selected is False
    assert evidence.candidate_accepted is False
    assert evidence.llm_calls == 0
    assert evidence.candidate == "NOT_APPLICABLE"
    assert isinstance(BaselineBUnavailable("gemini-3.6-flash", "stable"), BaselineBUnavailable)


def test_safe_application_does_not_execute_candidate_text() -> None:
    malicious_text = '__import__("os").system("touch SHOULD_NOT_EXIST")'
    result = apply_first_candidate(BaselineBConfiguration(), {"candidate": malicious_text}, baseline_fixture())
    assert result.candidate_received is True
    assert result.candidate_selected is True
    assert result.candidate_accepted is True
    assert result.application is not None
    assert result.application["generated_code_executed"] is False
    assert not (ROOT / "SHOULD_NOT_EXIST").exists()


def test_smoke_passes_with_deterministic_injected_model_response(monkeypatch) -> None:
    class FakeGemini:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def list_models(self):
            return ("models/gemini-3.6-flash",)

        def __call__(self, system_prompt: str, repair_prompt: str):
            return {"candidates": [_candidate("deterministic smoke candidate"), _candidate("ignored second candidate")]}

    monkeypatch.setenv("GEMINI_API_KEY", "test-double-key")
    monkeypatch.setattr(preflight, "GeminiApiCaller", FakeGemini)
    smoke = preflight.run_baseline_b_smoke(CONFIG)
    assert smoke["status"] == "PASS"
    assert smoke["checks"]["first_candidate_policy_executable"] is True
    assert smoke["checks"]["candidate_received"] is True
    assert smoke["checks"]["candidate_selected"] is True
    assert smoke["checks"]["candidate_accepted"] is True
    assert smoke["checks"]["candidate_present_in_raw_evidence"] is True
    assert smoke["checks"]["candidate_application_bounded"] is True
    assert smoke["adapter_evidence"]["output_eligible"] is True
    assert smoke["adapter_evidence"]["failure_state"] == "COMPLETED"
    assert smoke["runtime_ground_truth_payload"] == "NOT_PROVIDED"
