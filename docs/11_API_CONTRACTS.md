# 11 — Internal API Contracts

**Status:** Contract baseline for implementation. Exact provider endpoints remain unknown.  
**Design:** Internal APIs are versioned, idempotent where side effects exist, and state-aware.  
**External rule:** Do not represent Bright Data routes as internal or verified until the integration spike confirms them.

## API conventions

All internal endpoints use JSON, UTC timestamps, opaque IDs, and a `correlation_id`. Mutating commands require an idempotency key. Responses include `request_id`, `status`, and links to durable evidence. Errors use stable codes, not provider-specific free text. Authorization is role-based at the command boundary; read endpoints may redact raw content and secrets.

## Common schemas

```json
{
  "id": "opaque-id",
  "correlation_id": "episode-or-request-id",
  "created_at": "ISO-8601 UTC",
  "status": "terminal-or-current-status",
  "evidence_refs": ["evidence://..."],
  "version": 1
}
```

```json
{
  "error": {
    "code": "VERIFICATION_REQUIRED",
    "message": "Safe human-readable explanation",
    "retryable": false,
    "details": {}
  },
  "request_id": "opaque-id"
}
```

## Endpoint catalog

| Purpose | Method | Route | Side effect | Idempotency | State impact |
| --- | --- | --- | --- | --- | --- |
| Register collector | POST | `/v1/collectors` | Creates collector definition | `Idempotency-Key` required | None → registered |
| Get collector | GET | `/v1/collectors/{collector_id}` | None | N/A | None |
| Start collection | POST | `/v1/collectors/{collector_id}/collections` | Starts external collection | Required | → collection in progress |
| Get collection | GET | `/v1/collections/{collection_id}` | None | N/A | Collection status read |
| Record observation | POST | `/v1/collections/{collection_id}/observations` | Persists observation | Required | → observation recorded |
| Evaluate detection | POST | `/v1/observations/{observation_id}/detect` | Creates findings/event | Required | HEALTHY or ANOMALOUS |
| Diagnose anomaly | POST | `/v1/detection-events/{event_id}/diagnose` | Creates diagnosis/request | Required | ANOMALOUS → DIAGNOSING |
| Start repair | POST | `/v1/diagnoses/{diagnosis_id}/repairs` | Invokes adapter | Required | DIAGNOSING → HEALING |
| Get repair attempt | GET | `/v1/repairs/{repair_id}` | None | N/A | Read |
| List candidates | GET | `/v1/repairs/{repair_id}/candidates` | None | N/A | Read |
| Verify candidate | POST | `/v1/candidates/{candidate_id}/verifications` | Creates verification run | Required | → VERIFYING / terminal |
| Decide risk | POST | `/v1/candidates/{candidate_id}/risk-decisions` | Records decision | Required | ACCEPT/RETRY/QUARANTINE/ESCALATE |
| Commit candidate | POST | `/v1/candidates/{candidate_id}/commit` | Promotes version | Required | ACCEPTED → COMMITTED |
| Quarantine episode | POST | `/v1/episodes/{episode_id}/quarantine` | Blocks shipment | Required | → QUARANTINED |
| Start watch | POST | `/v1/commits/{commit_id}/watch-cycles` | Schedules validation | Required | COMMITTED → WATCHING |
| Roll back | POST | `/v1/pipelines/{pipeline_id}/rollback` | Restores known-good version | Required | REGRESSION → ROLLING_BACK |
| Get repair episode | GET | `/v1/repair-episodes/{episode_id}` | None | N/A | Read |
| Apply mutation | POST | `/v1/mutations/runs` | Mutates staging fixture | Required | Creates mutation run |
| Run benchmark | POST | `/v1/benchmarks/runs` | Executes protocol | Required | Creates benchmark run |
| Get benchmark report | GET | `/v1/benchmarks/runs/{run_id}/report` | None | N/A | Read |
| Get product output | GET | `/v1/product/gpu-prices` | None | N/A | Reads committed, non-quarantined data |

## Representative request and response schemas

### Start collection

```json
{
  "collector_id": "collector-1",
  "input": {"target": "fixture-or-approved-url"},
  "contract_id": "contract-1",
  "mode": "production|laboratory",
  "correlation_id": "episode-1"
}
```

```json
{
  "collection_id": "collection-1",
  "status": "RUNNING",
  "accepted_data_policy": "UNTRUSTED_UNTIL_VERIFIED",
  "request_id": "request-1"
}
```

### Verify candidate

```json
{
  "candidate_id": "candidate-1",
  "contract_id": "contract-1",
  "channels": ["contract", "history", "independent_evidence"],
  "expected_minimum_deterministic_passes": 2,
  "correlation_id": "episode-1"
}
```

The response lists channel results, evidence references, normalized output comparison, unresolved findings, and `eligible_for_commit`. `eligible_for_commit` is false unless the commit gate is satisfied.

### Risk decision

