# 16 — Testing Strategy

**Testing principle:** Safety invariants are executable tests, not documentation-only promises.  
**Release gate:** No unverified commit, no blind commit, and no unexplained L5 shipment.

## Test pyramid

### Unit tests

Unit tests cover extraction-contract validation, schema/type/null checks, statistical detectors, semantic invariants, response fingerprints, mutation seed handling, metric formulas, state-transition guards, retry bounds, redaction, and commit-gate predicates. Each test names the invariant or requirement ID it covers.

### Integration tests

Integration tests exercise the Bright Data adapter boundary, including authentication handling through injected secrets, collection normalization, healing request/polling behavior, timeout/error classification, evidence capture, approval boundary, and version resolution. A provider test double may verify AEGIS behavior, but real-provider tests must be labeled and captured separately.

### System tests

System tests run the complete lifecycle from collection through observation, detection, diagnosis, healing, candidate verification, risk decision, commit or quarantine, watch, regression, rollback, and memory. Tests use a deterministic fixture and inspect durable artifacts rather than only UI state.

### Mutation tests

Every qualified mutation class is executed against each applicable baseline and AEGIS. The harness checks expected detector outcome, repair outcome, verifier outcome, shipment status, and reset determinism. L5 tests assert bad-data-shipped rate directly.

### Regression tests

Every discovered defect becomes a permanent test with a stable fixture or recorded evidence. The regression test must identify the failed invariant, not merely reproduce a UI screenshot.

### Safety tests

| Safety behavior | Required assertion |
| --- | --- |
| Unverified repair | Commit command is rejected. |
| Single-model approval | Model pass without two deterministic channels cannot commit. |
| Quarantine | Uncertain output is withheld from product/current downstream output. |
| Rollback | Regression restores known-good or remains safely quarantined. |
| Escalation | High-risk unresolved episode creates an auditable escalation. |
| Prompt injection | Page text cannot change policy or invoke privileged operations. |
| Blind commits | Metric and release gate fail on any blind commit. |

### Demo tests

Run the exact final scenario repeatedly with the same fixture version, mutation ID, seed, benchmark report, and product output. Verify timestamp ranges, captions, muted comprehension, no secret leakage, no placeholder numbers, and links to measured artifacts.

## Test data rules

Fixtures must be versioned, resettable, and independent from expected truth. Mutation manifests carry seeds and truth references. Test doubles must be visibly labeled and cannot be used for Bright Data capability claims.

## Fault injection

Inject provider timeout, malformed response, missing evidence, duplicate callback, delayed poll, invalid candidate, one-channel verification pass, rollback failure, and storage failure. The expected behavior is bounded retry, quarantine, escalation, or fail-closed—not an implicit commit.

## Coverage and evidence

Coverage percentage is not sufficient. Each P0 requirement has a test or explicit manual evidence path. The final test report lists commands, environment, revision, pass/fail counts, skipped tests with reasons, and linked artifacts. A failed safety test blocks submission until resolved or the affected claim is removed.

## Mission 003 evidence — 2026-08-17

Mission 003 added 13 unit tests and one recorded-provider integration test. The suite covers known schema/statistical/semantic/silent-corruption mappings, unknown and ambiguous evidence, affected fields, evidence and provenance propagation, contract preservation, immutable RepairRequest construction, explicit `TEST_DOUBLE` diagnosis provenance, injected structured-model output validation, healthy/no-diagnosis behavior, and the no-execution repair boundary.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `26 passed`. Tests use no Bright Data credentials and do not call Bright Data. The recorded Mission 001 output is treated as a local evidence artifact, not a live healing result.

The furthest Mission 003 state is `REPAIR_REQUESTED`. The safety test asserts `execution_started=False`, no provider operation reference, and no approval/commit operation. Candidate verification, risk, commit, rollback, and post-commit watch remain unimplemented and untested by design.

## Mission 004 evidence — 2026-08-17

