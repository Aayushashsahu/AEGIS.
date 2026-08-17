from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from aegis.baseline_participants import (
    BASELINE_A_CONFIG_VERSION,
    BASELINE_A_SCHEMA_VERSION,
    BASELINE_B_MODEL_ID,
    BASELINE_B_MODEL_REVISION,
    BASELINE_B_REPAIR_PROMPT_TEMPLATE,
    BASELINE_B_REPAIR_PROMPT_VERSION,
    BASELINE_B_SYSTEM_PROMPT,
    BASELINE_B_SYSTEM_PROMPT_VERSION,
    PARTICIPANT_OUTPUT_SCHEMA,
    PARTICIPANT_NORMALIZATION,
)
from aegis.benchmark_config import freeze_config, load_benchmark_config, validate_config
from aegis.benchmark_runner import BenchmarkRunner, RunnerDryRunStatus, normalize_mutation_run
from aegis.mutation_lab import MutationLab
from aegis.participant_freeze import (
    OwnerReviewDecision,
    ParticipantFreezeProposal,
    PromotionStatus,
    apply_promotions,
    compute_participant_hash,
    promote_participant,
    validate_participant_proposal,
)


ROOT = Path(__file__).resolve().parents[2]
MISSION_011_HASH = "fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3"
BASELINE_IMPLEMENTATION_SHA = "0e8bcc4a2c2184cae9a50b291054ec47d83fc895"
AEGIS_IMPLEMENTATION_SHA = "7de2bc65ed9eeb9f4abd24017543f3f366990738"
MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")
COMMON_TIMEOUT_SECONDS = {"timeout_seconds": 300, "retry_count": 0, "backoff_seconds": 0}
COMMON_RETRY_POLICY = {"mode": "BOUNDED", "max_attempts": 1, "backoff_ms": 0}
COMMON_TIMEOUT_MS = {
    "collection_ms": 300000,
    "healing_ms": 300000,
    "polling_ms": 300000,
    "verification_ms": 300000,
    "total_ms": 300000,
}


def _common_metadata() -> dict[str, object]:
    return {
        "output_normalization_policy": PARTICIPANT_NORMALIZATION,
        "artifact_schema": PARTICIPANT_OUTPUT_SCHEMA,
        "timeout_policy": dict(COMMON_TIMEOUT_SECONDS),
        "retry_policy": dict(COMMON_RETRY_POLICY),
    }


