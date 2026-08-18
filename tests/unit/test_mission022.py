from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aegis import mutation_metrics
from aegis.benchmark_runner import NOT_APPLICABLE, ParticipantRunEvidence, RunnerState
from aegis.benchmark_executor import EXPECTED_BENCHMARK_RUN_ID, BenchmarkExecutor, FixtureController
from aegis.benchmark_config import load_benchmark_config
from aegis.metric_boundary import (
    METRIC_COMPATIBILITY_MATRIX,
    MetricBoundaryError,
    ParticipantEvidenceContext,
    adapt_completed_evidence,
    calculate_compatibility_metrics,
)
from aegis.models import ProviderProvenance
from aegis.mutation_lab import MutationLab

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
FIXED_TIME = datetime(2026, 8, 18, tzinfo=timezone.utc)


def _truth_and_evidence(
    *,
    participant_id: str = "AEGIS",
    mutation_id: str = "M005",
    severity: str = "L5",
    detected: bool | str = True,
    verification_status: str = "FAIL",
    risk_decision: str = "QUARANTINE",
    output_eligible: bool | str = False,
    run_suffix: str = "aegis__M005__trial-1__seed-12345",
    include_refs: bool = True,
):
    lab = MutationLab()
    case = lab.apply_mutation(mutation_id, 12345)
    truth_ref = f"ground-truth://gpu-price-staging/v1/{mutation_id}/12345/trial-1"
    run_id = f"mission_020_floor_2a80a8cf8d989326__participant-{run_suffix}"
    refs = (truth_ref, "detection://run", "verification://run", "risk://run") if include_refs else ()
    artifacts = ("benchmarks/runs/mission_020_floor_2a80a8cf8d989326/raw/run.json",) if include_refs else ()
    evidence = ParticipantRunEvidence(
        participant_id=participant_id,
        run_id=run_id,
        mutation_id=mutation_id,
        severity=severity,
        seed=12345,
        fixture_version="1",
        participant_revision="participant-revision",
        configuration_hash="59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b",
        ground_truth_reference=truth_ref,
        code_revision="b79050044be0a6d919eecd5633f72188469022df",
        environment_reference="test-double",
        timeout_policy={"total_ms": 1800000},
        retry_policy={"max_attempts": 1},
        artifact_root="benchmarks/runs/mission_020_floor_2a80a8cf8d989326",
        observation_reference="observation://run",
        detected=detected,
        verification_status=verification_status,
        risk_decision=risk_decision,
        output_eligible=output_eligible,
        failure_state="COMPLETED",
        timing_ms={"detection": 3, "verification": 4, "risk": 5, "total": 12},
        cost=NOT_APPLICABLE,
        llm_calls=0,
        evidence_refs=refs,
        artifact_refs=artifacts,
        provenance="TEST_DOUBLE",
        state=RunnerState.COMPLETED,
        candidate={"candidate": "preserved"},
        candidate_application={"application_mode": "SAFE_TEST_DOUBLE_BOUNDARY"},
    )
    context = ParticipantEvidenceContext(
        run_id=run_id,
        benchmark_id="AEGIS-BENCHMARK-V1",
        configuration_hash=evidence.configuration_hash,
        participant_configuration_hash="participant-config-hash",
        participant_revision=evidence.participant_revision,
        mutation_id=mutation_id,
        severity=severity,
        seed=12345,
        fixture_version="1",
        ground_truth_reference=truth_ref,
        trial_number=1,
        artifact_root=evidence.artifact_root,
        artifact_name="run.json",
    )
    return evidence, context, case.ground_truth


def test_complete_evidence_adapts_and_joins_truth_only_after_execution() -> None:
    evidence, context, truth = _truth_and_evidence()
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    assert report.passed is True
    assert len(report.records) == 1
    assert len(report.metric_inputs) == 1
    metric_input = report.metric_inputs[0]
    assert metric_input.ground_truth_reference.startswith("ground-truth://mission-022/")
    assert metric_input.participant_configuration_hash == "participant-config-hash"
    assert metric_input.trial_number == 1
    assert truth.expected_corrupted_state
    assert "expected_corrupted_state" not in json.dumps(metric_input.to_dict(), sort_keys=True)
    assert report.records[0].ground_truth_joined is True


def test_missing_required_evidence_fails_closed() -> None:
    evidence, context, truth = _truth_and_evidence(include_refs=False)
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    assert report.passed is False
    assert any("evidence_refs" in error for error in report.fatal_errors)
    with pytest.raises(MetricBoundaryError, match="FAILED_METRIC_BOUNDARY"):
        calculate_compatibility_metrics(report)


def test_missing_ground_truth_is_evaluator_boundary_failure() -> None:
    evidence, context, _truth = _truth_and_evidence()
    report = adapt_completed_evidence([evidence], {}, {evidence.run_id: context})
    assert report.passed is False
    assert any("missing evaluator ground truth" in error for error in report.fatal_errors)


