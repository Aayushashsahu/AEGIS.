# AEGIS Mission 014 — Owner-Approved Participant Validation

**Date:** 2026-08-17
**Status:** **BLOCKED_NOT_READY — exact owner input validation only**
**Scope:** Validate the supplied owner participant configuration exactly, identify unresolved or inconsistent fields, and stop before participant promotion, new configuration generation, benchmark-runner dry run, provider operation, healing, or metric generation.
**Explicitly out of scope:** Inferring revisions, inventing hashes, creating fake review identities/timestamps, changing timeout policies, changing mutation definitions/seeds/formulas/safety policy, participant execution, Bright Data, healing, approval, commit, rollback, and metrics.

> **AI proposes. Evidence decides.**

## 1. Result

The owner attachment was loaded as an exact input artifact. The validator did not infer alternatives or change any participant value. It confirmed many hard-rule and frozen-input fields, but it correctly stopped at `BLOCKED_NOT_READY` because the supplied configuration still contains unresolved implementation-revision and participant-hash placeholders, incomplete owner-review evidence, and a cross-participant timeout conflict.

The expected `READY_TO_EXECUTE` result was therefore **not emitted**. The user instruction explicitly requires stopping at `BLOCKED_NOT_READY` if any field is missing or inconsistent.

## 2. Exact participant validation

### Baseline A

The following owner-supplied fields pass exact validation: participant identity/purpose, TEST_DOUBLE provider and local fixture, static-selector strategy, selector/schema versions, all five CSS-selector field types, `NOT_USED` AEGIS/healing controls, retry count and backoff, normalization/artifact/provenance, M001–M006, seed `12345`, `gpu-price-staging` version `1`, zero LLM/provider cost, and `NOT_PROVIDED` runtime ground-truth payload.

The exact unresolved fields are:

| Field | Supplied value | Required action |
| --- | --- | --- |
| `implementation.revision` | `MUST_BE_GENERATED_FROM_THE_FINAL_BASELINE_A_COMMIT` | Supply/freeze the actual final Baseline A commit revision |
| `participant_hash` | `MUST_BE_COMPUTED_AFTER_FINAL_CONFIGURATION_AND_COMMIT_ARE_FROZEN` | Compute and supply the deterministic final participant hash |

Baseline A status: **`BLOCKED_NOT_READY`**.

### Baseline B

The following owner-supplied fields pass exact validation: `GOOGLE_GEMINI_API`, model `gemini-3.6-flash` revision `stable`, exact system prompt and repair prompt template versions/content, sampling values, `max_output_tokens=8192`, tools disabled, first-candidate policy, no-AEGIS-control policy, normalized output/provenance, M001–M006, seed `12345`, fixture version `1`, one LLM call per attempt, and runtime ground-truth payload `NOT_PROVIDED`.

The exact unresolved fields are:

| Field | Supplied value | Required action |
| --- | --- | --- |
| `implementation.revision` | `MUST_BE_GENERATED_FROM_THE_FINAL_BASELINE_B_COMMIT` | Supply/freeze the actual final Baseline B implementation commit revision |
| `participant_hash` | `MUST_BE_COMPUTED_AFTER_FINAL_CONFIGURATION_AND_COMMIT_ARE_FROZEN` | Compute and supply the deterministic final participant hash |

Baseline B status: **`BLOCKED_NOT_READY`**. No substitute model or prompt was selected.

### AEGIS

The following owner-supplied fields pass exact validation: `AegisAdapter`, TEST_DOUBLE collection/provenance, live Bright Data not used for the initial benchmark, M001–M006, seed `12345`, fixture version `1`, lifecycle controls, all five false safety flags, zero retries/backoff, normalized output/provenance, and Mission 010 metric formula version.

The exact unresolved fields are:

| Field | Supplied value | Required action |
| --- | --- | --- |
| `implementation.revision` | `MUST_USE_THE_FINAL_REVIEWED_AEGIS_BENCHMARK_COMMIT` | Supply/freeze the actual final reviewed AEGIS benchmark commit revision |
| `participant_hash` | `MUST_BE_COMPUTED_AFTER_FINAL_CONFIGURATION_AND_AEGIS_COMMIT_ARE_FROZEN` | Compute and supply the deterministic final participant hash |

AEGIS status: **`BLOCKED_NOT_READY`**.

## 3. OwnerReviewDecision validation

The input contains `approved=true` and `reviewer=PROJECT_OWNER`, which are preserved exactly. It does not contain the remaining required review evidence:

| Required field | Supplied value | Result |
| --- | --- | --- |
| Approval timestamp | `NOT_SUPPLIED` | Missing |
| Rationale | `NOT_SUPPLIED` | Missing |
| Correlation ID | `NOT_SUPPLIED` | Missing |
| Approved final configuration hash | `MUST_BE_COMPUTED_AFTER_FINAL_CONFIGURATION_AND_COMMIT_ARE_FROZEN` | Unresolved placeholder |

