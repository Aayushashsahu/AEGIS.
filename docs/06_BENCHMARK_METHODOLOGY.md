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

## Mission 010 measurement-infrastructure boundary — 2026-08-17

Mission 010 adds deterministic measurement infrastructure over immutable Mission 009 `MutationRun` records. The export preserves run identity, mutation and severity, seed, fixture and truth references, provenance, detector outcome, verification/risk/CommitGate fields, output eligibility, quarantine linkage, timing, timestamps, and evidence references. The export is redacted through the existing audit-store mechanism and orders records deterministically.

The Mission 010 calculator reports canonical formulas overall, by L1–L5 where meaningful, and by mutation ID. Ground truth is read only from `MutationGroundTruth`; actual failure state is never inferred from AEGIS output. Zero denominators return `NOT_APPLICABLE`, not measured zero. The generated artifacts are the machine-readable manifest/report under `experiments/` and the human-readable report at `docs/generated/mission_010_metrics.md`.

The current generated dataset contains the six Mission 009 V1 scenarios and is explicitly a **CONTROLLED_HARNESS_RESULT**. It is not the benchmark floor: no ten trials per class, baseline comparison, model freeze, 540-run execution, production claim, or hackathon headline metric is made. Benchmark scaling remains a later mission after this infrastructure is reviewed.

## Mission 011 configuration-freeze and validation-only dry run — 2026-08-17

Mission 011 freezes the initial benchmark definition without executing the benchmark. The immutable `BenchmarkConfig` records benchmark identity/version, the Mission 009 fixture ID/version, M001–M006, the unchanged L1–L5 severity mapping, fixed seed list, trial count, baseline slots, code/repository revision, environment/runtime references, model/prompt fields where applicable, retry and timeout policies, collection/evidence policies, artifact contract, Mission 010 metric formula version, creation timestamp, and a canonical configuration hash.

The committed validation configuration is `benchmarks/configs/mission_011_validation_floor.json`. Its code and repository revision is `3dea1cb103a331568f4853a56316ce22d13bd2c2`, and its configuration hash is `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3`. The configuration uses one fixed seed, `12345`, for the six existing mutation classes. This is a reproducibility seed, not a statistically significant trial sample.

The three required baseline slots are explicit: `BASELINE_A`, `BASELINE_B`, and `AEGIS`. Each has complete metadata fields, but each is `NOT_READY` because Mission 011 does not invent implementation revisions, model settings, prompts, baseline outputs, or results. A valid configuration definition is therefore distinct from benchmark execution readiness.

The validator fails closed for missing or duplicate mutation classes, invalid severity mappings, missing or duplicate seeds, incomplete or inconsistent baseline metadata, missing revisions or fixture version, invalid retry/timeout policy, missing artifact paths, conflicting code/repository fields, mismatched metric formula version, or a stale configuration hash. `freeze_config` recomputes the hash; changing a frozen field without regenerating the hash makes validation invalid.

`benchmarks/configs/mission_011_dry_run.json` and `benchmarks/configs/mission_011_execution_plan.json` are validation artifacts only. The dry run verifies the existing MutationLab fixture definitions, repeatability for each M001–M006/seed pair, baseline metadata resolvability, availability of the Mission 010 calculator, and the future artifact path without creating a future run directory. It produces an explicit 18-step plan (`3 baselines × 6 mutations × 1 seed`) with `execution=NOT_EXECUTED` for every step. The dry run was run twice and produced byte-identical substantive JSON and execution plans. `benchmark_runs_executed`, provider operations, healing operations, metric values generated, and execution authorization are all zero/false.

Mission 011 does not execute collection, healing, provider approval, metric calculation, benchmark trials, or 540 runs. It publishes no DetectionRate, AlarmPrecision, recovery, verification-miss, false-repair, refusal, or BlindCommitRate benchmark results. Mission 010 controlled-harness results remain separate. The frozen configuration is a prerequisite and review artifact, not a completed benchmark.

## Mission 012 common participants and validation-only runner — 2026-08-17

Mission 012 defines one provider-neutral participant contract for `BASELINE_A`, `BASELINE_B`, and `AEGIS`. Each planned input carries the same benchmark ID, frozen configuration hash, mutation ID, severity, seed, fixture version, evaluator ground-truth reference, code/environment references, timeout/retry policies, artifact root, and trial metadata. Participant identity is the only participant-specific input field.

