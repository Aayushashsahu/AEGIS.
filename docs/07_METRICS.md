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

## Mission 010 deterministic metric calculator — 2026-08-17

Mission 010 implements `MetricResult` as an immutable formula output with `metric_name`, `value`, `status`, numerator, denominator, scope, severity, mutation IDs, run count, formula version, optional generated timestamp, and evidence references. The calculator consumes immutable `MutationRun` records plus the corresponding `MutationGroundTruth` records. It does not create a second run model or infer truth from AEGIS output.

The deterministic manifest preserves the run-level fields required by this specification, including the distinction between mutation severity and observed detector severity. The manifest and metric report use the existing audit-store JSON normalization/redaction path; secret-bearing evidence-reference strings are fail-closed to `[REDACTED_REFERENCE]`. Record ordering, scope ordering, and formula version are stable for the same input set. `generated_at` is optional and defaults to `null` so the substantive payload is byte-stable.

The calculator supports overall, per-severity, and per-mutation `DetectionRate` and `AlarmPrecision` results. It also exposes `VerifiedRecovery`, `VerificationMissRate`, `FalseRepairRate`, `UnsafeRefusalRate`, `BlindCommitRate`, `MTTR`, `CostPerRepair`, and `LLMCallsPerRepair` with explicit unavailable states when Mission 009 lacks the necessary repair, commit, cost, or model-call denominator. L5 reporting includes detection rate, quarantine count/rate, output-eligibility count, bad-data-shipped count, and bad-data-shipped rate. A correctly blocked unsafe L5 run is not treated as a benchmark failure.

For the current six-run controlled harness, `DetectionRate` is measured as 5/5 overall, `AlarmPrecision` as 5/5 overall, and L5 detection/quarantine are each 2/2. L5 output eligibility and bad-data-shipped count are 0/2. These values are controlled-harness measurements only; they are not production or full-benchmark results. Recovery, verification-miss, false-repair, blind-commit, MTTR, cost, and LLM-call metrics remain `NOT_APPLICABLE` because their canonical denominators are absent.

## Mission 011 benchmark configuration and metric-integrity boundary — 2026-08-17

Mission 011 does not modify the Mission 010 metric formulas or calculate any metric result. The frozen `BenchmarkConfig.metric_formula_version` is `mission-010-metrics-v1`, and validation fails if the configuration names a different formula version. Future benchmark numbers must continue to use the Mission 010 deterministic calculator over `MutationGroundTruth` and `MutationRun`; no second calculator and no manual result-editing path is introduced.

The validation-only dry run records `metric_calculator_available=true` as an interface-availability check, not as a metric value. It records `metric_values_generated=0`, `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, and `benchmark_execution_authorized=false`. Therefore Mission 011 makes no DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, or LLM-call result claim. Mission 010’s six-run `CONTROLLED_HARNESS_RESULT` remains the latest controlled-harness measurement and is not reclassified as a benchmark.

The benchmark configuration hash covers mutation IDs and severity, seeds and trial count, baseline metadata, model/prompt fields, code and repository revision, fixture version, retry and timeout policies, collection/evidence policies, artifact contract, and metric formula version. A changed frozen field with the old hash fails closed.

## Mission 012 runner and metric-integrity boundary — 2026-08-17

Mission 012 produces normalized raw participant evidence and planned-run manifests only. It does not implement a metric formula, calculate a metric result, or embed baseline-specific metric logic. Mission 010 remains the sole calculator and its `mission-010-metrics-v1` formula version remains frozen in `BenchmarkConfig`.

Common normalization preserves `detected`, `verification_status`, `risk_decision`, `output_eligible`, `failure_state`, latency, cost, LLM-call count, evidence references, and provenance. For Baseline A and Baseline B, AEGIS-only fields are `NOT_APPLICABLE`; they are not converted into synthetic passes, failures, or safety equivalents. The runner records `metric_results_generated=0`, and any future metric calculation must consume raw participant evidence plus independent `MutationGroundTruth` through the Mission 010 calculator downstream.

The Mission 012 dry run reports `BLOCKED_NOT_READY` because the frozen participant slots are not benchmark-ready. This is a readiness state, not a benchmark result. No DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, LLM-call, or comparative result is published.

## Mission 013 participant freeze and metric-integrity boundary — 2026-08-17

Mission 013 does not add or modify a metric formula. Mission 010 remains the sole metric authority, with `metric_formula_version=mission-010-metrics-v1`. Participant metadata validation and readiness promotion emit status/check/evidence records only; they do not calculate DetectionRate, AlarmPrecision, recovery, verification-miss, false-repair, refusal, BlindCommitRate, cost, or LLM-call metrics.

The participant-freeze artifact records `metric_results_generated=0`. Its fairness check confirms that all three participant inputs use the same M005, seed `12345`, fixture/evaluator metadata, and `ground_truth_runtime_payload=NOT_PROVIDED`. Any future promoted participant configuration changes the benchmark configuration hash and must be recomputed before raw evidence is collected. No benchmark result is published by Mission 013.

## Mission 014 owner-input validation and metric boundary — 2026-08-17

Mission 014 generated no participant promotions, raw runs, benchmark metrics, or metric results. Mission 010 remains the sole metric authority. The owner-validation artifact records `metric_results_generated=0`, and the unresolved participant revisions/hashes and fairness timeout conflict prevent any `READY_TO_EXECUTE` outcome.

The supplied common metadata passes mutation-set, seed, fixture-version, retry/backoff, and runtime-ground-truth checks. Timeout fairness fails exactly because the owner-supplied values are 30 seconds for Baseline A, 60 seconds for Baseline B, and 300 seconds for AEGIS. The validator reports this conflict rather than averaging, selecting, or rewriting a timeout policy.


## Mission 015 evidence — metric-integrity boundary preserved

Mission 015 finalized participant metadata and a validation-only comparative execution plan but generated no benchmark metrics. The dry run exposed only metric-calculator availability as an interface check; it did not invoke metric calculation and recorded `metric_results_generated=0`. No DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, or LLM-call result is claimed by this mission.

The participant freeze records preserve the common mutation set `M001`–`M006`, seed `12345`, fixture `gpu-price-staging` v1, and formula version `mission-010-metrics-v1`. Any future ground-truth metric remains valid only after an authorized benchmark execution produces immutable raw evidence under the frozen configuration. `READY_TO_EXECUTE` is not a metric result and is not execution authorization.

The absolute Mission 015 counters were `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`.