def mission015_proposal(participant_id: str, *, aegis_configuration_hash: str = MISSION_011_HASH) -> ParticipantFreezeProposal:
    common = _common_metadata()
    if participant_id == "BASELINE_A":
        metadata = {
            **common,
            "description": "Deterministic fixed-selector static extraction baseline.",
            "provider": "TEST_DOUBLE",
            "extraction_implementation": "baseline-a-static-selector-v1",
            "selector_version": BASELINE_A_CONFIG_VERSION,
            "schema_version": BASELINE_A_SCHEMA_VERSION,
            "configuration": {
                "selector_version": BASELINE_A_CONFIG_VERSION,
                "schema_version": BASELINE_A_SCHEMA_VERSION,
                "mode": "STATIC_SELECTOR_ONLY",
                "selectors": {
                    "product_id": "FIELD_PASSTHROUGH",
                    "title": "CSS_SELECTOR",
                    "price": "CSS_SELECTOR",
                    "availability": "CSS_SELECTOR",
                    "rating": "CSS_SELECTOR",
                    "url": "CSS_SELECTOR",
                },
            },
            "healing": "NOT_USED",
            "llm": "NOT_USED",
            "aegis_verification": "NOT_USED",
            "risk_governor": "NOT_USED",
            "commit_gate": "NOT_USED",
            "quarantine": "NOT_USED",
            "watch": "NOT_USED",
            "rollback": "NOT_USED",
            "mutation_class_ids": list(MUTATIONS),
            "seed": 12345,
            "fixture_id": "gpu-price-staging",
            "fixture_version": "1",
            "provenance": "TEST_DOUBLE",
        }
        proposal = ParticipantFreezeProposal(
            participant_id=participant_id,
            prior_status="NOT_READY",
            implementation_revision=BASELINE_IMPLEMENTATION_SHA,
            configuration=metadata,
            timeout_policy=COMMON_TIMEOUT_SECONDS,
            retry_policy=COMMON_RETRY_POLICY,
            output_normalization_policy=PARTICIPANT_NORMALIZATION,
            provenance="TEST_DOUBLE",
            artifact_schema=PARTICIPANT_OUTPUT_SCHEMA,
            execution_policy="SINGLE_PASS_NO_HEALING",
            verification_policy="NOT_APPLICABLE_BASELINE_NO_VERIFICATION",
            commit_policy="NOT_APPLICABLE_BASELINE_NO_COMMIT",
        )
    elif participant_id == "BASELINE_B":
        metadata = {
            **common,
            "description": "Naive Gemini first-candidate repair baseline without AEGIS verification.",
            "provider": "GOOGLE_GEMINI_API",
            "model_identifier": BASELINE_B_MODEL_ID,
            "model_revision": BASELINE_B_MODEL_REVISION,
            "system_prompt_version": BASELINE_B_SYSTEM_PROMPT_VERSION,
            "system_prompt": BASELINE_B_SYSTEM_PROMPT,
            "repair_prompt_template_version": BASELINE_B_REPAIR_PROMPT_VERSION,
            "repair_prompt_template": BASELINE_B_REPAIR_PROMPT_TEMPLATE,
            "sampling_configuration": {
                "temperature": "NOT_APPLICABLE",
                "top_p": "NOT_APPLICABLE",
                "top_k": "NOT_APPLICABLE",
            },
            "max_output_tokens": 8192,
            "max_output": 8192,
            "tools_enabled": False,
            "tools_permitted": ["DISABLED"],
            "first_candidate_policy": "FIRST_CANDIDATE",
            "max_candidates": 1,
            "auto_accept_first_candidate": True,
            "aegis_verification": "NOT_USED",
            "risk_governor": "NOT_USED",
            "commit_gate": "NOT_USED",
            "mutation_ground_truth_runtime_payload": "NOT_PROVIDED",
            "mutation_class_ids": list(MUTATIONS),
            "seed": 12345,
            "fixture_id": "gpu-price-staging",
            "fixture_version": "1",
            "provenance": "MODEL_ASSISTED",
            "prompt_revision": "baseline-b-prompts-v1",
            "configuration": {
                "model_identifier": BASELINE_B_MODEL_ID,
                "model_revision": BASELINE_B_MODEL_REVISION,
                "system_prompt_version": BASELINE_B_SYSTEM_PROMPT_VERSION,
                "repair_prompt_template_version": BASELINE_B_REPAIR_PROMPT_VERSION,
                "prompt_revision": "baseline-b-prompts-v1",
                "max_output_tokens": 8192,
                "tools_enabled": False,
                "first_candidate_only": True,
                "auto_accept_first_candidate": True,
            },
        }
        proposal = ParticipantFreezeProposal(
            participant_id=participant_id,
            prior_status="NOT_READY",
            implementation_revision=BASELINE_IMPLEMENTATION_SHA,
            configuration=metadata,
            timeout_policy=COMMON_TIMEOUT_SECONDS,
            retry_policy=COMMON_RETRY_POLICY,
            output_normalization_policy=PARTICIPANT_NORMALIZATION,
            provenance="MODEL_ASSISTED",
            artifact_schema=PARTICIPANT_OUTPUT_SCHEMA,
            execution_policy="FIRST_CANDIDATE_ONLY",
            verification_policy="NO_AEGIS_VERIFICATION",
            commit_policy="FIRST_CANDIDATE_ACCEPTED_NO_AEGIS_COMMIT_GATE",
        )
    elif participant_id == "AEGIS":
        metadata = {
            **common,
            "description": "AEGIS safety lifecycle TEST_DOUBLE benchmark adapter.",
            "code_revision": AEGIS_IMPLEMENTATION_SHA,
            "participant_adapter": "AegisAdapter",
            "fixture_id": "gpu-price-staging",
            "fixture_version": "1",
            "mutation_class_ids": list(MUTATIONS),
            "seeds": [12345],
            "benchmark_configuration_hash": aegis_configuration_hash,
            "deterministic_test_double": True,
            "provider_execution": "NOT_USED_FOR_INITIAL_BENCHMARK",
            "live_bright_data_execution": "NOT_USED",
            "healing": "EXISTING_AEGIS_LIFECYCLE_ONLY",
            "verification": "USED",
            "risk_governor": "USED",
            "commit_gate": "USED",
            "quarantine": "USED",
            "watch": "USED",
            "rollback": "USED",
            "auto_approve": False,
            "verification_bypass": False,
            "blind_commit": False,
            "evaluator_ground_truth_runtime_access": False,
            "metric_formula_version": "mission-010-metrics-v1",
            "safety_policy": "UNCHANGED; VERIFICATION_RISK_COMMIT_GATE_REQUIRED",
            "provenance": "TEST_DOUBLE",
            "configuration": {
                "mode": "TEST_DOUBLE",
                "adapter": "AegisAdapter",
                "live_provider_execution": False,
                "ground_truth_runtime_access": False,
                "auto_approve": False,
                "verification_bypass": False,
                "blind_commit": False,
            },
        }
        proposal = ParticipantFreezeProposal(
            participant_id=participant_id,
            prior_status="NOT_READY",
            implementation_revision=AEGIS_IMPLEMENTATION_SHA,
            configuration=metadata,
            timeout_policy=COMMON_TIMEOUT_SECONDS,
            retry_policy=COMMON_RETRY_POLICY,
            output_normalization_policy=PARTICIPANT_NORMALIZATION,
            provenance="TEST_DOUBLE",
            artifact_schema=PARTICIPANT_OUTPUT_SCHEMA,
            execution_policy="FULL_AEGIS_LIFECYCLE_TEST_DOUBLE_ONLY",
            verification_policy="MISSION_010_DETERMINISTIC_VERIFICATION",
            commit_policy="COMMIT_GATE_REQUIRED_NO_DRY_RUN_COMMIT",
        )
    else:
        raise AssertionError(participant_id)
    return replace(proposal, configuration_hash=compute_participant_hash(proposal))


