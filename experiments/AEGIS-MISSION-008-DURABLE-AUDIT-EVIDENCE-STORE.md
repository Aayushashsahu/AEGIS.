# AEGIS Mission 008 — Durable Audit / Evidence Store + Read-Only History

**Date:** 2026-08-17
**Status:** **COMPLETE for the lightweight local durable persistence boundary**
**Scope:** Persist evidence-bearing AEGIS records in a redacted append-only SQLite store and expose read-only status/history queries around the existing immutable domain objects.
**Explicitly out of scope:** Provider rollback, automatic repair, memory learning, mutation lab, benchmark execution, frontend/dashboard, distributed infrastructure, and production deployment claims.

> **AI proposes. Evidence decides.**

## Mission result

Mission 008 adds a provider-neutral infrastructure boundary around the canonical AEGIS records:

```text
Immutable domain record
    → redacted AuditEvent envelope
    → append-only SQLiteAuditStore
    → read-only get/history/current_status queries
```

The domain models remain canonical. The store does not redesign them, update them in place, delete them, mutate evidence, or execute lifecycle actions. Corrections are represented as new events that may reference a prior event ID.

## 1. Technology choice

The canonical technology document leaves storage open and requires append-friendly, queryable lifecycle records. The workspace has no project dependency manifest and no selected distributed database. Mission 008 therefore uses Python’s standard-library `sqlite3` module as the smallest durable implementation compatible with the existing modular monolith and test environment.

This is a local durable boundary, not a production deployment decision. No PostgreSQL, Redis, event broker, ORM, container, or cloud storage dependency was introduced.

## 2. AuditEvent envelope

Every stored event contains:

| Field | Meaning |
| --- | --- |
| `event_id` | Opaque unique event identifier. |
| `event_type` | Typed event category for observation, detection, diagnosis, repair request, candidate, verification, risk, commit, quarantine, watch, regression, or evidence reference. |
| `aggregate_id` | Entity or lifecycle aggregate reference used for read queries. |
| `correlation_id` | Episode/request/watch correlation reference. |
| `timestamp` | UTC ISO-8601 creation timestamp. |
| `provenance` | `BRIGHT_DATA`, `TEST_DOUBLE`, or other explicit provenance string. |
| `schema_version` | Store envelope version, currently `1`. |
| `payload` | Recursively immutable, redacted normalized domain payload. |
| `evidence_refs` | Immutable evidence reference tuple. |

The stored payload is redacted before serialization. Keys matching API key, authorization, cookie, credential, password, secret, token, or private-key categories are replaced. Bearer-style and common key-shaped values are also redacted. The store never persists credentials, API keys, authorization headers, or unrestricted secret-bearing provider logs.

## 3. Append-only boundary

`SQLiteAuditStore.append_event(event)` inserts a new row and commits it. The SQL table has an immutable primary key on `event_id`; a duplicate event ID raises an append-only conflict instead of replacing the existing row. The public store has no update or delete operation.

A correction is represented by a new event, for example:

```text
original VERIFICATION(status=INCONCLUSIVE)
    → new VERIFICATION(status=PASS, corrects_event_id=original.event_id)
```

The original event remains queryable and unchanged. Read envelopes are recursively immutable in memory, so callers cannot mutate the returned payload or evidence references.

## 4. Persisted event coverage

The store provides convenience appenders for the records currently produced by Missions 001–007:

| Event category | Current append operation |
| --- | --- |
| Observation | `append_observation` |
| Detection | `append_detection` |
| Diagnosis | `append_diagnosis` |
| RepairRequest | `append_repair_request` |
| RepairCandidate | `append_candidate` |
| VerificationResult | `append_verification` |
| RiskDecision | `append_risk_decision` |
| CommitDecision | `append_commit_decision` |
| QuarantineRecord | `append_quarantine` |
| WatchRegistration | `append_watch_registration` |
| WatchCycle | `append_watch_cycle` |
| WatchResult | `append_watch_result` |
| RegressionEvent | `append_regression` |
| Evidence reference | `append_evidence_reference` |

Earlier records are supported at the infrastructure boundary without requiring an application-wide persistence rewrite in this mission.

## 5. Read-only history/status interface

The query surface is intentionally read-only:

```text
get_event(event_id)
history(aggregate_id=?, correlation_id=?, event_type=? )
current_status(aggregate_id)
```

`history` returns immutable events ordered by timestamp and insertion row. `current_status` reports the latest event-derived status, latest event ID/type, correlation ID, event count, and latest evidence references. Missing aggregates return `NOT_FOUND` with zero event count. There is no query method that writes, updates, deletes, or releases records.

## 6. Durability evidence

Tests create an on-disk SQLite database, append an event, close the store, reopen it, and recover the same event by aggregate and correlation queries. This demonstrates local file durability for the selected implementation. It is not a production durability, availability, backup, replication, or deployment claim.

## 7. Tests and results

The full suite was run with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
89 passed in 0.26s
```

Mission 008 tests cover on-disk reopen durability, append-only duplicate rejection, absence of update/delete interfaces, recursive payload immutability, secret redaction before persistence, aggregate/correlation/type queries, latest status reads, convenience appenders for Mission 006–007 records, correction-by-new-event semantics, and no new lifecycle side effects.

## 8. Safety checks

No provider rollback, automatic repair, memory learning, mutation laboratory, benchmark, frontend, distributed database, or provider operation was added. The store does not execute model output, approval commands, or downstream production writes. Secret-pattern scanning of implementation, tests, and the Mission 008 report found no credentials.

## 9. Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/audit_store.py` | Added SQLite audit envelope, redaction, append-only insert boundary, convenience appenders, and read-only queries. |
| `src/aegis/__init__.py` | Exported Mission 008 audit-store interfaces. |
| `tests/unit/test_mission008.py` | Added seven durability, immutability, redaction, query, and domain persistence tests. |
| `experiments/AEGIS-MISSION-008-DURABLE-AUDIT-EVIDENCE-STORE.md` | Added this evidence report. |
| `docs/07_METRICS.md` | Mission 008 persistence/metric evidence note. |
| `docs/11_API_CONTRACTS.md` | Audit store and read-only query contracts. |
| `docs/12_DATA_MODEL.md` | AuditEvent and persisted read-model boundary. |
| `docs/13_DECISION_LOG.md` | Mission 008 storage decision. |
| `docs/16_TESTING_STRATEGY.md` | Mission 008 persistence and safety test evidence. |
| `docs/18_BRIGHT_DATA_INTEGRATION.md` | Explicit provider-neutral persistence boundary; provider unknowns unchanged. |

## 10. Limitations and unresolved decisions

The implementation is local SQLite and currently uses an in-memory connection by default for isolated tests. Production path selection, backup/retention policy, encryption at rest, multi-process coordination, migration tooling, evidence object storage, and operational deployment remain open decisions. Raw provider payloads are not persisted automatically; the store receives redacted normalized payloads and evidence references.

Mission 008 does not claim provider-native rollback, Bright Data production durability, or benchmark results. The existing Bright Data capability labels remain unchanged.

## Exact recommended Mission 009

Mission 009 should add the **read-only audit/history API adapter and evidence export/redaction contract** around `SQLiteAuditStore`: expose status/history query objects without adding mutation routes, produce a deterministic redacted audit export for demo/evidence review, define retention and migration checks, and preserve the append-only invariant. Do not add provider rollback, automatic repair, memory learning, or benchmark execution automatically.
