# AEGIS Mission 012 — Baseline Definition + Benchmark Runner Contract

**Date:** 2026-08-17
**Status:** **COMPLETE for common participant contract and validation-only runner**
**Scope:** Define and validate the common `BASELINE_A` / `BASELINE_B` / `AEGIS` participant interface, readiness checks, normalized raw-run evidence, freeze enforcement, deterministic artifact naming, and a zero-execution `--dry-run` path.
**Explicitly out of scope:** Full benchmark execution, 540 trials, benchmark results, provider collection/healing, approval, production commit, rollback, metric calculation, model selection, prompt selection, threshold tuning, and safety-policy changes.

> **AI proposes. Evidence decides.**

## Mission result

Mission 012 turns the Mission 011 frozen experiment definition into a common participant contract. The runner can construct identical evaluator inputs for all three participants, validate readiness, create immutable planned-run manifests, normalize a controlled AEGIS `MutationRun` into common raw evidence, and reject freeze drift before a run can enter `RUNNING`.

The validation-only command returns `BLOCKED_NOT_READY`, because Mission 011 correctly records all three participant slots as not benchmark-ready. This is the intended fail-closed result. It is not a benchmark failure and it is not a benchmark result.

## 1. Baseline A readiness

`BASELINE_A` is represented by `BaselineAAdapter`. Its purpose is static selector extraction without healing or AEGIS trust controls. The readiness contract verifies that the adapter can consume the exact M001–M006 mutation set, normalize output into the common raw-evidence schema, carry timeout/retry policy, produce deterministic artifact references, and preserve `TEST_DOUBLE` provenance. It explicitly marks AEGIS detection, AEGIS verification, RiskGovernor, and CommitGate as `NOT_USED`.

The focused readiness test confirms `contract_ready=true` and `benchmark_ready=false` for the frozen Mission 011 slot. The adapter can normalize one controlled M001 fixture record when supplied a separately frozen READY Baseline A slot; this path produces `NOT_APPLICABLE` for verification, risk, and output eligibility rather than inventing equivalent concepts. Mission 012 does not promote the slot to READY or execute a benchmark.

| Check | Result |
| --- | --- |
| M001–M006 coverage | `PASS` |
| Common normalization | `PASS` |
| Timeout/retry fields | `PASS` |
| Artifact format | `PASS` |
| AEGIS detection | `NOT_USED` |
| AEGIS verification | `NOT_USED` |
| RiskGovernor | `NOT_USED` |
| CommitGate | `NOT_USED` |
| Participant provenance | `TEST_DOUBLE` |
| Frozen slot readiness | `NOT_READY` |

## 2. Baseline B readiness

`BASELINE_B` is represented by `BaselineBAdapter`, but it is intentionally a readiness validator rather than an executable naive-model implementation. The Mission 012 brief requires explicit owner approval of the model, prompt, configuration, system instructions, sampling configuration, timeout/retry policy, and first-candidate behavior. None of those values is silently selected.

The validator rejects or preserves `NOT_READY` when model ID, prompt revision, implementation revision, configuration hash, or required policy metadata is missing. The current frozen slot therefore remains `NOT_READY`; no model call, candidate proposal, first-candidate commit, or result is generated.

| Required metadata | Current state |
| --- | --- |
| Model ID | `TBD` / missing for execution |
| Prompt revision | `TBD` / missing for execution |
| Model configuration | Validation-only configuration; no approved Baseline B model configuration |
| Implementation revision | `NOT_READY` |
| Baseline configuration hash | `NOT_READY` |
| First-candidate policy | Defined as a slot, not executed |
| AEGIS verification/RiskGovernor/CommitGate | `NOT_USED` |
| Readiness | `NOT_READY` |

No substitute model or substitute participant is used.

## 3. AEGIS readiness

`AEGIS` is represented by `AegisAdapter`. It uses the existing Mission 009 lifecycle against the controlled mutation lab and normalizes the existing immutable `MutationRun` into `ParticipantRunEvidence`. The adapter preserves detection, verification, risk, CommitGate/output-eligibility, timing, quarantine/evidence, and `TEST_DOUBLE` provenance fields.

The AEGIS contract is structurally ready for TEST_DOUBLE normalization: mutation coverage, normalization, detection, verification, risk, CommitGate, and calculator interface availability all pass their contract checks. Its benchmark slot remains `NOT_READY_FOR_BENCHMARK`, exactly as required by Mission 012. Direct controlled normalization is not promoted into benchmark execution readiness.

The M005 path retains the canonical L5 safety fields: semantic verification/risk outcomes are preserved, `output_eligible=false`, evidence references are retained, and provenance is `TEST_DOUBLE`. Mission 012 does not alter the underlying safety policy or publish the controlled-harness result as a benchmark result.

## 4. Common runner interface

Every participant implements the provider-neutral conceptual interface:

```text
readiness(config)
prepare(execution_input)
run_mutation(prepared_run)
collect_result(raw_result)
return_run_evidence(raw_result)
```

All participants receive a `ParticipantExecutionInput` containing the same benchmark ID, configuration hash, mutation ID, severity, seed, fixture version, evaluator ground-truth reference, code/environment references, timeout policy, retry policy, artifact root, and trial metadata. The participant ID is the only intentional participant-specific identity field.

Every normalized `ParticipantRunEvidence` contains:

| Field family | Common fields |
| --- | --- |
| Identity | participant ID, deterministic run ID, mutation ID, severity, seed, fixture version |
| Freeze | participant revision, configuration hash, code revision, environment reference |
| Evaluator | ground-truth reference, timeout policy, retry policy, artifact root |
| Lifecycle | observation reference, detected, verification status, risk decision, output eligibility, failure state |
| Measurement | timing map, cost, LLM-call count |
| Evidence | evidence references, artifact references, provenance, runner state |

Baseline-only participants use `NOT_APPLICABLE` for AEGIS-only concepts. They do not receive synthetic verification or safety outcomes.

## 5. Freeze rules

`FreezeSnapshot` and `validate_freeze` compare the current configuration against the frozen Mission 011 definition. The runner rejects drift in:

| Frozen element | Enforcement result |
| --- | --- |
| Configuration hash | Mismatch produces `freeze mismatch: configuration_hash` |
| Code revision | Mismatch invalidates the snapshot |
| Fixture version | Mismatch invalidates the snapshot |
| Mutation IDs | Mismatch invalidates the snapshot |
| Severity mapping | Mismatch invalidates the snapshot |
| Seed list | Mismatch invalidates the snapshot |
| Baseline configuration hashes | Mismatch invalidates the snapshot |
| Metric formula version | Mismatch invalidates the snapshot |
| Timeout policy | Mismatch invalidates the snapshot |
| Retry policy | Mismatch invalidates the snapshot |

An invalid snapshot produces fail-closed `INVALIDATED` evidence in the explicit single-run boundary and cannot become `RUNNING`. The dry-run does not execute that boundary.

## 6. Dry-run output

The canonical command is:

```bash
PYTHONPATH=src python3 scripts/benchmark_runner.py \
  --config benchmarks/configs/mission_011_validation_floor.json \
  --dry-run
```

The command loads the frozen Mission 011 configuration, validates the configuration, checks all six mutation IDs and seed reproducibility, validates participant contracts/readiness, verifies Mission 010 calculator availability as an interface check, validates the freeze snapshot, constructs the plan, and prints JSON. It does not execute `run_mutation`, provider operations, healing, approval, commit, rollback, or metric calculation.

| Dry-run field | Observed value |
| --- | ---: |
| Status | `BLOCKED_NOT_READY` |
| Human-readable notice | `VALIDATION ONLY — NO BENCHMARK EXECUTED` |
| Configuration validation | `VALID` with no errors |
| Freeze validation | `valid=true`; all ten freeze checks `PASS` |
| Participant count | 3 |
| Mutation count | 6 |
| Seed count | 1 (`12345`) |
| Expected run count | 18 |
| Fixture checks | 6/6 `PASS` |
| Seed reproducibility checks | 6/6 `PASS` |
| Mission 010 calculator available | `true`; availability only |
| Benchmark runs executed | 0 |
| Provider operations executed | 0 |
| Healing operations executed | 0 |
| Metric results generated | 0 |
| Execution authorized | `false` |
| Planned-run states | 18/18 `PLANNED` |

Participant readiness in this same dry run is `BASELINE_A=NOT_READY`, `BASELINE_B=NOT_READY`, and `AEGIS=NOT_READY_FOR_BENCHMARK`. The runner does not substitute AEGIS for either missing baseline.

The generated machine-readable artifacts are:

| Artifact | SHA-256 |
| --- | --- |
| [`mission_012_runner_dry_run.json`](../benchmarks/configs/mission_012_runner_dry_run.json) | `3600c08a9dbc70e695e21b403df91ded4b51f83fd90a685b3f3fd5843d0a795f` |
| [`mission_012_execution_plan.json`](../benchmarks/configs/mission_012_execution_plan.json) | `51514b50e2f5046e55d2e3c4eeddcf39cb0dbc77e15b18cdac5e49337748bf87` |
| [`mission_012_participant_readiness.json`](../benchmarks/configs/mission_012_participant_readiness.json) | `29f3815c8aa3f693d2bf9959a35a7e965e5224599193e7e5badd54d39d4ccb5b` |

## 7. Determinism and artifact naming

The artifact generator runs the same frozen config through `BenchmarkRunner.dry_run()` twice. The two JSON payloads and plan tuples must be equal before artifacts are written. Planned run IDs are derived from participant ID, mutation ID, seed, and configuration hash. Artifact names use the same frozen inputs and are deterministic, for example:

```text
baseline_a__m001__seed-12345__041cd0ed4eb6.json
aegis__m005__seed-12345__88a8ee5c7f69.json
```

No run output is written under `benchmarks/results`; these names are references in a planned manifest only. The runner's plan is 18 records, ordered by participant, mutation ID, and seed, with every state set to `PLANNED`.

## 8. Tests and pass count

The focused Mission 012 command passed:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission012.py
```

```text
16 passed in 0.22s
```

The full repository command passed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

```text
170 passed in 0.58s
```

The tests cover participant slots, readiness blocking, Baseline A contract and normalization, Baseline B missing metadata, AEGIS TEST_DOUBLE normalization, fairness metadata equality, freeze drift, deterministic plan/artifact naming, zero participant execution during dry-run, Mission 010 calculator sole authority, explicit provenance, and absence of production controls.

## 9. Remaining blockers

Mission 012 does not make the benchmark executable end-to-end because the frozen baseline slots are not ready. Baseline A needs a real frozen implementation revision/configuration hash and owner review. Baseline B needs explicit owner-approved model, prompt, system instructions, sampling/configuration, timeout/retry policy, first-candidate policy, implementation revision, and configuration hash. AEGIS needs a separately reviewed benchmark slot even though its TEST_DOUBLE lifecycle can already normalize Mission 009 records.

The initial seed list contains one reproducibility seed and cannot support statistical significance. No baseline has produced a raw benchmark run, and no metric result exists. Provider execution remains outside the validation path. The Mission 010 calculator is available by interface only and was not invoked.

## 10. Exact recommended Mission 013

Mission 013 should implement the **owner-reviewed participant configuration and readiness promotion workflow**, still without launching the full benchmark. It should:

1. freeze and review Baseline A’s actual static-extractor implementation revision, configuration hash, timeout/retry policy, artifact schema, and TEST_DOUBLE behavior;
2. obtain explicit project-owner decisions for Baseline B’s model ID, prompt/system-instruction revision, model configuration, timeout/retry policy, first-candidate behavior, implementation revision, and configuration hash;
3. define and review the AEGIS benchmark adapter’s participant configuration hash and benchmark-specific execution metadata without changing AEGIS safety policy;
4. add a fail-closed readiness-promotion artifact that changes a slot from `NOT_READY` only when every required field is present and frozen;
5. validate that all three promoted participants receive identical mutation/seed/fixture/evaluator metadata and that Baseline A/B cannot consume AEGIS verification or ground-truth runtime payloads; and
6. prepare, but do not execute, a minimum-floor readiness-only plan that can be reviewed before any raw benchmark run is authorized.

Mission 013 must not choose a model or prompt automatically, substitute AEGIS for a missing baseline, alter the frozen mutation set/severity/seeds/formulas, run 540 trials, publish metrics without raw artifacts, invoke Bright Data, or begin benchmark execution automatically.

## Evidence files

| File | Purpose |
| --- | --- |
| [`benchmarks/configs/mission_012_runner_dry_run.json`](../benchmarks/configs/mission_012_runner_dry_run.json) | Blocked validation-only runner output |
| [`benchmarks/configs/mission_012_execution_plan.json`](../benchmarks/configs/mission_012_execution_plan.json) | Deterministic 18-step planned manifest |
| [`benchmarks/configs/mission_012_participant_readiness.json`](../benchmarks/configs/mission_012_participant_readiness.json) | Explicit readiness for all three participants |
| [`src/aegis/benchmark_runner.py`](../src/aegis/benchmark_runner.py) | Common participant, normalization, freeze, and runner contracts |
| [`tests/unit/test_mission012.py`](../tests/unit/test_mission012.py) | Mission 012 focused tests |
| [`scripts/benchmark_runner.py`](../scripts/benchmark_runner.py) | `--dry-run` validation-only command |
| [`tools/docs/generate_mission_012_artifacts.py`](../tools/docs/generate_mission_012_artifacts.py) | Deterministic artifact generator |
| [`docs/06_BENCHMARK_METHODOLOGY.md`](../docs/06_BENCHMARK_METHODOLOGY.md) | Canonical methodology appendix |
| [`docs/07_METRICS.md`](../docs/07_METRICS.md) | Canonical metric-integrity appendix |
| [`docs/11_API_CONTRACTS.md`](../docs/11_API_CONTRACTS.md) | Internal API appendix |
| [`docs/12_DATA_MODEL.md`](../docs/12_DATA_MODEL.md) | Data-model appendix |
| [`docs/13_DECISION_LOG.md`](../docs/13_DECISION_LOG.md) | Append-only decision record |
| [`docs/16_TESTING_STRATEGY.md`](../docs/16_TESTING_STRATEGY.md) | Testing appendix |

**Conclusion:** Mission 012 establishes one fair, provider-neutral participant contract and proves the frozen validation-only runner can construct deterministic raw-run plans while refusing execution until all participants are genuinely ready. No benchmark result was produced.
