from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.benchmark_config import BaselineSpec, freeze_config, load_benchmark_config
from aegis.nvidia_provider import (
    NVIDIA_CANDIDATE_MODEL_ID,
    NVIDIA_CANDIDATE_MODEL_REVISION,
    NVIDIA_HOSTED_ENDPOINT,
    NVIDIA_PROVIDER,
    candidate_model_descriptor,
    official_candidate_catalog,
    prompt_sha256,
)
from aegis.participant_freeze import ParticipantFreezeProposal, compute_participant_hash

ROOT = Path(__file__).resolve().parents[1]
OLD_CONFIG = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
NEW_CONFIG = ROOT / "benchmarks/configs/mission_026_nvidia_nim_candidate_config.json"
PROPOSAL = ROOT / "benchmarks/configs/mission_026_baseline_b_nvidia_proposal.json"
CATALOG = ROOT / "benchmarks/configs/mission_026_nvidia_catalog.json"


def main() -> None:
    old = load_benchmark_config(OLD_CONFIG)
    old_specs = {spec.baseline_id: spec for spec in old.baselines}
    old_b = old_specs["BASELINE_B"]
    old_meta = dict(old_b.metadata)
    system_prompt = str(old_meta["system_prompt"])
    repair_prompt = str(old_meta["repair_prompt_template"])
    prompt_hash = prompt_sha256(system_prompt, repair_prompt)
    implementation_revision = "mission-026-nvidia-adapter-" + hashlib.sha256((ROOT / "src/aegis/nvidia_provider.py").read_bytes()).hexdigest()[:16]
    timeout_policy = {"timeout_seconds": 300, "retry_count": 0, "backoff_seconds": 0}
    retry_policy = {"mode": "BOUNDED", "max_attempts": 1, "backoff_ms": 0}
    rate_limit = {
        "max_requests_per_minute": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
        "min_interval_seconds": 0,
        "concurrency_limit": 1,
        "verified_limit": False,
    }
    configuration = {
        "description": "Naive NVIDIA NIM first-candidate repair baseline without AEGIS verification.",
        "provider": NVIDIA_PROVIDER,
        "model_identifier": NVIDIA_CANDIDATE_MODEL_ID,
        "model_revision": NVIDIA_CANDIDATE_MODEL_REVISION,
        "endpoint": NVIDIA_HOSTED_ENDPOINT,
        "interface": "OPENAI_COMPATIBLE_CHAT_COMPLETIONS",
        "system_prompt": system_prompt,
        "repair_prompt_template": repair_prompt,
        "prompt_revision": "mission-026-baseline-b-prompts-v1",
        "prompt_hash": prompt_hash,
        "sampling_configuration": {"temperature": "NOT_APPLICABLE", "top_p": "NOT_APPLICABLE", "top_k": "NOT_APPLICABLE"},
        "max_output": 8192,
        "max_output_tokens": 8192,
        "tools_permitted": ["DISABLED"],
        "tools_enabled": False,
        "first_candidate_policy": "FIRST_CANDIDATE",
        "max_candidates": 1,
        "auto_accept_first_candidate": True,
        "timeout_policy": timeout_policy,
        "retry_policy": retry_policy,
        "rate_limit": rate_limit,
        "catalog_revision": "mission-026-catalog-v1",
        "catalog_status": "OFFICIAL_CATALOG_ENTRY",
        "model_reachability": "MODEL_REACHABLE",
        "smoke_status": "PASS",
        "candidate_policy_executable": True,
        "smoke_provider_operation_count": 1,
        "smoke_evidence": "experiments/mission026_nvidia_smoke.json",
        "runtime_ground_truth": "NOT_PROVIDED",
        "owner_review_status": "REQUIRED",
        "aegis_verification": "NOT_USED",
        "risk_governor": "NOT_USED",
        "commit_gate": "NOT_USED",
        "quarantine": "NOT_USED",
        "watch": "NOT_USED",
        "rollback": "NOT_USED",
        "mutation_ground_truth_runtime_payload": "NOT_PROVIDED",
        "fixture_id": old.fixture_id,
        "fixture_version": old.fixture_version,
        "mutation_class_ids": list(old.mutation_class_ids),
        "seed": old.seeds[0],
        "output_normalization_policy": "canonical-participant-run-v1",
        "artifact_schema": "participant-run-evidence-v1",
        "provenance": "MODEL_ASSISTED",
    }
    proposal = ParticipantFreezeProposal(
        participant_id="BASELINE_B",
        prior_status="NOT_READY",
        implementation_revision=implementation_revision,
        configuration=configuration,
        timeout_policy=timeout_policy,
        retry_policy=retry_policy,
        output_normalization_policy="canonical-participant-run-v1",
        provenance="MODEL_ASSISTED",
        artifact_schema="participant-run-evidence-v1",
        execution_policy="FIRST_CANDIDATE_ONLY",
        verification_policy="NO_AEGIS_VERIFICATION",
        commit_policy="FIRST_CANDIDATE_ACCEPTED_NO_AEGIS_COMMIT_GATE",
    )
    catalog = official_candidate_catalog().to_dict()
    new_b = BaselineSpec(
        baseline_id="BASELINE_B",
        description=configuration["description"],
        implementation_revision=implementation_revision,
        model_id=NVIDIA_CANDIDATE_MODEL_ID,
        prompt_revision=configuration["prompt_revision"],
        configuration_hash=proposal.configuration_hash,
        execution_policy="FIRST_CANDIDATE_ONLY",
        retry_policy=retry_policy,
        verification_policy="NO_AEGIS_VERIFICATION",
        commit_policy="FIRST_CANDIDATE_ACCEPTED_NO_AEGIS_COMMIT_GATE",
        status="NOT_READY",
        metadata=configuration,
    )
    new_config = replace(
        old,
        benchmark_id="aegis-benchmark-mission-026-nvidia-candidate",
        benchmark_version="mission-026-nvidia-candidate-v1",
        baselines=(old_specs["BASELINE_A"], new_b, old_specs["AEGIS"]),
        artifact_root="benchmarks/runs/mission_026_nvidia_nim_candidate",
        collection_policy={
            **dict(old.collection_policy),
            "mode": "CANDIDATE_NOT_READY",
            "provider_execution": "ONE_NVIDIA_SMOKE_COMPLETED; NO_BENCHMARK_EXECUTION",
            "supersedes_configuration_hash": old.configuration_hash,
            "baseline_b_provider": NVIDIA_PROVIDER,
        },
        environment_reference="AEGIS_MISSION_026_NVIDIA_CANDIDATE; SMOKE_DEFERRED; NO_BENCHMARK_EXECUTION",
        evidence_policy={
            **dict(old.evidence_policy),
            "provider": NVIDIA_PROVIDER,
            "model_id": NVIDIA_CANDIDATE_MODEL_ID,
            "owner_review": "REQUIRED_BEFORE_READY",
            "supersedes_configuration_hash": old.configuration_hash,
        },
        model_identifier=NVIDIA_CANDIDATE_MODEL_ID,
        model_configuration={
            "provider": NVIDIA_PROVIDER,
            "endpoint": NVIDIA_HOSTED_ENDPOINT,
            "model_id": NVIDIA_CANDIDATE_MODEL_ID,
            "model_revision": NVIDIA_CANDIDATE_MODEL_REVISION,
            "model_reachability": "MODEL_REACHABLE",
            "smoke_status": "PASS",
            "candidate_policy_executable": True,
            "smoke_provider_operation_count": 1,
            "smoke_evidence": "experiments/mission026_nvidia_smoke.json",
            "runtime_ground_truth": "NOT_PROVIDED",
            "prompt_revision": configuration["prompt_revision"],
            "prompt_hash": prompt_hash,
            "sampling": configuration["sampling_configuration"],
            "max_output_tokens": 8192,
            "tools_enabled": False,
            "candidate_policy": "FIRST_CANDIDATE",
            "max_candidates": 1,
            "auto_accept_first_candidate": True,
            "rate_limit": rate_limit,
            "timeout_policy": timeout_policy,
            "retry_policy": retry_policy,
        },
        prompt_version=configuration["prompt_revision"],
        repository_state="DIRTY_USER_FILES_PRESERVED",
        created_at="2026-08-18T00:00:00+00:00",
        configuration_hash="",
    )
    new_config = freeze_config(new_config)
    for path, payload in (
        (PROPOSAL, proposal.to_dict()),
        (CATALOG, catalog),
        (NEW_CONFIG, new_config.to_dict()),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "proposal_path": str(PROPOSAL),
        "proposal_hash": proposal.configuration_hash,
        "proposal_status": "NOT_READY",
        "catalog_path": str(CATALOG),
        "new_config_path": str(NEW_CONFIG),
        "new_config_hash": new_config.configuration_hash,
        "old_config_hash": old.configuration_hash,
        "model_id": NVIDIA_CANDIDATE_MODEL_ID,
        "prompt_hash": prompt_hash,
        "implementation_revision": implementation_revision,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
