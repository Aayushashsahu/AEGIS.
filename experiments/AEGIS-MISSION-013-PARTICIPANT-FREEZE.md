# AEGIS Mission 013 — Participant Freeze + Readiness Promotion

**Date:** 2026-08-17
**Status:** **COMPLETE for fail-closed participant-freeze workflow and validation-only readiness evidence**
**Scope:** Define human-reviewed participant metadata proposals, deterministic participant hashes, explicit `NOT_READY → READY` promotion evidence, participant-aware configuration invalidation, fairness checks, and a zero-execution dry-run boundary.
**Explicitly out of scope:** Owner approval that was not supplied, automatic model/prompt selection, full benchmark execution, the 10-trial floor, 540 runs, benchmark results, provider operations, healing, approval, production commit, rollback, metric calculation, and safety-policy changes.

> **AI proposes. Evidence decides.**

## Mission result

Mission 013 implements the readiness-promotion workflow required before the AEGIS benchmark can be considered executable. The workflow is deliberately human-reviewed: it records proposals and explicit placeholders, rejects incomplete metadata, requires an owner approval record for promotion, returns a new immutable configuration with a regenerated benchmark hash, and records an append-only `NOT_READY → READY` evidence transition.

No owner-approved participant values were supplied during this mission. Therefore no promotion was performed. The active Mission 011 configuration hash remains the source hash, all three participants remain not ready, and the final dry run is `BLOCKED_NOT_READY`. This is the correct fail-closed result.

## 1. Baseline A status

`BASELINE_A` is defined as static selector extraction only. The participant proposal requires an extraction implementation, configuration, timeout policy, retry policy, output normalization policy, provenance, artifact schema, and explicit `NOT_USED` values for healing, AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, and rollback.

The default artifact contains no final Baseline A implementation revision or approved participant configuration. Its proposal is explicit rather than empty: implementation, extraction configuration, timeout, normalization, and artifact schema are `NOT_READY`; prohibited AEGIS controls remain `NOT_USED`. The validator result is `NOT_READY`.

| Baseline A field | Mission 013 state |
| --- | --- |
| Implementation revision | `NOT_READY` |
| Extraction implementation | `NOT_READY` |
| Configuration | `{status: NOT_READY}` |
| Timeout policy | `{}` / missing for approval |
| Retry policy | Existing bounded slot metadata only |
| Output normalization | `NOT_READY` |
| Provenance | `TEST_DOUBLE` placeholder, not an approval |
| Artifact schema | `NOT_READY` |
| Healing / verification / risk / gate | Explicitly `NOT_USED` |
| Participant status | `NOT_READY` |
| Participant hash supplied | `NOT_READY` |
| Computed proposal hash | `8ace4f78cfcd7c7b87d02871c3447cd55444b2eae1304e4dbaa344f5c4bdadd1` |

The computed hash is a proposal-evaluation value, not a frozen approved hash. It is not inserted into the benchmark configuration.

## 2. Baseline B status

`BASELINE_B` remains the required project-owner decision. The proposal schema requires a model identifier, provider, exact system prompt, exact repair prompt/template, sampling configuration, max output, permitted tools, timeout, retry policy, first-candidate policy, implementation revision, artifact schema, and participant configuration hash.

The first-candidate behavior is represented explicitly as a policy slot: model proposes repair, the first candidate executes, the first candidate is accepted, and no AEGIS verification, RiskGovernor, or CommitGate is used. The implementation does not choose a model or prompt automatically.

| Baseline B field | Mission 013 state |
| --- | --- |
| Model identifier | `TBD` |
| Provider | `TBD` |
| Exact system prompt | `TBD` |
| Exact repair prompt/template | `TBD` |
| Sampling configuration | `TBD` |
| Max output | `TBD` |
| Tools permitted | `TBD` |
| Timeout policy | `{}` / missing for approval |
| Retry policy | Existing bounded slot metadata only |
| First-candidate policy | Explicit slot, not approved/executed |
| Implementation revision | `NOT_READY` |
| Participant status | `NOT_READY` |
| Participant hash supplied | `NOT_READY` |
| Computed proposal hash | `dde09e446a4a91348baeed2928d909fdefd696d6e1041f793da56c6b63c814ad` |

No model, provider, prompt, or system instruction is substituted.

## 3. AEGIS status

`AEGIS` requires reviewed metadata for the code revision, fixture version, exact M001–M006 mutation set, seed set, benchmark configuration hash, participant adapter, artifact schema, deterministic TEST_DOUBLE execution, timeout/retry policy, provenance, Mission 010 metric compatibility, and unchanged safety policy.

The current source has an existing AEGIS code revision and a working TEST_DOUBLE adapter, but its benchmark participant configuration hash and reviewed artifact schema are not frozen. The validator therefore returns `NOT_READY`. The computed proposal hash is evidence for the incomplete proposal only.

