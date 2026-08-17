# AEGIS Mission 006 — Commit Gate + Quarantine Ledger

**Date:** 2026-08-17
**Status:** **COMPLETE for the bounded AEGIS eligibility and quarantine slice**
**Scope:** Turn the existing `RiskDecision` into an enforceable downstream safety boundary with a deterministic `CommitGate`, provider-neutral `KnownGoodVersion`, immutable `QuarantineRecord`/`QuarantineLedger`, and output-eligibility result.
**Explicitly out of scope:** Bright Data approval execution, provider-native activation or rollback, post-commit watch, repair memory, mutation lab, benchmark execution, frontend/dashboard, predictive models, autonomous retries, and a production sink.

> **AI proposes. Evidence decides.**

## Mission result

Mission 006 adds the following boundary without changing the provider integration architecture:

```text
RepairCandidate
    → VerificationResult
    → RiskDecision
    → CommitGate
    → ELIGIBLE / BLOCKED
    → OutputEligibility only
    → QuarantineLedger when unsafe evidence or preconditions require retention
```

`ELIGIBLE` means that the candidate satisfies AEGIS’s preconditions for a future commit stage. It does not approve Bright Data, activate a collector, write production data, or perform rollback. `BLOCKED` is the fail-closed result for every missing, invalid, unknown, contradictory, or unsafe precondition.

## 1. CommitGate design

`CommitGate.evaluate(...)` accepts:

| Input | Safety meaning |
| --- | --- |
| `RepairCandidate` | Candidate proposal and provenance; remains immutable. |
| `VerificationResult` | Immutable channel-level evidence and overall status. |
| `RiskDecision` | Deterministic `ACCEPT`, `REJECT`, or `QUARANTINE` policy result. |
| `ExtractionContract` | Contract reference supplied to preserve the gate’s typed boundary. |
| `KnownGoodVersion` or `None` | AEGIS-level known-good reference; no provider-native rollback claim. |
| `AuthorizationContext` or `None` | Provider-neutral authorization evidence, not an executor. |
| `correlation_id` | Required lifecycle/audit correlation identifier. |
| Optional `QuarantineRecord` | Active quarantine state and verification re-entry requirement. |

It returns an immutable `CommitDecision` with a separate `CommitEligibility` of `ELIGIBLE` or `BLOCKED`. Every decision preserves candidate ID, verification ID, RiskDecision ID, evidence references, known-good reference, authorization reference, timestamp, provenance, and correlation ID. `production_commit_performed` is hard-coded false by the model guard.

## 2. Fail-closed rules

A candidate is blocked when any of the following is true:

| Condition | Resulting reason |
| --- | --- |
| RiskDecision is not `ACCEPT` or is not future-commit eligible | `RISK_NOT_ACCEPT` |
| Verification is not `PASS` or is not future-commit eligible | `VERIFICATION_NOT_PASS` |
| Any critical verification check fails | `CRITICAL_VERIFICATION_FAILURE` |
| A required contract, semantic, or independent-evidence channel is missing, unknown, or not pass | `REQUIRED_EVIDENCE_MISSING` |
| Required channel or aggregate evidence references are empty | `EVIDENCE_INCOMPLETE` |
| Candidate provenance is outside `BRIGHT_DATA`/`TEST_DOUBLE` | `INVALID_CANDIDATE_PROVENANCE` |
| Candidate is not `VerificationStatus.VERIFIED` | `CANDIDATE_NOT_VERIFIED` |
| AEGIS known-good reference is absent or correlation-mismatched | `KNOWN_GOOD_MISSING` / `IDENTIFIERS_MISSING` |
| Authorization is absent, invalid, lacks `candidate_commit_eligibility`, or correlation-mismatched | `INVALID_AUTHORIZATION` |
| Candidate, repair, verification, risk, or correlation identifiers are missing | `IDENTIFIERS_MISSING` |
| Active quarantine exists | `QUARANTINED` |
| Quarantine is represented as released without a new verification ID | `REQUISITE_REVERIFICATION` |