Mission 004 added healing adapter tests for exact command translation, contract-preserving prompt construction, asynchronous submission, state transitions, approval-gated status, preview/diff/operation capture, malformed and partial provider responses, provider command failure, bounded timeout, explicit `TEST_DOUBLE` scenarios, immutable `UNVERIFIED` candidates, candidate state guards, and absence of approval execution.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `40 passed`. No Bright Data credentials were required, and no live heal command was executed. Mission 001’s measured live heal latency of approximately 69,956 ms remains the only live measurement; Mission 004 test-double timings are not provider claims.

The safety scan confirms no `bdata scraper approve`, `--auto-approve`, candidate verification, risk decision, commit, rollback, watch, memory, benchmark, frontend, or dashboard implementation was added. The furthest Mission 004 state is `CANDIDATE_READY / UNVERIFIED`.

## Mission 005 evidence — 2026-08-17

Mission 005 adds deterministic verification and risk tests for all four evidence-channel concepts, PASS/FAIL/UNKNOWN state handling, optional history, correlated-source non-double-counting, missing-evidence quarantine, contradictory-evidence rejection, model non-authority, immutable result records, and zero blind-commit hooks.

The mandatory L5 fixture uses expected `price=599` and candidate `price=29.99` with valid schema and numeric type. Contract checks pass, semantic and independent evidence fail, VerificationResult is `FAIL`, and RiskDecision is `REJECT`. The candidate never reaches a commit operation.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `54 passed`. No Bright Data approval was executed, no provider state was changed, and no benchmark result was generated. The recorded Mission 001 artifact remains provider evidence only.

## Mission 006 evidence — 2026-08-17

Mission 006 adds deterministic safety tests for the CommitGate, KnownGoodVersion, QuarantineRecord, append-only QuarantineLedger, OutputEligibilityBoundary, correlation validation, immutable decisions, quarantine re-entry, and metric hooks. Explicit `TEST_DOUBLE` scenarios cover `COMMIT_ELIGIBLE`, `BLOCKED_REJECT`, `BLOCKED_QUARANTINE`, `BLOCKED_UNKNOWN`, `BLOCKED_MISSING_VERIFICATION`, `BLOCKED_MISSING_KNOWN_GOOD`, `BLOCKED_UNAUTHORIZED`, `BLOCKED_MISSING_EVIDENCE`, and correlation mismatch.

The recorded Bright Data proposal integration remains `UNVERIFIED` and is blocked by the Mission 006 gate even when provider-neutral known-good and authorization references are supplied. The gate performs no provider call, approval, activation, commit, rollback, or downstream write.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `71 passed`. No benchmark results were generated. The safety suite asserts that quarantine is retained, rejection is blocked, unknown evidence is blocked, release representation does not directly create eligibility, and all immutable records reject mutation.

## Mission 007 evidence — 2026-08-17

Mission 007 adds deterministic watch tests for healthy post-commit output, schema regression, semantic regression, statistical regression, unknown evidence, registration requirements, state-transition guards, immutable WatchResult/RegressionEvent/QuarantineRecord records, unchanged Observations, existing detection reuse, quarantine integration, and absence of repair/rollback/provider operations.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `82 passed`. Tests use an explicitly labeled `TEST_DOUBLE` eligible baseline; no production commit is faked and no Bright Data state is changed. Unknown watch evidence remains `UNKNOWN` and is not automatically quarantined by the default policy.

## Mission 008 evidence — 2026-08-17

Mission 008 adds persistence tests for on-disk SQLite reopen durability, append-only duplicate-event rejection, no update/delete interface, recursive payload immutability, secret redaction before SQL persistence, aggregate/correlation/type read queries, current-status projection, correction-by-new-event semantics, and Mission 006–007 domain record appenders.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `89 passed`. No provider operation, repair, rollback, memory, benchmark, frontend, or production sink is invoked. The SQLite test demonstrates local file durability only and is not a production availability or backup claim.

## Mission 009 evidence — 2026-08-17

Mission 009 adds 31 mutation-lab tests for baseline determinism, all six mutation definitions, five severity coverage, two L5 modes, same-seed reproduction, reversibility, explicit ground truth, L1–L4 behavior, L5 schema/type preservation, existing detection consumption, verification/risk/CommitGate integration, TEST_DOUBLE provenance, non-shipment, no benchmark runner, and no provider side effects.

