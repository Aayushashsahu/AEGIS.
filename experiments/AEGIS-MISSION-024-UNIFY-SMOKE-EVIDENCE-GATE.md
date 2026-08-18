# AEGIS Mission 024 — Unify Execution Gate with Validated Preflight Smoke Evidence

**Date:** 2026-08-18
**Branch:** `mission-024-unify-smoke-evidence-gate`
**Base:** Mission 023 `c39cad51cedd5c69069105809f78c5ce372e88cc`
**Status:** **IMPLEMENTED AND VALIDATED — BENCHMARK NOT EXECUTED**

## Executive result

Mission 024 removes the duplicate interpretation of immutable Mission 019 smoke evidence. The preflight and `BenchmarkExecutor.execution_gate()` now consume the same provider-neutral resolver and validator from `src/aegis/smoke_evidence.py`. Both resolve the exact same absolute paths from an explicit `repository_root`; neither derives evidence from the future benchmark output root, the run ID, or the current working directory.

The read-only preflight returned `PREFLIGHT_PASS`. The execution gate returned `passed=true`, `smoke_evidence=true`, `planned_run_count=true`, `artifact_root_absent=true`, and `execution_authorized=false`. The full suite passed with `259 passed`. No benchmark execution occurred.

## Exact inconsistency and root cause

Before Mission 024, `scripts/mission016_preflight_smoke.py` and `BenchmarkExecutor._validate_immutable_smoke_evidence()` each maintained their own path and validation logic. Mission 023 corrected the executor’s nested Baseline B path, but the two implementations still remained independent. This meant the two entry points could diverge even when they appeared to describe the same evidence contract.

The preflight’s actual contract was:

```text
SMOKE_ROOT = benchmarks/runs/mission_016_floor_59a11e27a71f/
BASELINE_B_SMOKE_ROOT = SMOKE_ROOT/baseline_b_execution_readiness_smoke/
SMOKE = BASELINE_B_SMOKE_ROOT/smoke.json
SMOKE_LOG = BASELINE_B_SMOKE_ROOT/execution_log.json
PREFLIGHT = SMOKE_ROOT/preflight.json
ROOT_EXECUTION_LOG = SMOKE_ROOT/execution_log.json
FROZEN_CONFIG = SMOKE_ROOT/frozen_config.json
```

The executor had equivalent-looking logic but constructed the required paths locally from its layout object. The defect was therefore a **consistency defect**, not a filesystem-missing condition. Mission 024 establishes one canonical implementation so this class of divergence cannot recur between preflight and execution-gate validation.

## Canonical resolver and validator

The canonical implementation is:

```text
src/aegis/smoke_evidence.py
├── resolve_immutable_smoke_evidence(repository_root)
└── validate_immutable_smoke_evidence(repository_root)
```

`SmokeEvidencePaths` returns the repository root, canonical smoke root, Baseline B smoke root, and all five required evidence paths. `SmokeEvidenceValidation` reuses the Mission 019/020 checks for status, boolean smoke checks, candidate acceptance, bounded application, generated-code prohibition, runtime ground truth, smoke-log status, preflight result, frozen hash, zero historical counters, and unauthorized execution.

The preflight keeps its historical exported path names for compatibility but derives them from `SmokeEvidencePaths` and wraps the shared validator. `BenchmarkExecutor` stores the same resolved paths and delegates its compatibility method directly to the shared validator. The executor layout continues to use the canonical smoke root for artifact isolation and the separate Baseline B smoke root for evidence location.

## Before and after paths

| Evidence identity | Before Mission 024 | After Mission 024 |
|---|---|---|
| Canonical smoke root | Independently represented by each caller | `SmokeEvidencePaths.smoke_root` |
| Baseline B smoke root | Independently derived | `SmokeEvidencePaths.baseline_b_smoke_root` |
| `smoke.json` | Caller-specific derivation | `baseline_b_smoke_root / "smoke.json"` |
| Baseline B smoke log | Caller-specific derivation | `baseline_b_smoke_root / "execution_log.json"` |
| Preflight evidence | Caller-specific derivation | `smoke_root / "preflight.json"` |
| Root execution log | Caller-specific derivation | `smoke_root / "execution_log.json"` |
| Frozen config evidence | Caller-specific derivation | `smoke_root / "frozen_config.json"` |
| Future benchmark root | `mission_020_floor_2a80a8cf8d989326` | Unchanged and separate |

All paths are resolved from `repository_root`, which is explicitly passed to the resolver. No path is derived from the future benchmark root or current working directory.

## Regression and validation results

The focused Mission 024 test proves that:

1. the preflight and executor resolve identical absolute `SmokeEvidencePaths`;
2. the shared validator discovers all five real tracked evidence files;
3. preflight returns `passed=true` without rerunning Gemini;
4. the executor’s validator returns `pass=true` and `status=VALID`;
5. candidate acceptance, bounded application, and `NOT_PROVIDED` runtime ground truth remain valid;
6. `execution_gate()` returns `passed=true` with `smoke_evidence=true`;
7. `planned_run_count=true`, `artifact_root_absent=true`, and `execution_authorized=false`;
8. the immutable smoke evidence remains byte-identical; and
9. the future benchmark root remains absent.

| Validation | Result |
|---|---|
| Focused Mission 024 tests | `2 passed` |
| Complete suite | `259 passed` |
| Read-only preflight | `PREFLIGHT_PASS` |
| Shared smoke validator | `pass=true`, `status=VALID` |
| Execution gate | `passed=true` |
| Configuration hash | `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b` |
| Planned run count | `180` |
| Future benchmark root | Absent |
| Historical evidence | Byte-identical |

The historical smoke JSON contains `provider_operation_count=1` as preserved Mission 019 smoke evidence. The current Mission 024 execution counters remain zero; no new provider operation was performed.

## Execution boundary

Mission 024 did not invoke `benchmark_runner.py --run`, `BenchmarkExecutor.execute()`, trial 1, Gemini, Bright Data, healing, approval, production commit, rollback, or metric generation.

| Counter | Value |
|---|---:|
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

## Exact future command

The real benchmark remains deferred:

```powershell
$env:PYTHONPATH = "src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_017_corrected_frozen_config.json `
  --run `
  --output benchmarks/runs/mission_020_floor_2a80a8cf8d989326
```

> AI proposes. Evidence decides.

## References

[1]: ../src/aegis/smoke_evidence.py "Canonical immutable smoke-evidence resolver and validator"
[2]: ../scripts/mission016_preflight_smoke.py "Read-only Mission 020 preflight"
[3]: ../src/aegis/benchmark_executor.py "Mission 021/024 execution gate"
[4]: ../tests/unit/test_mission024.py "Mission 024 shared-path regression tests"
[5]: ../docs/06_BENCHMARK_METHODOLOGY.md "Canonical benchmark methodology"
[6]: ../docs/11_API_CONTRACTS.md "Canonical API contracts"
