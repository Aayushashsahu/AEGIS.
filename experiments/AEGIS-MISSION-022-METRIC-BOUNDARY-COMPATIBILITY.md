# AEGIS Mission 022 — Bridge Benchmark Evidence into Mission 010 Metric Authority

**Date:** 2026-08-18
**Branch:** `mission-022-metric-boundary-compatibility`
**Base:** Mission 021 `2a32ac4152ffe73af9f0565213295e315bbabfea`
**Status:** **IMPLEMENTED AND VALIDATED — REAL BENCHMARK DEFERRED**

## Executive result

Mission 021 correctly stopped with `FAILED_METRIC_BOUNDARY` because its executor produced immutable `ParticipantRunEvidence`, while the existing Mission 010 calculator accepts `MutationRun` records plus evaluator-owned `MutationGroundTruth`. Mission 022 adds a provider-neutral compatibility boundary. It preserves every source evidence record, joins ground truth only after participant execution, produces immutable metric-input projections, and invokes only the existing `aegis.mutation_metrics.calculate_metrics()` function.

The synthetic acceptance test completed the full 180-opportunity Mission 021 test-double execution shape, adapted all 180 completed evidence records, and invoked Mission 010 exactly once with the honest metric-eligible AEGIS scope of 60 records. Baseline A and Baseline B remain present in the compatibility report with their `NOT_APPLICABLE` fields; they are not converted into fabricated detection, verification, risk, commit, or shipment values. The generated synthetic metric output is a compatibility test artifact, not a benchmark result.

No real benchmark was run. No real Gemini call, Bright Data call, healing operation, approval, production commit, rollback, or real-run metric result occurred.

## Exact root cause of `FAILED_METRIC_BOUNDARY`

The Mission 021 executor’s raw boundary is intentionally participant-neutral and emits `ParticipantRunEvidence`. The Mission 010 calculator’s input contract is the immutable `MutationRun` plus a mapping of `MutationGroundTruth` records. These types differ in both purpose and available semantics:

| Boundary | Actual contract | Consequence |
|---|---|---|
| Mission 021 participant execution | `ParticipantRunEvidence` for every participant | Preserves common raw evidence and explicit `NOT_APPLICABLE` fields |
| Mission 010 metrics | `MutationRun`-shaped records plus independent `MutationGroundTruth` | Calculates DetectionRate, AlarmPrecision, UnsafeRefusalRate, and controlled L5 measures; returns `NOT_APPLICABLE` for unavailable repair/commit paths |
| Previous Mission 021 bridge | Only AEGIS `MutationRun` records were available, so 60 of 180 opportunities were metric inputs | Executor correctly refused to calculate a partial or invented comparative report and returned `FAILED_METRIC_BOUNDARY` |

Mission 022 does **not** change Mission 010 formulas, modify the frozen configuration, weaken `MutationRun` safety invariants, or create a second calculator.

## Canonical Mission 010 fields and adaptation matrix

The adapter consumes the existing `MutationRun` field contract. The table records the exact source and treatment for each field. The additional immutable manifest context supplies fields that Mission 021 deliberately keeps outside the common evidence record, such as participant configuration hash and explicit trial ordinal.