| AEGIS field | Mission 013 state |
| --- | --- |
| Code revision | Existing Mission 012 revision `3dea1cb103a331568f4853a56316ce22d13bd2c2` |
| Fixture version | Required `1`, not promoted |
| Mutation set | M001–M006, unchanged in proposal schema |
| Seeds | `12345`, unchanged in proposal schema |
| Benchmark configuration hash | `NOT_READY` |
| Participant adapter | Existing `aegis.benchmark_runner.AegisAdapter` |
| Artifact schema | `NOT_READY` |
| Deterministic TEST_DOUBLE | Required, not promoted |
| Mission 010 compatibility | `mission-010-metrics-v1` in the proposal schema |
| Safety policy | Required unchanged; no benchmark flag bypasses it |
| Participant status | `NOT_READY` |
| Participant hash supplied | `NOT_READY` |
| Computed proposal hash | `f20d56918c93b94e1518add7a3502448fce49ab8008957a494477e882517df15` |

## 4. Participant hashes and configuration hash

The current active Mission 011 configuration hash is:

```text
fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3
```

No participant hash is approved. The participant proposal evaluator computes the following hashes from explicit proposal metadata:

| Participant | Supplied participant hash | Computed proposal hash | Approved? | Status |
| --- | --- | --- | --- | --- |
| `BASELINE_A` | `NOT_READY` | `8ace4f78cfcd7c7b87d02871c3447cd55444b2eae1304e4dbaa344f5c4bdadd1` | No | `NOT_READY` |
| `BASELINE_B` | `NOT_READY` | `dde09e446a4a91348baeed2928d909fdefd696d6e1041f793da56c6b63c814ad` | No | `NOT_READY` |
| `AEGIS` | `NOT_READY` | `f20d56918c93b94e1518add7a3502448fce49ab8008957a494477e882517df15` | No | `NOT_READY` |

A participant metadata change with the existing Mission 011 hash is invalid. An approved `apply_promotions` operation would return a new immutable `BenchmarkConfig` and regenerate the canonical configuration hash. Mission 013 does not generate that new hash because there is no owner-approved promotion to apply.

## 5. Readiness transition evidence

The transition model is append-only:

```text
NOT_READY → READY
```

Every `ReadinessPromotion` record requires participant ID, prior status, new status, implementation revision, participant hash, rationale, reviewer/owner, timestamp, and correlation ID. `promote_participant` rejects a non-approved review, incomplete metadata, a participant hash mismatch, or a transition whose prior state is already `READY`.

The actual Mission 013 result is:

| Evidence field | Value |
| --- | --- |
| Owner review status | `NOT_PROVIDED` |
| Promotion status | `NOT_PERFORMED` |
| Readiness transitions | Empty tuple |
| New configuration hash | `NOT_GENERATED` |
| Prior history mutation | None |

This is deliberate. The system does not convert a proposal into an approval merely because its shape exists.

## 6. Common fairness validation

The fairness check uses the existing `BenchmarkRunner.build_input` path for `BASELINE_A`, `BASELINE_B`, and `AEGIS` with M005 and seed `12345`. The participant-independent metadata is equal for all three inputs.

| Fairness field | Result |
| --- | --- |
| Mutation ID | M005 for all participants |
| Seed | 12345 for all participants |
| Fixture version | Mission 011 frozen fixture version 1 |
| Ground-truth reference | Same evaluator reference shape for all participants |
| Trial metadata | Same for all participants |
| Timeout policy | Same for all participants |
| Retry policy | Same for all participants |
| Runtime ground-truth payload | `NOT_PROVIDED` |
| Fairness status | `PASS` |

Participant-specific behavior remains limited to the explicit baseline methodology. Baseline A does not receive AEGIS safety controls. Baseline B does not receive AEGIS verification, RiskGovernor, CommitGate, or historical safety checks. AEGIS retains its existing safety architecture.

## 7. Final dry-run state

The Mission 013 artifact generator evaluates the explicit proposals, runs the existing validation-only runner twice, compares the substantive outputs and plans, and writes no benchmark result. The final state remains `BLOCKED_NOT_READY` because all three participants lack reviewed READY metadata.

| Dry-run field | Observed value |
| --- | ---: |
| Status | `BLOCKED_NOT_READY` |
| Configuration validation | `VALID` for the active Mission 011 config |
| Participant statuses | A=`NOT_READY`, B=`NOT_READY`, AEGIS=`NOT_READY_FOR_BENCHMARK` |
| Expected planned runs | 18 |
| Benchmark runs executed | 0 |
| Provider operations executed | 0 |
| Healing operations executed | 0 |
| Metric results generated | 0 |
| Execution authorized | `false` |
| Promotion performed | `false` |
| New configuration hash generated | `false` |
| Fairness check | `PASS` |
| Old-hash invalidation check | `true` |

The validation-only runner also supports `READY_TO_EXECUTE` for a future configuration in which all three participants are genuinely ready. That status remains planning-only and does not authorize execution. Mission 013’s actual result is not `READY_TO_EXECUTE`.

The committed artifacts are:

| Artifact | SHA-256 |
| --- | --- |
| [`mission_013_participant_freeze.json`](../benchmarks/configs/mission_013_participant_freeze.json) | `d9678e37494ef7368fa34c2d9c6aaf8679df94ce9c1504d0bdb64159e27792fa` |
| [`mission_013_readiness_dry_run.json`](../benchmarks/configs/mission_013_readiness_dry_run.json) | `3600c08a9dbc70e695e21b403df91ded4b51f83fd90a685b3f3fd5843d0a795f` |

## 8. Tests and results

The focused Mission 013 suite passed:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission013.py
```

```text
17 passed in 0.17s
```

The full repository suite passed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

```text
187 passed in 0.68s
```

The tests cover incomplete metadata for all participants, missing Baseline B model/prompt/configuration/first-candidate fields, complete frozen participant readiness, explicit owner approval, immutable promotion evidence, participant-hash determinism, old benchmark-hash invalidation after metadata change, code/mutation/seed drift, all-ready dry-run planning, fairness equality, zero execution, no provider/healing/approval/commit operations, no metric duplication, and no result artifact claim.

## 9. Remaining blockers

The benchmark remains blocked because no owner-approved participant metadata was provided. Baseline A needs its actual implementation/configuration and artifact schema frozen. Baseline B needs the project owner’s exact model/provider, system prompt, repair prompt, sampling settings, max output, tools, timeout/retry policy, first-candidate policy, implementation revision, and participant hash. AEGIS needs its benchmark-specific participant hash and reviewed artifact schema/metadata, even though its TEST_DOUBLE adapter and Mission 010 compatibility are already structurally available.

The active Mission 011 hash must not be reused after participant metadata changes. No participant can be marked READY by editing only its status field. No benchmark result exists, and the one-seed validation plan cannot support statistical claims.

## 10. Exact next action

The exact next action is to obtain explicit project-owner review decisions for Baseline A, Baseline B, and AEGIS and record them as `OwnerReviewDecision` inputs. The owner must supply or approve the required metadata rather than asking AEGIS to infer it. After review:

1. construct one complete `ParticipantFreezeProposal` per participant;
2. validate each proposal and participant hash;
3. create append-only `ReadinessPromotion` records only for approved `NOT_READY → READY` transitions;
4. apply promotions to return a new immutable `BenchmarkConfig` and regenerate its configuration hash;
5. run the validation-only command again; and
6. stop at `BLOCKED_NOT_READY` if any participant is incomplete, otherwise report `READY_TO_EXECUTE` without launching a benchmark.

Mission 013 must not choose a model or prompt automatically, substitute AEGIS for a missing baseline, alter M001–M006, alter severity mapping, alter the seed policy or Mission 010 formula, invoke Bright Data, run the 10-trial floor, run 540 trials, or begin benchmark execution automatically.

## Evidence files

| File | Purpose |
| --- | --- |
| [`benchmarks/configs/mission_013_participant_freeze.json`](../benchmarks/configs/mission_013_participant_freeze.json) | Explicit proposals, validation states, fairness check, hash invalidation, and zero-execution evidence |
| [`benchmarks/configs/mission_013_readiness_dry_run.json`](../benchmarks/configs/mission_013_readiness_dry_run.json) | Blocked validation-only runner output |
| [`src/aegis/participant_freeze.py`](../src/aegis/participant_freeze.py) | Proposal, participant hash, owner review, validation, promotion, and config application workflow |
| [`src/aegis/benchmark_runner.py`](../src/aegis/benchmark_runner.py) | Reviewed-metadata readiness and `READY_TO_EXECUTE` planning boundary |
| [`tests/unit/test_mission013.py`](../tests/unit/test_mission013.py) | Mission 013 focused tests |
| [`tools/docs/generate_mission_013_artifacts.py`](../tools/docs/generate_mission_013_artifacts.py) | Deterministic artifact generator |
| [`docs/06_BENCHMARK_METHODOLOGY.md`](../docs/06_BENCHMARK_METHODOLOGY.md) | Canonical methodology appendix |
| [`docs/07_METRICS.md`](../docs/07_METRICS.md) | Canonical metric-integrity appendix |
| [`docs/11_API_CONTRACTS.md`](../docs/11_API_CONTRACTS.md) | Internal API appendix |
| [`docs/12_DATA_MODEL.md`](../docs/12_DATA_MODEL.md) | Data-model appendix |
| [`docs/13_DECISION_LOG.md`](../docs/13_DECISION_LOG.md) | Append-only decision record |
| [`docs/16_TESTING_STRATEGY.md`](../docs/16_TESTING_STRATEGY.md) | Testing appendix |

**Conclusion:** Mission 013 makes participant readiness promotion explicit, human-reviewed, hash-bound, and fail-closed. Because no owner-approved metadata was supplied, it correctly leaves all participants `NOT_READY`, preserves the Mission 011 hash, reports `BLOCKED_NOT_READY`, and produces no benchmark result.
