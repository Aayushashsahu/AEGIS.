# 06 — Benchmark Methodology

**Purpose:** Define a reproducible comparison of static extraction, naive LLM repair, and AEGIS.  
**Metric source of truth:** Controlled mutation ground truth.  
**Result status:** No actual results are claimed until a run produces artifacts.

## Ground truth

> Production data does not provide a reliable observable “correct answer” for evaluating every failure. Therefore headline reliability metrics are computed against controlled mutations where ground truth is known.

The laboratory fixture contains canonical records and a mutation manifest. The expected output is stored independently from the code path used to extract the candidate. A benchmark run must preserve fixture version, mutation ID, seed, baseline version, model configuration, code revision, and raw outputs.

## Experimental design

The benchmark environment consists of a deterministic staging fixture, an adapter for the real Bright Data path where available, and a contract-preserving local adapter for laboratory isolation. The local adapter is a test double and cannot support claims about Bright Data platform behavior.

| Parameter | Protocol |
| --- | --- |
| Environment | Pinned runtime and dependency lockfile; staging fixture version recorded. |
| Mutation set | At least six classes; all L1–L5; at least two L5 classes. |
| Trials | Minimum 10 per class; target expansion may reach 540 total runs. |
| Seeds | Fixed seed list committed before execution. |
| Baselines | A, B, and C frozen before comparative runs. |
| LLM configuration | Model, system prompt, user prompt, temperature/configuration, tool permissions, and max output pinned for B. |
| Timeouts | Per collection, healing, polling, verification, and total episode deadline recorded. |
| Retries | Bounded and identical where the baseline definition requires equivalence; AEGIS policy is recorded separately. |
| Randomness | No unseeded randomness in mutation injection or fixture generation. |
| Outputs | Raw run manifest, observations, decisions, metrics, logs, and environment metadata retained. |

## Baselines

### Baseline A — Static selector scraper

Baseline A uses the pre-mutation selectors and contains no healing, semantic verification, quarantine, or rollback. It runs once per mutation/trial and reports the output and whether the static extraction matches ground truth. It must not be improved after freeze.

### Baseline B — Naive LLM repair

Baseline B uses a pinned model and pinned prompts to propose a repair. It has no AEGIS verification or risk governor, and the first candidate is auto-committed according to the benchmark definition. The exact model identity, prompt text, configuration, and adapter behavior must be committed before benchmark execution. If the model or provider is unavailable, the run is marked unavailable rather than silently substituted.

### System C — AEGIS

System C executes the full lifecycle: detection, diagnosis, Bright Data repair boundary, candidate verification, risk decision, quarantine/retry/escalation, commit, watch, rollback, and memory recording. For the L5 safety metric, the central outcome is whether incorrect data was shipped, not merely whether a repair was found.

## Benchmark floor and target

The minimum credible benchmark includes six mutation classes, all five severity levels, two L5 modes, ten trials per class, three baselines, fixed seeds, and complete metrics. The project target is **540 runs**, but the target may be reduced to the floor if implementation risk threatens detection, verification, or the final video. Benchmark breadth never outranks the core safety proof.

## Run procedure

1. Verify repository revision, fixture version, dependency lock, and baseline manifests.
2. Reset the fixture to the clean canonical state.
3. Apply the declared mutation with the declared seed.
4. Run the selected baseline or AEGIS exactly once for the trial.
5. Capture collection, observation, findings, candidate, verification, decision, shipment, watch, and rollback artifacts.
6. Compare output and shipment status to independent ground truth.
7. Append metrics without rewriting prior raw results.
8. Restore the clean fixture and validate reset before the next trial.

## Reproducibility command contract

The eventual implementation must provide commands equivalent to:

```bash
# Freeze and inspect configurations
./scripts/benchmark_config validate

# Run the minimum floor
./scripts/benchmark run \
  --manifest benchmarks/manifest.yaml \
  --seed-file benchmarks/seeds.txt \
  --baselines benchmarks/baselines \
  --output benchmarks/runs/<RUN_ID>

# Recalculate metrics from immutable raw artifacts
./scripts/benchmark report \
  --input benchmarks/runs/<RUN_ID> \
  --output benchmarks/reports/<RUN_ID>
```

These are required command shapes, not claims that the scripts already exist.

## Invalid benchmark conditions

A run is invalid if a baseline changes after freeze, a seed is missing, a mutation is not reset, a provider substitutes an unrecorded model, a timeout/retry policy differs without being recorded, ground truth is derived from the candidate output, or raw artifacts are missing. Invalid runs may be retained for audit but cannot support headline claims.

## Mission 009 V1 harness boundary — 2026-08-17

Mission 009 implements only the controlled mutation mechanism and six-scenario validation floor. It uses a local static fixture and `TEST_DOUBLE` collection provenance; it does not claim Bright Data behavior or implement the benchmark runner, baselines, pinned model configuration, ten trials per class, or 540 runs.

The harness drives existing Observation, Detection, Verification, RiskGovernor, CommitGate, and QuarantineLedger boundaries. It records immutable `MutationGroundTruth` and `MutationRun` records with seed, fixture version, timing, references, provenance, detected flags, outcomes, and explicit absent/future-stage fields. The mutation lab—not candidate output—supplies expected truth.

The current V1 has six mutation scenarios, all five severity levels, and two L5 silent-corruption modes. It is not benchmark-complete and must not be reported as a measured benchmark.
