# AEGIS Mission 025 — Resume Interrupted Benchmark Safely

**Date:** 2026-08-18
**Branch:** `mission-025-resume-interrupted-benchmark`
**Base:** Mission 024 `05c6d73752dd263a54a2896a8c1f8cbdc98dbdf2`
**Status:** **IMPLEMENTED AND VALIDATED — REAL RESUME DEFERRED**

## Executive result

Mission 025 adds fail-closed resume semantics to `BenchmarkExecutor` for the fixed run identity `mission_020_floor_2a80a8cf8d989326`. An existing root is no longer treated as an empty fresh run. The executor validates the existing frozen configuration, participant manifest, execution log, raw artifact identities, terminal states, filenames, configuration hash, participant revisions, and deterministic run IDs before it can execute any missing manifest entry.

Existing terminal artifacts are consumed exactly once. Existing `FAILED`, `TIMED_OUT`, and `INVALIDATED` artifacts are terminal attempts and are never retried. Missing manifests are computed in deterministic manifest order. Each newly executed missing trial is persisted with an exclusive raw write and the execution log is atomically reconstructed after the trial. Metrics are deferred until all 180 opportunities have terminal states and remain delegated to Mission 022’s adapter and Mission 010’s sole calculator.

## Important repository-state finding

The Mission 025 brief described an interrupted root with 60 Baseline A artifacts, 36 Baseline B artifacts, and no AEGIS artifacts. Inspection of consolidated Mission 024 `main` found that `benchmarks/runs/mission_020_floor_2a80a8cf8d989326/` was **absent** in both the canonical checked-out workspace and a detached `main` worktree. The tracked Mission 019 smoke evidence was present and untouched.

Therefore, Mission 025 did not claim to inspect or resume a real persisted benchmark root. The specified interrupted shape was reproduced only inside isolated TEST_DOUBLE fixtures for unit tests. No real benchmark artifact was created or modified.

## Resume contract

The new `src/aegis/benchmark_resume.py` module provides:

| Component | Responsibility |
|---|---|
| `TERMINAL_STATES` | Exactly `COMPLETED`, `FAILED`, `TIMED_OUT`, and `INVALIDATED` |
| `ResumeValidationError` | Fail-closed error for malformed, conflicting, or identity-inconsistent roots |
| `inspect_existing_run()` | Validate root files, frozen hash, manifest identity, raw artifacts, terminal state, artifact filename, duplicate IDs, and participant revisions |
| `ResumeInspection` | Immutable projection of consumed artifacts, missing manifests, terminal counts, reconstructed run records, and original artifact digests |
| `reconstruct_execution_log()` | Deterministic execution-log projection from persisted terminal artifacts without rewriting raw evidence |
| `deserialize_participant_evidence()` | Strict conversion of completed raw evidence into the existing normalized evidence model |

A raw artifact is consumed only if its manifest matches the current deterministic plan across benchmark identity, configuration hash, participant, participant revision, mutation, severity, trial, seed, fixture, ground-truth reference, timeout/retry policy, artifact identity, and deterministic run ID. A missing or malformed terminal state, wrong filename, duplicate run ID, wrong hash, wrong participant revision, or unknown run ID blocks the resume gate before execution.

## Executor behavior

The executor distinguishes two safe paths:

| Root state | Behavior |
|---|---|
| Absent | Preserve Mission 021 fresh-run behavior and create the root only after the normal gate passes |
| Existing and valid | Reconstruct terminal state, compute missing manifests, skip every consumed terminal ID, execute only missing manifests in order, and preserve all existing raw bytes |
| Existing but malformed/conflicting | Return `BLOCKED_NOT_READY` before any trial, with the exact resume validation error |

The gate now exposes `artifact_root_resumable`, `existing_terminal_artifacts_valid`, `missing_run_set_computed`, `missing_run_count`, and `execution_authorized=false`. A validated existing root is allowed to pass even though `artifact_root_absent=false`; a generic existing directory is not.

The execution log is reconstructed from raw artifacts on resume. It includes terminal counts, consumed run records, current run identity, configuration hash, and the pending/completed state. After each resumed trial, the new raw artifact is written exclusively and the log is replaced atomically. Existing `frozen_config.json` and `participant_manifest.json` are never rewritten on the resume path.

## Metrics boundary

No metric calculation occurs while any manifest remains missing. Once all 180 opportunities have terminal states, completed evidence is deserialized, evaluator-owned ground truth is joined through the existing MutationLab boundary, and the Mission 022 compatibility adapter is used. Only `aegis.mutation_metrics.calculate_metrics()` is reachable through the existing Mission 022 calculator boundary. Failed, timed-out, and invalidated evidence remains preserved in the raw root and is not retried.

## TEST_DOUBLE validation

The focused fixture reproduces the brief’s interrupted shape: 60 completed Baseline A artifacts, 26 completed plus 10 failed Baseline B artifacts, no AEGIS artifacts, 96 persisted terminal attempts, and 84 missing manifests. The ten failed Baseline B pairs are the specified M001/M002/M003/M004 trial pairs. The test fixture is temporary and is not a benchmark result.

| Validation | Result |
|---|---|
| Focused Mission 025 tests | `10 passed` |
| Complete repository suite | `269 passed` |
| Interrupted terminal fixture | `86 COMPLETED`, `10 FAILED`, `0 TIMED_OUT`, `0 INVALIDATED` |
| Missing manifests | `84` |
| Resume order | Deterministic manifest order |
| Existing terminal retries | `0` |
| Existing raw artifact preservation | Byte digests unchanged |
| Metric calculation before all terminal | `0` |
| Synthetic resumed completion | Completed with Mission 022/010 boundary |
| Real benchmark/provider/healing/metrics execution | `0` |

The complete suite remains green, and all tests use injected TEST_DOUBLE participants. No test calls the real CLI `--run`, `GEMINI_API_KEY`, Bright Data, healing, approval, commit, rollback, or a production benchmark root.

## Frozen values preserved

The implementation does not modify the frozen configuration, benchmark identity, participant definitions, mutations, seed, retry policy, timeout, backoff, or metric authority:

```text
configuration_hash = 59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b
benchmark_run_id = mission_020_floor_2a80a8cf8d989326
mutations = M001–M006
trials_per_mutation = 10
seed = 12345
retry_count = 0
backoff = 0
 timeout_seconds = 300
metric_formula_version = mission-010-metrics-v1
```

## Real execution boundary

Mission 025 itself performed no real resume. The exact deferred command is:

```powershell
$env:PYTHONPATH="src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_017_corrected_frozen_config.json `
  --run `
  --output benchmarks/runs/mission_020_floor_2a80a8cf8d989326
```

It must remain separately reviewed and authorized. Because the actual root was absent in the inspected repository, no current production counts are claimed and no command was run.

| Real counter | Value |
|---|---:|
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

> AI proposes. Evidence decides.

## References

[1]: ../src/aegis/benchmark_resume.py "Mission 025 resume inspection and terminal-artifact validation"
[2]: ../src/aegis/benchmark_executor.py "Mission 021–025 benchmark executor"
[3]: ../scripts/benchmark_runner.py "Explicit benchmark CLI"
[4]: ../tests/unit/test_mission025.py "Mission 025 TEST_DOUBLE resume tests"
[5]: ../docs/06_BENCHMARK_METHODOLOGY.md "Canonical benchmark methodology"
[6]: ../docs/11_API_CONTRACTS.md "Canonical API contracts"