The gate does not use an LLM opinion, provider approval response, or client override to weaken these rules. `UNKNOWN`, `REJECT`, `QUARANTINE`, and `UNVERIFIED` cannot become eligible.

## 3. KnownGoodVersion

`KnownGoodVersion` is an AEGIS-level immutable reference containing:

- `pipeline_reference`;
- `version_reference`;
- `observation_reference`;
- `verification_reference`;
- provenance;
- correlation ID; and
- timestamp.

It is intentionally not a Bright Data version object and does not provide provider-native rollback. Mission 001’s provider-native version/rollback status remains partial/documentation-only. The record gives a future commit stage an auditable local reference without fabricating provider capabilities.

## 4. QuarantineRecord and QuarantineLedger

`QuarantineRecord` preserves candidate ID, repair request ID, verification ID, risk decision ID, risk decision, reason, failed checks, unknown checks, evidence references, candidate provenance, timestamps, correlation ID, and current status. Initial status is `OPEN`; the model represents `REVIEWED`, `RELEASED`, and `REJECTED` as states only.

`QuarantineLedger` is an immutable tuple-backed append-only in-memory ledger. Adding a record returns a new ledger and preserves prior records. Changing a quarantine status returns a new record and a new ledger entry; it does not mutate or delete evidence. No human or provider release mechanism exists.

A represented `RELEASED` record cannot directly create output eligibility. `OutputEligibilityBoundary` requires the released record’s `reentry_verification_id` to match the current commit decision’s verification ID. Re-entry through verification is therefore explicit.

The ledger may retain records for:

- `RiskDecision=QUARANTINE`;
- inconclusive verification or unknown required evidence;
- blocked commit preconditions;
- malformed or unsafe candidates worth preserving as forensic evidence; and
- contradictory evidence.

Quarantined candidates are not eligible for downstream output.

## 5. Output eligibility

`OutputEligibilityBoundary.evaluate(...)` returns an immutable eligibility result only. It does not write to a product sink or production store.

A future output path may be considered eligible only when:

```text
VerificationResult = PASS
AND RiskDecision = ACCEPT
AND Candidate VerificationStatus = VERIFIED
AND CommitGate = ELIGIBLE
AND no active quarantine
```

A quarantined, rejected, unknown, unverified, or blocked candidate returns `eligible=False`. An `ACCEPT` RiskDecision by itself is insufficient.

## 6. TEST_DOUBLE scenarios

The explicit Mission 006 fixture factory provides:

| Scenario | Expected outcome |
| --- | --- |
| `COMMIT_ELIGIBLE` | `ELIGIBLE` when verification is pass, risk is accept, candidate is verified, known-good and authorization are valid, and evidence/correlation are complete. |
| `BLOCKED_REJECT` | `BLOCKED` with risk-not-accept and verification failure reasons. |
| `BLOCKED_QUARANTINE` | `BLOCKED`; quarantine ledger record is created. |
| `BLOCKED_UNKNOWN` | `BLOCKED` because required evidence is unknown. |
| `BLOCKED_MISSING_VERIFICATION` | `BLOCKED` because candidate remains `UNVERIFIED`. |
| `BLOCKED_MISSING_KNOWN_GOOD` | `BLOCKED` because known-good reference is absent. |
| `BLOCKED_UNAUTHORIZED` | `BLOCKED` because authorization is invalid. |
| `BLOCKED_MISSING_EVIDENCE` | `BLOCKED` because required evidence is unavailable. |
| `BLOCKED_CORRELATION` | `BLOCKED` because authorization correlation does not match. |

All fixtures use `TEST_DOUBLE` provenance and make no provider capability claim.

## 7. Recorded Bright Data boundary

The recorded Mission 001 Bright Data proposal is passed through the Mission 006 boundary as `BRIGHT_DATA` provenance with `VerificationStatus=UNVERIFIED`. Even when an AEGIS known-good reference and eligibility authorization are supplied, the CommitGate blocks it because the candidate is not verified and the recorded provider preview is not independent ground truth.

