# 07 — Metrics Specification

**Metric authority:** This document.  
**Reporting rule:** Every metric is reported overall and by L1, L2, L3, L4, and L5 where meaningful.  
**Safety rule:** Targets are not measured results.

## Metric definitions

| Name | Formula | Numerator | Denominator | Ground truth | Target / reporting |
| --- | --- | --- | --- | --- | --- |
| DetectionRate | detected actual failures / actual failures | Mutation trials with a qualifying failure detected | All mutation trials containing an actual failure | Required | Target ≥90%; report overall and per severity. |
| AlarmPrecision | true alarms / total alarms | Alarms corresponding to actual failures | All emitted alarms | Required | Target ≥90%; report with false-positive count. |
| VerifiedRecovery | correct repairs / actual failures | Trials producing a correct verified repair | All actual failures | Required | Target ≥85%; do not use for L5 as the only safety measure. |
| VerificationMissRate | wrong repairs that passed verification / committed repairs | Wrong candidates that passed and were committed | All committed repairs | Required | Target <1%; report numerator and denominator even when zero. |
| FalseRepairRate | wrong repair candidates proposed / repair attempts | Candidate proposals that are incorrect against truth | All repair attempts | Required | Report measured actual; no target asserted. |
| UnsafeRefusalRate | correctly refused high-risk events / high-risk events | High-risk events correctly quarantined/escalated | All high-risk events | Required | Report measured actual; define high-risk set in manifest. |
| BlindCommitRate | commits without ≥2 deterministic channels / total commits | Commits lacking the commit gate | All commits | Event log | Target 0%; any non-zero result is a release blocker. |
| MTTR | detection timestamp → verified commit timestamp | Per-episode elapsed time | Report distribution, not only mean | Event timestamps | Report median, p95, min/max; no target until measured. |
| CostPerRepair | attributable repair cost / completed repair episodes | Provider and execution cost | Completed repair episodes | Cost ledger | Report actual with currency and exclusions. |
| LLMCallsPerRepair | LLM calls / repair episodes | Count of model calls | Repair episodes | Trace events | Report distribution and model/configuration. |

## Per-severity and L5 reporting

For each metric, the report includes L1–L5 rows, trial counts, numerator, denominator, and undefined/zero-denominator handling. L5 receives a separate safety table:

| L5 safety measure | Definition |
| --- | --- |
| Detection rate | L5 actual failures detected / L5 actual failures. |
| Quarantine rate | L5 events quarantined before shipment / L5 actual failures. |
| Verified re-extraction | L5 events whose replacement output matched ground truth and passed verification / L5 actual failures. |
| Verification miss rate | Wrong L5 repairs passing verification / committed L5 repairs. |
| Bad-data-shipped rate | L5 trials in which incorrect output reached the downstream product / L5 actual failures. |

L5 is not ordinary recovery because preventing shipment is a valid safety outcome even when automatic recovery is not achieved.

## Data and calculation rules

Metrics are calculated from immutable raw run records, not manually entered summaries. Numerators and denominators must be exported with the metric result. A zero denominator is reported as `NOT_APPLICABLE`, not silently converted to zero. Recalculation must be deterministic from the run directory and metric specification version.

## Release gates

The release gate requires BlindCommitRate = 0% on the evaluated path, no unexplained verification misses, complete per-severity reporting, and no target presented as measured. The project may publish a lower DetectionRate or VerifiedRecovery than its target if that is the actual result; it may not alter the formula to improve appearance.

## Metric result schema

```json
{
  "metric_name": "DetectionRate",
  "spec_version": "1.0",
  "scope": {"baseline": "AEGIS", "severity": "L5"},
  "numerator": 0,
  "denominator": 0,
  "value": null,
  "status": "NOT_APPLICABLE",
  "target": 0.90,
  "run_ids": [],
  "calculated_at": "[MEASURED_TIMESTAMP]"
}
```

## Mission 005 metric hooks — 2026-08-17

Mission 005 adds `SafetyMetricHooks` for later calculation of verification and risk metrics from immutable event references. It records verification-completed and risk-decision events without executing benchmarks or synthesizing benchmark results.

On the Mission 005 path, no commit operation exists. Therefore the safety counter is `blind_commit_count=0`, `total_commit_count=0`, and `blind_commit_rate=0.0` as a zero-event safety counter. The corresponding status is `NOT_APPLICABLE` because the canonical metric denominator is zero. This is implementation-state instrumentation, not a measured production or mutation-lab result.

The following later metrics remain event-ready but unmeasured: `VerificationMissRate`, `FalseRepairRate`, and `UnsafeRefusalRate`. Ground-truth values must come from the mutation laboratory and must be reported with numerator, denominator, raw run references, and per-severity scope.

## Mission 006 metric hooks — 2026-08-17

Mission 006 adds `CommitSafetyMetricHooks` for later event-based calculation of `QuarantineRate` and `UnsafeRefusalRate`. It records commit decisions and quarantine records without running a benchmark or claiming production behavior.

With no production commit denominator, commit-related rate values remain `NOT_APPLICABLE` rather than being reported as measured zero. A blocked decision is an instrumented safety refusal event; it is not a benchmark result. Quarantine and unsafe-refusal numerators/denominators must later be calculated from immutable mutation-lab or controlled run events with per-severity scope.

## Mission 007 metric hooks — 2026-08-17

Mission 007 adds `WatchMetricHooks` for later calculation of `RegressionRate`, `WatchFailureRate`, and `UnsafeRefusalRate`. The current instrumentation defines watch failure as an unknown watch result and unsafe refusal as a regression that enters quarantine. It records watch, regression, unknown, and quarantine events without executing benchmarks or claiming production metrics.

With no watch cycles, the metrics are `NOT_APPLICABLE`. After controlled fixture events, the status is `INSTRUMENTED_NOT_BENCHMARKED`; values are not benchmark results. Future reporting must calculate numerators and denominators from immutable controlled-run events with per-severity scope.

## Mission 008 evidence boundary — 2026-08-17

Mission 008 persists metric-relevant evidence references and lifecycle events but does not calculate or report benchmark metrics. Future metric calculation may query immutable audit events by aggregate, correlation, event type, timestamp, and per-severity payload scope. Missing production or mutation-lab denominators remain `NOT_APPLICABLE`; persistence of an event is not measurement of a reliability outcome.

## Mission 009 mutation-lab hooks — 2026-08-17

Mission 009 provides immutable `MutationRun` fields needed for later DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, and BlindCommitRate calculations. It records detected-by-existing-detection separately from the combined detected outcome so L5 cases can show valid schema/type output that is caught by deterministic verification.

No metric result is published. The V1 harness has no benchmark denominator and no 540-run execution. Future values must be calculated from immutable mutation-run artifacts overall and by L1–L5; zero denominators remain `NOT_APPLICABLE`.
