from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from aegis.benchmark_config import default_validation_config, freeze_config, load_benchmark_config, validate_config
from aegis.benchmark_runner import BenchmarkRunner, FreezeSnapshot, RunnerDryRunStatus, validate_freeze
from aegis.participant_freeze import (
    OwnerReviewDecision,
    ParticipantFreezeProposal,
    PromotionError,
    PromotionStatus,
    apply_promotions,
    compute_participant_hash,
    default_mission013_proposals,
    promote_participant,
    validate_participant_proposal,
)


MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")


def config():
    return default_validation_config(code_revision="mission013-code", repository_state="DIRTY_USER_FILES_PRESERVED")


def review(participant_id: str, approved: bool = True) -> OwnerReviewDecision:
    return OwnerReviewDecision(
        participant_id=participant_id,
        approved=approved,
        owner="PROJECT_OWNER_NOT_PROVIDED" if not approved else "PROJECT_OWNER_REVIEWED",
        reviewer="AEGIS_REVIEWER",
        rationale="Explicit Mission 013 review record for participant metadata.",
        reviewed_at="2026-08-17T00:00:00+00:00",
        correlation_id=f"corr-mission013-{participant_id.lower()}",
    )


def proposal(participant_id: str) -> ParticipantFreezeProposal:
    common = {
        "description": f"Mission 013 reviewed {participant_id} definition",
        "output_normalization_policy": "ParticipantRunEvidence-v1",
        "provenance": "TEST_DOUBLE",
        "artifact_schema": "ParticipantRunEvidence-v1",
        "timeout_policy": {"collection_ms": 300000, "verification_ms": 30000, "total_ms": 1800000},
        "retry_policy": {"mode": "BOUNDED", "max_attempts": 1, "backoff_ms": 0},
    }
    if participant_id == "BASELINE_A":
        metadata = {
            **common,
            "extraction_implementation": "baseline-a-static-selector-v1",
            "configuration": {"selector": ".product-card", "mode": "STATIC_SELECTOR_ONLY"},
            "healing": "NOT_USED",
            "aegis_verification": "NOT_USED",
            "risk_governor": "NOT_USED",
            "commit_gate": "NOT_USED",
            "quarantine": "NOT_USED",
            "watch": "NOT_USED",
            "rollback": "NOT_USED",
        }
        return ParticipantFreezeProposal(
            participant_id=participant_id,
            prior_status="NOT_READY",
            implementation_revision="baseline-a-revision-1",
            configuration=metadata,
            timeout_policy=metadata["timeout_policy"],
            retry_policy=metadata["retry_policy"],
            output_normalization_policy=metadata["output_normalization_policy"],
            provenance=metadata["provenance"],
            artifact_schema=metadata["artifact_schema"],
            execution_policy="SINGLE_PASS_NO_HEALING",
            verification_policy="NOT_APPLICABLE_BASELINE_NO_VERIFICATION",
            commit_policy="NOT_APPLICABLE_BASELINE_NO_COMMIT",
        )
    if participant_id == "BASELINE_B":
        metadata = {
            **common,
            "model_identifier": "owner-approved-model-v1",
            "provider": "owner-approved-provider",
            "system_prompt": "owner-approved-system-prompt-v1",
            "repair_prompt_template": "owner-approved-repair-template-v1",
            "sampling_configuration": {"temperature": 0, "top_p": 1},
            "max_output": 2048,
            "tools_permitted": ["none"],
            "first_candidate_policy": "EXECUTE_FIRST_ACCEPT_NO_AEGIS_VERIFICATION",
            "configuration": {"model_identifier": "owner-approved-model-v1", "prompt_revision": "owner-approved-prompt-v1"},
        }
        return ParticipantFreezeProposal(
            participant_id=participant_id,
            prior_status="NOT_READY",
            implementation_revision="baseline-b-revision-1",
            configuration=metadata,
            timeout_policy=metadata["timeout_policy"],
            retry_policy=metadata["retry_policy"],
            output_normalization_policy=metadata["output_normalization_policy"],
            provenance=metadata["provenance"],
            artifact_schema=metadata["artifact_schema"],
            execution_policy="FIRST_CANDIDATE_ONLY",
            verification_policy="NO_AEGIS_VERIFICATION",
            commit_policy="FIRST_CANDIDATE_ACCEPTED_NO_AEGIS_COMMIT_GATE",
        )
    metadata = {
        **common,
        "code_revision": "aegis-code-revision-1",
        "fixture_version": "1",
        "mutation_class_ids": list(MUTATIONS),
        "seeds": [12345],
        "benchmark_configuration_hash": config().configuration_hash,
        "participant_adapter": "aegis.benchmark_runner.AegisAdapter",
        "deterministic_test_double": True,
        "metric_formula_version": "mission-010-metrics-v1",
        "safety_policy": "UNCHANGED; VERIFICATION_RISK_COMMIT_GATE_REQUIRED",
        "configuration": {"mode": "TEST_DOUBLE", "metric_calculator": "MISSION_010_ONLY"},
    }
    return ParticipantFreezeProposal(
        participant_id=participant_id,
        prior_status="NOT_READY",
        implementation_revision=metadata["code_revision"],
        configuration=metadata,
        timeout_policy=metadata["timeout_policy"],
        retry_policy=metadata["retry_policy"],
        output_normalization_policy=metadata["output_normalization_policy"],
        provenance=metadata["provenance"],
        artifact_schema=metadata["artifact_schema"],
        execution_policy="FULL_AEGIS_LIFECYCLE_TEST_DOUBLE_ONLY",
        verification_policy="MISSION_010_DETERMINISTIC_VERIFICATION",
        commit_policy="COMMIT_GATE_REQUIRED_NO_DRY_RUN_COMMIT",
    )