Each participant can expose `prepare`, `run_mutation`, `collect_result`, and `return_run_evidence`. The common normalized raw-evidence record contains participant ID, deterministic run ID, mutation/seed/fixture identity, participant/configuration/code revisions, ground-truth reference, observation reference, detected result where applicable, verification status, risk decision, output eligibility, failure state, timings, cost, LLM-call count, evidence/artifact references, provenance, and runner state. A baseline without an AEGIS-only concept uses `NOT_APPLICABLE`; it is not given a fabricated equivalent.

`BASELINE_A` is a minimal static-extraction contract and explicitly marks AEGIS detection, verification, RiskGovernor, and CommitGate as `NOT_USED`. `BASELINE_B` is a readiness-only naive-repair slot and cannot select a model, prompt, configuration, or first-candidate policy automatically. `AEGIS` uses the existing Mission 009 TEST_DOUBLE lifecycle for normalization, but its benchmark slot remains `NOT_READY_FOR_BENCHMARK`; this does not change the Mission 009 safety policy.

The Mission 012 runner states are `PLANNED`, `READY`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, and `INVALIDATED`. Its `--dry-run` command validates the frozen Mission 011 configuration, participant contracts/readiness, mutation IDs, seed/fixture equality, Mission 010 calculator availability, and freeze snapshot. It generates an 18-step participant × mutation × seed plan but does not execute any participant. Because all three frozen slots are not benchmark-ready at Mission 012 start, the dry-run status is `BLOCKED_NOT_READY`, not a successful benchmark readiness claim. No participant is substituted for another.

Freeze enforcement compares configuration hash, code revision, fixture version, mutation IDs and severity, seeds, baseline configuration hashes, metric formula version, timeout policy, and retry policy. Any mismatch returns `INVALIDATED`/fail-closed evidence and cannot enter `RUNNING`. The runner produces raw evidence only; Mission 010 remains the sole metric calculator downstream.

## Mission 013 participant freeze and readiness promotion — 2026-08-17

Mission 013 adds an explicit human-reviewed participant-freeze boundary. It does not choose a model, prompt, provider, configuration, or policy. `ParticipantFreezeProposal` records the proposed implementation/configuration, timeout/retry policy, normalization, provenance, artifact schema, execution policy, and AEGIS-only safety policy. `OwnerReviewDecision` records approval, owner/reviewer, rationale, timestamp, and correlation ID. `promote_participant` can produce a new immutable `BaselineSpec` only from a complete proposal with explicit approval and a `NOT_READY → READY` transition; it never mutates prior history.

At Mission 013 execution, no owner-approved participant metadata was supplied. The generated proposal artifact therefore records explicit placeholders and `owner_review_status=NOT_PROVIDED`, `promotion_status=NOT_PERFORMED`, and `new_configuration_hash=NOT_GENERATED`. `BASELINE_A`, `BASELINE_B`, and `AEGIS` remain `NOT_READY`. No values are guessed and no model is substituted.

The participant validator is fail-closed. Baseline A requires its static extraction implementation/configuration, timeout/retry, output normalization, provenance, artifact schema, and explicit absence of healing, AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, and rollback. Baseline B requires an owner-approved model/provider, exact system and repair prompts, sampling/max-output/tools settings, timeout/retry policy, first-candidate policy, implementation revision, and configuration hash; the policy remains model proposes → first candidate executes → first candidate accepted, with no AEGIS verification/risk/CommitGate. AEGIS requires code/fixture/mutation/seed/configuration references, participant adapter, artifact schema, deterministic TEST_DOUBLE behavior, timeout/retry, provenance, Mission 010 formula compatibility, and unchanged safety policy.

Participant metadata is included in the canonical benchmark configuration hash when present. A change to participant metadata with the Mission 011 hash is invalid. An approved promotion must regenerate a new configuration hash; the Mission 011 source hash `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3` remains the active frozen hash because no promotion occurred.

The existing validation-only runner now has a distinct `READY_TO_EXECUTE` dry-run status, but it remains planning-only and keeps `execution_authorized=false`. Mission 013’s actual dry run remains `BLOCKED_NOT_READY` because all three participants lack reviewed READY metadata. A future all-ready dry run may report `READY_TO_EXECUTE` only after the new participant configuration has been frozen and validated; that status never launches a benchmark by itself.

## Mission 014 owner-approved participant validation — 2026-08-17