def mission015_base_config():
    floor = load_benchmark_config(ROOT / "benchmarks/configs/mission_011_validation_floor.json")
    return freeze_config(
        replace(
            floor,
            benchmark_id="aegis-benchmark-mission-015",
            benchmark_version="mission-015-frozen-participants-v1",
            code_revision=AEGIS_IMPLEMENTATION_SHA,
            repository_revision=AEGIS_IMPLEMENTATION_SHA,
            timeout_policy=COMMON_TIMEOUT_MS,
            retry_policy=COMMON_RETRY_POLICY,
            artifact_root="benchmarks/results/mission_015",
            created_at="2026-08-17T00:00:00+00:00",
        )
    )


def promoted_mission015_config():
    base = mission015_base_config()
    promotions = tuple(
        promote_participant(
            proposal,
            OwnerReviewDecision(
                participant_id=participant_id,
                approved=True,
                owner="PROJECT_OWNER",
                reviewer="PROJECT_OWNER",
                rationale="Owner-approved benchmark participant configuration for the minimum comparative benchmark; participant behavior, safety boundaries, and common execution policy are frozen before benchmark execution.",
                reviewed_at="2026-08-17T00:00:00+00:00",
                correlation_id=f"mission-015-{participant_id.lower()}-review",
            ),
        )
        for participant_id, proposal in ((participant_id, mission015_proposal(participant_id)) for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS"))
    )
    return apply_promotions(base, promotions), promotions


def test_all_mission015_participants_validate_with_deterministic_hashes() -> None:
    for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS"):
        proposal = mission015_proposal(participant_id)
        validation = validate_participant_proposal(proposal)
        assert validation.status is PromotionStatus.READY
        assert proposal.configuration_hash == compute_participant_hash(proposal)
        assert proposal.configuration_hash == mission015_proposal(participant_id).configuration_hash


def test_mission015_promotions_record_owner_approval_and_ready_transitions() -> None:
    _config, promotions = promoted_mission015_config()
    assert [item.participant_id for item in promotions] == ["BASELINE_A", "BASELINE_B", "AEGIS"]
    for result in promotions:
        assert result.participant_spec.status == "READY"
        assert result.promotion.prior_status == "NOT_READY"
        assert result.promotion.new_status == "READY"
        assert result.promotion.owner == "PROJECT_OWNER"
        assert result.promotion.reviewer == "PROJECT_OWNER"
        assert result.promotion.correlation_id.startswith("mission-015-")


def test_mission015_config_is_new_frozen_config_with_common_policy_and_valid_hash() -> None:
    config, _promotions = promoted_mission015_config()
    assert validate_config(config).valid
    assert config.configuration_hash != MISSION_011_HASH
    assert config.configuration_hash
    assert config.timeout_policy == COMMON_TIMEOUT_MS
    assert config.retry_policy == COMMON_RETRY_POLICY
    assert tuple(spec.status for spec in config.baselines) == ("READY", "READY", "READY")
    assert tuple(spec.retry_policy for spec in config.baselines) == (COMMON_RETRY_POLICY,) * 3
    assert all(spec.configuration_hash not in {"", "TBD", "UNKNOWN", "NOT_READY"} for spec in config.baselines)


def test_mission015_aegis_readiness_and_normalization_are_ready_without_runtime_ground_truth() -> None:
    config, _promotions = promoted_mission015_config()
    runner = BenchmarkRunner(config)
    readiness = runner.registry.get("AEGIS").readiness(config)
    assert readiness.ready
    assert readiness.participant_configuration_hash == next(spec.configuration_hash for spec in config.baselines if spec.baseline_id == "AEGIS")
    lab = MutationLab()
    run, _case, _detection, _verification, _risk = lab.run("M001", 12345)
    evidence = normalize_mutation_run(run, runner.build_input("AEGIS", "M001", 12345), participant_revision=AEGIS_IMPLEMENTATION_SHA)
    assert evidence.participant_id == "AEGIS"
    assert evidence.provenance == "TEST_DOUBLE"
    assert evidence.ground_truth_reference.startswith("ground-truth://gpu-price-staging/v1/M001/12345")
    assert evidence.verification_status != "NOT_APPLICABLE"


def test_mission015_fairness_pass_and_ready_to_execute_is_not_authorization() -> None:
    config, _promotions = promoted_mission015_config()
    runner = BenchmarkRunner(config)
    shared = [runner.build_input(participant_id, "M005", 12345).shared_metadata() for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS")]
    assert shared[0] == shared[1] == shared[2]
    assert all(item["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED" for item in shared)
    result = runner.dry_run()
    assert result.status is RunnerDryRunStatus.READY_TO_EXECUTE
    assert result.expected_run_count == 18
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_results_generated == 0
    assert result.execution_authorized is False