def ready_config():
    current = config()
    promotions = tuple(promote_participant(proposal(participant_id), review(participant_id)) for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS"))
    return apply_promotions(current, promotions), promotions


def test_default_proposals_preserve_not_ready_and_do_not_guess() -> None:
    proposals = default_mission013_proposals(config())
    assert set(proposals) == {"BASELINE_A", "BASELINE_B", "AEGIS"}
    for item in proposals.values():
        assert item.prior_status == "NOT_READY"
        assert validate_participant_proposal(item).status is PromotionStatus.NOT_READY
    assert proposals["BASELINE_B"].configuration["model_identifier"] == "TBD"
    assert proposals["BASELINE_B"].configuration["system_prompt"] == "TBD"


@pytest.mark.parametrize("participant_id", ["BASELINE_A", "BASELINE_B", "AEGIS"])
def test_incomplete_participant_metadata_is_not_ready(participant_id: str) -> None:
    current = default_mission013_proposals(config())[participant_id]
    result = validate_participant_proposal(current)
    assert result.status is PromotionStatus.NOT_READY
    assert result.errors


@pytest.mark.parametrize("field", ["model_identifier", "system_prompt", "repair_prompt_template", "configuration", "first_candidate_policy"])
def test_baseline_b_missing_owner_value_is_not_ready(field: str) -> None:
    current = proposal("BASELINE_B")
    metadata = dict(current.configuration)
    metadata.pop(field)
    changed = replace(current, configuration=metadata, configuration_hash="")
    result = validate_participant_proposal(changed)
    assert result.status is PromotionStatus.NOT_READY
    assert any(field in error for error in result.errors)


def test_fully_frozen_participant_is_ready_and_hash_is_deterministic() -> None:
    current = proposal("BASELINE_A")
    result = validate_participant_proposal(current)
    assert result.status is PromotionStatus.READY
    assert result.participant_configuration_hash == compute_participant_hash(current)
    assert result.errors == ()
    assert current.to_dict()["configuration_hash"] == result.computed_configuration_hash


def test_promotion_requires_owner_approval_and_records_immutable_transition() -> None:
    current = proposal("BASELINE_A")
    with pytest.raises(PromotionError, match="owner approval"):
        promote_participant(current, review("BASELINE_A", approved=False))
    result = promote_participant(current, review("BASELINE_A"))
    assert result.participant_spec.status == "READY"
    assert result.promotion.prior_status == "NOT_READY"
    assert result.promotion.new_status == "READY"
    assert result.promotion.configuration_hash == current.configuration_hash
    assert result.promotion.correlation_id == "corr-mission013-baseline_a"
    with pytest.raises(FrozenInstanceError):
        result.promotion.new_status = "NOT_READY"  # type: ignore[misc]


def test_applying_promotions_returns_new_config_and_invalidates_old_hash() -> None:
    current = config()
    promotions = tuple(promote_participant(proposal(participant_id), review(participant_id)) for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS"))
    updated = apply_promotions(current, promotions)
    assert updated is not current
    assert updated.configuration_hash != current.configuration_hash
    assert validate_config(current).valid is True
    assert validate_config(updated).valid is True
    assert tuple(spec.status for spec in updated.baselines) == ("READY", "READY", "READY")


def test_old_hash_is_invalid_when_participant_metadata_changes_without_refreeze() -> None:
    current = config()
    changed_spec = replace(current.baselines[0], metadata={"extraction_implementation": "new"})
    changed = replace(current, baselines=(changed_spec, *current.baselines[1:]))
    result = validate_config(changed)
    assert result.valid is False
    assert "configuration_hash does not match canonical frozen configuration" in result.errors


def test_ready_dry_run_requires_all_participants_and_still_executes_zero_runs() -> None:
    updated, promotions = ready_config()
    result = BenchmarkRunner(updated).dry_run()
    assert result.status is RunnerDryRunStatus.READY_TO_EXECUTE
    assert all(report.ready for report in result.participant_readiness.values())
    assert result.expected_run_count == 18
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_results_generated == 0
    assert result.execution_authorized is False
    assert len(promotions) == 3


def test_fairness_metadata_remains_identical_after_promotion() -> None:
    updated, _ = ready_config()
    runner = BenchmarkRunner(updated)
    metadata = [runner.build_input(participant, "M005", 12345).shared_metadata() for participant in ("BASELINE_A", "BASELINE_B", "AEGIS")]
    assert metadata[0] == metadata[1] == metadata[2]
    assert metadata[0]["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED"


def test_drift_in_mutation_or_seed_is_not_ready_for_frozen_config() -> None:
    updated, _ = ready_config()
    snapshot = FreezeSnapshot.from_config(updated)
    changed_mutations = freeze_config(replace(updated, mutation_class_ids=("M001", "M002", "M003", "M004", "M005")))
    changed_seeds = freeze_config(replace(updated, seeds=(999,), trial_count=1))
    changed_code = freeze_config(replace(updated, code_revision="changed-code", repository_revision="changed-code"))
    assert validate_config(changed_mutations).valid is False
    assert validate_freeze(changed_mutations, snapshot).valid is False
    assert validate_freeze(changed_seeds, snapshot).valid is False
    assert validate_freeze(changed_code, snapshot).valid is False


def test_no_benchmark_result_artifact_is_claimed() -> None:
    assert not Path("benchmarks/results/mission_013").exists()
    assert not hasattr(BenchmarkRunner(config()), "calculate_metrics")
