# AEGIS Mission 023 — Fix Benchmark Smoke-Evidence Path Resolution

**Date:** 2026-08-18
**Branch:** `mission-023-fix-smoke-evidence-path`
**Base:** Mission 022 `2bcc2f072bc87eb0e4d4640cd7c3bb2eef7af123`
**Status:** **IMPLEMENTED AND VALIDATED — BENCHMARK NOT EXECUTED**

## Executive result

Mission 023 fixed a path-resolution defect in `BenchmarkExecutor._validate_immutable_smoke_evidence()`. The executor previously passed the canonical Mission 019 run directory as `layout.smoke_root`, but the validator treated that directory as if it were the Baseline B smoke subdirectory. It consequently searched for `smoke.json` and the smoke execution log one level too high and reported valid tracked evidence as missing.

The artifact-layout contract now explicitly represents the canonical smoke root, the Baseline B smoke-evidence root, and the separate future benchmark root. The validator reads the exact immutable paths, and the execution gate now passes without calling `execute()`, trial 1, Gemini, Bright Data, healing, metric generation, approval, commit, or rollback.

## Exact root cause

The actual tracked evidence layout is:

```text
benchmarks/runs/mission_016_floor_59a11e27a71f/
├── baseline_b_execution_readiness_smoke/
│   ├── smoke.json
│   └── execution_log.json
├── preflight.json
├── execution_log.json
└── frozen_config.json
```

The old executor value was:

```text
self.layout.smoke_root
= benchmarks/runs/mission_016_floor_59a11e27a71f/
```

The old validator then constructed:

```text
root / "smoke.json"
root / "execution_log.json"
root.parent / "preflight.json"
root.parent / "execution_log.json"
root.parent / "frozen_config.json"
```

The first two paths were incorrect because `root` was the canonical run root rather than the Baseline B smoke subroot. The latter three paths were also incorrect because `root.parent` was `benchmarks/runs/`, not the canonical Mission 019 run root. This caused `smoke_evidence=false` and the missing-evidence list even though every required file existed and was tracked.

## Corrected path contract

| Name | Correct resolved path |
|---|---|
| `SMOKE_ROOT` | `benchmarks/runs/mission_016_floor_59a11e27a71f/` |
| `BASELINE_B_SMOKE_ROOT` | `benchmarks/runs/mission_016_floor_59a11e27a71f/baseline_b_execution_readiness_smoke/` |
| `BENCHMARK_ROOT` | `benchmarks/runs/mission_020_floor_2a80a8cf8d989326/` |
| Smoke file | `BASELINE_B_SMOKE_ROOT/smoke.json` |
| Smoke execution log | `BASELINE_B_SMOKE_ROOT/execution_log.json` |
| Preflight | `SMOKE_ROOT/preflight.json` |
| Root execution log | `SMOKE_ROOT/execution_log.json` |
| Frozen config evidence | `SMOKE_ROOT/frozen_config.json` |

`BenchmarkArtifactLayout.smoke_root` now means the canonical immutable run root used for benchmark-root isolation. `BenchmarkArtifactLayout.baseline_b_smoke_root` and `smoke_evidence_root` identify the exact Baseline B smoke subroot used by the validator. Existing three-argument layout construction remains compatible by deriving the Baseline B subroot from the canonical smoke root.

The future benchmark root remains separate and unchanged:

```text
mission_020_floor_2a80a8cf8d989326
```

## Regression test

The focused Mission 023 regression test asserts all five required files exist at the exact canonical paths, validates `status=VALID`, and checks:

| Check | Result |
|---|---|
| Smoke status | `PASS` |
| Baseline B candidate accepted | `true` |
| Bounded application | `true` |
| Runtime ground truth | `NOT_PROVIDED` |
| Preflight | Passed |
| Frozen configuration hash | Matches `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b` |
| All execution counters in historical log | Zero / unauthorized |
| Smoke validator | `pass=true`, `status=VALID` |
| Execution gate | `passed=true` |
| Future benchmark root | Absent |

The test invokes `execution_gate()` only. It never calls `BenchmarkExecutor.execute()`.

## Validation

The focused Mission 023 suite passed with `2 passed`. The complete repository suite passed with `257 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission023.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The validation-only gate result was `passed=true`. All gate checks were true, including configuration hash, configuration validation, freeze validation, participant source revisions, participant readiness, fairness, clean fixture, smoke evidence, artifact isolation, deterministic run ID, artifact-root absence, duplicate-free plan, code/config freeze, metric authority availability, model-caller readiness, and the planned 180-run count.

The immutable Mission 019 smoke directory was byte-identical before and after validation. The future benchmark root was not created.

## Execution boundary

Mission 023 counters remain:

| Counter | Value |
|---|---:|
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

No real benchmark command was run. No Gemini, Bright Data, healing, approval, commit, rollback, or metric operation occurred.

## Exact deferred command

The future command remains deferred:

```powershell
$env:PYTHONPATH = "src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_017_corrected_frozen_config.json `
  --run `
  --output benchmarks/runs/mission_020_floor_2a80a8cf8d989326
```

> AI proposes. Evidence decides.

## References

[1]: ../src/aegis/benchmark_lifecycle.py "Benchmark lifecycle and artifact-layout contract"
[2]: ../src/aegis/benchmark_executor.py "Explicit benchmark execution gate and smoke validator"
[3]: ../tests/unit/test_mission023.py "Mission 023 path-resolution regression tests"
[4]: ../docs/06_BENCHMARK_METHODOLOGY.md "Canonical benchmark methodology"
[5]: ../docs/11_API_CONTRACTS.md "Canonical API contracts"
