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

## Mission 008 — Durable audit/evidence store boundary

Mission 008 adds a provider-neutral infrastructure interface around existing immutable domain records:

| Purpose | Operation | Side effect | Result |
| --- | --- | --- | --- |
| Append evidence event | `AuditStore.append_event(event)` | One immutable SQLite insert | Stored `AuditEvent` |
| Read event | `get_event(event_id)` | None | Immutable event or `None` |
| Read history | `history(aggregate_id=?, correlation_id=?, event_type=?)` | None | Ordered immutable event tuple |
| Read current status | `current_status(aggregate_id)` | None | Read-only status projection |

Convenience appenders cover observations, detections, diagnoses, repair requests, candidates, verification results, risk decisions, commit decisions, quarantine records, watch registrations, watch cycles, watch results, regression events, and evidence references. There is no update, delete, evidence mutation, or lifecycle-execution operation.

The SQLite implementation is a local infrastructure choice, not a provider or production deployment claim. Each event stores an opaque event ID, event type, aggregate/reference ID, correlation ID, UTC timestamp, provenance, schema version, redacted payload, and evidence-reference tuple. Corrections are new events that may reference a prior event ID.

## Mission 009 — Mutation Laboratory V1 contracts

Mission 009 adds provider-neutral local contracts:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `MutationLab.apply_mutation(mutation_id, seed)` | Apply one deterministic definition to the clean staging fixture | Returns immutable `MutationCase`; does not modify baseline. |
| `MutationLab.run(mutation_id, seed)` | Create a TEST_DOUBLE Observation and drive existing detection, verification, risk, and CommitGate boundaries | Returns immutable run/evidence objects; no provider call. |
| `MutationGroundTruth` | Preserve independent expected correct/corrupted state and safety expectation | Immutable record. |
| `MutationRun` | Preserve run IDs, references, detected flags, outcome, timing, provenance, and later-stage references | Immutable record; output eligibility is always false in V1. |

Mutation definitions are provider-neutral and must not embed Bright Data behavior. The harness uses existing `evaluate_detection`, `verify_candidate`, `RiskGovernor`, `CommitGate`, and `QuarantineLedger` rather than parallel implementations.

## Mission 010 — MutationRun manifest and metric-report contracts

Mission 010 adds provider-neutral read/calculation operations over existing immutable Mission 009 records:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `manifest_record(run, ground_truth)` | Project one immutable run and its independent truth into a redacted manifest record | None |
| `export_manifest(runs, ground_truths)` | Produce deterministic JSON ordered by mutation ID and run ID | None; no mutation of input records |
| `calculate_metrics(runs, ground_truths)` | Produce immutable `MetricReport` and `MetricResult` records using canonical formulas | None; no provider or lifecycle operation |
| `MetricResult` | Preserve status, numerator/denominator, scope, run IDs, formula version, and evidence references | Immutable record |

`export_manifest` preserves run ID, mutation ID, mutation severity, seed, fixture version, baseline/mutated/truth references, provenance, detection and detector-severity fields, verification result, risk decision, CommitGate result, output eligibility, quarantine reference, timing, timestamp, and evidence references. Ground-truth projection fields explicitly record `actual_failure`, expected detector behavior, expected safety behavior, and affected fields. Credentials, authorization headers, secret-bearing logs, and secret-bearing reference strings are not exported.

`calculate_metrics` uses only `MutationGroundTruth` to classify actual failure and healthy cosmetic mutation. Detection-related metrics support overall, per-severity, and per-mutation scopes. L5 safety metrics are reported separately. Missing denominators produce `status=NOT_APPLICABLE` with `value=null`; they are never represented as measured zero. Mission 009 has no repair attempts or production commits, so recovery, verification-miss, false-repair, and blind-commit results remain explicitly unavailable.

The generated files are `experiments/AEGIS-MISSION-010-MUTATION-MANIFEST.json`, `experiments/AEGIS-MISSION-010-METRICS.json`, and `docs/generated/mission_010_metrics.md`. They are derived artifacts and do not add an endpoint, provider capability, approval operation, commit operation, rollback operation, or benchmark runner.

## Mission 011 — BenchmarkConfig freeze and validation-only dry-run contracts