The full command `PYTHONPATH=src pytest -q tests/unit tests/integration` passed with `120 passed`. The V1 harness intentionally does not claim DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, BlindCommitRate, or any 540-run result.

## Mission 010 evidence — 2026-08-17

Mission 010 adds 13 unit tests covering deterministic manifest ordering, required run fields, redaction, immutable `MetricResult`, DetectionRate, AlarmPrecision, zero-alarm `NOT_APPLICABLE`, per-severity and per-mutation scopes, L5 detection/quarantine/output-eligibility/bad-data-shipped safety, mutation severity versus detector severity, traceability to evidence references, no fake recovery or verification-miss result, no fake blind-commit result, and byte-stable metric JSON.

The generator creates a six-run controlled harness manifest and metric report from immutable Mission 009 records with fixed timestamps and zero synthetic benchmark scaling. The generated output labels itself `CONTROLLED_HARNESS_RESULT`; it does not claim production behavior or the full benchmark. Recovery, verification-miss, false-repair, blind-commit, MTTR, cost, and LLM-call metrics are asserted as `NOT_APPLICABLE` because their required denominators are absent. L5 bad-data-shipped count is asserted as 0/2 within this controlled harness only.

The full repository test command remains the release validation command:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

## Mission 011 evidence — benchmark configuration freeze and dry-run validator

Mission 011 adds focused tests for immutable `BenchmarkConfig`/`BaselineSpec` records, explicit M001–M006 mutation and severity preservation, fixed seed policy, artifact-contract completeness, valid configuration acceptance, missing/duplicate mutation rejection, invalid severity rejection, missing seed rejection, incomplete baseline rejection, missing code/fixture/metric revisions, stale freeze hash, invalid timeout/retry policy, deterministic execution-plan ordering, repeated dry-run byte identity, fixture reproducibility, calculator availability, no provider/healing/benchmark execution, no execution authorization, and zero invented metric values.

The focused Mission 011 suite passed with `21 passed`. The validation configuration produces an 18-step plan from three baseline slots, six mutation classes, and one fixed seed, but every plan step is `NOT_EXECUTED`; all baseline slots remain `NOT_READY`. The dry-run was run twice and the substantive JSON and execution plan were byte-identical. The required full repository command remains:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Mission 011 publishes no benchmark metric result. Mission 010 controlled-harness evidence remains separate, and no 540-run execution or provider operation is invoked by the validator.

## Mission 012 evidence — common benchmark participant and runner contract

Mission 012 adds focused tests for the existence of all three participant slots; NOT_READY execution blocking; Baseline A static-contract readiness and one controlled normalized evidence record; Baseline B missing-model/prompt/implementation/configuration fail-closed readiness; AEGIS TEST_DOUBLE normalization; common schema fields; equal mutation/seed/fixture/ground-truth/trial metadata; configuration-hash, fixture-version, seed, and baseline-hash freeze drift; deterministic run IDs and artifact names; repeated dry-run identity; zero participant execution during dry-run; Mission 010 sole metric authority; explicit TEST_DOUBLE provenance; and absence of production approval/commit/rollback controls.

The focused Mission 012 suite passed with `16 passed`. The full repository suite passed with `170 passed`. The generated runner dry run returns `BLOCKED_NOT_READY`, constructs 18 planned manifests, preserves all six mutation IDs and seed `12345`, and reports zero benchmark runs, provider operations, healing operations, and metric results. The command boundary is:

```bash
PYTHONPATH=src python3 scripts/benchmark_runner.py \
  --config benchmarks/configs/mission_011_validation_floor.json \
  --dry-run
```

This command is validation-only. It does not authorize or execute the benchmark.

## Mission 013 evidence — participant freeze and readiness promotion

Mission 013 adds focused tests for incomplete Baseline A/B/AEGIS metadata, Baseline B missing model/prompt/configuration/first-candidate policy, fully frozen participant readiness, explicit owner approval, immutable `NOT_READY → READY` evidence, participant-hash determinism, old configuration-hash invalidation after participant metadata change, code/mutation/seed freeze drift, all-ready `READY_TO_EXECUTE` planning, fairness metadata equality, zero benchmark/provider/healing/metric execution, and no benchmark result artifact claims.

