# AEGIS Mission 011 — Benchmark Configuration Freeze + Dry-Run Validator

**Date:** 2026-08-17
**Status:** **COMPLETE for configuration freeze and validation-only dry run**
**Scope:** Define an immutable benchmark configuration, validate it fail-closed, prove fixture/seed reproducibility, generate an explicit unexecuted plan, and preserve the no-results boundary.
**Explicitly out of scope:** Full benchmark execution, 540 runs, baseline result generation, provider collection/healing, approval, production commit, rollback, metric calculation, threshold tuning, and headline metric claims.

> **AI proposes. Evidence decides.**

## 1. Mission result

Mission 011 closes the experiment-definition gap left after Mission 010. It adds an immutable `BenchmarkConfig`, explicit `BaselineSpec` slots, deterministic validation, canonical configuration hashing, an artifact contract, and a validation-only dry-run path. The implementation consumes the existing Mission 009 `MutationLab` definitions and checks the availability of the existing Mission 010 calculator without executing it.

The result is a valid **configuration definition**, not a completed benchmark. The configuration records all known values and uses `NOT_READY`, `TBD`, or `NOT_APPLICABLE` where implementation or model information is not established. In particular, all three baseline slots are explicit but `NOT_READY`; no baseline output or benchmark number is invented.

## 2. BenchmarkConfig schema

`BenchmarkConfig` is a recursively immutable dataclass. Its canonical fields are:

| Field | Mission 011 value or rule |
| --- | --- |
| `benchmark_id` | `aegis-benchmark-floor` |
| `benchmark_version` | `mission-011-validation-floor-v1` |
| `fixture_id` / `fixture_version` | `gpu-price-staging` / `1`, sourced from the existing Mission 009 fixture |
| `mutation_class_ids` | Exactly `M001`–`M006`; no additions or removals |
| `mutation_severity` | `M001=L1`, `M002=L2`, `M003=L3`, `M004=L4`, `M005=L5`, `M006=L5` |
| `seeds` / `trial_count` | `(12345,)` / `1`; reproducibility input, not statistical significance |
| `baselines` | `BASELINE_A`, `BASELINE_B`, and `AEGIS`, each with complete metadata shape |
| `code_revision` / `repository_revision` | `3dea1cb103a331568f4853a56316ce22d13bd2c2` |
| `repository_state` | `DIRTY_USER_FILES_PRESERVED`; user-owned files remain untouched and unstaged |
| `environment_reference` | Local validation-only, TEST_DOUBLE fixture, no provider execution |
| `runtime_reference` | Python 3.12; standard-library application modules; pytest test environment |
| `model_identifier` / `prompt_version` | `NOT_APPLICABLE` for the validation-only path |
| `model_configuration` | `NOT_APPLICABLE_FOR_VALIDATION_ONLY` |
| `retry_policy` | Bounded, one attempt, zero backoff for validation planning |
| `timeout_policy` | Positive collection/healing/polling/verification/total limits; total covers component limits |
| `collection_policy` | `VALIDATION_ONLY`, `TEST_DOUBLE_FIXTURE_ONLY`, provider execution `NOT_EXECUTED` |
| `evidence_policy` | Ground truth from `MutationGroundTruth`, raw inputs from `MutationRun`, metrics from Mission 010 only, Mission 008 redaction, no manual result editing |
| `artifact_contract` | `benchmarks/configs`, `benchmarks/manifests`, `benchmarks/runs`, `benchmarks/results`, `benchmarks/reports` |
| `artifact_root` | `benchmarks/results/mission_011_validation_floor`; future path, not created by Mission 011 |
| `metric_formula_version` | `mission-010-metrics-v1` |
| `created_at` | `2026-08-17T00:00:00+00:00`; frozen artifact timestamp |
| `configuration_hash` | `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3` |

The committed machine-readable configuration is [`benchmarks/configs/mission_011_validation_floor.json`](../benchmarks/configs/mission_011_validation_floor.json).

## 3. Frozen fields and hash behavior

The canonical SHA-256 hash covers the configuration version, benchmark identity, fixture, mutation IDs and severity mapping, seeds and trial count, every baseline field, code and repository revisions, repository state, environment/runtime references, model and prompt fields, retry and timeout policies, collection/evidence policies, artifact contract/root, metric formula version, and creation timestamp. The stored `configuration_hash` is excluded from its own input.

