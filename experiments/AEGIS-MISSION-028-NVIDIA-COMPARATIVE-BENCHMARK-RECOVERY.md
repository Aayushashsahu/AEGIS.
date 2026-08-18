# AEGIS Mission 028 — NVIDIA Comparative Benchmark Recovery

**Status:** Completed and preserved. The first Mission 028 attempt is explicitly invalidated and is not treated as a reproducible benchmark result. The recovery is a separate deterministic run under a new identity.

## Attempt disposition

| Attempt | Run ID | Status | Evidence disposition |
|---|---|---|---|
| First Mission 028 attempt | `mission_028_floor_00c77f2abd976a10` | `INVALIDATED` | Summary retained only as incident evidence; artifact root was removed before staging and must not be reused |
| Clean recovery | `mission_028_recovery_floor_4812160675146552` | `COMPLETED` | 180 raw terminal artifacts, execution log, compatibility report, metrics, and SHA-256 manifest preserved |

The first attempt’s observed execution summary reported 180 terminal opportunities and 38 metric results, but those claims are not reproducibly supported because the raw artifact root was deleted by provider-free test cleanup before staging. The first summary is therefore not a benchmark result and is not used in this report’s measured recovery claims.

## Recovery identity and frozen configuration

| Field | Value |
|---|---|
| Recovery attempt identifier | `mission-028-nvidia-comparative-benchmark-recovery-v1` |
| Recovery run ID | `mission_028_recovery_floor_4812160675146552` |
| Invalidated first-attempt ID | `mission_028_floor_00c77f2abd976a10` |
| Configuration hash | `8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4` |
| Promoted NVIDIA participant hash | `9b630269de415be0f69b92e7abd62dcaf4a3a535c3e8f3df982017a50ba25c14` |
| Mutations | M001–M006 |
| Seed | `12345` |
| Trials per mutation | `10` |
| Participants | `BASELINE_A`, `BASELINE_B` / NVIDIA, `AEGIS` / TEST_DOUBLE |
| Timeout | `300 seconds` |
| Retries | `0` |
| Backoff | `0` |

The recovery ID is derived from the frozen configuration hash, the explicit recovery attempt identifier, and the frozen sorted participant revisions. It is distinct from the invalidated first-attempt ID and was checked before trial 1.

## Preservation fix and pre-execution gate

Before recovery, the executor was fixed to accept an explicit immutable `runs_root`. Production execution uses the canonical repository benchmark root. Provider-free tests use a temporary root passed explicitly to the executor, and their cleanup fixture removes only that temporary root. The preservation tests passed before recovery, and the full suite passed with `323 passed` before execution.

The recovery preflight returned `RECOVERY_PREFLIGHT_PASS`. It verified configuration hash and validation, participant readiness and revisions, participant hash, fairness, clean fixture, immutable smoke evidence, metric authority, model caller availability, rate policy, artifact isolation, new-root absence, deterministic identity, no reuse of the invalidated ID, duplicate-free manifests, and exactly 180 planned opportunities.

## Exact recovery execution policy

| Policy | Frozen value |
|---|---:|
| AEGIS benchmark requests per minute | `6` |
| Minimum interval | `10 seconds` |
| Concurrency | `1` |
| NVIDIA provider RPM/free-tier limit | `UNKNOWN` |
| NVIDIA provider | `NVIDIA_NIM` |
| Model | `openai/gpt-oss-20b` |
| Revision | `gpt-oss-20b-v1.0-2025-08-05` |
| Generated code execution | `false` |
| Automatic retry | `0` |

The value 6 is the AEGIS benchmark-side throttle and is not represented as NVIDIA’s provider limit.

## Preserved recovery evidence

The recovery root was never removed or overwritten after execution. A post-run SHA-256 manifest covers every recovery artifact and the complete set of 180 raw files. The preservation validator reports `PASS` with 180 unique terminal run IDs and zero missing manifests.

| Artifact check | Result |
|---|---|
| Unique terminal raw artifacts | `180` |
| Raw files removed after execution | `0` |
| Raw hashes recorded | `180` |
| Missing terminal manifests | `0` |
| Execution log | Terminal `COMPLETED` |
| Execution log SHA-256 | `caf0308a833eb37e514a1bb500118181eb0b1e9e82140c4643f8c16f0e7e6968` |
| Mission 010 metrics SHA-256 | `d8c8b4fd50363ec950a3b79972c3a4e73942821ef6d2efdd3d86a5d0853ff29a` |
| Recovery preservation status | `PASS` |

The full suite was run with the recovery root present. It passed with `323 passed`; raw count remained `180`, the recovery root file count remained `185`, and the aggregate raw-artifact hash remained unchanged.

## Recovery terminal results

| Participant | Planned | Completed | Failed | Timed out | Invalidated | Provider operations |
|---|---:|---:|---:|---:|---:|---:|
| `BASELINE_A` | 60 | 60 | 0 | 0 | 0 | 0 |
| `BASELINE_B` / NVIDIA | 60 | 59 | 1 | 0 | 0 | 60 |
| `AEGIS` / TEST_DOUBLE | 60 | 60 | 0 | 0 | 0 | 0 |
| **Total** | **180** | **179** | **1** | **0** | **0** | **60** |

The single recovery provider failure was recorded at `mission_028_recovery_floor_4812160675146552__baseline_b__m002__trial-8__a0f7c5fd58899e74` as `Remote end closed connection without response`. No automatic retry occurred. It is classified as provider failure, not model-quality failure.

The final recovery counters are `benchmark_runs_executed=180`, `provider_operations_executed=60`, `healing_operations_executed=0`, `metric_results_generated=38`, and `execution_authorized=true`. Gemini was not invoked. Bright Data was not used. No healing, approval, commit, or rollback operation occurred.

## Canonical Mission 010 metrics

After all 180 recovery opportunities were terminal, the Mission 022 compatibility boundary passed and invoked only the Mission 010 calculator. The preserved recovery metric artifact contains 38 canonical results with `formula_version=mission-010-metrics-v1`. The eligible inputs are AEGIS `TEST_DOUBLE` controlled-harness evidence; these values are not real NVIDIA or Bright Data measurements.

| Metric | Scope | Result |
|---|---|---:|
| `DetectionRate` | Overall AEGIS controlled harness | `1.0` (`50/50`) |
| `AlarmPrecision` | Overall AEGIS controlled harness | `1.0` (`50/50`) |
| `L5DetectionRate` | AEGIS controlled harness | `1.0` (`20/20`) |
| `L5BadDataShippedCount` | AEGIS controlled harness | `0` |
| `L5BadDataShippedRate` | AEGIS controlled harness | `0.0` |
| `VerifiedRecovery` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `VerificationMissRate` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `FalseRepairRate` | Overall | `NOT_APPLICABLE` (`0/0`) |
| `BlindCommitRate` | Overall | `NOT_APPLICABLE` (`0/0`) |

Zero-denominator `NOT_APPLICABLE` results remain non-measurements and were not converted to zero.

## Final testing and stop condition

The preservation-focused suite passed with `22 passed`, and the full suite passed with `323 passed`. The recovery artifact validator passed after execution and after the full suite. The invalidated first-attempt summary remains separately marked as `INVALIDATED_NOT_REPRODUCIBLE`; it is not used to augment or substitute for recovery evidence.

AI proposes. Evidence decides.

### References

[1]: https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html "NVIDIA NIM documentation"
[2]: https://github.com/Aayushashsahu/AEGIS./tree/mission-028-nvidia-comparative-benchmark "AEGIS Mission 028 recovery branch"