Mission 011 adds provider-neutral, side-effect-free benchmark configuration operations:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `BaselineSpec` | Immutable slot for Baseline A, Baseline B, or AEGIS metadata and readiness status | None |
| `BenchmarkConfig` | Immutable benchmark definition with frozen mutation, seed, baseline, environment, policy, artifact, and metric-version fields | None |
| `validate_config(config)` | Fail-closed validation of configuration completeness, consistency, fixture alignment, policy ranges, artifact contract, and configuration hash | None |
| `compute_configuration_hash(config)` | Canonical SHA-256 hash over all frozen configuration fields except the stored hash itself | None |
| `freeze_config(config)` | Return a new immutable configuration with the canonical hash | None |
| `run_dry_run(config)` / `dry_run(config)` | Verify fixture definitions, seed reproducibility, baseline metadata, calculator availability, artifact path, and generate an unexecuted plan | No provider, benchmark, healing, metric, commit, or rollback operation |

`BenchmarkConfig` contains `benchmark_id`, `benchmark_version`, `fixture_id`, `fixture_version`, `mutation_class_ids`, `mutation_severity`, `seeds`, `trial_count`, baseline slots, code/repository revision, repository state, environment/runtime references, model/prompt fields, retry/timeout/collection/evidence policies, the artifact contract, artifact root, metric formula version, creation timestamp, and configuration hash. Nested mappings are recursively frozen. The artifact contract defines `benchmarks/configs`, `benchmarks/manifests`, `benchmarks/runs`, `benchmarks/results`, and `benchmarks/reports`; Mission 011 does not create fake run artifacts or future directories.

The validator rejects missing or duplicate mutation IDs, missing or invalid severity mappings, missing/duplicate/non-integer seeds, incomplete or inconsistent baselines, missing revisions or fixture version, invalid retry/timeout policies, missing artifact paths, unsupported metric formula versions, conflicting code/repository revisions, and stale configuration hashes. `NOT_READY`, `TBD`, `UNKNOWN`, and `NOT_APPLICABLE` remain explicit data where implementation or model details are not established.

A successful dry-run result is labeled `VALIDATION_ONLY` and contains `VALIDATION ONLY` / `NO BENCHMARK EXECUTED`, a deterministic execution plan, expected run/mutation/seed/baseline counts, validation checks, and zero execution counters. It never returns metric values and carries `benchmark_execution_authorized=false`. Repeated dry runs over the same immutable config must have byte-identical substantive output.

## Mission 012 — Common benchmark participants and raw-evidence runner

Mission 012 adds provider-neutral benchmark interfaces without adding a provider endpoint or an execution side effect to dry-run:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `ParticipantAdapter` | Common `readiness`, `prepare`, `run_mutation`, `collect_result`, and `return_run_evidence` contract | Participant execution only through an explicit later call; dry-run does not invoke it |
| `BaselineAAdapter` | Static selector contract; AEGIS detection/verification/risk/commit controls are explicitly `NOT_USED` | TEST_DOUBLE fixture execution only when a separately frozen READY slot is supplied |
| `BaselineBAdapter` | Owner-approved naive-repair slot and readiness validator | No execution while model/prompt/configuration is missing |
| `AegisAdapter` | Normalize existing Mission 009 AEGIS lifecycle under `TEST_DOUBLE` provenance | No provider operation; benchmark slot remains `NOT_READY_FOR_BENCHMARK` |
| `ParticipantExecutionInput` | Identical mutation/seed/fixture/trial metadata delivered to every participant | None |
| `ParticipantRunEvidence` | Common raw output schema with `NOT_APPLICABLE` for absent concepts | None |
| `RunManifest` | Immutable planned-run identity and artifact naming | None; no result payload |
| `FreezeSnapshot` / `validate_freeze` | Compare hash, revision, fixture, mutation, severity, seed, baseline hashes, formula, and policies | None; mismatch invalidates |
| `BenchmarkRunner.dry_run()` | Validate participants and create deterministic plan | No benchmark/provider/healing/metric operation |
| `scripts/benchmark_runner.py --dry-run` | Command boundary for validation-only mode | Prints raw dry-run JSON; execution is intentionally unavailable |

The normalized common evidence fields are `participant_id`, `run_id`, `mutation_id`, `severity`, `seed`, `fixture_version`, `participant_revision`, `configuration_hash`, `ground_truth_reference`, `code_revision`, `environment_reference`, `timeout_policy`, `retry_policy`, `artifact_root`, `observation_reference`, `detected`, `verification_status`, `risk_decision`, `output_eligible`, `failure_state`, `timing_ms`, `cost`, `llm_calls`, `evidence_refs`, `artifact_refs`, `provenance`, and runner state. Baseline-only concepts remain `NOT_APPLICABLE`.

