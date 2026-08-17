from __future__ import annotations

import pytest

from aegis.mutation_lab import MutationLab, MutationOutcome, MutationSeverity
from aegis.models import ProviderProvenance


MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")


def test_baseline_fixture_is_deterministic_and_known() -> None:
    first = MutationLab().fixture
    second = MutationLab().fixture
    assert first == second
    assert first.records[0]["price"] == 599
    assert first.records[0]["product_id"] == "gpu-1"
    assert first.fixture_version == "1"


def test_all_required_mutations_exist_and_cover_all_severity_levels() -> None:
    lab = MutationLab()
    assert lab.mutation_ids == MUTATIONS
    assert {lab.definition(mutation_id).severity for mutation_id in MUTATIONS} == {
        MutationSeverity.L1,
        MutationSeverity.L2,
        MutationSeverity.L3,
        MutationSeverity.L4,
        MutationSeverity.L5,
    }
    assert sum(lab.definition(mutation_id).severity is MutationSeverity.L5 for mutation_id in MUTATIONS) == 2


@pytest.mark.parametrize("mutation_id", MUTATIONS)
def test_same_seed_reproduces_identical_mutation_and_ground_truth(mutation_id: str) -> None:
    lab = MutationLab()
    first = lab.apply_mutation(mutation_id, 12345)
    second = lab.apply_mutation(mutation_id, 12345)
    assert first.mutated.fixture == second.mutated.fixture
    assert first.mutated.mutation_metadata == second.mutated.mutation_metadata
    assert first.ground_truth.expected_correct_state == second.ground_truth.expected_correct_state
    assert first.ground_truth.expected_corrupted_state == second.ground_truth.expected_corrupted_state
    assert first.ground_truth.deterministic_metadata == second.ground_truth.deterministic_metadata


@pytest.mark.parametrize("mutation_id", MUTATIONS)
def test_mutation_is_reversible_and_ground_truth_is_explicit(mutation_id: str) -> None:
    case = MutationLab().apply_mutation(mutation_id, 42)
    assert case.mutated.revert() == case.baseline
    assert case.ground_truth.mutation_id == mutation_id
    assert case.ground_truth.seed == 42
    assert case.ground_truth.severity is case.severity
    assert case.ground_truth.baseline_fixture_reference.startswith("fixture://")
    assert case.ground_truth.mutated_fixture_reference.endswith(f"/{mutation_id}/42")
    assert case.ground_truth.expected_detector_behavior
    assert case.ground_truth.expected_safety_behavior
    with pytest.raises((AttributeError, TypeError)):
        case.ground_truth.affected_fields += ("unexpected",)  # type: ignore[misc]


def test_l1_cosmetic_mutation_keeps_extraction_data_correct() -> None:
    case = MutationLab().apply_mutation("M001", 11)
    assert case.mutated.fixture.records == case.baseline.records
    assert case.mutated.fixture.page_markup != case.baseline.page_markup
    assert case.ground_truth.severity is MutationSeverity.L1


def test_l2_structural_mutation_changes_required_schema_field() -> None:
    case = MutationLab().apply_mutation("M002", 11)
    assert "availability" in case.baseline.records[0]
    assert "availability" not in case.mutated.fixture.records[0]
    assert case.ground_truth.affected_fields == ("availability",)


def test_l3_semantic_mutation_changes_meaningful_value() -> None:
    case = MutationLab().apply_mutation("M003", 11)
    assert case.mutated.fixture.records[0]["price"] == -599
    assert case.baseline.records[0]["price"] == 599
    assert case.ground_truth.severity is MutationSeverity.L3


def test_l4_behavioral_mutation_removes_expected_page_result() -> None:
    case = MutationLab().apply_mutation("M004", 11)
    assert case.baseline.records
    assert case.mutated.fixture.records == ()
    assert case.ground_truth.deterministic_metadata["mutation_metadata"]["mechanism"] == "deterministic_pagination_drop"