The supplied owner configuration was validated exactly as provided. The validator does not replace revision placeholders, compute missing approval metadata, infer participant hashes, or normalize participant-specific timeout values into a common policy. It stops at `BLOCKED_NOT_READY` when any required field is unresolved or when common fairness fields conflict.

The supplied values correctly preserve M001–M006, seed `12345`, fixture `gpu-price-staging` version `1`, `ground_truth_runtime_payload=NOT_PROVIDED`, the Baseline A/B no-AEGIS-control rules, and the AEGIS safety controls. However, Baseline A, Baseline B, and AEGIS each contain an unresolved implementation-revision placeholder and an unresolved participant-hash placeholder. The owner-review object also lacks an approval timestamp, rationale, correlation ID, and approved final configuration hash. The common timeout values are 30, 60, and 300 seconds respectively, so the fairness validator correctly reports a timeout conflict rather than silently selecting one value.

Because validation is blocked, no `OwnerReviewDecision` records are constructed, no `ReadinessPromotion` records are created, no new `BenchmarkConfig` is generated, and no new configuration hash is computed. The Mission 011 source hash remains evidence only and is not reused as a post-participant-freeze hash. The benchmark runner is not invoked for a new configuration; the validation artifact records `NOT_RUN_DUE_TO_BLOCKED_VALIDATION` and all execution counters remain zero.


## Mission 015 finalized participants and validation-only readiness — 2026-08-17

Mission 015 resolves the Mission 014 metadata blockers without executing comparative trials. Baseline A is the deterministic fixed-selector implementation at revision `0e8bcc4a2c2184cae9a50b291054ec47d83fc895`. Baseline B is the owner-approved naive first-candidate model boundary using `GOOGLE_GEMINI_API`, `gemini-3.6-flash`, stable revision, the exact approved system and repair prompts, `max_output_tokens=8192`, disabled tools, and `auto_accept_first_candidate=true`; an unavailable model call is represented honestly rather than substituted. The AEGIS TEST_DOUBLE adapter is finalized at revision `7de2bc65ed9eeb9f4abd24017543f3f366990738` and retains the existing detection, verification, RiskGovernor, CommitGate, quarantine, watch, and rollback lifecycle.

The participant configuration hashes are Baseline A `fc95be9ae66b859ab770d23ab46c2ce82dcad645325f833f5fac88959dc3e5d6`, Baseline B `20f90c001f061683c91acc65a2031f07651678041f88db064ad68157084bfb1b`, and AEGIS `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75`. Each was computed from the complete proposal and validated deterministically. All three received explicit owner review and append-only `NOT_READY → READY` promotion records.

The new frozen configuration is `benchmarks/configs/mission_015_frozen_config.json` with canonical hash `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96`, which differs from the Mission 011 source hash `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3`. M001–M006, the L1–L5 mapping, seed `12345`, fixture `gpu-price-staging` v1, and `mission-010-metrics-v1` remain unchanged. The common participant policy is timeout 300 seconds, zero retries, and zero backoff; the benchmark policy records 300000 ms for collection, healing, polling, verification, and total time with bounded one-attempt retry.

The validation-only runner returns `READY_TO_EXECUTE`, all three participants are `READY`, fairness is `PASS`, and the plan contains 18 manifests. `READY_TO_EXECUTE` is not execution authorization. The dry-run artifact records zero `benchmark_runs_executed`, zero `provider_operations_executed`, zero `healing_operations_executed`, zero `metric_results_generated`, and `execution_authorized=false`. No Bright Data call, model call, healing, approval, production commit, rollback, or metric result was performed, and no benchmark claim is made.


## Mission 016 preflight stop — frozen participant revision mismatch — 2026-08-17

Mission 016 did not execute the 180-run minimum floor. Mandatory preflight stopped before the Baseline B execution-readiness smoke test because the Mission 015 frozen configuration contains `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` for both Baseline A and Baseline B, while the actual committed implementation revision resolves to `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47`. AEGIS resolves to its frozen revision `7de2bc65ed9eeb9f4abd24017543f3f366990738`.

The configuration hash, fixture, mutation set, seed, participant readiness, fairness, metric formula, artifact paths, and clean fixture checks passed. The revision identity check failed, so the frozen configuration was not edited in place and no partial benchmark was attempted. The Baseline B smoke test is `NOT_RUN_DUE_TO_PREFLIGHT_STOP`; no Gemini call, Bright Data call, healing call, approval, commit, rollback, or metric calculation occurred. Planned runs remain 180; executed runs remain 0. The detailed evidence is in `benchmarks/runs/mission_016_floor_f48ec5c5792b/preflight_blocker.json` and `experiments/AEGIS-MISSION-016-BENCHMARK-FLOOR.md`.