`BenchmarkRunner.dry_run()` returns `VALIDATION_ONLY`, `BLOCKED_NOT_READY`, or `INVALID`. At Mission 012 start, the frozen slots produce `BLOCKED_NOT_READY`: Baseline A has a valid contract but a `NOT_READY` slot, Baseline B lacks owner-approved model/prompt/implementation/configuration values, and AEGIS has a TEST_DOUBLE normalization contract but is `NOT_READY_FOR_BENCHMARK`. The runner still constructs the deterministic 18-step plan and never substitutes AEGIS for a missing baseline.

No `approve`, production `commit`, provider activation, provider rollback, metric calculation, or automatic execution method is exposed by the dry-run boundary. An explicit `execute_one` method exists only as a later-run boundary and first checks freeze and participant readiness; it is never called by validation-only mode.

## Mission 013 — Human-reviewed participant freeze and readiness promotion

Mission 013 adds immutable review/promotion records and extends the runner’s readiness boundary:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `ParticipantFreezeProposal` | Hold complete participant metadata and a deterministic participant configuration hash | None; missing values remain placeholders |
| `OwnerReviewDecision` | Record explicit owner/reviewer approval, rationale, timestamp, and correlation ID | None |
| `validate_participant_proposal` | Fail-closed completeness and participant-hash validation for Baseline A, Baseline B, or AEGIS | None |
| `promote_participant` | Convert one explicitly reviewed `NOT_READY` proposal into a new immutable READY `BaselineSpec` | No benchmark/provider execution; prior records remain unchanged |
| `apply_promotions` | Return a new benchmark configuration with promoted specs and a regenerated canonical configuration hash | None; old config is not mutated |
| `ReadinessPromotion` | Immutable `NOT_READY → READY` evidence record | Append-only evidence |
| `RunnerDryRunStatus.READY_TO_EXECUTE` | Indicate all participant metadata and freeze checks pass in planning-only mode | Still `execution_authorized=false`; it does not launch runs |

The participant hash covers participant ID, implementation revision, configuration, timeout/retry policies, output normalization, provenance, artifact schema, execution policy, verification policy, and commit policy. `BenchmarkConfig` includes non-empty participant metadata in its canonical hash payload. Changing metadata while retaining the old Mission 011 hash makes `validate_config` invalid; applying a reviewed promotion returns a new frozen configuration hash.

Baseline B promotion requires explicit model/provider, exact system and repair prompts, sampling/max-output/tools settings, timeout/retry policy, and first-candidate policy. No missing model or prompt is selected automatically. AEGIS promotion requires unchanged safety policy and Mission 010 compatibility. A participant marked READY without valid reviewed metadata is rejected by adapter readiness.

The actual Mission 013 artifact contains no promotions because owner approval was not provided. The current `--dry-run` remains `BLOCKED_NOT_READY`. If all three slots are later promoted and the resulting configuration is frozen, the same side-effect-free runner can return `READY_TO_EXECUTE`; it still emits zero run/metric/provider counts and requires a separate explicit execution authorization boundary.

## Mission 014 — Owner-approved input validation gate

Mission 014 adds a declarative owner-input validator that preserves supplied participant values and fails closed before promotion:

| Contract | Behavior |
| --- | --- |
| `load_owner_payload` | Loads the exact owner-supplied participant configuration; it does not fill placeholders |
| `validate_owner_configuration` | Validates required fields, exact hard rules, participant hashes, review metadata, and common fairness fields |
| `ParticipantApprovalValidation` | Records per-participant status, missing fields, placeholder fields, exact checks, participant hash text, and errors |
| `OwnerReviewValidation` | Requires `approved=true`, reviewer `PROJECT_OWNER`, timestamp, rationale, correlation ID, and approved final configuration hash |
| `FairnessValidation` | Compares mutation IDs, seed, fixture, ground-truth payload, timeout, retry, and backoff values across participants |
| `OwnerApprovedValidationReport` | Records blocked/valid status and zero-execution counters without creating promotion or result records |

The supplied input is `BLOCKED_NOT_READY`: all three participant revisions and hashes are unresolved placeholders; owner-review timestamp, rationale, correlation ID, and final hash are not supplied; and timeout values conflict across participants. The validator therefore does not call `promote_participant`, `apply_promotions`, or the benchmark runner. `READY_TO_EXECUTE` is not emitted.


## Mission 015 — finalized participant contract and validation-only runner boundary

