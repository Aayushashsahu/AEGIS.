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


## Mission 017 corrected freeze — metric boundary preserved

Mission 017 corrected only participant revision identity and the immutable benchmark freeze after Mission 016 preflight invalidation. It did not execute participants, calculate metrics, or alter `mission-010-metrics-v1`. The corrected dry-run reports `READY_TO_EXECUTE` as a validation-only state with `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`.

The corrected configuration preserves M001–M006, the canonical severity mapping, seed `12345`, fixture `gpu-price-staging` v1, common 300-second timeout, zero retries, zero backoff, and `ground_truth_runtime_payload=NOT_PROVIDED`. No DetectionRate, AlarmPrecision, L5, recovery, false-repair, commit, cost, latency, or model-call benchmark result is claimed by Mission 017.


## Mission 019 — smoke-only metric boundary

Mission 019 repaired Baseline B’s first-candidate execution representation and ran only the authorized execution-readiness smoke. The smoke’s `output_eligible=true` means that Baseline B accepted its first candidate under its intentionally naive policy; it is not a correctness metric, shipment claim, or verified recovery result.

No MutationLab benchmark trial was executed, no metric calculator was invoked, and no Mission 010 formula was changed. The frozen configuration remains hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, with M001–M006, seed `12345`, `gpu-price-staging` v1, and `mission-010-metrics-v1` unchanged. Mission 019 therefore publishes no DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, or benchmark L5 result.

Mission 019 counters are `benchmark_runs_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. The one authorized Gemini readiness provider operation is smoke evidence only and is not a benchmark metric denominator.


## Mission 020 — artifact-separation metric boundary

Mission 020 only validates committed preflight/smoke evidence and plans a distinct future benchmark artifact root. It does not execute a participant, invoke `execute_one()`, run MutationLab trials, calculate metrics, or alter `mission-010-metrics-v1`.

The existing smoke `output_eligible=true` remains Baseline B policy evidence, not a correctness or benchmark metric. The future run ID `mission_020_floor_2a80a8cf8d989326` is an artifact identity only; no run directory or raw result exists for it after Mission 020.

Mission 020 counters are `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. No DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, latency, model-call benchmark result, or L5 result is claimed.


## Mission 021 — execution metric boundary remains Mission 010

Mission 021 adds no metric formula or calculator. The explicit executor persists immutable raw `ParticipantRunEvidence` and preserves evaluator-owned `MutationGroundTruth` references. Mission 010 remains the sole authority at `mission-010-metrics-v1`.

The current Mission 010 `calculate_metrics()` API consumes `MutationRun` records plus `MutationGroundTruth`, while the Mission 021 common participant boundary produces normalized `ParticipantRunEvidence` for all three participants. The executor therefore fails closed after raw execution with `FAILED_METRIC_BOUNDARY` when it cannot construct a complete, all-participant compatible input. It does not calculate partial metrics, coerce participant evidence into a second formula, or present test-double output as benchmark measurement.

Mission 021’s real execution counters remain zero. The focused test executor deliberately uses an injected model caller and temporary artifacts to prove 180 terminal raw records, but those are test-double opportunities, not benchmark results. No DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, LLM-call, or L5 benchmark result is claimed.


## Mission 022 — deterministic compatibility boundary

Mission 022 keeps Mission 010 as the sole metric authority. The adapter does not alter `mission-010-metrics-v1`, recalculate formulas, or convert unavailable concepts into zero. It reports an immutable metric-by-metric compatibility matrix with numerator source, denominator source, required evidence, zero-denominator behavior, and missing-data behavior.

DetectionRate, AlarmPrecision, UnsafeRefusalRate, L5DetectionRate, L5QuarantineRate, and L5BadDataShippedRate can consume honest AEGIS evidence after evaluator-owned truth is joined. VerifiedRecovery, VerificationMissRate, FalseRepairRate, BlindCommitRate, MTTR, CostPerRepair, and LLMCallsPerRepair remain Mission 010 `NOT_APPLICABLE` because the current formula boundary has no repair, verified-commit, cost-ledger, or repair-episode denominator. L5VerifiedReExtraction is not exposed by Mission 010 v1 and therefore remains unavailable rather than being synthesized.

Baseline A and Baseline B common fields that are not defined for their strategies remain `NOT_APPLICABLE`. The compatibility report preserves their full evidence and does not reinterpret Baseline B’s first-candidate `output_eligible` policy as AEGIS shipment or correctness. Missing evidence, missing truth, duplicate identities, and mismatched manifest/evidence identity return `FAILED_METRIC_BOUNDARY`.

The synthetic 180-opportunity test-double compatibility path adapted 180 records and invoked `calculate_metrics()` once over the honest 60-record AEGIS metric scope. The resulting JSON is a test artifact only. Mission 022 generated zero real-run metric results and claims no benchmark measurement.