This integration test performs no Bright Data call, approval, activation, commit, or rollback. It preserves the provider evidence in a quarantine record when blocked.

## 8. Metric hooks

`CommitSafetyMetricHooks` records commit decisions and quarantine records for later event-based calculation of `QuarantineRate` and `UnsafeRefusalRate`. It does not run benchmarks or fabricate results.

With no production commit denominator, commit-related metrics remain `NOT_APPLICABLE`. A blocked decision is instrumented as a refusal event, but it is not a measured benchmark result. Future numerator/denominator values must come from immutable controlled-run or mutation-lab artifacts with per-severity scope.

## 9. Tests and results

The full suite was run with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
71 passed in 0.20s
```

Mission 006 tests cover every required scenario, fail-closed precondition, immutable decision record, quarantine retention, append-only state representation, release-without-reverification blocking, downstream output blocking, correlation checks, no-provider-side-effect boundary, no approval command execution, no rollback, no benchmark generation, and the recorded Mission 001 provider-proposal path.

## 10. Safety checks

Python compilation passed. The source-level safety scan found no provider approval command, `--auto-approve`, activation, commit, rollback, watch, memory, benchmark, or model-execution implementation in the Mission 006 source. Secret-pattern scanning found no credentials in the implementation, tests, or evidence report. No Bright Data state was modified.

## 11. Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/commit_gate.py` | Added fail-closed CommitGate, KnownGoodVersion, AuthorizationContext, CommitDecision, QuarantineRecord, QuarantineLedger, OutputEligibility, output boundary, and metric hooks. |
| `src/aegis/commit_gate_double.py` | Added explicit Mission 006 TEST_DOUBLE scenarios. |
| `src/aegis/healing.py` | Added `VerificationStatus.VERIFIED` as a domain status accepted by the later commit-gate boundary while keeping unverified provider proposals intact. |
| `src/aegis/__init__.py` | Exported Mission 006 interfaces. |
| `tests/unit/test_mission006.py` | Added 16 deterministic gate, quarantine, output, immutability, and metric tests. |
| `tests/integration/test_mission006_recorded_provider_boundary.py` | Added recorded Bright Data proposal safety integration. |
| `experiments/AEGIS-MISSION-006-COMMIT-GATE-QUARANTINE-LEDGER.md` | Added this evidence report. |
| `docs/07_METRICS.md` | Added Mission 006 metric-hook interpretation. |
| `docs/11_API_CONTRACTS.md` | Added CommitGate, quarantine, and output-eligibility contracts. |
| `docs/12_DATA_MODEL.md` | Added known-good, commit decision, quarantine, ledger, and output eligibility records. |
| `docs/13_DECISION_LOG.md` | Added Mission 006 safety decision. |
| `docs/16_TESTING_STRATEGY.md` | Added Mission 006 test evidence and safety boundary. |
| `docs/18_BRIGHT_DATA_INTEGRATION.md` | Recorded that Mission 006 adds no provider operation and preserves rollback unknowns. |
| `README.md` | Updated implementation status and limitations through Mission 006. |

## 12. Unresolved provider capabilities

Mission 006 does not change the Mission 001 labels. Bright Data approval execution remains documented/tested only at the approval-gated proposal boundary and was not executed. Provider-native version identity and rollback remain partial/documentation-only. Raw HTML from the tested CLI path remains unknown. WARC remains partially documented but not artifact-tested. Candidate correctness remains an AEGIS verification concern and is not proven by provider output.

## Exact recommended Mission 007

Mission 007 should implement the **durable audit/evidence store and quarantine read model** around the current immutable in-memory records. It should persist CommitDecision, QuarantineRecord, VerificationResult, RiskDecision, evidence references, and correlation IDs append-only; provide read-only current-status queries; enforce redaction/retention; and preserve re-entry through verification. It must not implement provider-native approval, activation, rollback, post-commit watch, memory learning, or benchmark execution automatically.
