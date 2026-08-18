from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from aegis.benchmark_config import compute_configuration_hash, load_benchmark_config, validate_config
from aegis.mission027_freeze import (
    BENCHMARK_RATE_POLICY,
    MISSION_017_GEMINI_CONFIGURATION_HASH,
    MISSION_026_PROPOSAL_HASH,
    build_mission027_config,
    build_owner_approved_proposal,
    build_records,
    fairness_report,
    load_mission026_proposal,
    owner_review,
    promote_nvidia_baseline,
    validation_only,
)
from aegis.nvidia_provider import NvidiaParticipantRegistry
from aegis.participant_freeze import OwnerReviewDecision, PromotionError, ParticipantFreezeProposal, compute_participant_hash

ROOT = Path(__file__).resolve().parents[2]


def _build() -> tuple:
    return build_mission027_config(ROOT)


def test_complete_owner_review_is_explicit_and_hash_anchored() -> None:
    _config, _proposal, promotion, review = _build()
    record = review.to_dict()
    assert record["approved"] is True
    assert record["owner"] == "PROJECT_OWNER"
    assert record["reviewer"] == "PROJECT_OWNER"
    assert record["reviewed_at"] == "2026-08-18T10:40:27+00:00"
    assert record["correlation_id"] == "2a1d3d0b-9f61-4b9f-a995-a3d6d32b1d90"
    assert MISSION_026_PROPOSAL_HASH == "4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f"
    assert promotion.promotion.prior_status == "NOT_READY"


def test_incomplete_or_unapproved_review_fails_closed() -> None:
    _config, proposal, _promotion, _review = _build()
    with pytest.raises(PromotionError, match="explicit owner approval"):
        from aegis.participant_freeze import promote_participant

        promote_participant(
            proposal,
            OwnerReviewDecision(
                participant_id="BASELINE_B",
                approved=False,
                owner="PROJECT_OWNER",
                reviewer="PROJECT_OWNER",
                rationale="Not approved",
                reviewed_at="2026-08-18T10:40:27+00:00",
                correlation_id="2a1d3d0b-9f61-4b9f-a995-a3d6d32b1d90",
            ),
        )
    with pytest.raises(ValueError, match="rationale is required"):
        OwnerReviewDecision(
            participant_id="BASELINE_B",
            approved=True,
            owner="PROJECT_OWNER",
            reviewer="PROJECT_OWNER",
            rationale="",
            reviewed_at="2026-08-18T10:40:27+00:00",
            correlation_id="2a1d3d0b-9f61-4b9f-a995-a3d6d32b1d90",
        )


def test_deterministic_participant_promotion() -> None:
    source = load_mission026_proposal(ROOT)
    first, first_review = promote_nvidia_baseline(source)
    second, second_review = promote_nvidia_baseline(source)
    assert first.participant_spec.configuration_hash == second.participant_spec.configuration_hash
    assert first.promotion.to_dict() == second.promotion.to_dict()
    assert first_review.to_dict() == second_review.to_dict()
    assert first.participant_spec.status == "READY"


def test_readiness_transition_is_append_only() -> None:
    config, source, promotion, review = _build()
    records = build_records(config, source, promotion, review, validation_only(config))
    assert source.prior_status == "NOT_READY"
    assert records["readiness_promotions"][0]["prior_status"] == "NOT_READY"
    assert records["readiness_promotions"][0]["new_status"] == "READY"
    assert records["participant_states"] == {"BASELINE_A": "READY", "BASELINE_B": "READY", "AEGIS": "READY"}


def test_rate_policy_is_included_in_participant_hash_and_provider_limit_is_unknown() -> None:
    source = load_mission026_proposal(ROOT)
    approved = build_owner_approved_proposal(source)
    assert approved.configuration["benchmark_rate_policy"] == BENCHMARK_RATE_POLICY
    assert approved.configuration["rate_limit"]["provider_limit"] == "UNKNOWN"
    altered_metadata = dict(approved.configuration)
    altered_policy = dict(altered_metadata["benchmark_rate_policy"])
    altered_policy["benchmark_requests_per_minute"] = 7
    altered_metadata["benchmark_rate_policy"] = altered_policy
    altered = ParticipantFreezeProposal(
        participant_id=approved.participant_id,
        prior_status=approved.prior_status,
        implementation_revision=approved.implementation_revision,
        configuration=altered_metadata,
        timeout_policy=approved.timeout_policy,
        retry_policy=approved.retry_policy,
        output_normalization_policy=approved.output_normalization_policy,
        provenance=approved.provenance,
        artifact_schema=approved.artifact_schema,
        execution_policy=approved.execution_policy,
        verification_policy=approved.verification_policy,
        commit_policy=approved.commit_policy,
    )
    assert altered.configuration_hash != approved.configuration_hash
    assert compute_participant_hash(approved) == approved.configuration_hash