`freeze_config(config)` returns a new immutable configuration with the canonical hash. `validate_config(config)` recomputes the hash and rejects a configuration when the stored hash is stale. The focused regression test changes a frozen prompt field without updating the hash and confirms fail-closed invalidation. The same mechanism applies to mutation definitions represented by their IDs/severities, seeds, baselines, model/prompt metadata, code revision, fixture version, retry policy, timeout policy, and metric formula version.

## 4. Mutation and seed plan

Mission 011 preserves the six existing Mission 009 mutation definitions and does not alter ground truth. The initial validation configuration applies the existing deterministic seed behavior, `12345`, to each class.

| Quantity | Value |
| --- | ---: |
| Mutation classes | 6 |
| Severity levels represented | L1, L2, L3, L4, L5 |
| L5 classes | M005, M006 |
| Fixed seeds | 1 (`12345`) |
| Trials per mutation in this validation plan | 1 |
| Baseline slots | 3 |
| Expected plan steps | 18 (`3 × 6 × 1`) |
| Actual benchmark runs | 0 |

The seed list is a reproducibility input only. Mission 011 does not claim statistical significance, ten trials per class, the benchmark floor as executed, or the 540-run target.

## 5. Baseline status

The three baseline slots required by the canonical methodology are explicit and are not silently substituted.

| Baseline | Definition | Status | Safety interpretation |
| --- | --- | --- | --- |
| `BASELINE_A` | Static selector extraction without healing or AEGIS verification | `NOT_READY` | Implementation revision and configuration hash remain `NOT_READY`; no output exists |
| `BASELINE_B` | Naive LLM repair with a first-candidate policy slot | `NOT_READY` | Model and prompt are `TBD`; no candidate or result exists |
| `AEGIS` | Full AEGIS lifecycle with deterministic verification, risk, gate, quarantine, and watch boundaries | `NOT_READY` | Mission code revision is recorded, but no benchmark execution configuration/result is claimed |

All baseline records carry the required metadata fields: ID, description, implementation revision, model ID, prompt revision, configuration hash, execution policy, retry policy, verification policy, and commit policy. A valid configuration definition does not mean the baselines are ready for execution.

## 6. Dry-run output

The validator performs the following checks without invoking a provider, healing adapter, benchmark runner, or metric calculation: it checks the six existing mutation definitions, applies each mutation twice for the same seed and compares deterministic fixture/truth projections, checks baseline metadata resolvability, imports the existing Mission 010 calculator as an interface-availability check, validates the future artifact path without creating it, and constructs the ordered execution plan.

The committed dry-run output is [`benchmarks/configs/mission_011_dry_run.json`](../benchmarks/configs/mission_011_dry_run.json), and the explicit unexecuted plan is [`benchmarks/configs/mission_011_execution_plan.json`](../benchmarks/configs/mission_011_execution_plan.json).

| Dry-run field | Observed value |
| --- | ---: |
| Status | `VALIDATION_ONLY` |
| Human-readable notice | `VALIDATION ONLY` / `NO BENCHMARK EXECUTED` |
| Configuration validation | `VALID` with no errors |
| Fixture checks | 6/6 `PASS` |
| Seed reproducibility checks | 6/6 `PASS` |
| Baseline metadata checks | 3/3 `NOT_READY:RESOLVABLE_METADATA` |
| Metric calculator available | `true`; availability only, not execution |
| Artifact path check | `PASS_FUTURE_ROOT_PARENT_EXISTS_NOT_CREATED` |
| Expected run count | 18 |
| Benchmark runs executed | 0 |
| Provider operations executed | 0 |
| Healing operations executed | 0 |
| Metric values generated | 0 |
| Benchmark execution authorized | `false` |
| Plan step execution | `NOT_EXECUTED` for every step |

No fake run directory, observation, detection result, verification result, risk result, commit result, rollback result, or metric result is generated.

## 7. Determinism result

The generator runs the same dry run twice with the same committed code revision, fixture version, seed list, and immutable configuration. The substantive dry-run JSON and the execution-plan tuple are compared byte-for-byte/equality-wise before the artifacts are written.

**Result: PASS.** The two dry-run outputs were identical, the two execution plans were identical, and all 18 plan steps retained the same baseline/mutation/severity/seed/configuration-hash fields. The generated artifact SHA-256 values are:

| Artifact | SHA-256 |
| --- | --- |
| `mission_011_validation_floor.json` | `202f2bcf260148f18aa72388e11324367d0e346dafac2a004381631a395748fb` |
| `mission_011_dry_run.json` | `591f99b781a3043c64980eda5489e1ea68c6de17b0baa5621452eca454e517c4` |
| `mission_011_execution_plan.json` | `0a660deae59b03ac26750eaa781b6cd478636dfd66730dcbfa9a0d29aa78cf9d` |