The required next action is a new owner-reviewed freeze correction that resolves the actual participant revision, recomputes participant and configuration hashes, and supersedes the invalid Mission 015 freeze. No benchmark result or floor-credibility claim is made.


## Mission 017 corrected benchmark freeze — 2026-08-17

Mission 017 supersedes the invalidated Mission 015 freeze without editing Mission 015 artifacts in place. Mission 016 had stopped before the Baseline B smoke test because the frozen Baseline A/B revision `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` did not resolve to the actual implementation commit `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47`. Mission 017 verified that the actual revision resolves for both baselines and that the same commit contains two distinct paths: Baseline A calls only the deterministic static extractor, while Baseline B uses the pinned Gemini configuration and injected model-call seam with first-candidate behavior and no AEGIS verification, RiskGovernor, or CommitGate.

The corrected participant hashes are Baseline A `17b0f73fb909915f69e1a442959831463a08930df83dadcaedab7e543a60348f`, Baseline B `01a71de8a60c7d20e1d68744f1ffea3d5ebda0539c0a2e656d3d3e106169e113`, and AEGIS `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75`. The new immutable configuration is `benchmarks/configs/mission_017_corrected_frozen_config.json` with canonical hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, superseding Mission 015 hash `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96`.

All approved benchmark values remain unchanged: M001–M006, canonical L1–L5 mapping, seed `12345`, `gpu-price-staging` v1, `mission-010-metrics-v1`, common 300-second timeout, zero retries, zero backoff, and `ground_truth_runtime_payload=NOT_PROVIDED`. The corrected validation-only dry-run returns `READY_TO_EXECUTE` with fairness `PASS` and zero execution counters. This status remains validation readiness only; Mission 016 benchmark execution is not authorized by Mission 017.


## Mission 018 — repaired Mission 016 preflight boundary