The focused Mission 013 suite passed with `17 passed`. The full repository suite passed with `187 passed`. No owner-approved values were supplied during this mission, so the generated artifact deliberately records no readiness transition and the final dry run remains `BLOCKED_NOT_READY`. `READY_TO_EXECUTE` is covered only with synthetic fully frozen test records and remains validation-only; it never executes a benchmark.

## Mission 014 evidence — owner-approved input validation

Mission 014 tests preserve the exact owner-supplied fields, detect unresolved implementation revisions and participant hashes for all three participants, require complete owner-review metadata, compare common fairness fields without rewriting participant timeouts, preserve the Mission 011 source hash, and assert zero promotions and zero execution counters.

The focused owner-input validation suite passed with `5 passed`. Because the supplied input is blocked, the new benchmark configuration and `READY_TO_EXECUTE` dry run are intentionally not produced. The full repository suite remains the required final gate before any branch completion.


## Mission 015 evidence — participant freeze, fairness, and zero-execution gate

Mission 015 adds dedicated tests for the exact Baseline A fixed-selector configuration, Baseline B `gemini-3.6-flash` stable configuration and no-network unavailable seam, deterministic participant hashes, owner-review records, immutable `NOT_READY → READY` promotions, new configuration-hash generation, Mission 011 hash invalidation, common timeout/retry/backoff parity, AEGIS readiness and normalization, fairness, and the validation-only runner boundary.

The complete release command passed with `207 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The exact CLI validation command also returned `READY_TO_EXECUTE` for the frozen Mission 015 config and produced an 18-manifest plan. This result is intentionally not execution authorization. The safety assertions remained `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. No Bright Data call, model call, healing call, approval, production commit, rollback, or metric calculation was performed.

The final participant and runner artifacts are `benchmarks/configs/mission_015_frozen_config.json`, `benchmarks/configs/mission_015_dry_run.json`, and `experiments/mission_015_freeze_records.json`. The repository remains stopped before benchmark execution and Mission 016.


## Mission 016 evidence — preflight stop before benchmark execution

Mission 016 added a fail-closed preflight boundary for the minimum 180-run floor and an isolated Baseline B execution-readiness smoke boundary. The preflight verified the frozen Mission 015 configuration hash, fixture, mutation set, seed, participant readiness, fairness, metric formula, artifact paths, and clean fixture state. It stopped on a participant revision-integrity failure: the frozen Baseline A/B revision `0e8bcc4a2c2184cae9a50b291054ec47d83fc895` does not resolve to the actual committed implementation revision `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47`.

The Baseline B smoke test was not run because the mandatory preflight failed. No benchmark trial, provider call, healing operation, approval, commit, rollback, or metric calculation occurred. Planned runs remain 180 and executed runs remain zero. The full preflight blocker, frozen config copy, execution log, and report are preserved under `benchmarks/runs/mission_016_floor_f48ec5c5792b`, `benchmarks/reports/mission_016_floor_f48ec5c5792b/summary.md`, and `experiments/AEGIS-MISSION-016-BENCHMARK-FLOOR.md`.

This is a `STOPPED_PREFLIGHT` / `FIX` result. It is not a benchmark result, not a floor-credibility claim, and not authorization to scale or continue.


## Mission 017 corrected freeze — validation-only evidence

Mission 017 added correction-only tests for exact Git revision resolution, Baseline A/B strategy separation, deterministic participant hashes, preservation of M001–M006 and the canonical L1–L5 mapping, seed `12345`, fixture `gpu-price-staging` v1, `mission-010-metrics-v1`, common 300-second timeout, zero retries, zero backoff, owner approvals, and append-only `NOT_READY → READY` promotions.

The corrected configuration validates successfully, supersedes the Mission 015 configuration hash, passes fairness, and produces a validation-only `READY_TO_EXECUTE` dry-run with 18 planned manifests. The full test suite passes with 214 tests. No Baseline B smoke test, participant execution, provider operation, healing operation, approval, commit, rollback, or metric calculation was performed. Final counters are `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`.


## Mission 018 evidence — repaired Mission 016 preflight boundary