Mission 015 freezes the common participant contract at `canonical-participant-run-v1` with artifact schema `participant-run-evidence-v1`. Baseline A uses deterministic static-selector extraction with AEGIS-only controls marked `NOT_USED`. Baseline B uses the approved `GOOGLE_GEMINI_API` / `gemini-3.6-flash` configuration with tools disabled and a first-candidate-only policy; when no caller is injected, the model boundary returns an explicit unavailable raw-evidence state rather than silently selecting another provider or model. AEGIS uses the existing `AegisAdapter` TEST_DOUBLE lifecycle and preserves verification, RiskGovernor, CommitGate, quarantine, watch, and rollback boundaries.

The owner-review contract records `approved=true`, `owner=PROJECT_OWNER`, `reviewer=PROJECT_OWNER`, a current UTC review timestamp, a mission rationale, a generated correlation ID, and the computed participant configuration hash. Each participant has an immutable `NOT_READY → READY` promotion record. The benchmark-level timeout policy is frozen in milliseconds at 300000 for collection, healing, polling, verification, and total time; retry is bounded to one attempt with zero backoff.

The new configuration is `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96`, and validation reports all three participant slots ready. The runner produces an 18-manifest validation-only plan and `READY_TO_EXECUTE` readiness status without invoking collection, healing, provider, approval, commit, rollback, or metric operations. The persisted dry-run counters remain zero and `execution_authorized=false`.


## Mission 019 — Baseline B first-candidate execution contract

Mission 019 extends `ParticipantRunEvidence` with explicit raw Baseline B lifecycle fields: `candidate_received`, `candidate_selected`, `candidate_accepted`, `candidate`, and `candidate_application`. Non-Baseline-B participants retain `NOT_APPLICABLE` defaults for these fields.

For an available model response, Baseline B now applies the frozen `FIRST_CANDIDATE` / `max_candidates=1` / `auto_accept_first_candidate=true` policy explicitly. The first candidate is recorded, selected at index 0, accepted only when the bounded adapter execution contract succeeds, and normalized as `failure_state=COMPLETED`, `output_eligible=true`, `verification_status=NOT_APPLICABLE`, `risk_decision=NOT_APPLICABLE`, `llm_calls=1`, and `provenance=MODEL_ASSISTED`. Additional returned candidates are recorded only through `candidate_count_seen`; they are never selected or accepted.

The application boundary is `SAFE_TEST_DOUBLE_BOUNDARY`. It records a candidate digest and controlled fixture identity, explicitly sets `generated_code_executed=false`, and records that AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, and rollback were not invoked. It does not execute arbitrary generated code and does not receive `MutationGroundTruth` content. `output_eligible=true` means only that Baseline B accepted its first candidate under its naive policy; it is not a correctness or production-commit decision.

Unavailable or malformed model results remain fail-closed as unavailable/failed evidence and never become output eligible. The authorized Mission 019 real smoke produced `BASELINE_B_EXECUTION_READINESS_SMOKE` status `PASS`; the benchmark and metric boundaries remained unused.


## Mission 020 — lifecycle phase and artifact-root separation

Mission 020 introduces the provider-neutral `BenchmarkLifecyclePhase` values `PREFLIGHT`, `SMOKE`, and `BENCHMARK_EXECUTION`. The preflight runner and smoke runner carry their respective phase explicitly; the existing `BenchmarkRunner.execute_one()` boundary remains a separate benchmark-execution operation and is not called by Mission 020.

`deterministic_benchmark_run_id(configuration_hash, attempt_id, participant_revisions)` derives a stable `mission_020_floor_<digest>` identity from the corrected configuration hash, an explicit attempt/version identifier, and sorted participant source revisions. It is distinct from the Mission 019 preflight/smoke run ID and does not use wall-clock time as its identity.

`BenchmarkArtifactLayout` describes the future benchmark output tree and rejects roots that overlap, contain, or are contained by the immutable Mission 019 smoke root. `BenchmarkRunner` accepts an optional artifact-root override and forbidden-root set for the future execution boundary; default frozen configuration metadata remains unchanged. Mission 020 uses these contracts only for validation and planning, not for run creation or output writing.


## Mission 021 — explicit benchmark execution CLI and executor contract

