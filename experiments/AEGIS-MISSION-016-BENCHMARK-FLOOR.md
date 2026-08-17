# AEGIS Mission 016 — Minimum Credible Benchmark Floor

**Date:** 2026-08-17
**Run ID:** `mission_016_floor_f48ec5c5792b`
**Status:** **STOPPED_PREFLIGHT**
**Recommendation:** **FIX, then rerun Mission 016; do not scale**

## Executive result

Mission 016 did **not** execute the 180-run floor. The mandatory preflight correctly stopped the mission before the Baseline B smoke test and before every benchmark trial because the frozen Mission 015 participant metadata contains an implementation revision that does not resolve to the actual Git commit.

The exact mismatch is:

| Participant | Frozen revision in Mission 015 config | Actual Git commit | Result |
| --- | --- | --- | --- |
| BASELINE_A | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` | `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` | **FAIL** |
| BASELINE_B | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` | `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` | **FAIL** |
| AEGIS | `7de2bc65ed9eeb9f4abd24017543f3f366990738` | `7de2bc65ed9eeb9f4abd24017543f3f366990738` | PASS |

The two Baseline A/B values are not a valid abbreviated SHA and do not identify the committed implementation. This is a reproducibility and freeze-integrity failure. The frozen configuration was **not edited in place**, no participant hash was recomputed, and no benchmark was partially executed.

> **AI proposes. Evidence decides.** The preflight evidence rejected the run because the frozen participant identity could not be verified.

## Preflight result

The following checks passed before the revision mismatch caused the mandatory stop:

| Preflight check | Result |
| --- | --- |
| Mission 015 configuration hash | PASS: `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96` |
| Configuration validation | PASS |
| Fixture | PASS: `gpu-price-staging` v1 |
| Mutation set | PASS: M001–M006 |
| Seed | PASS: `12345` |
| Participant readiness | PASS: all three `READY` under the frozen artifact |
| Fairness | PASS |
| Metric authority | PASS: `mission-010-metrics-v1` |
| Artifact paths | PASS |
| Clean fixture state | PASS: immutable TEST_DOUBLE fixture |
| Mission 015 dry-run | PASS: `READY_TO_EXECUTE` |
| Participant code revision identity | **FAIL for BASELINE_A and BASELINE_B** |

The machine-readable evidence is stored in `benchmarks/runs/mission_016_floor_f48ec5c5792b/preflight_blocker.json`. The original preflight output is stored in `benchmarks/runs/mission_016_floor_f48ec5c5792b/preflight.json`.

## Baseline B smoke test

`BASELINE_B_EXECUTION_READINESS_SMOKE` was **not run**. This is required by the mission’s stop rule because a mandatory preflight check failed. Consequently, no claim is made about Gemini model reachability, prompt execution, first-candidate execution, normalized model evidence, or the model’s behavior on the fixture.

The Google Gemini connector was enabled only as a prerequisite for the required smoke boundary. Enabling the connector did not authorize a benchmark, and no Gemini call was made after the preflight failure.

## Benchmark execution

The requested floor was:

| Dimension | Count |
| --- | ---: |
| Mutations | 6 |
| Trials per mutation | 10 |
| Participants | 3 |
| Planned runs | **180** |
| Executed runs | **0** |

No raw participant run, mutation-trial result, observation, decision, metric result, or benchmark summary based on completed trials exists. The run directory contains only the frozen configuration, preflight evidence, blocker evidence, and zero-execution log. There are no `raw/`, `observations/`, `decisions/`, or `metrics/` results because the mission stopped before execution.

## Safety counters

| Counter | Value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

No Bright Data operation, healing operation, provider approval, production commit, rollback, or Mission 010 metric calculation was performed.

## Required fix

The frozen participant identity must be corrected through an owner-reviewed freeze correction. The next safe action is **not** to edit `mission_015_frozen_config.json` manually. Instead, create a new owner-approved correction mission that resolves the actual Baseline A/B implementation revision, recomputes the participant hashes and canonical configuration hash, preserves the same approved mutation set, seed, fixture, timeout/retry/backoff, participant definitions, safety policy, and metric formula, and records why the old Mission 015 hash is superseded.

After that correction is independently reviewed, rerun the Mission 016 preflight from a clean fixture. If and only if preflight passes, run the isolated Baseline B smoke test. If the smoke test passes, execute exactly 180 runs. Do not execute partial trials, tune thresholds, substitute a model, or scale to 540 runs.

## Reproducibility metadata

| Field | Value |
| --- | --- |
| Branch | `mission-016-benchmark-floor` |
| Current commit at preflight | `1f51f4b3826b092a62e6592228992ad3e8aac2c7` |
| Frozen Mission 015 configuration hash | `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96` |
| Fixture | `gpu-price-staging` v1 |
| Seed | `12345` |
| Metric authority | `mission-010-metrics-v1` |
| Runtime | Python 3.12; standard-library application modules; pytest |
| Preflight command | `PYTHONPATH=src python3 scripts/mission016_preflight_smoke.py` |
| Smoke status | `NOT_RUN_DUE_TO_PREFLIGHT_STOP` |
| Floor status | `STOPPED_PREFLIGHT` |

## Final recommendation

**FIX.** Do not present a benchmark result, do not claim the minimum floor is credible, do not scale, and do not start Mission 017. The correct reliability outcome is to preserve this invalidation evidence and obtain a corrected owner-approved participant freeze before any execution.
