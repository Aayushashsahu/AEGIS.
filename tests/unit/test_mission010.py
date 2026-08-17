from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from aegis.mutation_metrics import (
    MetricStatus,
    build_mission009_dataset,
    calculate_metrics,
    export_manifest,
)


MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")


def _result(report, metric_name: str, level: str = "overall", **scope):
    wanted = {"level": level, **scope}
    matches = [result for result in report.results if result.metric_name == metric_name and all(result.scope.get(key) == value for key, value in wanted.items())]
    assert len(matches) == 1, (metric_name, wanted)
    return matches[0]


def test_manifest_is_deterministic_and_ordered_by_mutation_and_run() -> None:
    runs, truths = build_mission009_dataset()
    independent_runs, independent_truths = build_mission009_dataset()
    assert export_manifest(runs, truths) == export_manifest(independent_runs, independent_truths)
    first = export_manifest(tuple(reversed(runs)), truths)
    second = export_manifest(runs, truths)
    assert first == second
    payload = json.loads(first)
    assert payload["run_count"] == 6
    assert [record["mutation_id"] for record in payload["runs"]] == list(MUTATIONS)
    assert payload["provenance"] == "TEST_DOUBLE"
    assert payload["severities"] == ["L1", "L2", "L3", "L4", "L5"]
    assert payload["fixture_versions"] == ["1"]
    assert all(record["timestamp"] == "2026-08-17T00:00:00+00:00" for record in payload["runs"])


def test_manifest_preserves_required_fields_and_evidence_references() -> None:
    runs, truths = build_mission009_dataset()
    record = json.loads(export_manifest(runs, truths))["runs"][4]
    required = {
        "run_id", "mutation_id", "severity", "seed", "fixture_version",
        "baseline_reference", "mutated_reference", "ground_truth_reference",
        "provenance", "detection_outcome", "detected_by_existing_detection",
        "detector_severity", "verification_result", "risk_decision",
        "commit_gate_result", "output_eligible", "quarantine_reference",
        "timing_ms", "timestamp", "evidence_references", "ground_truth",
    }
    assert required <= set(record)
    assert record["mutation_id"] == "M005"
    assert record["severity"] == "L5"
    assert record["ground_truth"]["actual_failure"] is True
    assert record["evidence_references"]
    assert all(ref.startswith(("ground-truth://", "contract://", "history://", "observation://", "detection://", "verification://", "semantic://", "independent://", "risk://", "quarantine://")) for ref in record["evidence_references"])


def test_manifest_reuses_existing_redaction_for_secret_bearing_evidence() -> None:
    runs, truths = build_mission009_dataset()
    secret_run = replace(runs[0], evidence_refs=("Authorization: Bearer test-secret-value", "api_key=should-not-export"))
    text = export_manifest((secret_run,), truths)
    assert "test-secret-value" not in text
    assert "should-not-export" not in text
    assert "[REDACTED_REFERENCE]" in text


def test_detection_rate_is_measured_over_actual_failures_and_per_severity() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    overall = _result(report, "DetectionRate")
    assert overall.status is MetricStatus.MEASURED
    assert overall.numerator == 5
    assert overall.denominator == 5
    assert overall.value == 1.0
    assert _result(report, "DetectionRate", "severity", severity="L1").status is MetricStatus.NOT_APPLICABLE
    for severity in ("L2", "L3", "L4", "L5"):
        result = _result(report, "DetectionRate", "severity", severity=severity)
        assert result.status is MetricStatus.MEASURED
        assert result.value == 1.0


def test_alarm_precision_is_not_applicable_when_no_alarm_exists() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics((runs[0],), truths)
    result = _result(report, "AlarmPrecision")
    assert result.status is MetricStatus.NOT_APPLICABLE
    assert result.value is None
    assert result.numerator == 0
    assert result.denominator == 0


def test_alarm_precision_is_measured_from_ground_truth_not_detector_alone() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    result = _result(report, "AlarmPrecision")
    assert result.status is MetricStatus.MEASURED
    assert result.numerator == 5
    assert result.denominator == 5
    assert result.value == 1.0
    assert _result(report, "AlarmPrecision", "mutation", mutation_id="M001").status is MetricStatus.NOT_APPLICABLE


def test_recovery_verification_miss_false_repair_and_blind_commit_are_not_fabricated() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    for name in ("VerifiedRecovery", "VerificationMissRate", "FalseRepairRate", "BlindCommitRate", "MTTR", "CostPerRepair", "LLMCallsPerRepair"):
        result = _result(report, name)
        assert result.status is MetricStatus.NOT_APPLICABLE
        assert result.value is None
        assert result.denominator == 0


def test_l5_safety_metrics_are_explicit_controlled_harness_results() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    assert _result(report, "L5DetectionRate").value == 1.0
    assert _result(report, "L5QuarantineCount").value == 2
    assert _result(report, "L5QuarantineRate").value == 1.0
    assert _result(report, "L5OutputEligibleCount").value == 0
    shipped = _result(report, "L5BadDataShippedCount")
    shipped_rate = _result(report, "L5BadDataShippedRate")
    assert shipped.value == 0
    assert shipped_rate.value == 0.0
    assert all(result.scope["result_class"] == "CONTROLLED_HARNESS_RESULT" for result in report.results if result.metric_name.startswith("L5") or result.metric_name == "UnsafeRefusalRate")


def test_unsafe_refusal_rate_is_measured_for_l5_actual_failures() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    result = _result(report, "UnsafeRefusalRate")
    assert result.status is MetricStatus.MEASURED
    assert result.numerator == 2
    assert result.denominator == 2
    assert result.value == 1.0


def test_per_mutation_results_are_traceable_to_exact_run_ids() -> None:
    runs, truths = build_mission009_dataset()
    report = calculate_metrics(runs, truths)
    for mutation_id, run in zip(MUTATIONS, runs):
        result = _result(report, "DetectionRate", "mutation", mutation_id=mutation_id)
        assert result.mutation_ids == (mutation_id,)
        assert result.run_count == 1
        assert any(run.evidence_refs[0] == reference for reference in result.evidence_references)


def test_mutation_severity_and_observed_detector_severity_remain_distinct() -> None:
    runs, truths = build_mission009_dataset()
    manifest = json.loads(export_manifest(runs, truths))
    m004 = next(record for record in manifest["runs"] if record["mutation_id"] == "M004")
    assert m004["severity"] == "L4"
    assert m004["detector_severity"] == "L3"


def test_metric_result_is_immutable_and_metric_output_is_byte_stable() -> None:
    runs, truths = build_mission009_dataset()
    first = calculate_metrics(runs, truths).to_json()
    second = calculate_metrics(tuple(reversed(runs)), truths).to_json()
    assert first == second
    result = _result(calculate_metrics(runs, truths), "DetectionRate")
    with pytest.raises(FrozenInstanceError):
        result.value = 0.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.scope["new"] = "value"  # type: ignore[index]


def test_metric_json_has_no_generation_timestamp_by_default() -> None:
    runs, truths = build_mission009_dataset()
    payload = json.loads(calculate_metrics(runs, truths).to_json())
    assert payload["generated_at"] is None
    assert all(item["generated_at"] is None for item in payload["results"])