```json
{
  "candidate_id": "candidate-1",
  "decision": "ACCEPT|RETRY|QUARANTINE|ESCALATE",
  "reason_code": "SUFFICIENT_EVIDENCE|INSUFFICIENT_EVIDENCE|HIGH_RISK|REVIEW_REQUIRED",
  "verification_run_ids": ["verification-1"],
  "retry_number": 0,
  "correlation_id": "episode-1"
}
```

### Commit

The commit endpoint rejects requests without a completed verification run, at least two independent deterministic passing channels, a matching ACCEPT decision, an authorized actor, and a known-good/version record. It is not permitted to accept a client-provided override that weakens those conditions.

## Error catalog

| Code | Retryable | Meaning |
| --- | --- | --- |
| `INVALID_CONTRACT` | No | Request violates the contract schema. |
| `NOT_FOUND` | No | Referenced entity does not exist. |
| `STATE_CONFLICT` | Usually no | Command is invalid for the current lifecycle state. |
| `UNAUTHORIZED` | No | Actor lacks required authority. |
| `PROVIDER_UNAVAILABLE` | Yes, bounded | External adapter unavailable. |
| `PROVIDER_TIMEOUT` | Yes, bounded | External call exceeded deadline. |
| `VERIFICATION_REQUIRED` | No | Commit attempted without sufficient deterministic evidence. |
| `QUARANTINED` | No | Output intentionally withheld. |
| `IDEMPOTENCY_CONFLICT` | No | Same key used with a different payload. |
| `EVIDENCE_MISSING` | No | Required evidence artifact is unavailable. |
| `BENCHMARK_INVALID` | No | Run cannot support headline metrics. |

## Authorization and state rules

Read access is separated from mutation commands. Collection and repair commands require the integration role; commit and rollback require the release role; benchmark configuration freeze requires the benchmark owner; submission claims require project-owner review. State transitions are validated server-side, and the caller cannot set a terminal state directly.

## External API boundary

Bright Data routes, CLI verbs, authentication, response formats, healing triggers, approval operations, and version semantics are documented only as adapter interfaces until verified. The adapter exposes AEGIS-normalized operations such as `collect`, `heal`, `poll`, `inspect`, `approve_if_authorized`, and `resolve_known_good`; the underlying provider call is recorded in the integration evidence.

## Mission 003 — Diagnosis and RepairRequest boundary

Mission 003 adds the following provider-neutral internal operations without executing healing:

| Purpose | Operation | Side effect | State impact |
| --- | --- | --- | --- |
| Diagnose detection | `diagnose(context: DiagnosisContext) -> Diagnosis | None` | Creates an immutable diagnosis record in memory | Detection evidence → `CREATED` or no diagnosis when healthy |
| Build repair intent | `build_repair_request(diagnosis, observation, contract) -> RepairRequest` | Creates an immutable repair request | Diagnosis `CREATED` → `REPAIR_REQUESTED` intent |
| Request healing boundary | `request_healing(repair_request) -> RepairAttemptHandle` | Mission 003 test boundary only; no provider call | Acknowledgement remains `REQUESTED`; execution is false |

`DiagnosisContext` accepts only an immutable Observation, immutable DetectionResult, ExtractionContract, detection ID, correlation ID, and explicit evidence references. It does not inspect arbitrary provider logs. `RepairRequest` is provider-neutral and describes what must be restored, not the provider implementation method.

A RepairRequest preserves affected fields, the extraction contract, target input, evidence references, known invariants, unaffected fields, mutation context when supplied, provenance, and a timestamp. It cannot contain provider endpoints, tokens, CLI commands, approval authority, or commit authority.

Mission 003 does not add candidate, verification, risk, approval, commit, rollback, watch, or memory operations. The furthest reachable state is `REPAIR_REQUESTED`; no request can transition into `COMMITTED`.

The model diagnostician seam is an injected structured backend that returns typed `failure_class`, qualitative `certainty`, affected fields, and rationale. It is not required for tests and cannot authorize provider operations.

## Mission 004 — Bright Data healing adapter boundary

Mission 004 extends the existing provider adapter with the following provider-facing boundary operations:

| Purpose | Operation | Side effect | State impact |
| --- | --- | --- | --- |
| Submit bounded heal request | `BrightDataCliAdapter.request_healing(repair_request)` | Starts one documented CLI heal command in a background worker | `SUBMITTED` |
| Poll provider heal | `BrightDataCliAdapter.poll_healing(handle)` | Reads the worker result and validates the provider envelope | `SUBMITTED → RUNNING → AWAITING_APPROVAL / FAILED / TIMED_OUT` |
| Retrieve untrusted proposal | `BrightDataCliAdapter.retrieve_heal_result(handle)` | Returns redacted provider envelope and `UNVERIFIED` candidate | `AWAITING_APPROVAL → CANDIDATE_READY` |

The adapter-only mapping is `RepairRequest.collector_reference → <collector_id>`, the generated bounded repair prompt → `<prompt>`, and `RepairRequest.target_input["target_url"] → --url <url>` in the documented command shape:

```text
npx -p @brightdata/cli bdata scraper heal <collector_id> <prompt> --url <url>
```