## Mission 026 — NVIDIA NIM metric boundary

Mission 026 performs capability verification only. The single real NVIDIA smoke is not a benchmark trial and produces no Mission 010 metric result. Its normalized evidence records provider operation count, model reachability, candidate receipt/selection/acceptance, latency, disabled controls, and `runtime_ground_truth=NOT_PROVIDED`; it does not claim DetectionRate, VerifiedRecovery, FalseRepairRate, UnsafeRefusalRate, L5 shipment safety, or any other benchmark metric.

The new NVIDIA participant proposal has a deterministic participant hash and a new candidate configuration hash, but remains `NOT_READY` pending owner review and immutable promotion. The historical Gemini configuration and Mission 019 smoke remain the comparison baseline. Any future 180-run output must pass through the existing Mission 022 compatibility boundary and the sole Mission 010 calculator. No new formula, estimator, metric fallback, or provider-derived truth is introduced.

## Mission 027 — NVIDIA metric boundary

Mission 027 produces no benchmark or metric result. Owner review, readiness promotion, the new configuration hash, fairness, and the validation-only plan are configuration/readiness evidence only. Mission 010 remains the sole metric authority, and no new formula or estimator is introduced.

The future protocol records 10 trials per mutation and 180 opportunities, while the current provider-free validation runner reports its existing 18-step planning representation. Both are planning counts; neither is an executed result. The final counters are `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`.

## Mission 028 — completed metric boundary

Mission 028 completed 180 terminal opportunities before calculating metrics. The Mission 022 compatibility boundary passed and invoked only the Mission 010 calculator, producing 38 results with `formula_version=mission-010-metrics-v1`. The eligible metric inputs are AEGIS `TEST_DOUBLE` records; the results are controlled-harness measurements, not real NVIDIA or Bright Data measurements.

Overall `DetectionRate=1.0 (50/50)` and `AlarmPrecision=1.0 (50/50)`. For L5, `L5DetectionRate=1.0 (20/20)`, `L5BadDataShippedCount=0`, and `L5BadDataShippedRate=0.0`. `L5QuarantineCount=0`, `L5QuarantineRate=0.0`, and `L5OutputEligibleCount=0`. `VerifiedRecovery`, `VerificationMissRate`, `FalseRepairRate`, `BlindCommitRate`, `MTTR`, `CostPerRepair`, and `LLMCallsPerRepair` remain `NOT_APPLICABLE` with zero denominators. No `NOT_APPLICABLE` result was converted to a measured zero.

The execution produced `benchmark_runs_executed=180`, `provider_operations_executed=60`, `healing_operations_executed=0`, and `metric_results_generated=38`. The one NVIDIA HTTP 502 remains provider-failure evidence and is excluded from any claim that it represents model quality. No second metric formula or provider-derived truth was introduced.

## Mission 028 recovery metric disposition

The first-attempt summary for `mission_028_floor_00c77f2abd976a10` is invalidated and produces no reproducible metric result because its raw artifact root was removed before staging. Its observed summary is not used as evidence.

The clean recovery run `mission_028_recovery_floor_4812160675146552` preserved 180 terminal artifacts before metric calculation. Mission 022 compatibility passed, and only Mission 010 generated the 38-result metric artifact. The eligible scope is AEGIS `TEST_DOUBLE` controlled-harness evidence. Overall DetectionRate and AlarmPrecision were `1.0 (50/50)`, L5DetectionRate was `1.0 (20/20)`, and L5BadDataShippedCount/Rate were `0/20` and `0.0`. Zero-denominator repair metrics remain `NOT_APPLICABLE` and are not substituted with zero. The recovery metrics artifact is SHA-256 recorded and remained unchanged through the full suite.

## Mission 029 — Explicit non-benchmark metric boundary

Mission 029 produced no benchmark metrics, comparative metrics, DetectionRate, AlarmPrecision, recovery-rate, or repair-rate claim. It is a product/demo evidence mission. The only counted values are live provider-operation facts: one collector create, one collector run, one heal request, zero approval, and zero production commit. The live AEGIS detection record is evidence for a single controlled demonstration, not a general performance metric. Mission 028 recovery remains the canonical benchmark evidence.

## Mission 030 — Explicit no-metrics compatibility boundary

Mission 030 produced no benchmark, comparative, detection-rate, recovery-rate, repair-rate, or provider-quality metric. It records one provider-transport compatibility preflight and one authorization-bounded heal submission only. The 676-character prompt projection removes the Mission 029 length-blocker but the provider still failed before candidate creation; this is a single provider-operation observation, not a quality or recovery metric. Mission 028 remains the only canonical benchmark metric evidence.