| Mission 010 field | ParticipantRunEvidence / manifest source | Transformation | Deterministic / derived | Missing behavior |
|---|---|---|---|---|
| `run_id` | Evidence `run_id` | Preserve exactly | Deterministic source identity | Fail closed |
| `mutation_id` | Evidence `mutation_id` | Preserve and cross-check truth | Deterministic source identity | Fail closed |
| `seed` | Evidence `seed` | Preserve and cross-check truth | Deterministic source identity | Fail closed |
| `collector_reference` | Adapter boundary | Set to `participant-run-evidence-bridge` | Deterministic adapter provenance | Not metric evidence |
| `observation_reference` | Evidence `observation_reference` | Preserve | Deterministic source reference | Fail closed if absent from source model |
| `detection_reference` | Evidence `detection://` reference, otherwise observation reference | Select existing evidence reference | Deterministic reference selection | Fail closed when required evidence is absent |
| `verification_reference` | Existing `verification://` evidence reference | Preserve if present | Deterministic reference selection | `None` remains explicit |
| `risk_decision_reference` | Existing `risk://` evidence reference | Preserve if present | Deterministic reference selection | `None` remains explicit |
| `ground_truth_reference` | Evidence reference joined to evaluator-owned truth | Normalize to `ground-truth://mission-022/<stable-id>` | SHA-256 of immutable source reference plus identity | Fail closed; no truth inference |
| `detected` | Evidence `detected` | Accept boolean only for AEGIS metric scope | Direct source value | Baseline `NOT_APPLICABLE`; otherwise fail closed |
| `detected_by_existing_detection` | No common participant field | Preserve as `NOT_APPLICABLE` in metric projection | Explicit absence, not a guessed result | Mission 010 formulas do not require it |
| `detector_severity` | No common participant field | Preserve as `NOT_APPLICABLE` in metric projection | Explicit absence, not mutation severity | Mission 010 formulas do not require it |
| `outcome` | No common participant outcome enum | Use `MutationOutcome.UNKNOWN` in the projection | Explicit unavailable concept | No metric formula uses it |
| `provenance` | Evidence `provenance` | Normalize to `ProviderProvenance.TEST_DOUBLE` for synthetic bridge | Deterministic test-double provenance | Fail closed if provenance is not known |
| `timing_ms` | Evidence timing map | Preserve unchanged | Direct source value | MTTR remains `NOT_APPLICABLE` because no commit timestamp path exists |
| `verification_status` | Evidence verification status | Preserve unchanged | Direct source value | Missing verification fails only when a formula requires it; current unavailable metrics remain `NOT_APPLICABLE` |
| `risk_decision` | Evidence risk decision | Preserve unchanged | Direct source value | Missing risk evidence fails UnsafeRefusalRate adaptation |
| `commit_eligibility` | Not present in common evidence | Preserve as `NOT_APPLICABLE` | Explicit absent production-commit concept | BlindCommitRate remains Mission 010 `NOT_APPLICABLE` |
| `output_eligible` | Evidence output eligibility | Accept boolean for AEGIS metric scope; preserve Baseline A/B `NOT_APPLICABLE` | Direct source value | Missing output/shipment evidence fails L5 shipment adaptation |
| `quarantine_reference` | Existing `quarantine://` evidence reference | Preserve if present | Deterministic reference selection | L5 quarantine metric fails if required evidence is missing |
| `evidence_refs` | Evidence references plus artifact references | Preserve and de-duplicate | Deterministic ordered tuple | Fail closed if empty |
| `created_at` | No common timestamp field | Use fixed epoch only in the metric projection | Deterministic compatibility timestamp | MTTR remains unavailable; no timestamp is invented as a measured event |
| `participant_id` | Evidence participant identity | Preserve in the extended metric-input record | Direct source value | Fail closed if context is absent |
| `participant_configuration_hash` | Immutable Mission 021 `RunManifest` context | Join by exact `run_id` | Deterministic manifest join | Fail closed if manifest context is absent or mismatched |
| `participant_revision` | Evidence and manifest | Preserve and cross-check | Deterministic source identity | Fail closed on mismatch |
| `configuration_hash` | Evidence and manifest/configuration | Preserve and cross-check | Deterministic frozen value | Fail closed on mismatch |
| `benchmark_id` | Immutable `RunManifest` context | Preserve | Deterministic manifest value | Fail closed if context is absent |
| `fixture_version` | Evidence and manifest | Preserve and cross-check truth metadata | Deterministic source identity | Fail closed on mismatch |
| `artifact_refs` | Evidence artifact references | Preserve unchanged | Deterministic source references | Fail closed if empty |
| `trial_number` | Mission 021 manifest / deterministic run ID | Join from manifest context; fallback parser is test-only | Deterministic trial ordinal | Fail closed when context is required |

The adapter retains the complete original `ParticipantRunEvidence` object and an explicit `preserved_fields` projection in the compatibility report. It does not reduce a source record to summary booleans.

## Metric-by-metric evidence sufficiency

Mission 010’s existing formulas determine whether a metric can be calculated. Mission 022 reports the numerator source, denominator source, required evidence, zero-denominator behavior, and missing-data behavior without adding formula logic.