def test_new_configuration_hash_and_frozen_fields() -> None:
    config, _proposal, promotion, _review = _build()
    assert config.configuration_hash == "8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4"
    assert compute_configuration_hash(config) == config.configuration_hash
    assert validate_config(config).valid
    assert config.configuration_hash != MISSION_017_GEMINI_CONFIGURATION_HASH
    assert config.mutation_class_ids == ("M001", "M002", "M003", "M004", "M005", "M006")
    assert config.mutation_severity["M005"] == "L5"
    assert config.seeds == (12345,)
    assert config.trial_count == 1
    assert config.collection_policy["trials_per_mutation"] == 10
    assert config.timeout_policy["total_ms"] == 300000
    assert config.retry_policy["backoff_ms"] == 0
    assert config.metric_formula_version == "mission-010-metrics-v1"
    assert config.baselines[1].status == "READY"
    assert config.baselines[1].metadata["provider"] == "NVIDIA_NIM"
    assert config.baselines[1].metadata["model_identifier"] == "openai/gpt-oss-20b"
    assert config.baselines[1].configuration_hash == promotion.participant_spec.configuration_hash


def test_successor_preserves_shared_configuration_and_non_baseline_b_slots() -> None:
    new_config, _proposal, _promotion, _review = _build()
    old_config = load_benchmark_config(ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json")
    assert new_config.fixture_id == old_config.fixture_id
    assert new_config.fixture_version == old_config.fixture_version
    assert new_config.mutation_class_ids == old_config.mutation_class_ids
    assert new_config.mutation_severity == old_config.mutation_severity
    assert new_config.seeds == old_config.seeds
    assert new_config.trial_count == old_config.trial_count
    assert new_config.timeout_policy == old_config.timeout_policy
    assert new_config.retry_policy == old_config.retry_policy
    assert new_config.metric_formula_version == old_config.metric_formula_version
    assert new_config.baselines[0] == old_config.baselines[0]
    assert new_config.baselines[2] == old_config.baselines[2]
    assert new_config.baselines[1].metadata["provider"] == "NVIDIA_NIM"
    assert new_config.baselines[1].metadata["model_identifier"] == "openai/gpt-oss-20b"


def test_fairness_passes_and_only_provider_model_execution_differs() -> None:
    config, _proposal, _promotion, _review = _build()
    fairness = fairness_report(config)
    assert fairness["status"] == "PASS"
    assert all(fairness[key] for key in fairness if key != "status")


def test_validation_only_dry_run_is_ready_but_execution_free() -> None:
    config, _proposal, _promotion, _review = _build()
    result = validation_only(config)
    assert result.status.value == "READY_TO_EXECUTE"
    assert result.expected_run_count == 18
    assert result.execution_authorized is False
    assert result.benchmark_runs_executed == 0
    assert result.provider_operations_executed == 0
    assert result.healing_operations_executed == 0
    assert result.metric_results_generated == 0


def test_no_nvidia_provider_call_in_mission027_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("Mission 027 dry-run must not call NVIDIA")

    monkeypatch.setattr("aegis.nvidia_provider.NvidiaModelCaller.__call__", forbidden)
    config, _proposal, _promotion, _review = _build()
    result = validation_only(config)
    assert result.status.value == "READY_TO_EXECUTE"
    assert called is False
    assert isinstance(NvidiaParticipantRegistry(config), NvidiaParticipantRegistry)


def test_no_gemini_or_bright_data_operation_in_mission027() -> None:
    config, _proposal, _promotion, _review = _build()
    assert config.baselines[1].metadata["provider"] == "NVIDIA_NIM"
    assert config.baselines[1].metadata["provider"] != "GOOGLE_GEMINI_API"
    assert config.baselines[1].metadata["provider"] != "BRIGHT_DATA"
    assert config.collection_policy["provider_execution"] == "NOT_EXECUTED"


def test_historical_gemini_config_and_evidence_remain_unchanged() -> None:
    config_path = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
    smoke_path = ROOT / "benchmarks/runs/mission_016_floor_59a11e27a71f"
    historical = load_benchmark_config(config_path)
    assert historical.configuration_hash == MISSION_017_GEMINI_CONFIGURATION_HASH
    assert historical.baselines[1].metadata["provider"] == "GOOGLE_GEMINI_API"
    assert subprocess.run(["git", "diff", "--quiet", "main", "--", str(config_path.relative_to(ROOT))], cwd=ROOT).returncode == 0
    assert subprocess.run(["git", "diff", "--quiet", "main", "--", str(smoke_path.relative_to(ROOT))], cwd=ROOT).returncode == 0


def test_generated_records_preserve_source_hash_and_counters() -> None:
    config, source, promotion, review = _build()
    dry_run = validation_only(config)
    records = build_records(config, source, promotion, review, dry_run)
    assert records["participant_proposal_hash"] == MISSION_026_PROPOSAL_HASH
    assert records["owner_review_decisions"]["BASELINE_B"]["participant_hash"] == MISSION_026_PROPOSAL_HASH
    assert records["promoted_participant_hash"] == promotion.participant_spec.configuration_hash
    assert records["new_configuration_hash"] == config.configuration_hash
    assert records["fairness"]["status"] == "PASS"
    assert records["validation_only_protocol"]["planned_opportunities"] == 180
    assert records["validation_only_protocol"]["provider_operations_executed"] == 0
    assert records["validation_only_protocol"]["metric_results_generated"] == 0


def test_no_benchmark_run_root_is_created() -> None:
    config, _proposal, _promotion, _review = _build()
    validation_only(config)
    assert not (ROOT / config.artifact_root).exists()