Mission 018 adds focused tests for loading the Mission 017 corrected configuration, rejecting the superseded Mission 015 hash as the active configuration, resolving the corrected Baseline A/B/AEGIS revisions, preserving the historical Mission 016 run directory, deterministic corrected run-ID isolation, fail-closed preflight behavior, normal validation-only `READY_TO_EXECUTE` evaluation, and the absence of smoke/run/result side effects.

The focused Mission 018 suite passed with `7 passed`. The tests do not invoke `scripts/mission016_preflight_smoke.py` as a live entry point, do not call Gemini, and do not create the corrected future run directory or benchmark result files. The future smoke boundary remains available only after the corrected preflight passes.


## Mission 019 evidence — Baseline B first-candidate execution contract

Mission 019 adds focused tests for explicit candidate receipt, first-candidate selection, acceptance, normalized `COMPLETED` evidence, `output_eligible=true`, `NOT_APPLICABLE` verification/risk, one LLM call, `MODEL_ASSISTED` provenance, `NOT_PROVIDED` runtime ground truth, no AEGIS controls, no provider operation in unit tests, no arbitrary-code execution, unavailable/failed model behavior, first-candidate-only handling, and deterministic injected smoke success.

The focused Mission 019 suite passed with `9 passed`. The complete repository command passed with `227 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The corrected preflight was executed and passed. The authorized real Gemini readiness smoke returned `BASELINE_B_EXECUTION_READINESS_SMOKE` status `PASS` with `first_candidate_policy_executable=true`, explicit candidate received/selected/accepted fields, bounded safe application, exact approved model/prompts, disabled tools, no AEGIS controls, and runtime ground truth `NOT_PROVIDED`. One provider operation was used for this smoke only. The repaired entry point stops with `BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK` and does not activate the 180-run floor.

Mission 019 generated no benchmark trial, healing operation, approval, production commit, rollback, or metric result. Counters remain `benchmark_runs_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`; the smoke-only provider count is recorded separately as `1`.


## Mission 020 evidence — immutable smoke reuse and benchmark-root separation

Mission 020 adds focused tests for: accepting existing Mission 019 smoke evidence; proving preflight does not recreate or overwrite it; proving valid evidence does not call Gemini; fail-closed handling of corrupt smoke evidence; deterministic benchmark run-ID derivation; distinct smoke and benchmark roots; explicit `PREFLIGHT`, `SMOKE`, and `BENCHMARK_EXECUTION` phases; benchmark-root rejection when it overlaps the smoke root; byte-identical historical artifacts; and zero benchmark/provider/healing/metric counters.

The focused Mission 020 suite passed with `7 passed`. The Mission 018 compatibility tests passed with `7 passed` in the combined focused run, and the complete repository suite passed with `234 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The repaired command was run in read-only mode and returned `PREFLIGHT_PASS`. It validated existing smoke evidence as `VALID`, reported benchmark run ID `mission_020_floor_2a80a8cf8d989326`, and did not rerun Gemini or write any artifact. Mission 020 did not execute `BenchmarkRunner.execute_one()`, create the future benchmark root, call Bright Data, execute healing, or generate metrics.

Mission 020 counters are `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. The historical Mission 019 smoke directory and Mission 016 STOPPED_PREFLIGHT directory remained byte-identical.


## Mission 021 evidence — explicit executor boundary and zero real benchmark execution

Mission 021 adds focused tests for the explicit CLI mode contract, dry-run non-execution, required `--run`/`--output`, corrected configuration acceptance, wrong hash blocking, participant revision blocking, fairness blocking, output-root collision blocking, deterministic ten-trial IDs, exactly 180 planned manifests, exactly 180 injected execution opportunities, participant-specific semantics, reset between trials, reset-failure invalidation, immutable raw evidence, terminal-state persistence, duplicate-free artifacts, Mission 010 metric-boundary incompatibility, and Mission 019 smoke-root preservation.

The focused Mission 021 suite passed with `12 passed`. The complete suite passed with `246 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