Mission 021 adds an explicit execution boundary without changing the Mission 012–020 validation contracts:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `scripts/benchmark_runner.py --help` | Expose `--config`, `--dry-run`, `--run`, and `--output` | None |
| `scripts/benchmark_runner.py --dry-run` | Preserve validation-only behavior and zero counters | None; future root remains absent |
| `scripts/benchmark_runner.py --run --output PATH` | Authorize the frozen execution boundary only after all gates pass | Creates only the isolated future run root |
| `BenchmarkExecutor.execution_gate()` | Validate hash, freeze, revisions, readiness, fairness, fixture, smoke, isolation, deterministic ID, absence, and metric interface | None; fail-closed |
| `BenchmarkExecutor.plan_manifests()` | Produce exactly `3 × 6 × 10 = 180` deterministic opportunities | In-memory only |
| `BenchmarkExecutor.execute()` | Execute one participant per planned opportunity and persist raw evidence | Explicit execution only |
| `ExecutionSummary` | Report planned/completed/failed/timed-out/invalidated counts and authorization | Immutable result |

The explicit run command must use `benchmarks/configs/mission_017_corrected_frozen_config.json` and output `benchmarks/runs/mission_020_floor_2a80a8cf8d989326`. The root is created only after authorization and cannot overlap `benchmarks/runs/mission_016_floor_59a11e27a71f/`.

Mission 021 retains the frozen configuration and seed `12345`. Its executor-level `trial_number` from 1 through 10 is included in deterministic trial IDs, artifact names, manifests, and raw evidence, allowing the requested ten opportunities per mutation without editing the frozen configuration hash or seed list. The historical validation-only plan remains 18 steps; the explicit execution plan is 180 steps.

Each raw record includes a participant-run evidence envelope, deterministic run identity, benchmark/configuration/run references, participant identity/revision/configuration hash, mutation/severity/trial/seed/fixture identity, ground-truth reference, code/environment revision, timeout/retry policies, provenance, timing, failure state, detection/diagnosis/repair/candidate/verification/risk fields where applicable, output eligibility, cost, LLM calls, evidence references, and artifact references. Terminal states are `COMPLETED`, `FAILED`, `TIMED_OUT`, and `INVALIDATED`; failures are never converted into success.

The CLI constructs the real Gemini caller only after explicit `--run`; tests inject a fake caller. No arbitrary generated code is executed, no ground-truth payload is supplied to participants, and no AEGIS verification is bypassed. Mission 010 remains the sole metric authority; an incompatible all-participant metric input fails closed with `FAILED_METRIC_BOUNDARY` rather than invoking a second calculator.


## Mission 022 — ParticipantRunEvidence to Mission 010 compatibility contract

Mission 022 adds a provider-neutral compatibility module without changing the Mission 010 calculator:

| Operation/model | Purpose | Side effect |
| --- | --- | --- |
| `ParticipantEvidenceContext` | Immutable RunManifest fields joined by exact run ID | None |
| `MetricMutationInput` | Immutable duck-typed `MutationRun` projection plus traceability fields | None |
| `EvidenceCompatibilityRecord` | Preserve original evidence, context, bridge result, truth join, and missing fields | None |
| `MetricCompatibilityReport` | Deterministic matrix, all source records, metric-ready scope, and fatal errors | None |
| `adapt_completed_evidence()` | Validate identity, join evaluator-owned truth, preserve evidence, and build metric inputs | None; fail-closed |
| `calculate_compatibility_metrics()` | Invoke only `aegis.mutation_metrics.calculate_metrics()` after bridge validation | Existing Mission 010 calculator only |

`MetricCompatibilityReport.passed` means that all supplied evidence records adapted without integrity failure. `metric_calculation_ready` is separate and requires at least one honest metric-input scope. This distinction allows complete Baseline A/B evidence to remain in the report with explicit `NOT_APPLICABLE` fields without converting unavailable concepts into false values.

The adapter requires completed state, non-empty evidence references, non-empty artifact references, exact manifest/evidence run identity, matching mutation/seed/severity truth identity, and evaluator-owned ground truth. Duplicate run IDs, missing truth, missing context, mismatched context, non-terminal evidence, or missing references produce `FAILED_METRIC_BOUNDARY`. Truth is joined only after participant execution and is never included in participant runtime input.

The adapter preserves the original source object and an explicit `preserved_fields` projection. It retains participant configuration hash and trial ordinal from immutable Mission 021 manifest context. It creates deterministic normalized truth references but does not copy truth content into the metric input. Mission 010’s `calculate_metrics()` remains the only calculator and receives only the honest AEGIS metric-input scope under the current v1 formula boundary.


