# Mission 010 Deterministic Mutation Metrics

> **CONTROLLED_HARNESS_RESULT — not a production benchmark result.**

Formula version: `mission-010-metrics-v1`
Run count: `6`
Provenance: `TEST_DOUBLE`

## Manifest summary

| Field | Value |
| --- | --- |
| Run IDs | `mutation_run_M001_12345, mutation_run_M002_12345, mutation_run_M003_12345, mutation_run_M004_12345, mutation_run_M005_12345, mutation_run_M006_12345` |
| Mutation IDs | `M001, M002, M003, M004, M005, M006` |
| Severities | `L1, L2, L3, L4, L5` |
| Fixture versions | `1` |

## Measured controlled-harness metrics

| Metric | Scope | Formula | Numerator | Denominator | Value |
| --- | --- | --- | ---: | ---: | ---: |
| DetectionRate | M002 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | M003 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | M004 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | M005 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | M006 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | overall | detected actual failures / actual failures | 5 | 5 | 1.0 |
| DetectionRate | L2 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | L3 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | L4 | detected actual failures / actual failures | 1 | 1 | 1.0 |
| DetectionRate | L5 | detected actual failures / actual failures | 2 | 2 | 1.0 |
| AlarmPrecision | M002 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | M003 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | M004 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | M005 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | M006 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | overall | true alarms / total alarms | 5 | 5 | 1.0 |
| AlarmPrecision | L2 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | L3 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | L4 | true alarms / total alarms | 1 | 1 | 1.0 |
| AlarmPrecision | L5 | true alarms / total alarms | 2 | 2 | 1.0 |
| UnsafeRefusalRate | overall | correctly refused high-risk events / high-risk events | 2 | 2 | 1.0 |
| L5DetectionRate | overall | detected L5 failures / L5 actual failures | 2 | 2 | 1.0 |
| L5QuarantineCount | overall | L5 runs with quarantine reference | 2 | 2 | 2 |
| L5QuarantineRate | overall | L5 quarantine count / L5 actual failures | 2 | 2 | 1.0 |
| L5OutputEligibleCount | overall | L5 runs marked output eligible | 0 | 2 | 0 |
| L5BadDataShippedCount | overall | L5 actual failures with output_eligible=true | 0 | 2 | 0 |
| L5BadDataShippedRate | overall | L5 bad-data-shipped count / L5 actual failures | 0 | 2 | 0.0 |

## Unavailable metrics

| Metric | Scope | Status | Reason/formula |
| --- | --- | --- | --- |
| DetectionRate | M001 | NOT_APPLICABLE | detected actual failures / actual failures |
| DetectionRate | L1 | NOT_APPLICABLE | detected actual failures / actual failures |
| AlarmPrecision | M001 | NOT_APPLICABLE | true alarms / total alarms |
| AlarmPrecision | L1 | NOT_APPLICABLE | true alarms / total alarms |
| VerifiedRecovery | overall | NOT_APPLICABLE | correct verified repairs / actual failures; no repair path in Mission 009 |
| VerificationMissRate | overall | NOT_APPLICABLE | wrong repairs that passed verification / committed repairs; no commits in Mission 009 |
| FalseRepairRate | overall | NOT_APPLICABLE | wrong candidates proposed / repair attempts; no repair attempts in Mission 009 |
| BlindCommitRate | overall | NOT_APPLICABLE | commits without required deterministic verification / total commits; no commit denominator in Mission 009 |
| MTTR | overall | NOT_APPLICABLE | detection timestamp → verified commit timestamp; no verified commit path |
| CostPerRepair | overall | NOT_APPLICABLE | attributable repair cost / completed repair episodes; no cost ledger |
| LLMCallsPerRepair | overall | NOT_APPLICABLE | LLM calls / repair episodes; no LLM repair path |

## L5 safety summary

| Measure | Result |
| --- | ---: |
| L5DetectionRate | 1.0 |
| L5QuarantineCount | 2 |
| L5QuarantineRate | 1.0 |
| L5OutputEligibleCount | 0 |
| L5BadDataShippedCount | 0 |
| L5BadDataShippedRate | 0.0 |

## Traceability

Every metric result carries the run evidence references used in its numerator and denominator. Ground truth is taken only from `MutationGroundTruth`; no result infers actual failure state from the candidate output.

## Benchmark boundary

This report covers the Mission 009 six-scenario controlled harness only. It does not claim ten trials per class, frozen A/B/C baselines, 540 runs, production reliability, or a hackathon headline metric.
