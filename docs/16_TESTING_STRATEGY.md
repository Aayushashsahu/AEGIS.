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
