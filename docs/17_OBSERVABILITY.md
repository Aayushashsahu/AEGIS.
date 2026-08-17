# 17 — Observability

**Goal:** Make every reliability decision explainable from events, evidence, and state.  
**Constraint:** Observability must not become a generic dashboard project.

## Correlation model

Every collection, observation, detection event, diagnosis, repair attempt, candidate, verification, decision, commit, watch cycle, rollback, mutation trial, and benchmark run carries a correlation ID. Child operations preserve the parent episode ID and create operation IDs for provider calls. Timestamps are UTC and monotonic duration measurements are recorded where possible.

## Pipeline observability

Record current state, last collection, last healthy observation, active anomaly, repair count, verification count, rollback count, current risk, active version, last known-good version, and quarantine status. The minimum product-facing surface exposes only safe, relevant status; raw content and secrets remain restricted.

## Repair observability

Record diagnosis class, evidence references, request hash, provider operation reference, candidate count, candidate status, verification channel results, latency, cost, model-call count, retry number, risk decision, and final outcome. A provider timeout is distinguishable from a candidate rejection and from an evidence insufficiency decision.

## Benchmark observability

Record mutation ID/severity, fixture version, seed, baseline, code revision, environment, model/configuration, trial outcome, shipment status, numerator/denominator inputs, and metric outputs. Invalid runs remain visible with an invalid reason but are excluded from headline metrics.

## Events

Canonical event names are:

```text
CollectionRequested
CollectionCompleted
ObservationRecorded
DetectionEvaluated
AnomalyDetected
DiagnosisCreated
RepairRequested
RepairCandidateReceived
VerificationCompleted
RiskDecisionRecorded
CandidateCommitted
QuarantineEntered
WatchCycleCompleted
RegressionDetected
RollbackStarted
RollbackCompleted
RepairEpisodeClosed
MutationInjected
MutationReset
BenchmarkRunStarted
BenchmarkRunCompleted
MetricCalculated
```

Events are append-oriented and include schema version, actor, correlation ID, entity ID, state before/after, reason, evidence references, and redacted metadata.

## Logs, traces, and evidence

Use structured logs for operational facts and traces for cross-component timing. Raw HTML, response bodies, screenshots, and provider payloads belong in controlled evidence artifacts with redaction and access controls. The UI should link to evidence IDs rather than embed unbounded content.

## Alerts and debugging

Alert on provider timeout rate, detection failures, verification misses, blind commit attempts, quarantine spikes, rollback failures, missing evidence, benchmark invalidity, and secret-scan failures. Debugging begins with correlation ID, then episode timeline, then channel evidence, then provider operation trace. Avoid alerts for every expected quarantine; quarantine is a safety outcome, though rate changes should be visible.

## Operational dashboards

A minimal dashboard may show pipeline status, active episodes, recent decisions, benchmark run status, and the product output. It must not imply health based solely on non-empty output. Each green status requires a linked contract/detection evaluation and last verified timestamp.