No `OwnerReviewDecision` records were constructed because creating complete records would require inventing these values. No fake reviewer identity or timestamp was created.

## 4. Fairness validation

The common frozen inputs pass: M001–M006, seed `12345`, fixture `gpu-price-staging` version `1`, retry count `0`, backoff `0`, and runtime ground-truth payload `NOT_PROVIDED` for all participants.

Fairness fails for the timeout policy because the owner-supplied participant values differ:

| Participant | `execution.timeout_seconds` |
| --- | ---: |
| `BASELINE_A` | 30 |
| `BASELINE_B` | 60 |
| `AEGIS` | 300 |

The validator does not choose 30, 60, or 300 seconds. The owner must supply a common fairness-approved timeout policy or explicitly amend the benchmark methodology through the project’s decision process. The exact conflict recorded is:

```text
timeout_policy differs across participants: {'BASELINE_A': 30, 'BASELINE_B': 60, 'AEGIS': 300}
```

Fairness status: **`BLOCKED_NOT_READY`**.

## 5. Promotion and configuration result

Because participant and owner-review validation failed, the promotion gate was not entered.

| Result | Value |
| --- | --- |
| `OwnerReviewDecision` records | 0 |
| `ReadinessPromotion` records | 0 |
| `NOT_READY → READY` transitions | 0 |
| New immutable `BenchmarkConfig` | `NOT_GENERATED` |
| New canonical configuration hash | `NOT_GENERATED` |
| Previous Mission 011 hash | `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3` |
| Previous hash reused after metadata change | No |

The old Mission 011 hash was preserved as the source hash only. It was not reused as a post-promotion hash.

## 6. Validation-only execution boundary

The new configuration required by the owner command does not exist because promotion was blocked. Therefore the requested command with `<NEW_FROZEN_BENCHMARK_CONFIG>` was not run. The artifact records `dry_run_status=NOT_RUN_DUE_TO_BLOCKED_VALIDATION`, which is the required stop condition.

No benchmark or provider operation was attempted:

| Counter | Value |
| --- | ---: |
| `benchmark_runs_executed` | 0 |
| `provider_operations_executed` | 0 |
| `healing_operations_executed` | 0 |
| `metric_results_generated` | 0 |
| `execution_authorized` | `false` |

No Bright Data command, healing operation, approval, production commit, rollback, or metric calculator was called.

## 7. Artifacts and reproducibility

| Artifact | SHA-256 |
| --- | --- |
| [`mission_014_owner_approved_participants.json`](../benchmarks/configs/mission_014_owner_approved_participants.json) | `47a994c3e4349b918f7bf2739086fec9a22e9c790214959f6aab3159f742e156` |
| [`mission_014_owner_validation.json`](../benchmarks/configs/mission_014_owner_validation.json) | `2f3581541f2933439c369e5b984ebd4d307beb8c6c9621ae099fbb9eb7b91ef7` |

The validation artifact preserves the source Mission 011 hash, per-participant checks and errors, owner-review errors, fairness checks/conflicts, zero counters, and the explicit stop reason.

## 8. Tests

The focused owner-configuration validation suite passed:

```bash
PYTHONPATH=src pytest -q tests/unit/test_owner_approved_validation.py
```

```text
5 passed
```

The final full repository suite passed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

```text
192 passed in 0.63s
```

The final executable-operation safety scan passed. No benchmark result is claimed.

## 9. Exact required owner follow-up

To continue toward the requested `READY_TO_EXECUTE` dry run, the owner must provide, without placeholders:

1. the final Baseline A implementation commit revision;
2. the final Baseline B implementation commit revision;
3. the final reviewed AEGIS benchmark commit revision;
4. a deterministic participant hash for each final participant configuration;
5. one approval timestamp;
6. one rationale;
7. one correlation ID; and
8. a common timeout policy that satisfies the fairness contract, or an explicit documented methodology decision changing the common-timeout requirement.

After those exact values are available, the next bounded operation is to validate them, create complete `OwnerReviewDecision` records, create append-only promotions, generate a new `BenchmarkConfig` and hash, and run only:

```bash
PYTHONPATH=src python3 scripts/benchmark_runner.py \
  --config <NEW_FROZEN_BENCHMARK_CONFIG> \
  --dry-run
```

The process must stop before benchmark execution even if that dry run reports `READY_TO_EXECUTE`.

**Conclusion:** The supplied owner input is not complete enough to promote. AEGIS correctly refuses to infer revisions, hashes, review evidence, or timeout policy and reports `BLOCKED_NOT_READY` with zero execution.