CLI help passed and exposed `--config`, `--dry-run`, `--run`, and `--output`. The frozen-config dry-run passed with the canonical hash `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, historical 18-step validation plan, zero benchmark/provider/healing/metric counters, `execution_authorized=false`, and no future root creation.

The 180-opportunity tests use an injected fake model caller and temporary output roots only. They do not call the real CLI `--run`, Gemini, Bright Data, healing, provider approval, commit, rollback, or production systems. The executor’s current metric incompatibility is asserted as `FAILED_METRIC_BOUNDARY` with raw terminal evidence preserved and zero metric results, not converted into a benchmark success.


## Mission 022 evidence — deterministic metric-boundary compatibility

Mission 022 adds focused tests for complete evidence adaptation, missing evidence failure, evaluator-only truth joining, deterministic output, evidence/artifact reference preservation, L1–L5 severity preservation, Baseline A/B `NOT_APPLICABLE` honesty, AEGIS verification/risk/output preservation, zero-denominator `NOT_APPLICABLE` behavior, complete metric-matrix coverage, exactly one call to the existing Mission 010 calculator, and zero real provider execution.

The focused Mission 022 suite passed with `9 passed`. The complete repository suite passed with `255 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission022.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The synthetic acceptance test completes 180 injected TEST_DOUBLE opportunities, adapts 180 raw evidence records, joins 180 evaluator-owned truth records, and invokes only `aegis.mutation_metrics.calculate_metrics()` once with 60 honest AEGIS metric inputs. The compatibility report preserves all 180 records and retains Baseline A/B unavailable concepts as `NOT_APPLICABLE`. No second calculator, formula change, partial comparative report, real Gemini call, Bright Data call, healing, approval, commit, rollback, or real benchmark execution occurs.

Mission 022 real counters remain `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated_from_real_runs=0`, and `execution_authorized=false`. Synthetic compatibility JSON is test evidence only and is not a benchmark result.


## Mission 023 evidence — exact smoke-evidence path resolution

Mission 023 adds focused tests for the five canonical evidence files, explicit `SMOKE_ROOT`, explicit `BASELINE_B_SMOKE_ROOT`, separate `BENCHMARK_ROOT`, smoke status PASS, candidate acceptance, bounded application, runtime ground truth `NOT_PROVIDED`, preflight/hash validation, all historical zero-execution counters, `pass=true`/`status=VALID`, gate PASS, artifact-root absence, and backward-compatible three-argument layout construction.

The focused Mission 023 suite passed with `2 passed`. The complete repository suite passed with `257 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission023.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The validation-only gate passed with `configuration_hash`, `smoke_evidence`, `participants_ready`, `fairness`, `planned_run_count`, and `artifact_root_absent` all true. The immutable Mission 019 evidence tree was byte-identical before and after validation, and the future benchmark root was absent. No `execute()` call, trial, Gemini call, Bright Data call, healing, approval, commit, rollback, or metric operation occurred.


## Mission 024 evidence — one smoke validator for preflight and execution gate

Mission 024 adds focused tests for identical absolute paths from preflight and `BenchmarkExecutor`, all five canonical evidence files, shared semantic validation, byte-identical historical evidence, no Gemini rerun, no future benchmark root, execution-gate PASS, planned-run count, artifact-root absence, and explicit gate-level `execution_authorized=false`.

The focused Mission 024 suite passed with `2 passed`. The complete repository suite passed with `259 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission024.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The read-only preflight returned `PREFLIGHT_PASS`. Its smoke result and the executor’s `smoke_evidence_detail` came from the same canonical validator and both returned `pass=true`, `status=VALID`, and empty errors. The immutable Mission 019 evidence tree remained byte-identical before and after validation. The future benchmark root remained absent. No `benchmark_runner.py --run`, executor `execute()`, trial, Gemini call, Bright Data call, healing, approval, commit, rollback, or metric operation occurred.


## Mission 025 evidence — safe interrupted-run resume

Mission 025 adds focused tests for fresh-root startup, interrupted-root detection, exact terminal-state consumption, completed/failed/timed-out/invalidated classification, malformed-artifact blocking, wrong hash/revision/run-ID blocking, duplicate prevention, deterministic missing order, exact `60/36/0` participant fixture shape, total `96` persisted terminal attempts, total `84` missing manifests, no failed-run retry, no completed-run retry, per-trial interruption recovery, reconstructed execution logs, metric deferral until all 180 terminal, one Mission 022/010 metric boundary call after completion, raw-byte preservation, smoke preservation, frozen-configuration preservation, and zero real provider execution.

