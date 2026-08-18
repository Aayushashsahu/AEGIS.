# AEGIS Mission 020 — Separate Preflight/Smoke Artifacts from Benchmark-Run Artifacts

**Date:** 2026-08-18
**Branch:** `mission-020-separate-preflight-artifacts`
**Status:** **PREFLIGHT_PASS — BENCHMARK DEFERRED**

## Executive result

Mission 020 repaired the artifact lifecycle collision without modifying the frozen configuration or committed Mission 019 evidence. The existing Mission 019 preflight/smoke directory is now treated as immutable validation evidence. The repaired command validates that evidence read-only, does not rerun Gemini when the evidence is valid, and reports a separate deterministic future benchmark-run identity.

No benchmark trial, Gemini operation, Bright Data call, healing operation, approval, production commit, rollback, or metric calculation was performed in Mission 020.

## Root cause

Mission 019 committed successful preflight/smoke evidence under:

```text
benchmarks/runs/mission_016_floor_59a11e27a71f/
```

The directory contains frozen configuration, preflight evidence, smoke evidence, and execution logs. The existing entry point still assumed this directory was a new future floor directory and performed:

```python
FLOOR_RUN_ROOT.mkdir(parents=True, exist_ok=False)
```

It then attempted to rewrite the committed evidence. The result was a `FileExistsError` before the lifecycle could validate the already completed smoke phase.

## Corrected lifecycle design

Mission 020 separates the lifecycle phases explicitly:

| Phase | Role | Mission 020 behavior |
| --- | --- | --- |
| `PREFLIGHT` | Validate frozen configuration, participant identity, fairness, fixture, and existing evidence | Read-only; returns `PREFLIGHT_PASS` or fails closed |
| `SMOKE` | Exercise the authorized Baseline B readiness boundary | Existing Mission 019 evidence is validated; Gemini is not rerun |
| `BENCHMARK_EXECUTION` | Future 180-run floor and raw evidence production | Not activated; `execute_one()` is not called |

The preflight now validates the existing Mission 019 files in place:

```text
benchmarks/runs/mission_016_floor_59a11e27a71f/
├── frozen_config.json
├── preflight.json
├── execution_log.json
└── baseline_b_execution_readiness_smoke/
    ├── smoke.json
    └── execution_log.json
```

The validator checks file presence, JSON shape, smoke status, all boolean smoke checks, candidate acceptance, bounded application, `NOT_PROVIDED` runtime ground truth, preflight status, frozen configuration hash, zero benchmark/provider/healing/metric counters, and `execution_authorized=false`. Missing, corrupt, or semantically invalid evidence returns a fail-closed result. No file is rewritten.

## Deterministic future benchmark identity

The future benchmark attempt uses an identity derived from the corrected configuration hash, explicit attempt/version identifier, and sorted participant source revisions:

```text
configuration_hash = 59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b
attempt_id = mission-020-floor-v1
participant revisions = BASELINE_A 067c06d8..., BASELINE_B 067c06d8..., AEGIS b7905004...
benchmark_run_id = mission_020_floor_2a80a8cf8d989326
```

The identifier is deterministic, provider-neutral, distinct from `mission_016_floor_59a11e27a71f`, and does not depend solely on wall-clock time.

The future benchmark artifact layout is planned as:

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

Mission 020 does not create this directory. `BenchmarkArtifactLayout` rejects any root that equals, contains, or is contained by the immutable Mission 019 smoke root. `BenchmarkRunner` accepts a future artifact-root override only through this isolated execution boundary; frozen configuration metadata remains unchanged.

## Frozen values and historical preservation

The corrected Mission 017 configuration remains unchanged with canonical hash:

```text
59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b
```

M001–M006, seed `12345`, fixture `gpu-price-staging` v1, `gemini-3.6-flash`, exact prompts, timeout/retry/backoff, `mission-010-metrics-v1`, and all participant policies remain unchanged. The Mission 019 smoke directory and Mission 016 STOPPED_PREFLIGHT evidence were verified byte-identical before and after read-only preflight.

## Validation result

The exact command was run in read-only mode:

```bash
PYTHONPATH=src python scripts/mission016_preflight_smoke.py
```

It returned:

```text
status = PREFLIGHT_PASS
smoke_evidence.status = VALID
preflight_smoke_run_id = mission_016_floor_59a11e27a71f
benchmark_run_id = mission_020_floor_2a80a8cf8d989326
benchmark_execution_available = false
```

The command did not invoke `run_baseline_b_smoke()`, did not call Gemini, and did not write preflight/smoke or benchmark artifacts.

## Tests

The focused Mission 020 suite passed with `7 passed`:

```bash
PYTHONPATH=src:. pytest -q tests/unit/test_mission020.py
```

The Mission 018 compatibility tests passed with `7 passed` in the combined focused run. The complete repository suite passed with `234 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The focused coverage proves that existing smoke evidence is accepted without recreation, valid evidence does not call Gemini, corrupt evidence fails closed, the future run ID is deterministic and distinct, lifecycle phases are explicit, benchmark roots cannot overlap smoke evidence, historical artifacts remain byte-identical, and all execution counters remain zero.

## Safety counters

| Counter | Value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

No metrics are claimed. Mission 010 remains the sole metric authority.

## Exact future command boundary

Mission 020 does not provide or invoke a live benchmark command. The only validated command is the read-only preflight above; it must precede any separately authorized future benchmark attempt. The existing benchmark CLI remains validation-only:

```bash
PYTHONPATH=src python scripts/benchmark_runner.py --config benchmarks/configs/mission_017_corrected_frozen_config.json --dry-run
```

No 180-run benchmark command is executed or claimed by Mission 020. The future benchmark root and layout are deterministic and documented, but execution authorization remains false.

> AI proposes. Evidence decides.
