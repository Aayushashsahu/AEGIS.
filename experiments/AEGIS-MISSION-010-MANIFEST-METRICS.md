# AEGIS Mission 010 — Mutation Manifest + Deterministic Metric Calculator

**Date:** 2026-08-17
**Status:** **COMPLETE for deterministic measurement infrastructure over the Mission 009 V1 harness**
**Scope:** Convert immutable `MutationRun` records into a redacted deterministic manifest and calculate canonical metrics with explicit denominator/status handling.
**Explicitly out of scope:** 540-run scaling, ten trials per class, baseline comparison, model/prompt freeze, provider capability changes, Bright Data state changes, healing behavior, approval, commit, rollback, frontend, dashboard, and production metric claims.

> **AI proposes. Evidence decides.**

## 1. Mission result

Mission 010 closes the measurement-infrastructure gap identified by Mission 009 without changing the AEGIS lifecycle or creating a second run model. The implementation consumes immutable `MutationRun` records and the corresponding immutable `MutationGroundTruth` records, exports a deterministic redacted manifest, and calculates `MetricResult` values with numerator, denominator, scope, status, formula version, run count, and evidence references.

The generated artifacts are:

| Artifact | Purpose |
| --- | --- |
| [`AEGIS-MISSION-010-MUTATION-MANIFEST.json`](AEGIS-MISSION-010-MUTATION-MANIFEST.json) | Deterministic redacted run manifest. |
| [`AEGIS-MISSION-010-METRICS.json`](AEGIS-MISSION-010-METRICS.json) | Machine-readable metric report with traceability. |
| [`../docs/generated/mission_010_metrics.md`](../docs/generated/mission_010_metrics.md) | Human-readable report. |
| [`../src/aegis/mutation_metrics.py`](../src/aegis/mutation_metrics.py) | Manifest and calculator implementation. |
| [`../tests/unit/test_mission010.py`](../tests/unit/test_mission010.py) | Mission 010 unit tests. |

## 2. Manifest schema

Each exported run record preserves `run_id`, `mutation_id`, mutation `severity`, `seed`, `fixture_version`, `baseline_reference`, `mutated_reference`, `ground_truth_reference`, `provenance`, detection outcome, `detected`, `detected_by_existing_detection`, observed `detector_severity`, verification result, risk decision, CommitGate result, `output_eligible`, quarantine reference, timing fields, timestamp, and evidence references. It also includes a small ground-truth projection with `actual_failure`, expected detector behavior, expected safety behavior, and affected fields.

The manifest is ordered by mutation ID and run ID. The generated timestamp is separate and defaults to `null`, while the run timestamp is preserved from the immutable input record. The substantive output is therefore byte-stable for the same run set and truth mapping. The current generated run set contains six records, mutation IDs M001–M006, severities L1–L5, fixture version 1, and explicit `TEST_DOUBLE` provenance.

Redaction uses the existing Mission 008 audit-store JSON normalization/redaction mechanism. Credentials, authorization headers, secret-bearing provider logs, and secret-bearing evidence-reference strings are not emitted. Evidence references containing credential-like key/value material fail closed to `[REDACTED_REFERENCE]`.

## 3. Metric definitions used

The formulas remain those defined by [`docs/07_METRICS.md`](../docs/07_METRICS.md). `MutationGroundTruth` is the only source for actual failure state.

| Metric | Formula | Mission 009 availability |
| --- | --- | --- |
| DetectionRate | detected actual failures / actual failures | Measured overall, by severity, and by mutation ID where a denominator exists. |
| AlarmPrecision | true alarms / total alarms | Measured where an alarm exists; zero alarms are `NOT_APPLICABLE`. |
| VerifiedRecovery | correct verified repairs / actual failures | `NOT_APPLICABLE`; no repair attempts are executed. |
| VerificationMissRate | wrong repairs that passed verification / committed repairs | `NOT_APPLICABLE`; no production commits exist. |
| FalseRepairRate | wrong candidates proposed / repair attempts | `NOT_APPLICABLE`; no repair attempts exist. |
| UnsafeRefusalRate | correctly refused high-risk events / high-risk events | Measured for L5 actual failures in the controlled harness. |
| BlindCommitRate | commits without required deterministic verification / total commits | `NOT_APPLICABLE`; no commit denominator exists. |
| MTTR | detection timestamp → verified commit timestamp | `NOT_APPLICABLE`; no verified commit path exists. |
| CostPerRepair | attributable repair cost / completed repair episodes | `NOT_APPLICABLE`; no cost ledger exists. |
| LLMCallsPerRepair | LLM calls / repair episodes | `NOT_APPLICABLE`; no LLM repair path exists. |

A zero denominator is never converted into measured zero. `MetricResult.status` is one of `MEASURED`, `NOT_APPLICABLE`, or `INSUFFICIENT_DATA`; unavailable results carry `value=null` and an explanatory formula/reason.

## 4. Current measured metrics

The following are **CONTROLLED_HARNESS_RESULT** values from the six Mission 009 deterministic scenarios. They are not production results, not full-benchmark results, and not hackathon headline claims.

| Metric | Numerator | Denominator | Value |
| --- | ---: | ---: | ---: |
| DetectionRate, overall | 5 | 5 | 1.0 |
| AlarmPrecision, overall | 5 | 5 | 1.0 |
| UnsafeRefusalRate, L5 actual failures | 2 | 2 | 1.0 |
| L5DetectionRate | 2 | 2 | 1.0 |
| L5QuarantineCount | 2 | 2 | 2 |
| L5QuarantineRate | 2 | 2 | 1.0 |
| L5OutputEligibleCount | 0 | 2 | 0 |
| L5BadDataShippedCount | 0 | 2 | 0 |
| L5BadDataShippedRate | 0 | 2 | 0.0 |