Mission 018 repaired only the future Mission 016 preflight/smoke boundary. The active configuration source is now `benchmarks/configs/mission_017_corrected_frozen_config.json` with expected canonical hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`. The superseded Mission 015 configuration and the historical Mission 016 run remain unchanged.

The repaired preflight expects Baseline A and Baseline B revision `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47` and AEGIS revision `7de2bc65ed9eeb9f4abd24017543f3f366990738`. It uses the new deterministic future run ID `mission_016_floor_59a11e27a71f`, while preserving `benchmarks/runs/mission_016_floor_f48ec5c5792b` as immutable historical STOPPED_PREFLIGHT evidence. A pre-existing corrected run directory remains a fail-closed collision.

Mission 018 did not run the repaired preflight entry point, the Baseline B smoke test, Gemini, Bright Data, healing, approval, commit, rollback, benchmark, or metric calculation. Focused tests exercise the normal validation-only runner boundary and assert the expected corrected `READY_TO_EXECUTE` state without creating run or result artifacts.


## Mission 019 — Baseline B smoke-pass, benchmark still deferred

Mission 019 traced and repaired the Baseline B first-candidate contract. The prior adapter recorded a returned candidate as `MODEL_CANDIDATE_RECEIVED_NOT_EXECUTED` with `output_eligible=NOT_APPLICABLE`; the corrected adapter now records explicit candidate receipt, index-0 selection, bounded acceptance, raw candidate evidence, and `failure_state=COMPLETED` / `output_eligible=true` only after the safe TEST_DOUBLE application contract succeeds.

The authorized corrected preflight passed, and the real `BASELINE_B_EXECUTION_READINESS_SMOKE` returned `PASS` with `first_candidate_policy_executable=true`. The smoke used the frozen `gemini-3.6-flash` model and exact prompts, disabled tools, no runtime ground-truth content, no AEGIS verification/risk/CommitGate controls, and one provider operation. The safe application boundary never executed generated code; it recorded candidate digest and fixture identity only.

The entry point records `BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK`. No 180-run trial, additional benchmark trial, Bright Data call, healing, approval, production commit, rollback, or metric calculation occurred. The frozen Mission 017 configuration and historical Mission 015–018 artifacts remain unchanged. The smoke result is readiness evidence, not a benchmark result or correctness claim.


## Mission 020 — separate immutable preflight/smoke evidence from benchmark artifacts

Mission 020 resolves the artifact collision introduced when the successful Mission 019 preflight/smoke evidence was committed under `benchmarks/runs/mission_016_floor_59a11e27a71f/` and the future entry point still treated that directory as absent. The Mission 019 directory is now explicitly immutable validation evidence; it is not a benchmark output directory and is never recreated or overwritten.

The read-only preflight loads `benchmarks/configs/mission_017_corrected_frozen_config.json`, validates the canonical hash and participant/fixture/mutation/seed/fairness contracts, validates the existing smoke evidence, and returns `PREFLIGHT_PASS` only when that evidence is valid. It does not rerun Gemini merely because the smoke files exist. Corrupt, missing, or incomplete smoke evidence fails closed.

The future benchmark namespace is provider-neutral and separate. Mission 020 derives `mission_020_floor_2a80a8cf8d989326` from configuration hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, attempt identifier `mission-020-floor-v1`, and the frozen participant source revisions. The ID is deterministic, differs from `mission_016_floor_59a11e27a71f`, and is not created by Mission 020. Its planned layout is `frozen_config.json`, `participant_manifest.json`, `raw/`, `observations/`, `decisions/`, `metrics/`, `reports/`, and `execution_log.json`. The lifecycle contract rejects any benchmark artifact root that equals, contains, or is contained by the immutable smoke root.

The runner distinguishes `PREFLIGHT`, `SMOKE`, and `BENCHMARK_EXECUTION` phases. `READY_TO_EXECUTE` remains planning-only, and Mission 020 does not activate `execute_one`, create benchmark output, call Bright Data, execute healing, or calculate metrics.


## Mission 021 — explicit benchmark execution CLI and 180-opportunity boundary

Mission 021 replaces the Mission 012 validation-only wrapper with an explicit CLI boundary. `--dry-run` remains validation-only; execution requires both `--run` and `--output`. Without either mode the command fails closed. Importing the executor has no side effects and does not create the future run directory.

The execution identity remains the Mission 020 deterministic run `mission_020_floor_2a80a8cf8d989326`, derived from the corrected configuration hash, `mission-020-floor-v1`, and the verified participant source revisions. The immutable Mission 019 evidence directory `benchmarks/runs/mission_016_floor_59a11e27a71f/` is a forbidden root for execution. The future root is created only after all pre-execution gates pass and is never used by preflight or smoke validation.

Mission 021 expands only the explicit execution plan to the requested minimum floor of `3 participants × 6 mutations × 10 trial ordinals = 180 opportunities`. The frozen configuration remains unchanged, including seed `12345`; trial ordinal is an executor-level deterministic identity dimension rather than a modification to the frozen seed list or configuration hash. The validation-only dry-run therefore retains its historical 18-step plan, while the separately authorized execution boundary plans 180 raw participant opportunities.

Each opportunity validates clean fixture state, obtains evaluator-owned `MutationGroundTruth` without exposing its contents to a participant, applies the declared mutation, executes one participant, persists immutable raw evidence, resets the fixture, verifies reset determinism, and records one of `COMPLETED`, `FAILED`, `TIMED_OUT`, or `INVALIDATED`. A reset failure preserves the artifact and halts according to fail-closed policy. No generated participant code is executed.

The executor uses the existing Baseline A, Baseline B, and AEGIS adapters. Baseline B’s model caller is injected in tests and is constructed from the frozen Gemini Developer API boundary only when the real CLI is explicitly invoked with `--run`. The existing AEGIS TEST_DOUBLE lifecycle remains responsible for detection, verification, RiskGovernor, CommitGate, quarantine, watch, and rollback semantics.

Mission 010 remains the sole metric authority. Its current calculator consumes `MutationRun` records, whereas the common execution output is `ParticipantRunEvidence`. If an all-participant compatible adaptation is unavailable after raw execution, the executor records `FAILED_METRIC_BOUNDARY` and does not calculate partial metrics or create a second calculator. This incompatibility is an implementation finding, not a benchmark result.


## Mission 022 — bridge ParticipantRunEvidence into Mission 010 metric authority

Mission 022 resolves the Mission 021 compatibility boundary without modifying Mission 010 formulas or adding a second calculator. The new provider-neutral adapter consumes completed `ParticipantRunEvidence`, joins evaluator-owned `MutationGroundTruth` by immutable reference after participant execution, and creates an immutable metric-input projection accepted by the existing Mission 010 calculator.

The adapter preserves the original evidence object, manifest context, participant configuration hash, participant revision, benchmark/configuration identity, mutation/severity/trial/seed/fixture identity, ground-truth reference, run state, detection, candidate, verification, risk, output eligibility, quarantine, timing, cost, LLM calls, evidence references, artifact references, and provenance. Mission 021 fields that are not in the common evidence record, such as participant configuration hash and explicit trial ordinal, are joined from the immutable manifest by exact run ID. A missing or mismatched manifest context fails closed.

The compatibility report covers all 180 completed synthetic records. Baseline A and Baseline B records remain explicit in the report with `NOT_APPLICABLE` metric fields where the common contract does not define AEGIS detection, verification, risk, commit, or shipment concepts. Only the 60 AEGIS records have the boolean detection/risk/output fields required by the current Mission 010 formulas; this is an honest metric scope, not a comparative benchmark result or a fabricated baseline zero.

Ground truth is never passed into participant runtime. The executor records evaluator-owned truth after each mutation application, and the adapter verifies mutation ID, seed, and severity identity before joining it. Missing truth, missing evidence references, duplicate run IDs, non-terminal evidence, or identity mismatches return `FAILED_METRIC_BOUNDARY`.

The synthetic acceptance path calls only `aegis.mutation_metrics.calculate_metrics()` once after adaptation. It produces no second formula, no partial comparative report, and no real-run metric. Mission 022 does not invoke the real `--run` CLI, Gemini, Bright Data, healing, approval, commit, or rollback.


## Mission 023 — explicit smoke-evidence path resolution

Mission 023 fixes a path-resolution bug at the execution-gate boundary. The immutable Mission 019 run root is `benchmarks/runs/mission_016_floor_59a11e27a71f/`; the Baseline B smoke evidence is specifically under its `baseline_b_execution_readiness_smoke/` subdirectory. The future benchmark root remains `benchmarks/runs/mission_020_floor_2a80a8cf8d989326/`.

The artifact-layout contract now exposes both `SMOKE_ROOT` and `BASELINE_B_SMOKE_ROOT`. Smoke validation reads `BASELINE_B_SMOKE_ROOT/smoke.json` and `BASELINE_B_SMOKE_ROOT/execution_log.json`, while it reads `preflight.json`, the root `execution_log.json`, and `frozen_config.json` directly from `SMOKE_ROOT`. Isolation continues to compare the future benchmark root against the canonical `SMOKE_ROOT`, not against the narrower smoke subdirectory.

The validator does not search arbitrary directories, copy evidence, weaken checks, or rewrite historical files. The validation-only execution gate passes with the exact canonical evidence paths while the future benchmark root remains absent. No benchmark execution, Gemini call, Bright Data call, healing, approval, commit, rollback, or metric operation occurs.


## Mission 024 — one canonical smoke-evidence resolver and validator

Mission 024 unifies the read-only preflight and the benchmark execution gate behind `src/aegis/smoke_evidence.py`. `resolve_immutable_smoke_evidence(repository_root)` returns the canonical Mission 019 smoke root, Baseline B smoke root, five exact evidence paths, and no future benchmark paths. `validate_immutable_smoke_evidence(repository_root)` applies the shared Mission 019/020 semantic checks without modifying files or invoking any provider.

The preflight wrapper and `BenchmarkExecutor` both consume this implementation. The preflight preserves its historical exported constants for compatibility, but derives them from the shared path object. The executor retains the canonical smoke root for artifact isolation and uses the same shared validator for `smoke_evidence` gate state. This removes independent interpretations of smoke root, Baseline B smoke root, preflight, root execution log, and frozen configuration evidence.

Mission 024 validation returned `PREFLIGHT_PASS` and an execution gate with `passed=true`, `smoke_evidence=true`, `planned_run_count=true`, `artifact_root_absent=true`, and `execution_authorized=false`. The immutable Mission 019 evidence remained byte-identical and the future benchmark root remained absent. No benchmark, trial, provider, healing, approval, commit, rollback, or metric operation occurred.


## Mission 025 — resumable interrupted benchmark roots

Mission 025 adds a recovery path for an existing deterministic benchmark root without changing the benchmark identity or frozen configuration. An existing root is inspected through `src/aegis/benchmark_resume.py`; it is not recreated and its raw artifacts are not rewritten.

A persisted raw artifact is consumed only when its manifest matches the current deterministic plan, participant identity and revision, mutation, severity, trial, seed, configuration hash, artifact identity, and benchmark run ID, and when its terminal state is one of `COMPLETED`, `FAILED`, `TIMED_OUT`, or `INVALIDATED`. Malformed JSON, missing terminal state, non-terminal state, wrong identity, wrong filename, duplicate run ID, or missing root-level frozen/manifest/log files fails closed before the next trial.

The recovery gate computes missing manifests in deterministic manifest order. Existing failed, timed-out, and invalidated attempts remain consumed because the frozen retry count is zero. Every newly executed missing trial writes an exclusive raw artifact first and atomically reconstructs the execution log. Existing raw files, frozen configuration, and participant manifest are preserved byte-for-byte on the resume path.

Metrics are prohibited until every one of the 180 opportunities has a terminal state. At terminal completion, completed evidence passes through the Mission 022 compatibility boundary and only Mission 010 remains the metric authority. Mission 025 tests use isolated TEST_DOUBLE fixtures only; the real resume command remains separately deferred.

## Mission 026 — NVIDIA NIM participant capability and smoke boundary

Mission 026 adds a provider-neutral NVIDIA NIM catalog and caller while preserving the historical Gemini Baseline B configuration and smoke evidence. The official NVIDIA hosted interface is the OpenAI-compatible `POST https://integrate.api.nvidia.com/v1/chat/completions` operation. The selected candidate is `openai/gpt-oss-20b`, represented by an immutable model descriptor and a new `NOT_READY` participant proposal.

