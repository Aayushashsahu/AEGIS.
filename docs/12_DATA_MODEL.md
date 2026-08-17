# 12 — Data Model

**Status:** Logical model; physical storage technology is an open decision.  
**Identifiers:** Opaque UUID/ULID-like identifiers; no business meaning encoded in IDs.  
**Retention:** Preserve benchmark and safety evidence through submission review; final production retention requires owner policy.

## Entity catalog

| Entity | Purpose | Key relationships | Lifecycle |
| --- | --- | --- | --- |
| Collector | Identifies a Bright Data/custom collection definition. | Has contracts and collections. | REGISTERED → ACTIVE → RETIRED |
| ExtractionContract | Defines expected fields, types, invariants, units, and evidence rules. | Belongs to collector; used by detection/verification. | DRAFT → FROZEN → SUPERSEDED |
| Collection | One execution request/result envelope. | Belongs to collector; has observation. | REQUESTED → RUNNING → SUCCEEDED/FAILED/TIMED_OUT |
| Observation | Immutable extracted output and evidence snapshot. | Belongs to collection; evaluated by detection. | RECORDED → EVALUATED |
| DetectionEvent | Anomaly or healthy evaluation outcome. | References observation and findings. | OPEN → DIAGNOSED/CLOSED |
| Diagnosis | Failure class and structured repair request. | Belongs to detection event; creates repair attempts. | CREATED → SUBMITTED → RESOLVED |
| RepairAttempt | One provider healing attempt. | Belongs to diagnosis; yields candidates. | STARTED → POLLING → SUCCEEDED/FAILED/TIMED_OUT |
| RepairCandidate | Proposed repaired collector/version/output. | Belongs to attempt; has verification runs and decision. | PROPOSED → VERIFIED/REJECTED → COMMITTED |
| VerificationRun | Channel-level evidence evaluation. | Belongs to candidate; references observations. | RUNNING → PASSED/FAILED/INCONCLUSIVE |
| RiskDecision | Safety decision for candidate/episode. | References verification; may create quarantine/escalation. | RECORDED → EXECUTED |
| WatchCycle | Post-commit validation. | Belongs to commit/version. | SCHEDULED → PASSED/REGRESSION/FAILED |
| RollbackEvent | Evidence and outcome of restoration. | References regression, prior/current versions. | STARTED → SUCCEEDED/FAILED |
| RepairEpisode | Aggregate audit record for one anomaly-to-outcome journey. | Links all lifecycle entities. | OPEN → TERMINAL |
| Mutation | Seeded laboratory change with ground truth. | Used by benchmark trials. | DEFINED → INJECTED → RESET |
| BenchmarkRun | One reproducible experiment set. | Has trial results and metric results. | CREATED → RUNNING → COMPLETE/INVALID |
| MetricResult | Formula output with numerator/denominator and provenance. | Belongs to benchmark run and spec version. | CALCULATED → REVIEWED |

## Field contracts

### Collector

`collector_id` (ID, required, unique), `name` (string), `provider` (enum; Bright Data or test double), `provider_reference` (redacted string), `status`, `created_at`, `updated_at`, `version`. Provider credentials are never stored in this entity.

### ExtractionContract

`contract_id`, `collector_id`, `version`, `status`, `fields` (array of field definitions), `entity_key`, `allowed_units`, `null_policy`, `deterministic_channels_required` (minimum 2 for commit), `semantic_invariants`, `effective_at`, `created_at`. Frozen contracts are immutable.

### Collection and Observation

Collection includes `collection_id`, `collector_id`, `contract_id`, `mode`, `requested_at`, `started_at`, `completed_at`, `provider_run_reference`, `status`, `error_code`, and `correlation_id`. Observation includes `observation_id`, `collection_id`, `raw_output_ref`, `normalized_output`, `response_fingerprint`, `raw_response_ref`, `collected_at`, `evidence_manifest_ref`, and `trust_status`. Output remains untrusted until verification.

### DetectionEvent and Diagnosis

DetectionEvent includes `event_id`, `observation_id`, `event_type`, `severity`, `channel_findings`, `confidence` (diagnostic signal only), `opened_at`, `closed_at`, and `episode_id`. Diagnosis includes `diagnosis_id`, `event_id`, `failure_class`, `evidence_refs`, `repair_request`, `model_assistance` (optional metadata, not authority), `created_at`, and `status`.

### RepairAttempt and RepairCandidate

RepairAttempt includes `repair_id`, `diagnosis_id`, `attempt_number`, `provider_operation_ref`, `request_payload_ref`, `started_at`, `deadline`, `completed_at`, `status`, `retryable`, `cost`, and `latency_ms`. RepairCandidate includes `candidate_id`, `repair_id`, `candidate_version_ref`, `candidate_output_ref`, `created_at`, `status`, and `provider_evidence_ref`.

### VerificationRun and RiskDecision