The overall DetectionRate denominator contains M002–M006 because M001 is a healthy cosmetic mutation and is not an actual failure. The overall AlarmPrecision denominator contains five alarms; the healthy M001 run emits no alarm. M005 and M006 remain schema-compatible and numeric, but deterministic verification and the risk/CommitGate path block them from output.

## 5. `NOT_APPLICABLE` metrics

Mission 009 intentionally does not perform provider repair attempts or production commits. Accordingly, the generated report returns `NOT_APPLICABLE`, rather than zero, for `VerifiedRecovery`, `VerificationMissRate`, `FalseRepairRate`, and `BlindCommitRate`. `MTTR`, `CostPerRepair`, and `LLMCallsPerRepair` are also unavailable because their required event/cost/model-call evidence does not exist. `DetectionRate` for L1 and `AlarmPrecision` for M001 are `NOT_APPLICABLE` because their respective denominators are zero.

These statuses are evidence of a missing measurement path, not failures and not zeros. The implementation does not infer future repair behavior from the absence of a repair attempt.

## 6. L5 safety summary

M005 is the explicit silent-corruption case where the canonical `price=599` becomes `price=29.99`; M006 is a deterministic plausible price decoy. Both preserve the expected extraction shape and numeric type. In the controlled harness, both are detected by the combined AEGIS outcome, quarantined, blocked by the CommitGate, and remain `output_eligible=false`. Therefore the controlled-harness bad-data-shipped count is 0/2.

This is the required safety interpretation: correctly refusing unsafe output is a reliability feature. The result must not be described as ordinary automatic recovery or as a production guarantee.

## 7. Per-severity and per-mutation results

| Scope | DetectionRate | AlarmPrecision |
| --- | ---: | ---: |
| L1 | `NOT_APPLICABLE` (0/0) | `NOT_APPLICABLE` (0/0) |
| L2 | 1.0 (1/1) | 1.0 (1/1) |
| L3 | 1.0 (1/1) | 1.0 (1/1) |
| L4 | 1.0 (1/1) | 1.0 (1/1) |
| L5 | 1.0 (2/2) | 1.0 (2/2) |
| Overall | 1.0 (5/5) | 1.0 (5/5) |

| Mutation | Ground-truth severity | Detector severity | DetectionRate | AlarmPrecision |
| --- | --- | --- | --- | --- |
| M001 | L1 | `NONE` | `NOT_APPLICABLE` (0/0) | `NOT_APPLICABLE` (0/0) |
| M002 | L2 | L2 | 1.0 (1/1) | 1.0 (1/1) |
| M003 | L3 | L3 | 1.0 (1/1) | 1.0 (1/1) |
| M004 | L4 | L3 | 1.0 (1/1) | 1.0 (1/1) |
| M005 | L5 | `NONE` in basic detector; combined outcome detected by verification | 1.0 (1/1) | 1.0 (1/1) |
| M006 | L5 | `NONE` in basic detector; combined outcome detected by verification | 1.0 (1/1) | 1.0 (1/1) |

The M004 row preserves the distinction between mutation severity and detector signal severity: the ground-truth mutation is L4 even though the existing statistical detector emits an L3 signal. The M005/M006 rows preserve the L5 distinction: basic schema/type detection is silent, while deterministic verification supplies the safety detection.

## 8. Test results

Focused Mission 010 validation passed:

```text
PYTHONPATH=src pytest -q tests/unit/test_mission010.py
13 passed
```

The tests cover manifest generation and ordering, required field preservation, redaction, canonical metric formulas, zero denominators, per-severity and per-mutation scopes, L5 safety, traceability, severity distinction, immutable `MetricResult`, byte-stable output, and no fake recovery/verification-miss/blind-commit result.

The full repository suite is the final acceptance command and is recorded in the final mission update after execution.

## 9. Reproducibility result

Two exports from the same immutable run set and truth mapping are byte-identical even when input run order is reversed. Metric JSON is also byte-identical under reversed input order. The generated artifacts use fixed Mission 009 harness timestamps and leave `generated_at` null. No 540-run benchmark or trial scaling was executed.

## 10. Safety checks and benchmark gaps

Mission 010 adds no Bright Data command, approval operation, auto-approve flag, provider-side commit, rollback, or new healing behavior. `output_eligible` remains false in all generated TEST_DOUBLE runs. Provider-native rollback remains outside this mission and is not reclassified. The implementation adds no frontend, dashboard, distributed infrastructure, or benchmark runner.

The missing future evidence remains substantial: ten trials per class, frozen baseline A/B/C configurations, pinned model/prompt configuration where applicable, complete benchmark-run manifests, repair attempts, verified recovery, production commit evidence, cost ledger, LLM trace events, and any Bright Data production claims. The controlled-harness values above must not be used as substitutes for those artifacts.

## 11. Exact recommended Mission 011

Mission 011 should implement the **benchmark-run orchestration and frozen configuration boundary only**, without yet publishing headline results. It should define and validate the minimum benchmark manifest: fixture version, six mutation classes, fixed seed list, baseline identifiers, code revision, environment reference, retry/timeout policy, and artifact root. It should run a small dry-run or validation-only path that proves reset/determinism and rejects incomplete manifests, but it must not silently scale to 540 runs, alter metric formulas, or claim benchmark outcomes until the benchmark configuration is frozen and reviewed.

The subsequent benchmark execution mission—not Mission 011 by assumption—may perform the agreed trial floor after configuration freeze. Any repair/commit metrics must continue to use the same evidence-first calculator and keep `BlindCommitRate` at zero.