The replacement proposal freezes the exact provider, model identifier and revision, endpoint, prompt revision and SHA-256, sampling values, output limit, disabled tools, first-candidate policy, timeout, zero-retry policy, and an explicitly unknown provider rate limit. No 40 RPM value is assumed without primary evidence. A configurable limiter supports future provider/account limits without baking an unverified assumption into the benchmark.

The authorized Mission 026 smoke performed exactly one real NVIDIA operation. It returned HTTP 200, `MODEL_REACHABLE=true`, `candidate_received=true`, `candidate_selected=true`, and `candidate_accepted=true`. The bounded application recorded `generated_code_executed=false` and invoked no AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, or rollback. Runtime ground truth remained `NOT_PROVIDED`. The smoke stopped before any benchmark run, healing, approval, commit, rollback, or metrics.

The new participant remains `NOT_READY` because owner review and an immutable promotion have not occurred. The new candidate configuration has its own deterministic hash and artifact root, while the Mission 017 corrected Gemini configuration and Mission 019 evidence remain immutable historical records. Dry-run remains provider-free and returns `BLOCKED_NOT_READY` for the NVIDIA candidate until promotion.

## Mission 027 — NVIDIA owner-review freeze

Mission 027 applies the explicitly supplied owner approval to the Mission 026 NVIDIA Baseline B candidate through the existing append-only readiness workflow. The source proposal hash `4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f` is preserved. The new promoted participant hash is `9b630269de415be0f69b92e7abd62dcaf4a3a535c3e8f3df982017a50ba25c14`, and the new immutable benchmark configuration hash is `8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4`.