## Mission 023 — explicit smoke-root and Baseline B smoke-root contract

`BenchmarkArtifactLayout` now represents three distinct paths:

| Field | Meaning |
|---|---|
| `smoke_root` | Canonical immutable Mission 019 root: `benchmarks/runs/mission_016_floor_59a11e27a71f/` |
| `baseline_b_smoke_root` / `smoke_evidence_root` | Exact Baseline B smoke subroot: `benchmarks/runs/mission_016_floor_59a11e27a71f/baseline_b_execution_readiness_smoke/` |
| `root` | Separate future benchmark root: `benchmarks/runs/mission_020_floor_2a80a8cf8d989326/` |

The smoke validator reads the two smoke files from `smoke_evidence_root` and the preflight/root-log/frozen-config files from `smoke_root`. `validate_isolation()` continues to reject a benchmark root that overlaps or contains the canonical `smoke_root`. A legacy three-argument layout construction derives the Baseline B subroot deterministically and remains compatible.

The execution gate reports the smoke detail as `status=VALID`, `pass=true`, candidate accepted, bounded application, runtime ground truth not provided, preflight passed, frozen hash passed, and all historical zero-execution counters valid. Gate validation does not invoke `execute()`.


## Mission 024 — shared immutable smoke-evidence API

Mission 024 adds a single provider-neutral contract:

| Operation/model | Purpose | Side effect |
|---|---|---|
| `resolve_immutable_smoke_evidence(repository_root)` | Resolve the canonical Mission 019 root, Baseline B subroot, and five evidence files | None |
| `SmokeEvidencePaths` | Immutable absolute path bundle shared by preflight and executor | None |
| `validate_immutable_smoke_evidence(repository_root)` | Apply the exact Mission 019/020 smoke checks from `repository_root` | Read-only |
| `SmokeEvidenceValidation` | Return `pass`, `status`, checks, errors, missing paths, and preserved historical provider count | None |

The required paths are `BASELINE_B_SMOKE_ROOT/smoke.json`, `BASELINE_B_SMOKE_ROOT/execution_log.json`, `SMOKE_ROOT/preflight.json`, `SMOKE_ROOT/execution_log.json`, and `SMOKE_ROOT/frozen_config.json`. No path is derived from the future benchmark output root, the deterministic benchmark run ID, or the process current working directory.

`BenchmarkExecutor._validate_immutable_smoke_evidence()` remains as a compatibility method but delegates directly to `validate_immutable_smoke_evidence(self.repository_root)`. The preflight wrapper delegates to the same function. `ExecutionGateResult.execution_authorized` is explicitly `false` for gate validation; authorization occurs only in the separately invoked execution boundary.


## Mission 025 — interrupted-root resume API

Mission 025 adds the following provider-neutral resume contract:

| Operation/model | Purpose | Side effect |
|---|---|---|
| `inspect_existing_run(root, manifests, ...)` | Validate existing frozen root and consume valid terminal artifacts | Read-only |
| `ResumeInspection` | Expose consumed artifacts, terminal counts, missing manifests, reconstructed run records, and original raw digests | None |
| `ResumeValidationError` | Fail closed on corruption, conflicting identity, malformed state, duplicates, or missing root files | None |
| `deserialize_participant_evidence(payload)` | Rehydrate completed normalized evidence for the Mission 022 boundary | None |
| `reconstruct_execution_log(inspection, ...)` | Build deterministic log state from persisted terminal artifacts | None |

Terminal consumption requires exact benchmark/run identity, participant, participant revision, mutation, severity, trial, seed, configuration hash, artifact filename, and a valid terminal state. `FAILED`, `TIMED_OUT`, and `INVALIDATED` are consumed attempts and are not retried. The executor computes missing entries from the frozen manifest order and executes only those entries.

For an existing root, `artifact_root_absent=false` is expected, while `artifact_root_resumable`, `existing_terminal_artifacts_valid`, and `missing_run_set_computed` must be true. The normal execution authorization remains explicit and is never inferred from root existence. Existing `frozen_config.json`, `participant_manifest.json`, and terminal raw files are not rewritten by resume inspection.

## Mission 026 — NVIDIA NIM API contract