VerificationRun includes `verification_id`, `candidate_id`, `channels`, `channel_results`, `deterministic_pass_count`, `semantic_assessment`, `unresolved_findings`, `started_at`, `completed_at`, `status`, and `eligible_for_commit`. RiskDecision includes `decision_id`, `candidate_id`, `decision`, `reason_code`, `verification_ids`, `retry_number`, `actor`, `created_at`, and `executed_at`.

### WatchCycle and RollbackEvent

WatchCycle includes `watch_id`, `commit_id`, `scheduled_at`, `collection_id`, `validation_results`, `status`, and `regression_event_id`. RollbackEvent includes `rollback_id`, `episode_id`, `from_version`, `to_known_good_version`, `trigger_evidence_refs`, `started_at`, `completed_at`, `status`, and `post_rollback_validation_id`.

### RepairEpisode

`episode_id`, `pipeline_id`, `initial_observation_id`, `detection_event_ids`, `diagnosis_ids`, `repair_ids`, `candidate_ids`, `verification_ids`, `decision_ids`, `watch_ids`, `rollback_ids`, `mutation_id`, `outcome`, `latency_ms`, `cost`, `llm_call_count`, `opened_at`, `closed_at`, and `audit_version`. Episodes are append-linked; no evidence is deleted to simplify a summary.

### Mutation, BenchmarkRun, MetricResult

Mutation includes the manifest fields in `05_MUTATION_TAXONOMY.md`, plus `fixture_version`, `seed`, `truth_ref`, and reset status. BenchmarkRun includes `run_id`, `manifest_version`, `code_revision`, `environment_ref`, `seed_set_ref`, `baseline_versions`, `started_at`, `completed_at`, `status`, `invalid_reason`, and artifact root. MetricResult includes metric name/spec version, scope, numerator, denominator, value/status, target, run references, and calculated timestamp.

## Constraints and indexes

Every foreign key must point to an existing immutable or versioned record. Unique constraints apply to collector name/version, contract version, mutation ID/fixture version, benchmark run ID, and metric result scope/spec version. Index by `correlation_id`, `pipeline_id`, `episode_id`, `collector_id`, `status`, `severity`, `mutation_id`, `benchmark_run_id`, and timestamps. Raw evidence references must point to content-addressed or versioned artifacts where possible.

## ER-style relationship description

```text
Collector 1──N ExtractionContract
Collector 1──N Collection
Collection 1──1 Observation
Observation 1──N DetectionEvent
DetectionEvent 1──1 Diagnosis
Diagnosis 1──N RepairAttempt
RepairAttempt 1──N RepairCandidate
RepairCandidate 1──N VerificationRun
RepairCandidate 1──N RiskDecision
RepairCandidate 0──1 Commit
Commit 1──N WatchCycle
WatchCycle 0──1 RollbackEvent
RepairEpisode 1──N lifecycle records
Mutation 1──N BenchmarkTrial (implementation sub-entity)
BenchmarkRun 1──N BenchmarkTrial
BenchmarkRun 1──N MetricResult
```

## Retention and deletion

Benchmark raw runs, mutation truth, safety failures, and submission artifacts must be retained through final review. Secrets, transient provider tokens, and unnecessary personal data must never enter the model. If a retention policy requires deletion, delete only according to an approved policy while preserving aggregate audit references and documenting the deletion.

## Mission 003 logical additions — Diagnosis and RepairRequest

Mission 003 adds the following immutable logical records without changing the existing lifecycle authority:

| Entity | Required fields | Lifecycle / safety boundary |
| --- | --- | --- |
| `DiagnosisContext` | `observation`, `detection`, `contract`, `detection_id`, `evidence_refs`, `correlation_id` | Typed input only; arbitrary provider logs are excluded. |
| `Diagnosis` | `diagnosis_id`, `observation_id`, `detection_id`, `correlation_id`, `failure_class`, `candidate_classes`, `severity`, `affected_fields`, `evidence_references`, `detector_provenance`, `rationale`, `certainty`, `diagnosis_provenance`, `timestamp`, `status` | `CREATED → REPAIR_REQUESTED`; no candidate or commit transition. |
| `RepairRequest` | `repair_request_id`, `collector_reference`, `observation_id`, `diagnosis_id`, `detection_id`, `correlation_id`, `affected_fields`, `failure_class`, `severity`, `extraction_contract`, `evidence_references`, `target_input`, `repair_objective`, `constraints`, `mutation_context`, `provenance`, `timestamp`, `status` | Terminal Mission 003 intent state `REPAIR_REQUESTED`; provider-neutral and immutable. |
| `RepairAttemptHandle` | `attempt_id`, `repair_request_id`, `status`, `provenance`, `provider_operation_reference`, `execution_started`, `timestamp` | Mission 003 acknowledgement only; `execution_started` must remain false. |

Certainty is qualitative (`DETERMINED`, `AMBIGUOUS`, `UNKNOWN`) rather than an additive score. Correlated detector signals are not converted into independent confidence weights. Unknown or conflicting patterns preserve bounded candidate classes but select `UNKNOWN`.

The Mission 003 records retain correlation IDs, source detection IDs, evidence references, provider/test-double/model provenance, and timestamps. Physical persistence and append-only audit storage remain open implementation decisions.
