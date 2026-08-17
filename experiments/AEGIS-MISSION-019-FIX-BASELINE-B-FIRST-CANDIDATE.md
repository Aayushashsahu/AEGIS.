# AEGIS Mission 019 — Fix Baseline B First-Candidate Execution Contract

**Date:** 2026-08-18
**Branch:** `mission-019-fix-baseline-b-first-candidate`
**Status:** **BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK**

## Executive result

Mission 019 fixed the Baseline B execution/readiness contract and ran the authorized corrected Mission 016 preflight plus one real Gemini execution-readiness smoke. The smoke passed. Mission 019 stopped before the 180-run benchmark floor, as required.

No Bright Data call, healing operation, provider approval, production commit, rollback, benchmark trial, or metric calculation was performed. The single provider operation was the explicitly authorized Gemini readiness smoke.

## Root cause

The real Gemini candidate was being returned successfully, but `BaselineBAdapter.run_mutation()` normalized every available model response as:

```text
failure_state = MODEL_CANDIDATE_RECEIVED_NOT_EXECUTED
output_eligible = NOT_APPLICABLE
```

It emitted no auditable candidate lifecycle fields. Consequently, the smoke condition requiring `failure_state=COMPLETED` and `output_eligible=true` could never pass, even when the provider returned a candidate. The prior implementation conflated **candidate text returned** with the separate question of whether Baseline B had selected and accepted its first candidate under its own naive policy.

## Code changes

Mission 019 adds a bounded `apply_first_candidate()` helper and extends normalized `ParticipantRunEvidence` with:

| Field | Meaning |
| --- | --- |
| `candidate_received` | A model candidate was present in the returned response. |
| `candidate_selected` | Candidate index 0 was selected under `FIRST_CANDIDATE`, `max_candidates=1`. |
| `candidate_accepted` | The bounded adapter execution contract succeeded and the naive baseline accepted the first candidate. |
| `candidate` | The selected raw candidate payload, stored immutably and serialized in evidence. |
| `candidate_application` | Safe application metadata, including candidate digest, fixture identity, candidate count, and explicit control-invocation flags. |

The safe application boundary is deterministic and labeled `SAFE_TEST_DOUBLE_BOUNDARY`. It records and hashes the candidate, validates the controlled fixture identity, and captures normalized fixture metadata. It sets `generated_code_executed=false`; it never executes arbitrary model-generated code.

Multiple returned candidates are handled deterministically: only candidate index 0 can be selected or accepted. A missing or unavailable model result remains failed/unavailable and is never output eligible.

## Required Baseline B semantics

On successful first-candidate execution, normalized evidence now contains:

```text
participant_id = BASELINE_B
failure_state = COMPLETED
verification_status = NOT_APPLICABLE
risk_decision = NOT_APPLICABLE
output_eligible = true
llm_calls = 1
provenance = MODEL_ASSISTED
candidate_received = true
candidate_selected = true
candidate_accepted = true
```

The evaluator runtime payload remains `NOT_PROVIDED`. The model and adapter do not receive `MutationGroundTruth` content. `output_eligible=true` means only that the naive Baseline B policy accepted its first candidate; it does not mean the candidate is correct, verified, safe for production, or committed.

The application evidence explicitly records:

```text
aegis_verification_invoked = false
risk_governor_invoked = false
commit_gate_invoked = false
quarantine_invoked = false
watch_invoked = false
rollback_invoked = false
generated_code_executed = false
```

## Frozen configuration preservation

The Mission 017 corrected configuration was not modified. The following values remain unchanged:

| Field | Frozen value |
| --- | --- |
| Configuration hash | `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b` |
| Model | `gemini-3.6-flash` |
| Model revision | `stable` |
| Max output tokens | `8192` |
| Tools | Disabled |
| Candidate policy | `FIRST_CANDIDATE` |
| Maximum candidates | `1` |
| Auto-accept first candidate | `true` |
| Timeout | 300 seconds |
| Retry | 0 |
| Backoff | 0 |
| Seed | `12345` |
| Mutations | M001–M006 |
| Fixture | `gpu-price-staging` v1 |
| Metric formula | `mission-010-metrics-v1` |

The historical Mission 015 freeze, Mission 016 STOPPED_PREFLIGHT evidence, Mission 017 corrected freeze, and Mission 018 repair evidence remain preserved.

## Preflight and real smoke evidence

The corrected preflight passed all checks, including configuration hash, configuration validation, source-revision resolution, fixture, mutation set, seed, participant readiness, fairness, metric formula, artifact paths, historical-run preservation, clean fixture state, and validation-only `READY_TO_EXECUTE` dry-run status.

The real Gemini smoke returned:

```text
name = BASELINE_B_EXECUTION_READINESS_SMOKE
status = PASS
first_candidate_policy_executable = true
candidate_received = true
candidate_selected = true
candidate_accepted = true
candidate_application_bounded = true
model_reachable = true
configured_model = gemini-3.6-flash
exact_system_prompt_loaded = true
exact_repair_prompt_loaded = true
tools_disabled = true
aegis_verification_not_invoked = true
risk_governor_not_invoked = true
commit_gate_not_invoked = true
no_evaluator_ground_truth_in_prompt = true
runtime_ground_truth_payload = NOT_PROVIDED
provider_operation_count = 1
```

The artifacts are under `benchmarks/runs/mission_016_floor_59a11e27a71f/`. The historical Mission 016 directory `benchmarks/runs/mission_016_floor_f48ec5c5792b/` was not modified.

The entry point now records `BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK` and returns without activating the floor executor. The smoke command was intentionally not followed by any benchmark command.

## Tests

The focused Mission 019 suite passed with `9 passed`:

```bash
PYTHONPATH=src:. pytest -q tests/unit/test_mission019.py tests/unit/test_baseline_b.py
```

The complete repository suite passed with `227 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Coverage includes candidate receipt, selection, acceptance, normalized evidence, first-candidate-only behavior, unavailable model behavior, safe non-execution of arbitrary candidate text, no AEGIS controls, ground-truth exclusion, deterministic injected smoke success, corrected preflight compatibility, and historical artifact preservation.

## Execution counters

| Counter | Value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `smoke_provider_operation_count` | 1 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | false |

The one smoke provider operation is recorded separately as `smoke_provider_operation_count=1`. `provider_operations_executed=0` refers to benchmark/provider execution counters and remains zero because no benchmark operation was started. The smoke operation is not a benchmark trial and is not used to calculate metrics.

## Subsequent benchmark command

The subsequent 180-run benchmark command remains intentionally deferred. When separately authorized, the corrected preflight/smoke boundary should be run first:

```bash
PYTHONPATH=src python scripts/mission016_preflight_smoke.py
```

The 180-run floor must not be started from Mission 019. Mission 019 stops after the passing smoke boundary.

> AI proposes. Evidence decides.
