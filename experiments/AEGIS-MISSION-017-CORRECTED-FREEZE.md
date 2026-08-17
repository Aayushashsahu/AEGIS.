# AEGIS Mission 017 — Corrected Benchmark Freeze After Preflight Invalidation

**Date:** 2026-08-17
**Status:** **CORRECTED_FREEZE_VALIDATED_ONLY**
**Recommendation:** **STOP before Mission 016 rerun**
**Branch:** `mission-017-corrected-freeze`

## Executive result

Mission 017 corrected the participant revision identity failure discovered by Mission 016. It created a new owner-reviewed, immutable benchmark configuration that supersedes Mission 015 without modifying Mission 015’s historical configuration or freeze records in place.

Mission 017 performed **no benchmark execution**. It did not run the Baseline B Gemini smoke test, a mutation trial, Bright Data, healing, approval, production commit, rollback, or metric calculation.

> **AI proposes. Evidence decides.** Mission 017 accepted the correction only after the actual Git revisions resolved, the two baseline strategies were inspected, participant hashes were recomputed, owner approvals and readiness promotions were recorded, configuration validation passed, fairness passed, and the validation-only dry-run returned `READY_TO_EXECUTE`.

## Mission 015 invalidation and supersession

Mission 016 stopped because Mission 015 stored the non-resolving Baseline A/B revision `0e8bcc4a2c2184cae9a50b291054ec47d83fc895`. The actual committed implementation revision is `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47`. AEGIS was already correct at `7de2bc65ed9eeb9f4abd24017543f3f366990738`.

| Historical item | Value | Mission 017 treatment |
| --- | --- | --- |
| Mission 015 configuration hash | `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96` | **SUPERSEDED** |
| Mission 015 frozen configuration | `benchmarks/configs/mission_015_frozen_config.json` | Preserved unchanged |
| Mission 015 freeze records | `experiments/mission_015_freeze_records.json` | Preserved unchanged |
| Mission 016 result | `STOPPED_PREFLIGHT` | Preserved as historical invalidation evidence |

## Actual implementation revisions

All three revisions resolved exactly as Git commits.

| Participant | Actual revision | Resolution | Role |
| --- | --- | --- | --- |
| BASELINE_A | `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` | PASS | Deterministic static-selector extraction |
| BASELINE_B | `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` | PASS | Naive Gemini first-candidate repair boundary |
| AEGIS | `7de2bc65ed9eeb9f4abd24017543f3f366990738` | PASS | Existing AEGIS TEST_DOUBLE lifecycle |

## Baseline A/B strategy separation

Inspection of the actual implementation represented by `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` confirmed that the two participant paths are distinct despite sharing one implementation commit.

| Check | Baseline A | Baseline B |
| --- | --- | --- |
| Static selector extractor | PASS | Not applicable |
| Gemini model path | Not used | PASS: `gemini-3.6-flash` |
| Approved prompts | Not used | PASS: exact frozen system and repair prompts |
| First-candidate behavior | Not used | PASS: `FIRST_CANDIDATE`, one candidate, auto-accept policy |
| LLM/model caller | Absent | Injected model-call seam present |
| AEGIS verification | Not used | Not used |
| RiskGovernor | Not used | Not used |
| CommitGate | Not used | Not used |
| Participant execution | Not performed | Not performed |

Baseline A is static extraction only. Baseline B is the naive model-assisted repair strategy. No evaluator ground truth was passed into either participant during this identity inspection.

## Corrected participant hashes

Hashes were independently recomputed from the corrected participant proposal, actual implementation revision, and frozen participant metadata. The Mission 015 hashes were not reused.

| Participant | Corrected participant hash |
| --- | --- |
| BASELINE_A | `17b0f73fb909915f69e1a442959831463a08930df83dadcaedab7e543a60348f` |
| BASELINE_B | `01a71de8a60c7d20e1d68744f1ffea3d5ebda0539c0a2e656d3d3e106169e113` |
| AEGIS | `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75` |

