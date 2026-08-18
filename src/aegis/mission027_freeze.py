"""Mission 027 NVIDIA Baseline B owner-review and freeze boundary.

This module is deliberately validation-only. It never constructs a real NVIDIA
caller, invokes a provider, executes healing, creates benchmark artifacts, or
calculates metrics. It preserves the Mission 026 proposal hash as historical
reviewed input while deriving a new promoted participant hash that includes the
owner-approved AEGIS benchmark-side throttle.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from .audit_store import _to_jsonable
from .benchmark_config import BenchmarkConfig, freeze_config, load_benchmark_config
from .benchmark_runner import BenchmarkRunner, RunnerDryRunResult
from .nvidia_provider import NVIDIA_PROVIDER, NvidiaParticipantRegistry
from .participant_freeze import (
    OwnerReviewDecision,
    ParticipantFreezeProposal,
    PromotionResult,
    apply_promotions,
    promote_participant,
)

MISSION_026_PROPOSAL_HASH = "4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f"
MISSION_017_GEMINI_CONFIGURATION_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
MISSION_026_CONFIGURATION_HASH = "52618538bdffaba5edeadcf29257848f1f7e0744079e1f7cb9d4de22db5f859e"
MISSION_027_REVIEWED_AT = "2026-08-18T10:40:27+00:00"
MISSION_027_CORRELATION_ID = "2a1d3d0b-9f61-4b9f-a995-a3d6d32b1d90"
MISSION_027_IMPLEMENTATION_REVISION = "mission-026-nvidia-adapter-74817617100cc17d"
TRIALS_PER_MUTATION = 10

BENCHMARK_RATE_POLICY: Mapping[str, Any] = {
    "policy_owner": "PROJECT_OWNER",
    "policy_status": "OWNER_APPROVED",
    "benchmark_requests_per_minute": 6,
    "benchmark_min_interval_seconds": 10,
    "concurrency_limit": 1,
    "provider_limit": "UNKNOWN",
    "provider_limit_status": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
}


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def load_mission026_candidate(root: str | Path) -> BenchmarkConfig:
    return load_benchmark_config(Path(root) / "benchmarks/configs/mission_026_nvidia_nim_candidate_config.json")


def load_mission026_proposal(root: str | Path) -> ParticipantFreezeProposal:
    payload = json.loads(
        (Path(root) / "benchmarks/configs/mission_026_baseline_b_nvidia_proposal.json").read_text(encoding="utf-8")
    )
    proposal = ParticipantFreezeProposal(
        participant_id=payload["participant_id"],
        prior_status=payload["prior_status"],
        implementation_revision=payload["implementation_revision"],
        configuration=payload["configuration"],
        timeout_policy=payload["timeout_policy"],
        retry_policy=payload["retry_policy"],
        output_normalization_policy=payload["output_normalization_policy"],
        provenance=payload["provenance"],
        artifact_schema=payload["artifact_schema"],
        execution_policy=payload["execution_policy"],
        verification_policy=payload["verification_policy"],
        commit_policy=payload["commit_policy"],
        configuration_hash=payload["configuration_hash"],
    )
    if proposal.configuration_hash != MISSION_026_PROPOSAL_HASH:
        raise ValueError("Mission 026 proposal hash does not match the frozen historical value")
    return proposal


def build_owner_approved_proposal(source: ParticipantFreezeProposal) -> ParticipantFreezeProposal:
    """Create the new immutable promotion input without modifying source history."""

    metadata = _mapping(source.configuration)
    metadata["configuration"] = {
        "adapter": "NvidiaBaselineBAdapter",
        "mode": "MODEL_ASSISTED_NAIVE_FIRST_CANDIDATE",
        "provider": NVIDIA_PROVIDER,
        "model_id": "openai/gpt-oss-20b",
        "verification_bypass": True,
        "risk_governor": "NOT_USED",
        "commit_gate": "NOT_USED",
    }
    metadata["benchmark_rate_policy"] = dict(BENCHMARK_RATE_POLICY)
    metadata["rate_limit"] = {
        "provider_limit": "UNKNOWN",
        "provider_limit_status": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
        "benchmark_requests_per_minute": 6,
        "benchmark_min_interval_seconds": 10,
        "concurrency_limit": 1,
        "verified_limit": False,
    }
    metadata["owner_review_status"] = "APPROVED"
    metadata["owner_reviewed_at"] = MISSION_027_REVIEWED_AT
    metadata["owner_review_correlation_id"] = MISSION_027_CORRELATION_ID
    metadata["source_proposal_hash"] = MISSION_026_PROPOSAL_HASH
    metadata["implementation_revision"] = MISSION_027_IMPLEMENTATION_REVISION

    return ParticipantFreezeProposal(
        participant_id=source.participant_id,
        prior_status="NOT_READY",
        implementation_revision=MISSION_027_IMPLEMENTATION_REVISION,
        configuration=metadata,
        timeout_policy=source.timeout_policy,
        retry_policy=source.retry_policy,
        output_normalization_policy=source.output_normalization_policy,
        provenance=source.provenance,
        artifact_schema=source.artifact_schema,
        execution_policy=source.execution_policy,
        verification_policy=source.verification_policy,
        commit_policy=source.commit_policy,
    )


def owner_review(proposal: ParticipantFreezeProposal) -> OwnerReviewDecision:
    return OwnerReviewDecision(
        participant_id="BASELINE_B",
        approved=True,
        owner="PROJECT_OWNER",
        reviewer="PROJECT_OWNER",
        rationale=(
            "Approve NVIDIA NIM Baseline B for the Mission 027 validation freeze using the "
            "verified openai/gpt-oss-20b candidate. The provider RPM/free-tier ceiling remains "
            "UNKNOWN; AEGIS independently throttles benchmark-side execution to 6 requests per "
            "minute, a 10-second minimum interval, and concurrency 1. The naive baseline remains "
            "without AEGIS verification, RiskGovernor, or CommitGate authority."
        ),
        reviewed_at=MISSION_027_REVIEWED_AT,
        correlation_id=MISSION_027_CORRELATION_ID,
    )


def promote_nvidia_baseline(source: ParticipantFreezeProposal) -> tuple[PromotionResult, OwnerReviewDecision]:
    proposal = build_owner_approved_proposal(source)
    review = owner_review(proposal)
    return promote_participant(proposal, review), review


def build_mission027_config(root: str | Path) -> tuple[BenchmarkConfig, ParticipantFreezeProposal, PromotionResult, OwnerReviewDecision]:
    base = load_benchmark_config(Path(root) / "benchmarks/configs/mission_017_corrected_frozen_config.json")
    source = load_mission026_proposal(root)
    promotion, review = promote_nvidia_baseline(source)

    promoted = apply_promotions(base, (promotion,))
    collection_policy = _mapping(promoted.collection_policy)
    collection_policy.update(
        {
            "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
            "baseline_b_provider": NVIDIA_PROVIDER,
            "mode": "VALIDATION_ONLY",
            "provider_execution": "NOT_EXECUTED",
            "trials_per_mutation": TRIALS_PER_MUTATION,
            "planned_opportunities": 180,
            "supersedes_configuration_hash": MISSION_017_GEMINI_CONFIGURATION_HASH,
        }
    )
    evidence_policy = _mapping(promoted.evidence_policy)
    evidence_policy.update(
        {
            "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
            "owner_review": "APPROVED",
            "provider_limit": "UNKNOWN",
            "provider": NVIDIA_PROVIDER,
            "supersedes_configuration_hash": MISSION_017_GEMINI_CONFIGURATION_HASH,
        }
    )
    model_configuration = _mapping(promoted.model_configuration)
    model_configuration.update(
        {
            "provider": NVIDIA_PROVIDER,
            "model_id": source.configuration["model_identifier"],
            "model_revision": source.configuration["model_revision"],
            "endpoint": source.configuration["endpoint"],
            "prompt_revision": source.configuration["prompt_revision"],
            "prompt_hash": source.configuration["prompt_hash"],
            "smoke_status": source.configuration["smoke_status"],
            "smoke_evidence": source.configuration["smoke_evidence"],
            "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
            "owner_review_status": "APPROVED",
            "provider_limit": "UNKNOWN",
            "provider_limit_status": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
            "rate_limit": {
                "provider_limit": "UNKNOWN",
                "provider_limit_status": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
                "benchmark_requests_per_minute": 6,
                "benchmark_min_interval_seconds": 10,
                "concurrency_limit": 1,
                "verified_limit": False,
            },
        }
    )
    config = replace(
        promoted,
        benchmark_id="aegis-benchmark-mission-027-nvidia-owner-freeze",
        benchmark_version="mission-027-nvidia-owner-freeze-v1",
        artifact_root="benchmarks/runs/mission_027_nvidia_owner_freeze",
        collection_policy=collection_policy,
        environment_reference="AEGIS_MISSION_027_VALIDATION_ONLY; NVIDIA_PROVIDER_LIMIT_UNKNOWN; BENCHMARK_THROTTLE_6_RPM",
        evidence_policy=evidence_policy,
        model_configuration=model_configuration,
        repository_state="DIRTY_USER_FILES_PRESERVED",
        created_at=MISSION_027_REVIEWED_AT,
        config_version="mission-027-nvidia-benchmark-config-v1",
        configuration_hash="",
    )
    return freeze_config(config), build_owner_approved_proposal(source), promotion, review


def fairness_report(config: BenchmarkConfig) -> Mapping[str, Any]:
    common = {
        "same_mutations": tuple(config.mutation_class_ids) == ("M001", "M002", "M003", "M004", "M005", "M006"),
        "same_seed": config.seeds == (12345,),
        "same_fixture": config.fixture_id == "gpu-price-staging" and config.fixture_version == "1",
        "same_trial_count": config.collection_policy.get("trials_per_mutation") == TRIALS_PER_MUTATION,
        "same_timeout": config.timeout_policy == {
            "collection_ms": 300000,
            "healing_ms": 300000,
            "polling_ms": 300000,
            "total_ms": 300000,
            "verification_ms": 300000,
        },
        "same_retry": config.retry_policy == {"backoff_ms": 0, "max_attempts": 1, "mode": "BOUNDED"},
        "same_backoff": config.retry_policy.get("backoff_ms") == 0,
        "same_ground_truth_reference_structure": config.evidence_policy.get("ground_truth") == "MutationGroundTruth_ONLY",
        "same_evaluator_isolation": config.evidence_policy.get("ground_truth") == "MutationGroundTruth_ONLY" and all(
            spec.metadata.get("evaluator_ground_truth_runtime_access", False) is False
            for spec in config.baselines
            if spec.baseline_id == "AEGIS"
        ),
        "only_provider_model_execution_differs": config.baselines[1].metadata.get("provider") == NVIDIA_PROVIDER,
    }
    return {**common, "status": "PASS" if all(common.values()) else "FAIL"}


def validation_only(config: BenchmarkConfig) -> RunnerDryRunResult:
    """Run the local dry-run planner with an NVIDIA registry and no caller."""

    registry = NvidiaParticipantRegistry(config)
    return BenchmarkRunner(config, registry=registry).dry_run()


def planned_execution_count(config: BenchmarkConfig, root: str | Path) -> int:
    """Plan the future 180-opportunity protocol without invoking its gate or executor."""

    from .benchmark_executor import BenchmarkExecutor

    executor = BenchmarkExecutor(
        config,
        repository_root=Path(root),
        output_root=Path(root) / config.artifact_root,
        registry=NvidiaParticipantRegistry(config),
    )
    return len(executor.plan_manifests())


def build_records(
    config: BenchmarkConfig,
    source: ParticipantFreezeProposal,
    promotion: PromotionResult,
    review: OwnerReviewDecision,
    dry_run: RunnerDryRunResult,
    planned_opportunities: int = 180,
) -> Mapping[str, Any]:
    fairness = fairness_report(config)
    review_record = {
        **dict(review.to_dict()),
        "participant_hash": MISSION_026_PROPOSAL_HASH,
        "source_proposal_hash": MISSION_026_PROPOSAL_HASH,
        "promoted_participant_hash": promotion.participant_spec.configuration_hash,
        "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
        "provider_limit": "UNKNOWN",
    }
    promotion_record = {
        **dict(promotion.promotion.to_dict()),
        "source_proposal_hash": MISSION_026_PROPOSAL_HASH,
        "prior_participant_hash": MISSION_026_PROPOSAL_HASH,
        "promoted_participant_hash": promotion.participant_spec.configuration_hash,
        "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
    }
    return {
        "mission": "027",
        "created_at": MISSION_027_REVIEWED_AT,
        "owner_review_decisions": {"BASELINE_B": review_record},
        "readiness_promotions": [promotion_record],
        "participant_proposal_hash": MISSION_026_PROPOSAL_HASH,
        "promoted_participant_hash": promotion.participant_spec.configuration_hash,
        "new_configuration_hash": config.configuration_hash,
        "superseded_historical_configuration_hash": MISSION_017_GEMINI_CONFIGURATION_HASH,
        "source_mission026_configuration_hash": MISSION_026_CONFIGURATION_HASH,
        "participant_states": {
            "BASELINE_A": "READY",
            "BASELINE_B": "READY",
            "AEGIS": "READY",
        },
        "benchmark_rate_policy": dict(BENCHMARK_RATE_POLICY),
        "provider_limit": "UNKNOWN",
        "fairness": fairness,
        "dry_run": dry_run.to_dict(),
        "validation_only_protocol": {
            "status": "PASS" if dry_run.status.value == "READY_TO_EXECUTE" else dry_run.status.value,
            "planned_opportunities": planned_opportunities,
            "trials_per_mutation": TRIALS_PER_MUTATION,
            "plan_source": "BenchmarkExecutor.plan_manifests",
            "execution_authorized": False,
            "benchmark_runs_executed": 0,
            "provider_operations_executed": 0,
            "healing_operations_executed": 0,
            "metric_results_generated": 0,
        },
        "historical_artifacts_unchanged": True,
        "source_proposal_preserved": source.configuration_hash == MISSION_026_PROPOSAL_HASH,
    }


def json_bytes(payload: Any) -> str:
    return json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n"


__all__ = [
    "BENCHMARK_RATE_POLICY",
    "MISSION_017_GEMINI_CONFIGURATION_HASH",
    "MISSION_026_CONFIGURATION_HASH",
    "MISSION_026_PROPOSAL_HASH",
    "MISSION_027_CORRELATION_ID",
    "MISSION_027_IMPLEMENTATION_REVISION",
    "MISSION_027_REVIEWED_AT",
    "TRIALS_PER_MUTATION",
    "build_mission027_config",
    "build_owner_approved_proposal",
    "build_records",
    "fairness_report",
    "json_bytes",
    "load_mission026_candidate",
    "load_mission026_proposal",
    "owner_review",
    "planned_execution_count",
    "promote_nvidia_baseline",
    "validation_only",
]
