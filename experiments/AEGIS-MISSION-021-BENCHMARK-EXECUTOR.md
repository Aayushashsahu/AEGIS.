# AEGIS Mission 021 — Explicit Benchmark Execution CLI

**Date:** 2026-08-18
**Branch:** `mission-021-benchmark-executor`
**Base:** Mission 020 `06d047e9110bcc10368674da95ed5b03ace91baf`
**Status:** **IMPLEMENTED AND VALIDATED — REAL BENCHMARK DEFERRED**

## Executive result

Mission 021 replaces the Mission 012 validation-only CLI wrapper with an explicit execution contract. The default remains non-executing. `--dry-run` continues to validate only; execution requires both `--run` and `--output`. The executor performs fail-closed gates before creating the future benchmark root and is capable of planning exactly 180 participant-trial opportunities using injected test callers.

The real 180-run benchmark was **not** invoked. No real Gemini call, Bright Data operation, healing operation, provider approval, production commit, rollback, or benchmark metric calculation occurred during Mission 021.

## CLI changes

The wrapper now supports:

```text
--config PATH
--dry-run
--run
--output PATH
```

The modes are mutually exclusive. Without either mode, the CLI returns a clear `BLOCKED_NOT_READY` response requiring `--dry-run` or `--run`. `--run` without `--output` is rejected. Importing the executor creates no benchmark directory and performs no provider operation.

The exact future command is:

```powershell
$env:PYTHONPATH = "src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_017_corrected_frozen_config.json `
  --run `
  --output benchmarks/runs/mission_020_floor_2a80a8cf8d989326
```

That command is documented as the future execution boundary only. It was not run in Mission 021.

## Execution boundary and artifact identity

The executor uses `BenchmarkLifecyclePhase.BENCHMARK_EXECUTION` and the Mission 020 deterministic identity:

```text
benchmark_run_id = mission_020_floor_2a80a8cf8d989326
configuration_hash = 59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b
attempt_id = mission-020-floor-v1
```

It rejects any output root that overlaps the immutable Mission 019 smoke root:

```text
benchmarks/runs/mission_016_floor_59a11e27a71f/
```

It also requires the deterministic future root to be absent. The root is created only after the explicit execution gate passes. The planned tree is:

```text
benchmarks/runs/mission_020_floor_2a80a8cf8d989326/
├── frozen_config.json
├── participant_manifest.json
├── raw/
├── observations/
├── decisions/
├── metrics/
├── reports/
└── execution_log.json
```

Every raw record carries an immutable participant-run evidence envelope, manifest, terminal state, trial number, deterministic run ID, participant identity/revision/hash, mutation/severity/seed/fixture identity, ground-truth reference, timeout/retry policies, evidence references, artifact references, provenance, and failure details. Raw files are created exclusively and duplicate run IDs are rejected by the focused tests.

## Freeze and pre-execution gate

Before any execution opportunity, the executor checks the frozen configuration hash, canonical config validation, freeze snapshot, participant source revisions, participant revision metadata, participant readiness, fairness/shared metadata, clean fixture state, valid Mission 019 smoke evidence, artifact-root isolation, deterministic run ID, output-root absence, duplicate-free plan, code/config freeze, and Mission 010 calculator interface availability. The explicit model-caller requirement is also enforced for `--run`.

A failed gate returns `BLOCKED_NOT_READY` with `execution_authorized=false`, zero counters, and no created benchmark root. The gate does not modify the frozen configuration or historical Mission 019 evidence.

## Trial plan and lifecycle

Mission 021 executes the requested floor shape:

| Dimension | Count |
| --- | ---: |
| Participants | 3 |
| Mutations | 6 |
| Trial ordinals | 10 |
| Planned opportunities | **180** |

The frozen configuration remains byte-for-byte unchanged, including its single committed seed `12345`. Mission 021 represents the ten-trial floor with an explicit deterministic `trial_number` dimension while retaining the frozen seed for every trial. This avoids silently editing the configuration hash or inventing additional seed values. The existing validation-only dry-run therefore remains its historical 18-step plan; only the explicit execution boundary expands the authorized floor to 180 opportunities.

For each planned opportunity, the executor validates the clean fixture, obtains evaluator-owned mutation/ground-truth data without passing the truth payload to participants, applies the mutation, executes exactly one adapter, persists raw evidence, resets the fixture, verifies the clean reset, and records a terminal state. The allowed terminal states are `COMPLETED`, `FAILED`, `TIMED_OUT`, and `INVALIDATED`. Reset failures preserve the current raw artifact as `INVALIDATED` and halt the run.

Baseline A uses the existing static selector adapter and marks AEGIS-only concepts `NOT_APPLICABLE`. Baseline B uses the existing frozen Gemini configuration and first-candidate adapter, but tests inject a fake caller. AEGIS uses the existing TEST_DOUBLE lifecycle and preserves detection, diagnosis/evaluation, verification, RiskGovernor, CommitGate, quarantine, watch, and rollback semantics. No generated participant code is executed.

## Metric boundary compatibility

Mission 010 remains the sole metric authority. Mission 021 does not add a calculator. The existing `calculate_metrics()` boundary accepts `MutationRun` records, while the common executor produces `ParticipantRunEvidence` for all three participants and only the AEGIS TEST_DOUBLE path currently exposes evaluator `MutationRun` records. The executor therefore fails closed with `FAILED_METRIC_BOUNDARY` after raw execution if an all-participant compatible adaptation is unavailable; it does not calculate misleading partial metrics or invent a second formula.

This incompatibility was exercised by the injected test executor: all 180 test-double opportunities reached terminal `COMPLETED` raw records, but metric generation remained zero and the exact incompatibility was persisted in the execution log. This is a compatibility finding, not a benchmark result.

## Tests and validation

The focused Mission 021 suite passed with `12 passed`. It covers explicit CLI mode requirements, dry-run non-execution, corrected hash acceptance, wrong-hash blocking, wrong-revision blocking, fairness blocking, output-root collision blocking, deterministic trial IDs, 180 planned opportunities, exactly 180 injected execution opportunities, participant-specific provider-operation accounting, reset between trials, reset-failure invalidation, immutable raw evidence, terminal-state persistence, metric-boundary fail-closed behavior, and Mission 019 smoke-root preservation.

The complete suite passed with `246 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

CLI help passed:

```bash
PYTHONPATH=src python scripts/benchmark_runner.py --help
```

Frozen-config dry-run passed and preserved zero execution counters:

```bash
PYTHONPATH=src python scripts/benchmark_runner.py \
  --config benchmarks/configs/mission_017_corrected_frozen_config.json \
  --dry-run
```

Observed dry-run values include configuration hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. The historical Mission 019 smoke directory was not changed, and the future benchmark root was not created.

## Mission 021 real-execution counters

| Counter | Mission 021 real execution value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

The focused executor tests deliberately use injected fake model calls and temporary roots to prove the execution boundary. Those test-double opportunities are not real benchmark trials and do not support benchmark metrics or claims.

> AI proposes. Evidence decides.
