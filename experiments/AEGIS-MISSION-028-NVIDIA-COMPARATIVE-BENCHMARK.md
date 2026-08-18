# AEGIS Mission 028 — NVIDIA Comparative Benchmark

> **INVALIDATED — NOT A REPRODUCIBLE BENCHMARK RESULT.** The first run summary below was generated during execution, but its benchmark artifact root was subsequently removed by provider-free test cleanup before staging. The run ID `mission_028_floor_00c77f2abd976a10` must not be reused or represented as preserved evidence. The clean recovery run is recorded separately under `mission_028_recovery_floor_4812160675146552`.

**Status:** INVALIDATED. One authorized Mission 028 run was attempted from the immutable Mission 027 NVIDIA configuration. Its surviving summary is retained only as an incident record; its raw artifacts and metrics are not reproducibly available in the repository.

> **Interpretation boundary:** Baseline A is static extraction, Baseline B is the real NVIDIA participant, and AEGIS is the approved local `TEST_DOUBLE` lifecycle. The AEGIS results are not real Bright Data or NVIDIA results. Provider failures are preserved as provider failures and are not reinterpreted as model-quality failures.

## Frozen identity and pre-execution gate

| Field | Recorded value |
|---|---|
| Branch | `mission-028-nvidia-comparative-benchmark` |
| Base | Mission 027 commit `fc563b3e9837834612d84db7afd331d1a18f80e6` |
| Configuration hash | `8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4` |
| Attempt identifier | `mission-028-nvidia-comparative-benchmark-v1` |
| Benchmark run ID | `mission_028_floor_00c77f2abd976a10` |
| Planned opportunities | `180` |
| Gate status | `PREFLIGHT_PASS` |
| Gate execution authorization | `false` during preflight; `true` only for the authorized run |
| New artifact root before trial 1 | Absent and isolated |
| Duplicate run IDs | None |
| Smoke evidence | `VALID`; Mission 026 smoke count remains separate |
| Metric authority | Available; Mission 010 only |

The gate passed configuration hash, configuration validation, freeze validation, participant readiness, participant revisions, participant hash, fairness, clean fixture, smoke evidence, metric authority, model caller availability, rate-policy validity, artifact-root absence/isolation, deterministic run identity, duplicate-free planning, and the 180-opportunity count before trial 1.

## Frozen participant and rate policy

The run used NVIDIA Baseline B exactly as promoted in Mission 027: provider `NVIDIA_NIM`, model `openai/gpt-oss-20b`, revision `gpt-oss-20b-v1.0-2025-08-05`, and endpoint `https://integrate.api.nvidia.com/v1`. The promoted participant hash is `9b630269de415be0f69b92e7abd62dcaf4a3a535c3e8f3df982017a50ba25c14`.

| Policy field | Value |
|---|---:|
| AEGIS benchmark requests per minute | 6 |
| AEGIS minimum interval | 10 seconds |
| Concurrency | 1 |
| NVIDIA provider RPM/free-tier limit | `UNKNOWN` |
| Retries | 0 |
| Backoff | 0 |
| Timeout | 300 seconds |
| Baseline B calls per trial | 1 |

The value 6 is the AEGIS benchmark-side throttle and is not a claim about NVIDIA’s provider limit.

## Execution plan and terminal outcomes

The deterministic plan was `3 participants × 6 mutations × 10 trials = 180 opportunities`, executed in participant, mutation, trial, and seed order. The run resumed once after an interruption. The first partial execution persisted 65 terminal artifacts; the safe resume consumed only the remaining manifests and never reran those terminal run IDs. The final raw set contains 180 unique terminal artifacts.

| Participant | Planned | Completed | Failed | Timed out | Invalidated | Provider operations |
|---|---:|---:|---:|---:|---:|---:|
| `BASELINE_A` | 60 | 60 | 0 | 0 | 0 | 0 |
| `BASELINE_B` / NVIDIA | 60 | 59 | 1 | 0 | 0 | 60 |
| `AEGIS` / `TEST_DOUBLE` | 60 | 60 | 0 | 0 | 0 | 0 |
| **Total** | **180** | **179** | **1** | **0** | **0** | **60** |