def test_adaptation_is_deterministic_and_preserves_references_and_severity() -> None:
    evidence, context, truth = _truth_and_evidence()
    first = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    second = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    assert first.to_json() == second.to_json()
    record = first.records[0]
    assert record.source_evidence.evidence_refs == evidence.evidence_refs
    assert record.source_evidence.artifact_refs == evidence.artifact_refs
    assert record.context is not None and record.context.severity == "L5"
    assert record.metric_input is not None and record.metric_input.evidence_refs[-1] == evidence.artifact_refs[0]
    assert first.metric_matrix["L5BadDataShippedRate"]["denominator_source"] == "joined truth severity == L5"


def test_baseline_not_applicable_fields_remain_honest() -> None:
    for participant_id in ("BASELINE_A", "BASELINE_B"):
        evidence, context, truth = _truth_and_evidence(
            participant_id=participant_id,
            detected=NOT_APPLICABLE,
            verification_status=NOT_APPLICABLE,
            risk_decision=NOT_APPLICABLE,
            output_eligible=NOT_APPLICABLE,
            run_suffix=f"{participant_id.lower()}__M005__trial-1__seed-12345",
        )
        report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
        assert report.passed is True
        assert report.metric_inputs == ()
        assert report.records[0].metric_eligible is False
        assert report.records[0].reason.startswith("participant fields are NOT_APPLICABLE")


def test_aegis_fields_feed_existing_mission010_calculator_and_l5_shipment_is_preserved() -> None:
    evidence, context, truth = _truth_and_evidence(output_eligible=True)
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    metric_report = calculate_compatibility_metrics(report)
    shipped = next(item for item in metric_report.results if item.metric_name == "L5BadDataShippedRate")
    assert shipped.numerator == 1
    assert shipped.denominator == 1
    assert shipped.value == 1.0
    assert shipped.evidence_references


def test_zero_denominators_use_existing_not_applicable_semantics() -> None:
    evidence, context, truth = _truth_and_evidence(mutation_id="M001", severity="L1", detected=False, verification_status=NOT_APPLICABLE, risk_decision=NOT_APPLICABLE)
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    metric_report = calculate_compatibility_metrics(report)
    detection = next(item for item in metric_report.results if item.metric_name == "DetectionRate" and item.scope.get("level") == "overall")
    l5 = next(item for item in metric_report.results if item.metric_name == "L5DetectionRate")
    assert detection.status.value == "NOT_APPLICABLE"
    assert detection.value is None
    assert l5.status.value == "NOT_APPLICABLE"
    assert l5.value is None


def test_synthetic_180_run_test_double_dataset_reaches_only_mission010_calculator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aegis.benchmark_executor import BenchmarkExecutor

    calls = 0
    original = mutation_metrics.calculate_metrics

    def spy(runs, truths, *, generated_at=None):
        nonlocal calls
        calls += 1
        assert len(runs) == 60
        assert len(truths) == 60
        return original(runs, truths, generated_at=generated_at)

    monkeypatch.setattr(mutation_metrics, "calculate_metrics", spy)
    cfg = load_benchmark_config(CONFIG_PATH)
    executor = BenchmarkExecutor(
        cfg,
        repository_root=tmp_path,
        output_root=tmp_path / "benchmarks/runs/mission_020_floor_2a80a8cf8d989326",
        source_revision_checker=lambda _revision, _path: True,
        smoke_evidence_validator=lambda: {"pass": True, "status": "VALID", "checks": {}},
        model_caller=lambda _system, _repair: {"candidates": [{"candidate": {"code": "test"}}]},
    )
    summary = executor.execute()
    assert summary.status == "COMPLETED"
    assert summary.completed_runs == 180
    assert summary.benchmark_runs_executed == 180
    assert summary.metric_results_generated > 0
    assert calls == 1
    compatibility = json.loads((tmp_path / "benchmarks/runs/mission_020_floor_2a80a8cf8d989326/reports/mission-022-metric-boundary-compatibility.json").read_text(encoding="utf-8"))
    assert compatibility["record_count"] == 180
    assert compatibility["metric_input_count"] == 60
    assert compatibility["ground_truth_joined_count"] == 180
    assert (tmp_path / "benchmarks/runs/mission_020_floor_2a80a8cf8d989326/metrics/mission-010-metrics.json").is_file()


def test_compatibility_matrix_covers_requested_metrics() -> None:
    expected = {
        "DetectionRate", "AlarmPrecision", "VerifiedRecovery", "VerificationMissRate", "FalseRepairRate",
        "UnsafeRefusalRate", "BlindCommitRate", "MTTR", "CostPerRepair", "LLMCallsPerRepair",
        "L5DetectionRate", "L5QuarantineRate", "L5VerifiedReExtraction", "L5BadDataShippedRate",
    }
    assert expected <= set(METRIC_COMPATIBILITY_MATRIX)
