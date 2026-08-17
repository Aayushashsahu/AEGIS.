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