The one NVIDIA failure was preserved as a provider failure: HTTP 502 `Bad Gateway` with an upstream-request-failed response on run ID `mission_028_floor_00c77f2abd976a10__baseline_b__m002__trial-6__7e07448e97fe7405`. No automatic retry was applied. It was not classified as model-quality failure.

The final execution counters are `benchmark_runs_executed=180`, `provider_operations_executed=60`, `healing_operations_executed=0`, `metric_results_generated=38`, and `execution_authorized=true`. Gemini was not invoked. Bright Data was not invoked during the benchmark. No healing, approval, commit, or rollback operation occurred.

## Canonical Mission 010 metrics

The Mission 022 compatibility boundary passed, and only the existing Mission 010 calculator produced metrics. The 38 generated results are the canonical output. The metric boundary’s eligible inputs are AEGIS `TEST_DOUBLE` evidence; therefore these values are controlled-harness measurements for the AEGIS path, not real NVIDIA or Bright Data measurements and not fabricated participant-comparison estimates.

| Metric | Scope | Result |
|---|---|---:|
| `DetectionRate` | Overall AEGIS metric boundary | `1.0` (`50/50`) |
| `AlarmPrecision` | Overall AEGIS metric boundary | `1.0` (`50/50`) |
| `L5DetectionRate` | AEGIS L5 controlled harness | `1.0` (`20/20`) |
| `UnsafeRefusalRate` | AEGIS L5 controlled harness | `1.0` (`20/20`) |
| `L5QuarantineCount` | AEGIS L5 controlled harness | `0` |
| `L5QuarantineRate` | AEGIS L5 controlled harness | `0.0` |
| `L5OutputEligibleCount` | AEGIS L5 controlled harness | `0` |
| `L5BadDataShippedCount` | AEGIS L5 controlled harness | `0` |
| `L5BadDataShippedRate` | AEGIS L5 controlled harness | `0.0` |
| `VerifiedRecovery` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `VerificationMissRate` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `FalseRepairRate` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `BlindCommitRate` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `MTTR` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `CostPerRepair` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `LLMCallsPerRepair` | Overall | `NOT_APPLICABLE` (`0/0`) |

`NOT_APPLICABLE` is preserved as a zero-denominator status and is not converted to a measured zero. The canonical metric artifact reports `formula_version=mission-010-metrics-v1` and `generated_at=null`, as required by the existing calculator boundary.

## Safety and provenance

The historical Mission 017 Gemini configuration remains unchanged at `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`. Mission 019 smoke evidence remains untouched. The Mission 028 root is separate from historical Gemini artifacts and contains its own frozen configuration, participant manifest, execution log, raw evidence, compatibility report, and Mission 010 metrics.

The NVIDIA smoke operation from Mission 026 is tracked separately from the 60 benchmark provider operations. Generated candidate code was not executed. No claim is made that a successful NVIDIA HTTP response implies candidate correctness. No claim is made that this NVIDIA run is directly comparable to the historical Gemini run without an explicit methodology review.

## Testing

Mission 028 adds 20 focused provider-free `TEST_DOUBLE` tests covering deterministic identity, artifact-root isolation, participant readiness and hash, rate limiting, concurrency, 180-opportunity planning, ordering, no Gemini invocation, provider-error preservation, zero retries, duplicate prevention, interruption/resume safety, raw persistence, fixture reset, all-terminal metric gating, Mission 022 adaptation, Mission 010-only metric invocation, historical Gemini preservation, and provider-free preflight.

The focused suite passed with `20 passed`. The complete repository suite passed with `321 passed` before real execution. The run’s post-execution artifact validation confirmed 180 unique terminal raw files, 179 completed and 1 failed, 38 canonical metric results, compatibility `PASS`, zero healing operations, and no duplicate run IDs.

AI proposes. Evidence decides.
