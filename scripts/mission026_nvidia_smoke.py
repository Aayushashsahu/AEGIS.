from __future__ import annotations

import json
import sys
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.baseline_participants import (
    BASELINE_B_REPAIR_PROMPT_TEMPLATE,
    BASELINE_B_SYSTEM_PROMPT,
    BaselineBConfiguration,
    apply_first_candidate,
)
from aegis.benchmark_runner import NOT_APPLICABLE, ParticipantRunEvidence
from aegis.mutation_lab import baseline_fixture
from aegis.nvidia_provider import (
    NVIDIA_CANDIDATE_MODEL_ID,
    NVIDIA_CANDIDATE_MODEL_REVISION,
    NVIDIA_PROVIDER,
    NvidiaModelCaller,
    NvidiaProviderError,
    candidate_model_descriptor,
    load_nvidia_api_key,
    prompt_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/mission026_nvidia_smoke.json"


def main() -> int:
    api_key = load_nvidia_api_key()
    base = {
        "mission": "026",
        "provider": NVIDIA_PROVIDER,
        "model_id": NVIDIA_CANDIDATE_MODEL_ID,
        "model_revision": NVIDIA_CANDIDATE_MODEL_REVISION,
        "prompt_hash": prompt_sha256(BASELINE_B_SYSTEM_PROMPT, BASELINE_B_REPAIR_PROMPT_TEMPLATE),
        "tools_enabled": False,
        "runtime_ground_truth": "NOT_PROVIDED",
        "benchmark_runs_executed": 0,
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
        "execution_authorized": False,
    }
    if not api_key:
        payload = {**base, "status": "BLOCKED_NOT_READY", "model_reachable": False, "candidate_policy_executable": False, "provider_operation_count": 0, "error": "NVIDIA API key is not configured"}
        OUTPUT.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 2

    caller = NvidiaModelCaller(candidate_model_descriptor(), api_key=api_key, timeout_seconds=300)
    repair_prompt = BASELINE_B_REPAIR_PROMPT_TEMPLATE.format(
        target="https://example.test/gpu-1",
        extraction_contract="gpu-price-schema-v1",
        observed_output="[{'product_id': 'gpu-1', 'price': 29.99}]",
        failure_description="Mission 026 controlled NVIDIA smoke policy check",
        scraper_source="approved static selector scraper configuration",
    )
    try:
        model_result = caller(BASELINE_B_SYSTEM_PROMPT, repair_prompt, tools_enabled=False, max_output_tokens=8192)
        policy = apply_first_candidate(BaselineBConfiguration(model_id=NVIDIA_CANDIDATE_MODEL_ID, model_revision=NVIDIA_CANDIDATE_MODEL_REVISION), model_result, baseline_fixture())
        evidence = ParticipantRunEvidence(
            participant_id="BASELINE_B",
            run_id="mission026-nvidia-smoke",
            mutation_id="SMOKE",
            severity="NOT_APPLICABLE",
            seed=0,
            fixture_version="1",
            participant_revision="mission-026-nvidia-smoke",
            configuration_hash="NOT_READY",
            ground_truth_reference="NOT_PROVIDED",
            code_revision="mission-026-nvidia-smoke",
            environment_reference="NVIDIA_HOSTED_SMOKE_ONLY",
            timeout_policy={"timeout_seconds": 300},
            retry_policy={"retry_count": 0},
            artifact_root="experiments",
            observation_reference="mission026-nvidia-smoke#observation",
            detected=NOT_APPLICABLE,
            verification_status=NOT_APPLICABLE,
            risk_decision=NOT_APPLICABLE,
            output_eligible=policy.candidate_accepted,
            failure_state=policy.failure_state,
            timing_ms={"model": caller.last_observation.latency_ms if caller.last_observation else 0},
            cost=NOT_APPLICABLE,
            llm_calls=1,
            evidence_refs=("mission026-nvidia-smoke#model-output",),
            artifact_refs=("experiments/mission026_nvidia_smoke.json",),
            provenance="MODEL_ASSISTED",
            candidate_received=policy.candidate_received,
            candidate_selected=policy.candidate_selected,
            candidate_accepted=policy.candidate_accepted,
            candidate=policy.candidate,
            candidate_application=policy.application or NOT_APPLICABLE,
        )
        observation = caller.last_observation
        payload = {
            **base,
            "status": "PASS" if policy.candidate_accepted else "FAILED",
            "model_reachable": True,
            "candidate_policy_executable": policy.candidate_accepted,
            "provider_operation_count": caller.request_count,
            "candidate_count": policy.candidate_count,
            "candidate_received": policy.candidate_received,
            "candidate_selected": policy.candidate_selected,
            "candidate_accepted": policy.candidate_accepted,
            "generated_code_executed": bool(policy.application and policy.application.get("generated_code_executed")),
            "aegis_verification_invoked": bool(policy.application and policy.application.get("aegis_verification_invoked")),
            "risk_governor_invoked": bool(policy.application and policy.application.get("risk_governor_invoked")),
            "commit_gate_invoked": bool(policy.application and policy.application.get("commit_gate_invoked")),
            "evidence": evidence,
            "provider_observation": observation,
        }
    except NvidiaProviderError as exc:
        payload = {**base, "status": "FAILED", "model_reachable": False, "candidate_policy_executable": False, "provider_operation_count": caller.request_count, "provider_error": str(exc), "status_code": exc.status_code, "rate_limit_retry_after_seconds": exc.retry_after_seconds}
        OUTPUT.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2))
        return 2
    OUTPUT.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