| Metric | Numerator / denominator source | Required evidence | Zero denominator | Missing or unsupported evidence |
|---|---|---|---|---|
| `DetectionRate` | Detected actual failures / actual failures from joined truth severity `!= L1` | Boolean detection, mutation identity, truth reference | Mission 010 `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |
| `AlarmPrecision` | True alarms / detected alarms, classified by joined truth | Boolean detection and truth reference | `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |
| `VerifiedRecovery` | Mission 010 v1 has no repair-success formula | Verification, output, truth references are preserved but no formula exists | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; future request fails closed |
| `VerificationMissRate` | Mission 010 v1 has no committed-repair denominator | Verification, commit eligibility, output fields | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; future request fails closed |
| `FalseRepairRate` | Mission 010 v1 has no repair-attempt formula | Candidate, acceptance, truth fields | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; future request fails closed |
| `UnsafeRefusalRate` | Correct L5 rejection/quarantine without output / L5 actual failures | Risk, output eligibility, truth | `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |
| `BlindCommitRate` | Mission 010 v1 has no commit denominator | Commit, verification, risk fields | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; no commit is invented |
| `MTTR` | Mission 010 v1 has no verified-commit timestamp path | Timing plus verification/commit event references | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; no timestamp is invented |
| `CostPerRepair` | Mission 010 v1 has no cost ledger or repair denominator | Cost and repair-acceptance fields | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; no cost is invented |
| `LLMCallsPerRepair` | Mission 010 v1 has no repair-episode denominator | LLM calls and repair-acceptance fields | `NOT_APPLICABLE` | Remains `NOT_APPLICABLE`; no repair is invented |
| `L5DetectionRate` | Detected L5 failures / L5 actual failures | Boolean detection and truth | `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |
| `L5QuarantineRate` | L5 quarantine references / L5 actual failures | Quarantine reference and truth | `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |
| `L5VerifiedReExtraction` | Not exposed by Mission 010 v1 | Verification, truth, output fields are preserved | Mission 010 does not expose this metric | `FAILED_METRIC_BOUNDARY` if requested |
| `L5BadDataShippedRate` | L5 output-eligible records / L5 actual failures | Boolean output eligibility and truth | `NOT_APPLICABLE` | `FAILED_METRIC_BOUNDARY` |

The current calculator’s actual L5 names also include `L5QuarantineCount`, `L5OutputEligibleCount`, and `L5BadDataShippedCount`; the adapter preserves the source fields needed for all three. Baseline A and Baseline B remain out of the AEGIS-only metric-input scope when their common fields are `NOT_APPLICABLE`. This is an explicit scope boundary, not a fabricated zero.

## Ground-truth boundary

The participant receives only the deterministic reference in its execution input. Mission 022 stores evaluator-owned `MutationGroundTruth` after execution, verifies mutation/seed/severity identity against the participant evidence, and joins the truth by immutable reference. Truth content is never passed into participant runtime and is not serialized inside the metric-input projection. Missing or mismatched truth returns `FAILED_METRIC_BOUNDARY`.

## Synthetic 180-run acceptance test

The focused acceptance test uses the existing Mission 021 test-double execution path, an injected model caller, and a temporary artifact root. It does not invoke the real CLI `--run` boundary.

| Acceptance item | Observed result |
|---|---:|
| Participant opportunities | 180 |
| Completed raw evidence records | 180 |
| Compatibility report records | 180 |
| Evaluator-owned truth joins | 180 |
| Honest Mission 010 metric inputs | 60 AEGIS records |
| Calls to `mutation_metrics.calculate_metrics` | 1 |
| New calculator/formula | 0 |
| Real provider calls | 0 |
| Real benchmark runs | 0 |
| Partial metric report | 0 |

The synthetic compatibility report preserves all 180 participant records and marks Baseline A/B metric fields `NOT_APPLICABLE`. Mission 010 is invoked once on the only scope it can calculate honestly under its existing v1 contract. The resulting synthetic JSON is a test artifact only and is not a benchmark result.

## Validation

The focused Mission 022 suite passed with `9 passed`. The complete suite passed with `255 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission022.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Static checks confirmed that `src/aegis/mutation_metrics.py`, the Mission 021 common evidence source, the corrected frozen configuration, and Mission 015–019 historical evidence were unchanged on the Mission 022 branch. The future benchmark root was not created. No `benchmark_runner.py --run` command was invoked.

## Mission 022 real-execution counters

| Counter | Value |
|---|---:|
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated_from_real_runs` | 0 |
| `execution_authorized` | false |

## Exact future 180-run command

The future command remains deferred and was not run:

```powershell
$env:PYTHONPATH = "src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_017_corrected_frozen_config.json `
  --run `
  --output benchmarks/runs/mission_020_floor_2a80a8cf8d989326
```

> AI proposes. Evidence decides.

## References

[1]: ../src/aegis/mutation_metrics.py "Mission 010 deterministic metric calculator"
[2]: ../src/aegis/mutation_lab.py "MutationRun and MutationGroundTruth contracts"
[3]: ../src/aegis/benchmark_runner.py "Common ParticipantRunEvidence contract"
[4]: ../src/aegis/metric_boundary.py "Mission 022 compatibility adapter and matrix"
[5]: ../src/aegis/benchmark_executor.py "Mission 021 explicit execution boundary"
[6]: ../docs/07_METRICS.md "Canonical metric definitions and authority"
[7]: ../docs/11_API_CONTRACTS.md "Canonical API contracts"