`src/aegis/nvidia_provider.py` defines a provider-neutral `ModelDescriptor`, `NvidiaModelCatalog`, `NvidiaModelCaller`, `NvidiaProviderError`, `RateLimitConfig`, `ProviderRateLimiter`, `NvidiaBaselineBAdapter`, and `NvidiaParticipantRegistry`. The hosted caller targets `https://integrate.api.nvidia.com/v1/chat/completions` only when explicitly constructed and invoked. It reads one of `NVIDIA_API_KEY`, `NVIDIA_NIM_API_KEY`, or `NGC_API_KEY`; no credential is written to artifacts or metadata.

The caller normalizes OpenAI-compatible `choices[].message.content` into the existing Baseline B candidate mapping. It records provider, model, revision, endpoint, status, latency, request count, failure state, and retry-after observation without storing authorization headers. HTTP 429, 5xx, transport, invalid JSON, and malformed-choice failures are explicit and non-retrying by default. Rate limits remain configuration values; an unverified numeric RPM is never assumed.

The CLI selects the NVIDIA registry only when the loaded Baseline B metadata declares `provider=NVIDIA_NIM`. `--dry-run` constructs no network caller and remains provider-free. `--run` remains explicit and requires `--output`; the NVIDIA candidate configuration is `NOT_READY`, so it cannot authorize the benchmark until owner review and promotion are recorded.

## Mission 027 — NVIDIA owner-review API contract

Mission 027 reuses `OwnerReviewDecision`, `ParticipantFreezeProposal`, `promote_participant`, `ReadinessPromotion`, and `apply_promotions`. The owner review is immutable data containing `approved`, owner, reviewer, rationale, explicit UTC timestamp, correlation ID, source participant hash, and the owner-approved benchmark-side rate policy. Promotion records only the append-only `NOT_READY → READY` transition; it does not mutate Mission 026 history.

The promoted NVIDIA metadata contains provider `NVIDIA_NIM`, model `openai/gpt-oss-20b`, its pinned revision, the existing first-candidate/no-AEGIS-control policy, and the separate rate fields `benchmark_requests_per_minute=6`, `benchmark_min_interval_seconds=10`, and `concurrency_limit=1`. `provider_limit=UNKNOWN` remains a distinct field. The new canonical configuration is frozen through `compute_configuration_hash`; the historical Gemini configuration is not rewritten.

The validation-only CLI constructs an NVIDIA participant registry without a model caller and returns `READY_TO_EXECUTE` only as a planning state. It does not invoke NVIDIA, Gemini, Bright Data, healing, approval, commit, rollback, or metrics. The explicit `--run` boundary remains outside Mission 027.

## Mission 028 — authorized NVIDIA execution contract

Mission 028 derives `benchmark_run_id=mission_028_floor_00c77f2abd976a10` from the Mission 027 configuration hash, explicit attempt identifier `mission-028-nvidia-comparative-benchmark-v1`, and sorted participant revisions. The executor accepts explicit configuration, attempt, run-prefix, source-revision, expected-run, and additional-gate parameters while preserving Mission 020 defaults for historical behavior.

The pre-execution gate requires configuration hash and validation, freeze validation, participant readiness and revision/hash checks, fairness, clean fixture, immutable smoke evidence, metric authority, model caller availability, valid benchmark-side throttle, isolated/absent artifact root, deterministic identity, duplicate-free manifests, and exactly 180 planned opportunities. A failed gate returns before trial 1 and creates no benchmark root.

The authorized NVIDIA caller uses the frozen provider/model/revision and the owner-approved AEGIS throttle of 6 requests per minute, 10-second minimum interval, and concurrency 1. NVIDIA’s provider limit remains `UNKNOWN`. Credentials are read transiently from approved environment-variable names and are never persisted. Provider HTTP 429, 5xx, timeout, authentication, and transport failures remain explicit terminal provider failures with zero automatic retries.

Mission 025 resume semantics remain active. Existing terminal raw artifacts are validated by run ID, configuration hash, participant revision, manifest identity, and artifact filename. A resume consumes only missing manifests and never reruns a terminal run ID. Mission 028 completed 180 terminal artifacts after one interruption, including one explicit NVIDIA HTTP 502 failure.

After all terminal artifacts exist, participant evidence crosses the Mission 022 compatibility boundary and only Mission 010’s calculator may generate metrics. The completed run generated 38 canonical results. No Gemini, Bright Data, healing, approval, commit, rollback, or alternative metric calculator was invoked.

## Mission 028 recovery preservation contract

The first attempt `mission_028_floor_00c77f2abd976a10` is an invalidated, non-reproducible incident record and cannot be reused. Recovery derives `mission_028_recovery_floor_4812160675146552` from the same frozen configuration hash, a distinct recovery attempt identifier, and the frozen participant revisions.

