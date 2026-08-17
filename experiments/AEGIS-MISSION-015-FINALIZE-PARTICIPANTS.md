# AEGIS Mission 015 — Finalize Benchmark Participants

**Date:** 2026-08-17
**Scope:** Participant implementation finalization, owner-reviewed readiness promotion, new frozen benchmark configuration, and validation-only dry run.
**Execution boundary:** No comparative benchmark trial, Bright Data operation, healing operation, provider approval, production commit, rollback, or metric calculation was executed.

## Decision summary

Mission 015 resolved the Mission 014 `BLOCKED_NOT_READY` state using only the owner-approved values. Baseline A, Baseline B, and the AEGIS TEST_DOUBLE adapter were implemented or finalized, tested, assigned real implementation revisions, and converted into deterministic participant-freeze proposals. Each proposal passed validation, received an explicit owner-review record, and was promoted through an immutable `NOT_READY → READY` transition. The promotions were applied to a new immutable `BenchmarkConfig` derived from the Mission 011 validation floor.

The central safety principle remains unchanged:

> **AI proposes. Evidence decides.**

`READY_TO_EXECUTE` means that the frozen protocol is internally ready. It is **not** authorization to execute the benchmark.

## Implementation revisions and participant hashes

| Participant | Implementation revision | Participant configuration hash | Status |
| --- | --- | --- | --- |
| BASELINE_A | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` | `fc95be9ae66b859ab770d23ab46c2ce82dcad645325f833f5fac88959dc3e5d6` | READY |
| BASELINE_B | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` | `20f90c001f061683c91acc65a2031f07651678041f88db064ad68157084bfb1b` | READY |
| AEGIS | `7de2bc65ed9eeb9f4abd24017543f3f366990738` | `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75` | READY |

Baseline A is the deterministic fixed-selector extractor using `baseline-a-v1` and `gpu-price-schema-v1`, with no LLM, healing, AEGIS detection, AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, or rollback path. Baseline B uses `GOOGLE_GEMINI_API`, model `gemini-3.6-flash`, stable revision, the exact approved prompt configuration, `max_output_tokens=8192`, disabled tools, first-candidate-only behavior, and `auto_accept_first_candidate=true`. It has no AEGIS verification, RiskGovernor, or CommitGate. Without an explicitly injected model caller, it records `MODEL_CALL_NOT_EXECUTED_IN_VALIDATION_ONLY_MISSION` rather than substituting a provider or model. AEGIS uses the existing `AegisAdapter` TEST_DOUBLE lifecycle and retains the existing safety gates.

## Owner-review decisions

The three owner-review records are stored in `experiments/mission_015_freeze_records.json`. Each record has `approved=true`, `owner=PROJECT_OWNER`, `reviewer=PROJECT_OWNER`, the mission-level rationale, the same current UTC approval timestamp (`2026-08-17T16:46:21.378886+00:00`), a generated UUID correlation ID, and the participant hash shown above.

| Participant | Correlation ID | Approved | Participant hash |
| --- | --- | --- | --- |
| BASELINE_A | `d03222b4-93f8-492f-b851-19efcc16ec8e` | true | `fc95be9ae66b859ab770d23ab46c2ce82dcad645325f833f5fac88959dc3e5d6` |
| BASELINE_B | `c8ae8923-8094-434b-8b34-10ca6c97e2a1` | true | `20f90c001f061683c91acc65a2031f07651678041f88db064ad68157084bfb1b` |
| AEGIS | `d2c914c8-1253-48da-8804-f89fe5d7d974` | true | `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75` |

Rationale used for all three records:

> Owner-approved benchmark participant configuration for the minimum comparative benchmark; participant behavior, safety boundaries, and common execution policy are frozen before benchmark execution.

## Readiness promotions

Each promotion is append-only and records the following transition:

| Participant | Prior status | New status | Reviewer | Implementation revision |
| --- | --- | --- | --- | --- |
| BASELINE_A | `NOT_READY` | `READY` | `PROJECT_OWNER` | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` |
| BASELINE_B | `NOT_READY` | `READY` | `PROJECT_OWNER` | `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` |
| AEGIS | `NOT_READY` | `READY` | `PROJECT_OWNER` | `7de2bc65ed9eeb9f4abd24017543f3f366990738` |

No Mission 013 or Mission 014 evidence was modified.

## Frozen benchmark configuration

The new configuration is stored at `benchmarks/configs/mission_015_frozen_config.json`. Its canonical SHA-256 is:

```text
f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96
```

The historical Mission 011 source hash was:

```text
fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3
```

The hashes differ, so the old configuration hash is invalidated and was not reused. The following frozen values were preserved or applied:

| Field | Frozen value |
| --- | --- |
| Mutation IDs | `M001`, `M002`, `M003`, `M004`, `M005`, `M006` |
| Severity mapping | Canonical L1–L5 mapping unchanged |
| Fixture | `gpu-price-staging` v1 |
| Seed | `12345` |
| Metric formula | `mission-010-metrics-v1` |
| Participant timeout | 300 seconds |
| Participant retry | 0 retries |
| Participant backoff | 0 seconds |
| Benchmark timeout | `collection_ms=300000`, `healing_ms=300000`, `polling_ms=300000`, `verification_ms=300000`, `total_ms=300000` |
| Benchmark retry | `BOUNDED`, `max_attempts=1`, `backoff_ms=0` |

## Fairness and dry-run result

Fairness is `PASS`. All participants receive the same mutation, seed, fixture, ground-truth reference shape, timeout policy, retry policy, backoff, and trial metadata. The runtime ground-truth payload is `NOT_PROVIDED` for all participants. Ground truth is not supplied to participant logic at runtime.

The dry-run artifact is stored at `benchmarks/configs/mission_015_dry_run.json`. The exact CLI boundary was:

```bash
PYTHONPATH=src python3 scripts/benchmark_runner.py \
  --config benchmarks/configs/mission_015_frozen_config.json \
  --dry-run
```

The result was `READY_TO_EXECUTE` with an 18-manifest plan and all three participant readiness reports `READY`. This result is a validation-only state and does not authorize execution.

## Safety counters

| Counter | Result |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

The complete test command passed with **207 tests**:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

No benchmark metrics are claimed. The repository is intentionally stopped before benchmark execution and before Mission 016.
