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