The owner-approved AEGIS benchmark-side rate policy is `benchmark_requests_per_minute=6`, `benchmark_min_interval_seconds=10`, and `concurrency_limit=1`. This is deliberately distinct from the NVIDIA provider RPM/free-tier limit, which remains `UNKNOWN` and is recorded as `UNKNOWN_UNTIL_ACCOUNT_RESPONSE`. The value 6 is never represented as a provider limit.

The new configuration contains `BASELINE_A`, NVIDIA `BASELINE_B`, and `AEGIS`. It preserves M001–M006, canonical L1–L5 mapping, `gpu-price-staging` v1, seed `12345`, the existing 300-second timeout, zero retries, zero backoff, runtime ground truth `NOT_PROVIDED`, and `mission-010-metrics-v1`. The schema’s deterministic seed `trial_count=1` remains unchanged; the future execution protocol records `trials_per_mutation=10` and therefore 180 planned opportunities. Fairness passes for mutations, seed, fixture, trial policy, timeout, retry, backoff, ground-truth reference structure, and evaluator isolation.

The validation-only runner returned `READY_TO_EXECUTE` with all three participants READY and configuration hash MATCH. Its planning representation contains 18 validation steps; the future execution protocol contains 180 opportunities. Counters remain `execution_authorized=false`, `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, and `metric_results_generated=0`. No benchmark root was created.

## Mission 028 — completed NVIDIA comparative benchmark

Mission 028 executed one authorized clean comparative run from the immutable Mission 027 configuration. The exact deterministic run identity is `mission_028_floor_00c77f2abd976a10`, derived from configuration hash `8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4`, attempt `mission-028-nvidia-comparative-benchmark-v1`, and sorted participant revisions. The pre-execution gate passed configuration hash and validation, readiness, participant revisions and hash, fairness, fixture cleanliness, immutable smoke evidence, metric authority, model caller availability, benchmark-side rate policy, artifact isolation/absence, deterministic identity, duplicate-free planning, and 180 planned opportunities.

The benchmark used `BASELINE_A`, NVIDIA `BASELINE_B`, and AEGIS `TEST_DOUBLE` in deterministic order for `3 × 6 × 10 = 180` opportunities. The run resumed once after an interruption. The first 65 terminal raw artifacts were preserved and the resume consumed only the remaining manifests. The final root contains 180 unique terminal artifacts: Baseline A `60 COMPLETED`, NVIDIA Baseline B `59 COMPLETED` and `1 FAILED`, and AEGIS `60 COMPLETED`. The one NVIDIA failure is preserved as an HTTP 502 provider failure with zero automatic retries; it is not a model-quality classification.

The owner-approved benchmark throttle was 6 requests per minute, a 10-second minimum interval, and concurrency 1. NVIDIA’s provider RPM/free-tier limit remains `UNKNOWN`; the benchmark-side value 6 is not a provider-limit claim. The run executed 60 NVIDIA provider operations, tracked separately from the single Mission 026 smoke operation. Gemini was not invoked, Bright Data was not invoked during the benchmark, and healing operations remained zero.

After all 180 opportunities were terminal, the Mission 022 compatibility boundary passed and invoked only the Mission 010 metric calculator. It produced 38 canonical results with `formula_version=mission-010-metrics-v1`. The eligible metric inputs are AEGIS `TEST_DOUBLE` evidence; these are controlled-harness measurements and are not real NVIDIA or Bright Data measurements. Overall DetectionRate was `1.0 (50/50)`, AlarmPrecision was `1.0 (50/50)`, L5DetectionRate was `1.0 (20/20)`, and L5BadDataShippedCount/Rate were `0/20` and `0.0`. VerifiedRecovery, VerificationMissRate, FalseRepairRate, BlindCommitRate, MTTR, CostPerRepair, and LLMCallsPerRepair remain `NOT_APPLICABLE` with zero denominators.

The final execution counters are `benchmark_runs_executed=180`, `provider_operations_executed=60`, `healing_operations_executed=0`, `metric_results_generated=38`, and `execution_authorized=true`. The historical Mission 017 Gemini configuration and Mission 019 smoke evidence remain unchanged. No claim is made that a successful NVIDIA response proves candidate correctness or that this run is directly comparable to the historical Gemini run without methodology review.

## Mission 028 recovery and first-attempt invalidation

The first Mission 028 identity `mission_028_floor_00c77f2abd976a10` is **INVALIDATED_NOT_REPRODUCIBLE**. Its surviving execution summary is incident evidence only because the benchmark root was removed by provider-free test cleanup before staging. Its summary must not be used as a benchmark result and its run ID must never be reused.

Before recovery, the executor was changed to accept an explicit immutable `runs_root`. Production execution uses the canonical repository benchmark root; provider-free tests pass temporary roots explicitly and clean only those temporary paths. The focused preservation suite passed with `22 passed`, and the full suite passed with `323 passed` before recovery.

The clean recovery identity is `mission_028_recovery_floor_4812160675146552`, derived from the frozen configuration hash `8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4`, recovery attempt `mission-028-nvidia-comparative-benchmark-recovery-v1`, and frozen participant revisions. It is distinct from the invalidated identity. Recovery preflight passed all existing gates and explicitly recorded the old ID as invalidated.

The recovery executed the same `3 × 6 × 10 = 180` protocol under the frozen 6 RPM, 10-second, concurrency-1 AEGIS throttle. It preserved 180 unique terminal raw artifacts, 179 completed and 1 failed, with 60 NVIDIA provider operations and zero healing operations. After all terminal artifacts existed, Mission 022 compatibility passed and Mission 010 generated 38 results. The recovery root was retained through the full 323-test suite with no raw-file removal and unchanged aggregate raw hashes.
