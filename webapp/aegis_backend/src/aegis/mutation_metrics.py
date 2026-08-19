"""Mission 010 deterministic mutation manifest and metric calculator.

This module consumes immutable Mission 009 MutationRun/MutationGroundTruth
records. It never infers truth from AEGIS output, mutates historical records,
scales the benchmark, or changes provider state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .audit_store import _redact, _to_jsonable
from .immutability import freeze_mapping
from .mutation_lab import MutationGroundTruth, MutationLab, MutationRun, MutationSeverity
from .risk import RiskDecisionType


FORMULA_VERSION = "mission-010-metrics-v1"
CONTROLLED_HARNESS_RESULT = "CONTROLLED_HARNESS_RESULT"


class MetricStatus(str, Enum):
    MEASURED = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class MetricResult:
    metric_name: str
    value: float | int | None
    status: MetricStatus
    numerator: int
    denominator: int
    scope: Mapping[str, Any]
    severity: str | None
    mutation_ids: tuple[str, ...]
    run_count: int
    formula_version: str = FORMULA_VERSION
    generated_at: str | None = None
    evidence_references: tuple[str, ...] = ()
    formula: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", freeze_mapping(self.scope))
        object.__setattr__(self, "mutation_ids", tuple(sorted(self.mutation_ids)))
        object.__setattr__(self, "evidence_references", tuple(sorted(set(self.evidence_references))))
        if self.denominator == 0 and self.status is MetricStatus.MEASURED:
            raise ValueError("measured MetricResult requires a non-zero denominator")
        if self.status is MetricStatus.NOT_APPLICABLE and self.value is not None:
            raise ValueError("NOT_APPLICABLE MetricResult must not contain a value")
        if self.numerator < 0 or self.denominator < 0:
            raise ValueError("metric counts cannot be negative")


@dataclass(frozen=True)
class MetricReport:
    manifest: Mapping[str, Any]
    results: tuple[MetricResult, ...]
    formula_version: str = FORMULA_VERSION
    generated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest", freeze_mapping(self.manifest))
        object.__setattr__(self, "results", tuple(self.results))

    def to_json(self) -> str:
        payload = {
            "formula_version": self.formula_version,
            "generated_at": self.generated_at,
            "manifest": self.manifest,
            "results": [metric_to_dict(result) for result in self.results],
        }
        return json.dumps(_redact(_to_jsonable(payload)), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"

    def to_markdown(self) -> str:
        measured = [result for result in self.results if result.status is MetricStatus.MEASURED]
        unavailable = [result for result in self.results if result.status is not MetricStatus.MEASURED]
        lines = [
            "# Mission 010 Deterministic Mutation Metrics",
            "",
            "> **CONTROLLED_HARNESS_RESULT — not a production benchmark result.**",
            "",
            f"Formula version: `{self.formula_version}`",
            f"Run count: `{self.manifest.get('run_count', 0)}`",
            f"Provenance: `{self.manifest.get('provenance', 'UNKNOWN')}`",
            "",
            "## Manifest summary",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Run IDs | `{', '.join(self.manifest.get('run_ids', ()))}` |",
            f"| Mutation IDs | `{', '.join(self.manifest.get('mutation_ids', ()))}` |",
            f"| Severities | `{', '.join(self.manifest.get('severities', ()))}` |",
            f"| Fixture versions | `{', '.join(self.manifest.get('fixture_versions', ()))}` |",
            "",
            "## Measured controlled-harness metrics",
            "",
            "| Metric | Scope | Formula | Numerator | Denominator | Value |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
        for result in measured:
            scope = _scope_label(result)
            lines.append(f"| {result.metric_name} | {scope} | {result.formula} | {result.numerator} | {result.denominator} | {result.value} |")
        lines.extend([
            "",
            "## Unavailable metrics",
            "",
            "| Metric | Scope | Status | Reason/formula |",
            "| --- | --- | --- | --- |",
        ])
        for result in unavailable:
            lines.append(f"| {result.metric_name} | {_scope_label(result)} | {result.status.value} | {result.formula} |")
        lines.extend([
            "",
            "## L5 safety summary",
            "",
            "| Measure | Result |",
            "| --- | ---: |",
        ])
        for result in self.results:
            if result.metric_name.startswith("L5") and result.scope.get("level") == "overall":
                value = result.value if result.status is MetricStatus.MEASURED else result.status.value
                lines.append(f"| {result.metric_name} | {value} |")
        lines.extend([
            "",
            "## Traceability",
            "",
            "Every metric result carries the run evidence references used in its numerator and denominator. Ground truth is taken only from `MutationGroundTruth`; no result infers actual failure state from the candidate output.",
            "",
            "## Benchmark boundary",
            "",
            "This report covers the Mission 009 six-scenario controlled harness only. It does not claim ten trials per class, frozen A/B/C baselines, 540 runs, production reliability, or a hackathon headline metric.",
            "",
        ])
        return "\n".join(lines)


def manifest_record(run: MutationRun, ground_truth: MutationGroundTruth) -> Mapping[str, Any]:
    fixture_version = ground_truth.deterministic_metadata.get("fixture_version", "UNKNOWN")
    record = {
        "run_id": run.run_id,
        "mutation_id": run.mutation_id,
        "severity": ground_truth.severity.value,
        "seed": run.seed,
        "fixture_version": fixture_version,
        "baseline_reference": ground_truth.baseline_fixture_reference,
        "mutated_reference": ground_truth.mutated_fixture_reference,
        "ground_truth_reference": run.ground_truth_reference,
        "provenance": run.provenance.value,
        "detection_outcome": run.outcome.value,
        "detected": run.detected,
        "detected_by_existing_detection": run.detected_by_existing_detection,
        "detector_severity": run.detector_severity,
        "verification_result": run.verification_status,
        "risk_decision": run.risk_decision,
        "commit_gate_result": run.commit_eligibility,
        "output_eligible": run.output_eligible,
        "quarantine_reference": run.quarantine_reference,
        "timing_ms": dict(run.timing_ms),
        "timestamp": run.created_at.isoformat(),
        "evidence_references": _safe_evidence_references(run.evidence_refs),
        "ground_truth": {
            "actual_failure": ground_truth.severity is not MutationSeverity.L1,
            "expected_behavior": ground_truth.expected_detector_behavior,
            "expected_safety_behavior": ground_truth.expected_safety_behavior,
            "affected_fields": tuple(ground_truth.affected_fields),
        },
    }
    return _redact(_to_jsonable(record))


def export_manifest(runs: Sequence[MutationRun], ground_truths: Mapping[str, MutationGroundTruth], *, generated_at: str | None = None) -> str:
    records = [manifest_record(run, _truth_for_run(run, ground_truths)) for run in runs]
    records.sort(key=lambda record: (record["mutation_id"], record["run_id"]))
    payload = {
        "manifest_version": "mission-010-manifest-v1",
        "formula_version": FORMULA_VERSION,
        "generated_at": generated_at,
        "run_count": len(records),
        "run_ids": tuple(record["run_id"] for record in records),
        "mutation_ids": tuple(sorted({record["mutation_id"] for record in records})),
        "severities": tuple(sorted({record["severity"] for record in records})),
        "fixture_versions": tuple(sorted({record["fixture_version"] for record in records})),
        "provenance": "TEST_DOUBLE" if all(record["provenance"] == "TEST_DOUBLE" for record in records) else "MIXED",
        "runs": records,
    }
    return json.dumps(_redact(_to_jsonable(payload)), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


def calculate_metrics(runs: Sequence[MutationRun], ground_truths: Mapping[str, MutationGroundTruth], *, generated_at: str | None = None) -> MetricReport:
    ordered_runs = tuple(sorted(runs, key=lambda run: (run.mutation_id, run.run_id)))
    manifest_payload = json.loads(export_manifest(ordered_runs, ground_truths, generated_at=generated_at))
    results: list[MetricResult] = []
    results.extend(_detection_results(ordered_runs, ground_truths))
    results.extend(_alarm_results(ordered_runs, ground_truths))
    results.extend(_unsafe_refusal_results(ordered_runs, ground_truths))
    results.extend(_l5_results(ordered_runs, ground_truths))
    for metric_name, formula in (
        ("VerifiedRecovery", "correct verified repairs / actual failures; no repair path in Mission 009"),
        ("VerificationMissRate", "wrong repairs that passed verification / committed repairs; no commits in Mission 009"),
        ("FalseRepairRate", "wrong candidates proposed / repair attempts; no repair attempts in Mission 009"),
        ("BlindCommitRate", "commits without required deterministic verification / total commits; no commit denominator in Mission 009"),
        ("MTTR", "detection timestamp → verified commit timestamp; no verified commit path"),
        ("CostPerRepair", "attributable repair cost / completed repair episodes; no cost ledger"),
        ("LLMCallsPerRepair", "LLM calls / repair episodes; no LLM repair path"),
    ):
        results.append(_not_applicable(metric_name, ordered_runs, formula, scope={"level": "overall"}, mutation_ids=tuple(run.mutation_id for run in ordered_runs)))
    results.sort(key=lambda result: (_metric_order(result.metric_name), str(result.scope), result.severity or "", result.mutation_ids))
    return MetricReport(manifest=manifest_payload, results=tuple(results), formula_version=FORMULA_VERSION, generated_at=generated_at)


def build_mission009_dataset(seed: int = 12345) -> tuple[tuple[MutationRun, ...], Mapping[str, MutationGroundTruth]]:
    """Build a stable representation of the Mission 009 V1 sample run set.

    MutationLab creates the immutable evidence. This function normalizes only
    generated IDs/timing in new immutable copies so exports are reproducible.
    """

    fixed_timestamp = datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc)
    lab = MutationLab()
    runs: list[MutationRun] = []
    truths: dict[str, MutationGroundTruth] = {}
    for mutation_id in lab.mutation_ids:
        run, case, _, _, _ = lab.run(mutation_id, seed)
        stable_truth_id = f"ground_truth_{mutation_id}_{seed}"
        stable_truth = replace(case.ground_truth, ground_truth_id=stable_truth_id, created_at=fixed_timestamp)
        old_truth_ref = f"ground-truth://{case.ground_truth.ground_truth_id}"
        new_truth_ref = f"ground-truth://{stable_truth_id}"
        stable_evidence: list[str] = []
        for ref in run.evidence_refs:
            if ref == old_truth_ref:
                stable_evidence.append(new_truth_ref)
            elif ref.startswith("observation://"):
                stable_evidence.append(f"observation://mutation-{mutation_id}-{seed}")
            elif ref.startswith("detection://"):
                stable_evidence.append(f"detection://mutation-{mutation_id}-{seed}")
            elif ref.startswith("verification://"):
                stable_evidence.append(f"verification://mutation-{mutation_id}-{seed}")
            elif ref.startswith("risk://"):
                stable_evidence.append(f"risk://mutation-{mutation_id}-{seed}")
            else:
                stable_evidence.append(ref)
        stable_evidence = tuple(sorted(set(stable_evidence)))
        stable_run = replace(
            run,
            run_id=f"mutation_run_{mutation_id}_{seed}",
            observation_reference=f"observation://mutation-{mutation_id}-{seed}",
            detection_reference=f"detection://mutation-{mutation_id}-{seed}",
            verification_reference=f"verification://mutation-{mutation_id}-{seed}",
            risk_decision_reference=f"risk://mutation-{mutation_id}-{seed}",
            ground_truth_reference=new_truth_ref,
            timing_ms={"detection": 0, "verification": 0, "risk": 0, "total": 0},
            quarantine_reference=f"quarantine://mutation-{mutation_id}-{seed}" if run.quarantine_reference else None,
            evidence_refs=stable_evidence,
            created_at=fixed_timestamp,
        )
        runs.append(stable_run)
        truths[stable_truth_id] = stable_truth
    return tuple(runs), truths


def _truth_for_run(run: MutationRun, ground_truths: Mapping[str, MutationGroundTruth]) -> MutationGroundTruth:
    truth_id = run.ground_truth_reference.rsplit("/", 1)[-1]
    if truth_id not in ground_truths:
        raise ValueError(f"missing ground truth for run {run.run_id}: {truth_id}")
    return ground_truths[truth_id]


def _scope_evidence(runs: Sequence[MutationRun]) -> tuple[str, ...]:
    return tuple(sorted({ref for run in runs for ref in _safe_evidence_references(run.evidence_refs)}))


def _safe_evidence_references(references: Sequence[str]) -> tuple[str, ...]:
    """Reuse audit redaction and fail closed for non-reference-shaped strings."""
    safe: list[str] = []
    for reference in references:
        redacted = _redact(reference)
        lowered = reference.lower()
        if redacted != reference or any(token in lowered for token in ("api_key=", "apikey=", "authorization=", "credential=", "password=", "secret=", "token=")):
            safe.append("[REDACTED_REFERENCE]")
        else:
            safe.append(reference)
    return tuple(sorted(set(safe)))


def _metric(metric_name: str, value: float | int | None, numerator: int, denominator: int, runs: Sequence[MutationRun], *, scope: Mapping[str, Any], severity: str | None = None, status: MetricStatus | None = None, formula: str) -> MetricResult:
    final_status = status or (MetricStatus.MEASURED if denominator > 0 else MetricStatus.NOT_APPLICABLE)
    final_value = value if final_status is MetricStatus.MEASURED else None
    return MetricResult(metric_name=metric_name, value=final_value, status=final_status, numerator=numerator, denominator=denominator, scope=scope, severity=severity, mutation_ids=tuple(run.mutation_id for run in runs), run_count=len(runs), evidence_references=_scope_evidence(runs), formula=formula)


def _not_applicable(metric_name: str, runs: Sequence[MutationRun], formula: str, *, scope: Mapping[str, Any], mutation_ids: tuple[str, ...]) -> MetricResult:
    return MetricResult(metric_name=metric_name, value=None, status=MetricStatus.NOT_APPLICABLE, numerator=0, denominator=0, scope=scope, severity=scope.get("severity"), mutation_ids=mutation_ids, run_count=len(runs), evidence_references=_scope_evidence(runs), formula=formula)


def _detection_results(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth]) -> list[MetricResult]:
    results: list[MetricResult] = []
    results.append(_detection_metric(runs, truths, {"level": "overall"}))
    for severity in ("L1", "L2", "L3", "L4", "L5"):
        subset = tuple(run for run in runs if _truth_for_run(run, truths).severity.value == severity)
        results.append(_detection_metric(subset, truths, {"level": "severity", "severity": severity}, severity=severity))
    for mutation_id in sorted({run.mutation_id for run in runs}):
        subset = tuple(run for run in runs if run.mutation_id == mutation_id)
        results.append(_detection_metric(subset, truths, {"level": "mutation", "mutation_id": mutation_id}))
    return results


def _detection_metric(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth], scope: Mapping[str, Any], severity: str | None = None) -> MetricResult:
    actual = [run for run in runs if _truth_for_run(run, truths).severity is not MutationSeverity.L1]
    detected = [run for run in actual if run.detected]
    return _metric("DetectionRate", len(detected) / len(actual) if actual else None, len(detected), len(actual), runs, scope=scope, severity=severity, formula="detected actual failures / actual failures")


def _alarm_results(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth]) -> list[MetricResult]:
    results = [_alarm_metric(runs, truths, {"level": "overall"})]
    for severity in ("L1", "L2", "L3", "L4", "L5"):
        subset = tuple(run for run in runs if _truth_for_run(run, truths).severity.value == severity)
        results.append(_alarm_metric(subset, truths, {"level": "severity", "severity": severity}, severity=severity))
    for mutation_id in sorted({run.mutation_id for run in runs}):
        subset = tuple(run for run in runs if run.mutation_id == mutation_id)
        results.append(_alarm_metric(subset, truths, {"level": "mutation", "mutation_id": mutation_id}))
    return results


def _alarm_metric(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth], scope: Mapping[str, Any], severity: str | None = None) -> MetricResult:
    alarms = [run for run in runs if run.detected]
    true_alarms = [run for run in alarms if _truth_for_run(run, truths).severity is not MutationSeverity.L1]
    return _metric("AlarmPrecision", len(true_alarms) / len(alarms) if alarms else None, len(true_alarms), len(alarms), runs, scope=scope, severity=severity, formula="true alarms / total alarms")


def _unsafe_refusal_results(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth]) -> list[MetricResult]:
    high_risk = tuple(run for run in runs if _truth_for_run(run, truths).severity is MutationSeverity.L5)
    result = _metric("UnsafeRefusalRate", sum(1 for run in high_risk if run.risk_decision in {RiskDecisionType.REJECT.value, RiskDecisionType.QUARANTINE.value} and not run.output_eligible) / len(high_risk) if high_risk else None, sum(1 for run in high_risk if run.risk_decision in {RiskDecisionType.REJECT.value, RiskDecisionType.QUARANTINE.value} and not run.output_eligible), len(high_risk), runs, scope={"level": "overall", "high_risk_definition": "L5 actual failures"}, severity=None, formula="correctly refused high-risk events / high-risk events")
    result = replace(result, scope=freeze_mapping({**result.scope, "result_class": CONTROLLED_HARNESS_RESULT}))
    return [result]


def _l5_results(runs: Sequence[MutationRun], truths: Mapping[str, MutationGroundTruth]) -> list[MetricResult]:
    l5 = tuple(run for run in runs if _truth_for_run(run, truths).severity is MutationSeverity.L5)
    detection = _metric("L5DetectionRate", sum(run.detected for run in l5) / len(l5) if l5 else None, sum(run.detected for run in l5), len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="detected L5 failures / L5 actual failures")
    quarantine_count = sum(run.quarantine_reference is not None for run in l5)
    quarantine = _metric("L5QuarantineCount", quarantine_count if l5 else None, quarantine_count, len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="L5 runs with quarantine reference")
    quarantine_rate = _metric("L5QuarantineRate", quarantine_count / len(l5) if l5 else None, quarantine_count, len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="L5 quarantine count / L5 actual failures")
    eligible = _metric("L5OutputEligibleCount", sum(run.output_eligible for run in l5) if l5 else None, sum(run.output_eligible for run in l5), len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="L5 runs marked output eligible")
    shipped = _metric("L5BadDataShippedCount", sum(run.output_eligible for run in l5) if l5 else None, sum(run.output_eligible for run in l5), len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="L5 actual failures with output_eligible=true")
    shipped_rate = _metric("L5BadDataShippedRate", sum(run.output_eligible for run in l5) / len(l5) if l5 else None, sum(run.output_eligible for run in l5), len(l5), l5, scope={"level": "overall", "result_class": CONTROLLED_HARNESS_RESULT}, formula="L5 bad-data-shipped count / L5 actual failures")
    return [detection, quarantine, quarantine_rate, eligible, shipped, shipped_rate]


def _metric_order(name: str) -> int:
    order = {"DetectionRate": 1, "AlarmPrecision": 2, "UnsafeRefusalRate": 3, "L5DetectionRate": 4, "L5QuarantineCount": 5, "L5QuarantineRate": 6, "L5OutputEligibleCount": 7, "L5BadDataShippedCount": 8, "L5BadDataShippedRate": 9}
    return order.get(name, 99)


def _scope_label(result: MetricResult) -> str:
    if result.scope.get("level") == "overall":
        return "overall"
    if result.scope.get("level") == "severity":
        return str(result.scope.get("severity"))
    return str(result.scope.get("mutation_id"))


def metric_to_dict(result: MetricResult) -> Mapping[str, Any]:
    return _redact(_to_jsonable({
        "metric_name": result.metric_name,
        "value": result.value,
        "status": result.status.value,
        "numerator": result.numerator,
        "denominator": result.denominator,
        "scope": result.scope,
        "severity": result.severity,
        "mutation_ids": result.mutation_ids,
        "run_count": result.run_count,
        "formula_version": result.formula_version,
        "generated_at": result.generated_at,
        "evidence_references": result.evidence_references,
        "formula": result.formula,
    }))