`BenchmarkExecutor` accepts an explicit `runs_root`. Production recovery supplies the canonical repository benchmark root; TEST_DOUBLE tests supply a temporary root explicitly. Test cleanup is permitted to remove only the temporary root and must never resolve to the production recovery root. The recovery artifact hash manifest records SHA-256 for every raw file and all run artifacts.

The recovery gate passes only when the new root is absent before trial 1, the old run identity is not reused, and all existing terminal artifacts are resumable without rerun. After completion, the root is immutable for release validation: raw-file count and aggregate hashes must remain unchanged through the full test suite. Metrics remain blocked until all 180 terminal artifacts exist, then only Mission 010 may run.

## Mission 029 — Bright Data live-demo failure contract

`BrightDataCliAdapter` preserves collection mode and operation identifiers from the combined stdout/stderr provider trace, because the live CLI reported realtime-to-batch fallback and batch job identity on stderr. The original raw operation envelope remains immutable; reconciliation emits separate `*_reconciled.json` evidence with `provider_operations_executed_by_correction=0`.

The Mission 029 live orchestration boundary may create one collector, run one collector, and submit one heal. If healing exits non-zero or no candidate is normalized, it emits a terminal `FAILED_BEFORE_CANDIDATE` record. That record contains the original `HealHandle`, redacted provider failure, zero retry, zero approval, zero production commit, and null candidate/verification/risk/commit identifiers. No code may fabricate a `RepairCandidate`, `VerificationResult`, `RiskDecision`, or `CommitDecision` after this terminal failure.

## Mission 030 — Compact Bright Data heal prompt contract

`build_bright_data_heal_prompt` is a deterministic provider-transport projection of an immutable `RepairRequest`; it is not a replacement RepairRequest and it does not authorize state change. It emits policy version, exact prompt text, character length, SHA-256, configured limit, and `within_limit`. The projection preserves target, objective, affected fields, required schema/types, relevant invariants, unaffected required fields, and explicit no-approval/no-commit/no-shipment constraints while excluding raw rows and verbose evidence payloads. `BrightDataCliAdapter` accepts `heal_prompt_limit`; an over-limit projection raises `HEAL_BLOCKED_PROVIDER_PROMPT_LIMIT` before a runner or provider operation is created.

`mission030_validate_heal.py` is replay-safe. Before `--live`, it records a zero-operation preflight. With `--live`, it permits at most one external heal submission, records the redacted provider envelope, and writes a terminal result. A candidate remains `UNVERIFIED` if normalized. If no candidate exists, candidate/verification/risk/commit identifiers remain null and no downstream record is fabricated. A completed terminal artifact replays locally rather than making a second provider call.

`Mission029ArtifactLoader` is read-only. It validates the committed artifact bundle for schema, identity, safe HTTPS target, consistent row count, and sensitive keys; it raises an explicit load error on missing, malformed, inconsistent, or unsafe evidence. It must never contact a provider or invent candidate, verification, risk, or commit state.

## Mission 031 — Judge Mode snapshot and demo-session contract

`scripts/mission031_build_demo_snapshot.py` creates `experiments/mission_031/judge_mode_snapshot.json` only from committed Mission 029/030 artifacts, the frozen Mission 028 recovery run, and the deterministic `VerificationFixture.SILENT_CORRUPTION` test double. It performs zero provider, benchmark, NVIDIA, Gemini, approval, commit, or rollback operations. It validates input shape and redaction, records source SHA-256 values, preserves the terminal real-provider lane, and separates it from the `TEST_DOUBLE_CONTROLLED_REPLAY` lane.

The real-provider lane may report `HEAL_FAILED_BEFORE_CANDIDATE` only when its terminal Mission 030 artifact supplies the status. The controlled replay must contain `mode=TEST_DOUBLE_CONTROLLED_REPLAY`, `candidate.provenance=TEST_DOUBLE`, a prominent non-provider disclaimer, and deterministic verification/risk/commit data derived through the existing modules. It cannot be represented as a candidate emitted by Bright Data.

`scripts/run_demo.py` defaults to `REPLAY_READY`. It writes `demo_session.json` with zero external-operation counters and the Judge Mode launch instruction. Its `--live` branch returns `BLOCKED_PROVIDER_AUTHORIZATION_REQUIRED` and exits without calling a provider. A future live mode must implement and record the documented G1–G5 authorization gates before it can create, run, or heal a collector.