These hashes identify the committed validation artifacts; they do not identify benchmark results because no benchmark ran.

## 8. Validation tests

The focused Mission 011 test command passed:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission011.py
```

```text
21 passed in 0.18s
```

The tests cover valid configuration acceptance, nested immutability, missing/duplicate mutations, invalid severity, missing/duplicate seeds, incomplete baselines, ready-baseline metadata requirements, missing code/fixture/metric revisions, invalid timeout/retry policies, artifact-contract completeness, stale configuration-hash invalidation, deterministic hash and plan ordering, repeated dry-run identity, invalid-config plan blocking, no provider/healing/benchmark execution, no execution authorization, and zero invented metric values.

The full repository validation command remains a release requirement and is run before Mission 011 is pushed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

## 9. Remaining benchmark blockers

Mission 011 intentionally leaves benchmark execution blocked. `BASELINE_A`, `BASELINE_B`, and `AEGIS` are all `NOT_READY`; Baseline B has no selected model, prompt, or configuration hash; Baseline A has no frozen implementation revision; and AEGIS has no benchmark-run configuration beyond this validation-only slot. The configuration uses one seed and one validation trial per mutation, so it cannot support statistical claims. No actual collection, healing, repair, approval, commit, rollback, or metric calculation has occurred in this mission. Bright Data capability labels and provider-native rollback limitations remain unchanged.

The Mission 010 six-run controlled-harness result remains separate. Mission 011 publishes no DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, MTTR, cost, LLM-call, production, or hackathon headline result.

## 10. Exact recommended Mission 012

Mission 012 should implement the **baseline-definition and benchmark-runner contract**, still without automatically launching the full benchmark. It should:

1. define and review the real Baseline A implementation/configuration;
2. select and pin Baseline B’s model, prompt, configuration, and first-candidate policy only after an explicit project-owner decision;
3. define the executable AEGIS benchmark adapter around the frozen configuration while preserving the Mission 010 calculator as the sole metric authority;
4. add artifact-path validation for future manifests, runs, and reports;
5. add a validation-only runner boundary that rejects any baseline still `NOT_READY` and refuses to execute when the configuration hash, code revision, fixture version, seeds, or baseline hashes differ; and
6. prepare the minimum-floor execution command without running it until all three baseline slots are genuinely ready and reviewed.

Mission 012 must not silently substitute AEGIS for a missing baseline, modify frozen mutations/seeds/formulas, scale to 540 runs automatically, publish benchmark results without raw artifacts, or begin provider execution as part of configuration validation.

## Evidence files

| File | Purpose |
| --- | --- |
| [`benchmarks/configs/mission_011_validation_floor.json`](../benchmarks/configs/mission_011_validation_floor.json) | Frozen machine-readable configuration |
| [`benchmarks/configs/mission_011_dry_run.json`](../benchmarks/configs/mission_011_dry_run.json) | Validation-only result with zero execution counters |
| [`benchmarks/configs/mission_011_execution_plan.json`](../benchmarks/configs/mission_011_execution_plan.json) | Deterministic 18-step plan marked `NOT_EXECUTED` |
| [`src/aegis/benchmark_config.py`](../src/aegis/benchmark_config.py) | Immutable config, validation, hashing, and dry-run implementation |
| [`tests/unit/test_mission011.py`](../tests/unit/test_mission011.py) | Mission 011 focused tests |
| [`tools/docs/generate_mission_011_artifacts.py`](../tools/docs/generate_mission_011_artifacts.py) | Reproducible artifact generator |
| [`docs/06_BENCHMARK_METHODOLOGY.md`](../docs/06_BENCHMARK_METHODOLOGY.md) | Canonical methodology appendix |
| [`docs/07_METRICS.md`](../docs/07_METRICS.md) | Canonical metric-integrity appendix |
| [`docs/11_API_CONTRACTS.md`](../docs/11_API_CONTRACTS.md) | API contract appendix |
| [`docs/12_DATA_MODEL.md`](../docs/12_DATA_MODEL.md) | Data-model appendix |
| [`docs/13_DECISION_LOG.md`](../docs/13_DECISION_LOG.md) | Append-only decision record |
| [`docs/16_TESTING_STRATEGY.md`](../docs/16_TESTING_STRATEGY.md) | Testing appendix |

**Conclusion:** Mission 011 freezes a reproducible experiment definition and proves the dry-run plan is deterministic. It does not execute the benchmark and does not claim benchmark results.