The AEGIS hash equals the prior value because its actual revision and participant metadata were already correct; this equality was independently produced by the deterministic calculation rather than copied into the corrected proposal.

## Owner-review evidence and readiness promotions

The corrected rationale was recorded exactly as requested:

> “Superseding owner-approved benchmark freeze after Mission 016 preflight identified a participant revision identity mismatch. All benchmark methodology, safety policy, mutation definitions, seed, fixture, timeout, retry, and metric formula remain unchanged.”

Each participant received `approved=true`, reviewer and owner `PROJECT_OWNER`, an approval timestamp, a unique correlation ID, the corrected revision, and the corrected participant hash. The append-only promotions are all `NOT_READY → READY`.

| Participant | Approval timestamp | Correlation ID | Promotion |
| --- | --- | --- | --- |
| BASELINE_A | `2026-08-17T18:49:04.194777+00:00` | `ad472cd8-1131-4e25-a5cc-e19bd44dbc11` | NOT_READY → READY |
| BASELINE_B | `2026-08-17T18:49:04.194777+00:00` | `b458f8b8-9a34-4eef-8a48-7c9e44a2084d` | NOT_READY → READY |
| AEGIS | `2026-08-17T18:49:04.194777+00:00` | `8d654c19-398d-48f5-af8a-b160c3ff436c` | NOT_READY → READY |

The complete records are in `experiments/mission_017_corrected_freeze_records.json`.

## Corrected immutable configuration

The new configuration is `benchmarks/configs/mission_017_corrected_frozen_config.json`.

| Field | Value |
| --- | --- |
| Benchmark ID | `aegis-benchmark-mission-017-corrected` |
| Benchmark version | `mission-017-corrected-freeze-v1` |
| New canonical configuration hash | `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b` |
| Superseded configuration hash | `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96` |
| Fixture | `gpu-price-staging` v1 |
| Mutations | M001–M006 |
| Seed | `12345` |
| Metric authority | `mission-010-metrics-v1` |
| Timeout | 300 seconds |
| Retry count | 0 |
| Backoff | 0 |
| Runtime ground-truth payload | `NOT_PROVIDED` |

All other approved benchmark methodology and safety values remain unchanged. The corrected dry-run artifact is `benchmarks/configs/mission_017_corrected_dry_run.json`.

## Validation-only dry-run

The exact required command was run:

```bash
PYTHONPATH=src python3 scripts/benchmark_runner.py \
  --config benchmarks/configs/mission_017_corrected_frozen_config.json \
  --dry-run
```

The result was `READY_TO_EXECUTE` with 18 planned manifests, all three participants ready, and fairness `PASS`. This status is validation readiness only and is not authorization to execute Mission 016.

| Dry-run check | Result |
| --- | --- |
| Configuration validation | PASS |
| Participant readiness | PASS: BASELINE_A, BASELINE_B, AEGIS |
| Freeze/hash validation | PASS |
| Fixture and mutation checks | PASS |
| Seed check | PASS: 12345 |
| Fairness | PASS |
| Planned manifests | 18 |
| Validation-only | true |
| Benchmark execution authorized | false |

The runner warning that the repository is not clean is expected because user-modified Mission 002/008 files and unrelated workspace files were preserved. No benchmark execution is authorized by the dry-run.

## Safety counters

| Counter | Value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

## Test evidence

The dedicated Mission 017 tests and the complete existing suite passed:

```text
214 passed
```

The tests cover actual revision resolution, Baseline A/B separation, corrected participant hashes, preservation of frozen benchmark values, owner approvals, readiness promotions, fairness, corrected configuration validation, old-hash supersession, and zero-execution dry-run counters.

## Exact next action

Mission 017 is complete. The exact command to rerun the Mission 016 preflight after this corrected freeze is:

```bash
PYTHONPATH=src python3 scripts/mission016_preflight_smoke.py
```

Do **not** start Mission 016 from this task, do **not** run the Baseline B smoke test, and do **not** execute a benchmark or generate metrics. Mission 017 stops at the corrected validation-only freeze.