The focused Mission 025 suite passed with `10 passed`. The complete repository suite passed with `269 passed`:

```bash
PYTHONPATH=src pytest -q tests/unit/test_mission025.py
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The tests use only temporary TEST_DOUBLE roots and injected callers. They do not invoke the real CLI `--run`, Gemini, Bright Data, healing, approval, commit, rollback, or production metrics. The actual frozen benchmark root was absent from the inspected consolidated repository, so no real artifact was modified and no real interrupted-run counts are claimed.

## Mission 026 — NVIDIA NIM testing

Mission 026 adds 18 focused provider-free tests for catalog selection, model descriptors, allowed credential names, prompt hashing, OpenAI-compatible response normalization, secret redaction, HTTP/429/5xx/transport failures, no implicit retries, configurable limiting, tools-disabled enforcement, first-candidate semantics, normalized evidence, deterministic participant/configuration hashes, old Gemini preservation, and owner-review `NOT_READY` behavior.

The complete suite passed with `287 passed`. The candidate CLI exposes `--run` and `--output`; its provider-free dry-run returns `BLOCKED_NOT_READY` with zero benchmark/provider/healing/metric counters. Exactly one real NVIDIA smoke operation was then performed with the visible NVIDIA API key. It returned HTTP 200, `MODEL_REACHABLE=true`, `CANDIDATE_POLICY_EXECUTABLE=true`, one candidate received/selected/accepted, and `execution_authorized=false`. No real benchmark run, Gemini call, Bright Data call, healing, approval, commit, rollback, or metric generation occurred.

The model-generated candidate remains untrusted data. The bounded application records `generated_code_executed=false`, and no AEGIS verification, RiskGovernor, or CommitGate is invoked by the naive baseline. The historical Gemini smoke artifact was not modified, and the new candidate benchmark root was not created.

## Mission 027 — NVIDIA owner-review testing

Mission 027 adds 14 focused provider-free tests using local deterministic objects. The tests cover complete and incomplete owner review, deterministic participant promotion, append-only readiness, inclusion of the benchmark-side rate policy in the participant hash, explicit unknown provider limits, fairness, new configuration hashing, preservation of the historical Gemini configuration and Mission 019 evidence, validation-only execution freedom, no NVIDIA/Gemini/Bright Data operations, no benchmark root, and zero counters.

The focused Mission 027 tests passed with `14 passed`. The complete suite passed with `301 passed`. The validation-only CLI returned `READY_TO_EXECUTE` with `execution_authorized=false`, `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, and `metric_results_generated=0`. The future 180-run executor was not invoked.

## Mission 028 — NVIDIA benchmark execution testing

Mission 028 adds 20 focused provider-free `TEST_DOUBLE` tests for deterministic run identity, new artifact-root isolation, NVIDIA readiness and participant hash, the 6 RPM/10-second/concurrency-1 policy, the 180-opportunity plan, participant and trial ordering, no Gemini invocation, provider-failure preservation, zero retries, duplicate prevention, interruption/resume safety, raw artifact persistence, fixture reset, all-terminal metric gating, Mission 022 adaptation, Mission 010-only metric invocation, historical Gemini preservation, and provider-free preflight.

The focused suite passed with `20 passed`. The full repository suite passed with `321 passed` before real execution. The pre-execution gate passed all required checks and returned `PREFLIGHT_PASS` with zero execution counters and an absent run root.

Post-execution validation found 180 unique terminal raw artifacts: 179 completed and 1 failed. The failed artifact records an NVIDIA HTTP 502 provider failure and no retry. Participant counts are 60 each for Baseline A, NVIDIA Baseline B, and AEGIS TEST_DOUBLE; NVIDIA provider operations are 60; healing operations are zero. Mission 022 compatibility passed, Mission 010 produced 38 results, and no alternative metric calculator was invoked. Gemini and Bright Data were not used during the benchmark, and the historical Gemini configuration/evidence remained untouched.

## Mission 028 recovery preservation testing