No `bdata scraper approve`, `--auto-approve`, activation, verification, risk, commit, or rollback operation is exposed by Mission 004. Provider `awaiting_approval` is data indicating a proposal, not AEGIS approval.

Candidate creation requires a structured status, preview result, and provider operation identifier. Missing, malformed, unexpected, failed, or timed-out provider responses fail closed. The candidate’s only verification status in this mission is `UNVERIFIED`.

## Mission 005 — Verification and Risk Governor boundary

Mission 005 adds deterministic internal operations that evaluate a provider proposal without executing provider approval or production commit:

| Purpose | Operation | Side effect | State/result |
| --- | --- | --- | --- |
| Verify candidate | `verify_candidate(context: VerificationContext) -> VerificationResult` | Creates immutable channel checks and evidence references | `PASS`, `FAIL`, or `INCONCLUSIVE` |
| Decide risk | `RiskGovernor.decide(verification, candidate, policy) -> RiskDecision` | Creates immutable deterministic decision record | `ACCEPT`, `REJECT`, or `QUARANTINE` |
| Record metric event | `SafetyMetricHooks.record_verification()` / `record_risk_decision()` | Appends local measurement hooks only | No benchmark or commit operation |

Verification evaluates exactly four conceptual channels: `CONTRACT`, `HISTORY`, `SEMANTIC_INVARIANT`, and `INDEPENDENT_EVIDENCE`. Each check is `PASS`, `FAIL`, or `UNKNOWN` and includes evidence, provenance, timestamp, correlation ID, affected fields, and criticality. Unknown is never converted to pass.

The initial acceptance gate requires `CONTRACT`, `SEMANTIC_INVARIANT`, and `INDEPENDENT_EVIDENCE` to pass with no critical contradiction. `HISTORY` strengthens the decision when available but is optional. Missing required evidence produces `QUARANTINE`; deterministic failure produces `REJECT`. No additive confidence weights are used.

`RiskDecision.ACCEPT` means eligible for a later commit stage only. It does not activate a provider version, ship data, or perform production commit. Mission 005 exposes no provider approval, activation, commit, rollback, watch, memory, or benchmark endpoint.

## Mission 006 — CommitGate and QuarantineLedger boundary

Mission 006 adds a provider-neutral eligibility layer after Mission 005 `RiskDecision`:

| Purpose | Operation | Side effect | State/result |
| --- | --- | --- | --- |
| Evaluate commit preconditions | `CommitGate.evaluate(candidate, verification, risk, contract, known_good, authorization, correlation_id)` | None; creates an immutable decision | `ELIGIBLE` or `BLOCKED` |
| Record unsafe outcome | `QuarantineLedger.record_for_decision(...)` | Appends an immutable forensic record in the in-memory ledger | `OPEN` quarantine record |
| Evaluate future output eligibility | `OutputEligibilityBoundary.evaluate(commit_decision, quarantine_record)` | None; creates an authorization/eligibility result only | eligible or blocked |

The gate fails closed. It requires `RiskDecision=ACCEPT`, `VerificationResult=PASS`, all required deterministic evidence, no critical failures, an allowed candidate provenance, `VerificationStatus=VERIFIED`, a provider-neutral known-good reference, valid authorization, complete identifiers, complete evidence references, and no active quarantine. `ACCEPT` remains eligibility for a later commit stage only; no provider commit or production sink is exposed.

`KnownGoodVersion` is an AEGIS-level reference containing pipeline, version, observation, verification, provenance, and correlation references. It is not a Bright Data version or rollback claim. `QuarantineRecord` preserves candidate, repair, verification, risk, reason, failed/unknown checks, evidence, provenance, timestamps, and correlation IDs. A release status is only represented as data; re-entry requires a new verification ID and no release mechanism is implemented.

## Mission 007 — Post-commit watch boundary

Mission 007 adds provider-neutral internal operations after a future eligible commit:

| Purpose | Operation | Side effect | State/result |
| --- | --- | --- | --- |
| Register watch | `WatchEngine.register(candidate, verification, risk, commit_decision, known_good, contract, ...)` | Creates immutable registration only when the existing CommitGate is `ELIGIBLE` | `COMMITTED` |
| Evaluate watch cycle | `WatchEngine.evaluate(registration, observation, ...)` | Reuses `evaluate_detection`; creates immutable cycle/result/evidence | `HEALTHY`, `REGRESSION`, or `UNKNOWN` |
| Quarantine regression | `QuarantineLedger.record_watch_regression(...)` | Appends the existing Mission 006 quarantine record | `OPEN` quarantine record |
| Record watch metrics | `WatchMetricHooks.record(evaluation)` | Appends local metric events only | No benchmark or provider operation |

The watch state boundary is `COMMITTED → WATCHING → HEALTHY/REGRESSION/UNKNOWN`, with `REGRESSION → QUARANTINED` when the watch policy requires it. The watch layer does not repair, re-diagnose, activate, approve, commit, or rollback.

`UNKNOWN` is preserved when required watch evidence is unavailable. The default policy does not quarantine merely because optional evidence is absent. Any serious regression uses the existing `QuarantineLedger`; no second quarantine implementation exists.