def test_l5_value_swap_preserves_schema_and_numeric_type() -> None:
    lab = MutationLab()
    case = lab.apply_mutation("M005", 11)
    baseline_row = case.baseline.records[0]
    mutated_row = case.mutated.fixture.records[0]
    assert set(mutated_row) == set(baseline_row)
    assert isinstance(mutated_row["price"], (int, float))
    assert mutated_row["price"] == 29.99
    assert baseline_row["price"] == 599
    assert case.ground_truth.severity is MutationSeverity.L5


def test_l5_plausible_decoy_preserves_schema_and_type() -> None:
    case = MutationLab().apply_mutation("M006", 11)
    baseline_row = case.baseline.records[0]
    mutated_row = case.mutated.fixture.records[0]
    assert set(mutated_row) == set(baseline_row)
    assert type(mutated_row["price"]) is float
    assert mutated_row["price"] != baseline_row["price"]
    assert case.ground_truth.severity is MutationSeverity.L5


@pytest.mark.parametrize("mutation_id", MUTATIONS)
def test_run_records_ground_truth_and_test_double_provenance(mutation_id: str) -> None:
    run, case, detection, verification, risk = MutationLab().run(mutation_id, 12345)
    assert run.mutation_id == mutation_id
    assert run.seed == 12345
    assert run.ground_truth_reference == f"ground-truth://{case.ground_truth.ground_truth_id}"
    assert run.observation_reference.startswith("observation://")
    assert run.detection_reference.startswith("detection://")
    assert run.verification_reference is not None
    assert run.risk_decision_reference is not None
    assert run.provenance is ProviderProvenance.TEST_DOUBLE
    assert run.collector_reference == "mutation-lab-test-double"
    assert run.output_eligible is False
    assert detection is not None
    assert verification is not None
    assert risk is not None


def test_l5_value_swap_is_not_healthy_and_cannot_be_shipped() -> None:
    run, case, detection, verification, risk = MutationLab().run("M005", 12345)
    assert case.ground_truth.expected_correct_state["records"][0]["price"] == 599
    assert case.ground_truth.expected_corrupted_state["records"][0]["price"] == 29.99
    assert detection.detected is False  # valid schema/type is intentionally silent to basic detection
    assert run.detected is True  # verification/history/independent evidence detects the known corruption
    assert verification.overall_status.value == "FAIL"
    assert risk.decision.value in {"REJECT", "QUARANTINE"}
    assert run.commit_eligibility == "BLOCKED"
    assert run.output_eligible is False
    assert run.outcome in {MutationOutcome.DETECTED_REJECTED, MutationOutcome.DETECTED_QUARANTINED}


def test_l5_plausible_decoy_is_not_healthy_and_cannot_be_shipped() -> None:
    run, _, detection, verification, risk = MutationLab().run("M006", 12345)
    assert detection.detected is False
    assert verification.overall_status.value == "FAIL"
    assert risk.decision.value in {"REJECT", "QUARANTINE"}
    assert run.detected is True
    assert run.output_eligible is False


def test_l1_healthy_path_still_cannot_fake_production_commit() -> None:
    run, _, detection, verification, risk = MutationLab().run("M001", 12345)
    assert detection.detected is False
    assert verification.overall_status.value == "PASS"
    assert risk.decision.value == "ACCEPT"
    assert run.outcome is MutationOutcome.HEALTHY
    assert run.commit_eligibility == "BLOCKED"  # candidate remains an uncommitted TEST_DOUBLE proposal
    assert run.output_eligible is False


def test_existing_detection_consumes_mutated_observation_for_structural_semantic_and_behavioral_cases() -> None:
    lab = MutationLab()
    for mutation_id in ("M002", "M003", "M004"):
        run, _, detection, _, _ = lab.run(mutation_id, 12345)
        assert detection.detected is True
        assert run.detected_by_existing_detection is True


def test_mutation_lab_has_no_benchmark_runner_or_provider_operation() -> None:
    lab = MutationLab()
    assert not hasattr(lab, "run_benchmark")
    assert not hasattr(lab, "approve")
    assert not hasattr(lab, "rollback")
    assert all(lab.run(mutation_id, 7)[0].provenance is ProviderProvenance.TEST_DOUBLE for mutation_id in MUTATIONS)