The preservation correction adds explicit `runs_root` injection. Production recovery uses the canonical benchmark root, while TEST_DOUBLE tests use temporary roots. The focused suite now contains 22 tests and passed with `22 passed`; it verifies the recovery identity `mission_028_recovery_floor_4812160675146552`, rejects reuse of `mission_028_floor_00c77f2abd976a10`, and confirms test cleanup does not touch either production root.

The full suite passed with `323 passed` before recovery. After recovery, it passed again with `323 passed` while the preserved recovery root remained intact: raw count stayed at `180`, total recovery-root file count stayed at `185`, and the aggregate raw-artifact hash stayed unchanged. The hash validator reports 180 unique terminal run IDs, zero missing manifests, terminal execution log `COMPLETED`, Mission 022 compatibility `PASS`, and 38 Mission 010 results.

The invalidated first-attempt summary is marked `INVALIDATED_NOT_REPRODUCIBLE` and is not used as test or benchmark evidence. Recovery artifacts are separate, hashed, and preserved. Gemini, Bright Data, healing, and alternative metric calculators were not used.

## Mission 029 — Live-demo orchestration testing

Mission 029 adds 23 focused provider-free tests for public target/schema validation, credential redaction, fresh collector ID handling, documented CLI normalization, stdout/stderr realtime-to-batch fallback capture, Observation conversion, reversible `DEMO_MUTATION`, deterministic detection, ambiguous diagnosis preservation, bounded RepairRequest construction, candidate normalization, `UNVERIFIED` status, verification/risk/CommitGate behavior, no auto-approval, no production commit, evidence-chain identifiers, replay-safe fallback, and TEST_DOUBLE healing fallback.

The focused suite passed with `23 passed` before the live provider operation. The live path used exactly one create, one run, and one heal. The fresh collector/run succeeded; the heal returned a provider prompt-length failure before candidate creation. The provider-free reconciliation and finalizer made no provider call and recorded `FAILED_BEFORE_CANDIDATE`, zero retry, zero approval, zero commit, and zero shipment. The full repository suite passed with `346 passed`; replay-safety validation confirmed the provider-operation count remained exactly `3`.

## Mission 030 — Compact-prompt and evidence-loader testing

Mission 030 adds 17 focused provider-free tests covering exact compact-prompt determinism, SHA-256, bounded length, required target/objective/schema/invariant/unaffected-field preservation, raw-evidence exclusion, credential-shape redaction, command projection, over-limit blocking before a runner call, zero-operation preflight, read-only Mission 029 artifact normalization, actual lifecycle-state preservation, identifier/latency/error/provenance mapping, missing/malformed/sensitive-artifact failure, and terminal replay suppression of a second Bright Data operation.

The focused suite passed with `17 passed`. The full repository suite passed with `363 passed`. The single live operation envelope stayed byte-identical through the full suite, and the provider-operation directory contained exactly one `operation_001.json` file. UI type-check and production build passed after the static Evidence Ledger moved to the committed-artifact loader. The unused public debug collector was removed only after confirming it was not loaded by the static entry point.

## Mission 031 — Snapshot, replay-runner, and Judge Mode validation

Mission 031 adds seven focused provider-free tests. The snapshot tests assert the compact Mission 030 prompt metadata, terminal no-candidate boundary, source-artifact redaction, deterministic snapshot equality, fail-closed sensitive-input rejection, benchmark identity/scope, and the deterministic silent-corruption replay outcome: a `TEST_DOUBLE` candidate with price `29.99` versus expected `599` is verification `FAIL`, risk `REJECT`, output-ineligible, and never shipped. The runner tests assert default `REPLAY_READY` counters are zero and `--live` returns `BLOCKED_PROVIDER_AUTHORIZATION_REQUIRED` without an external call.

The full repository suite passed with `370 passed`. Final repository safety validation passed `git diff --check`, confirmed exactly one Mission 030 provider operation envelope, confirmed Mission 029/030 and frozen Mission 028 benchmark paths were unchanged, and scanned changed text/code artifacts for credential-like strings. Judge Mode type-check and production build passed before and after the single visual-review refinement. Desktop and mobile visual passes verified source labels, terminal live status, the controlled replay disclaimer, evidence drawers, and the absence of approval/commit controls.
