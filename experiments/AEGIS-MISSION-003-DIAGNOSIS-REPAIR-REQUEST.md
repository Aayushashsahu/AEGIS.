# AEGIS Mission 003 — Detection → Diagnosis → Repair Request

**Date:** 2026-08-17
**Status:** **COMPLETE for the defined bounded slice**
**Scope:** Convert immutable `DetectionResult` evidence into immutable `Diagnosis` and provider-neutral `RepairRequest` records.
**Explicitly out of scope:** Bright Data healing execution, candidate retrieval, candidate verification, risk decisions, approval, commit, rollback, post-commit watch, repair memory, mutation benchmark, frontend, and dashboard.

> **AI proposes. Evidence decides.**

## Mission result

Mission 003 adds the next bounded lifecycle segment:

```text
Observation + DetectionResult + ExtractionContract
    → Diagnosis
    → RepairRequest
    → [no-execution boundary]
    → REPAIR_REQUESTED
```

The domain remains independent of Bright Data implementation details. A `RepairRequest` describes **what should be fixed** while preserving the extraction contract, unaffected fields, known invariants, target input, and evidence references. It does not contain provider endpoints, provider tokens, CLI commands, approval operations, or commit authority.

No provider-side healing was executed. The only repair boundary included in this mission is `NoExecutionRepairBoundary`, an explicitly bounded test double that returns a request acknowledgement with `execution_started=False` and no provider operation reference.

## Domain models

| Model | Purpose |
| --- | --- |
| `FailureClass` | Small extensible enum: `SCHEMA_DRIFT`, `STRUCTURAL_DRIFT`, `STATISTICAL_DRIFT`, `SEMANTIC_INVARIANT`, `SILENT_CORRUPTION`, `BEHAVIORAL_DRIFT`, `NETWORK_DRIFT`, and `UNKNOWN`. |
| `DiagnosisContext` | Typed input containing only immutable Observation, DetectionResult, ExtractionContract, detection ID, correlation ID, and explicit evidence references. |
| `Diagnosis` | Immutable diagnosis record with observation/detection references, failure class, candidate classes, severity, affected fields, evidence, detector provenance, qualitative certainty, rationale, origin, timestamp, and lifecycle status. |
| `RepairRequest` | Immutable provider-neutral repair intent preserving collector, observation, diagnosis, detection, contract, target input, affected fields, evidence, constraints, mutation context, provenance, and `REPAIR_REQUESTED` status. |
| `RepairAttemptHandle` | Provider-neutral acknowledgement record only. It cannot execute healing and has no candidate, approval, or commit transition. |

Certainty is qualitative rather than numeric: `DETERMINED`, `AMBIGUOUS`, or `UNKNOWN`. No additive confidence weights are used, and correlated evidence is not double-counted. Multiple or partially unknown evidence classes remain `UNKNOWN` with candidate classes and `AMBIGUOUS` certainty.

## Deterministic classification

The deterministic diagnostician maps known detection evidence codes as follows:

| Evidence pattern | Diagnosis |
| --- | --- |
| Missing, null, invalid-type, or unexpected field | `SCHEMA_DRIFT` |
| Explicit relocation/order/wrapper evidence | `STRUCTURAL_DRIFT` |
| Row-count, non-finite, or numeric-bound evidence | `STATISTICAL_DRIFT` |
| Invalid URL or failed local invariant | `SEMANTIC_INVARIANT` |
| Explicit field replacement, entity mismatch, decoy, or unit mismatch | `SILENT_CORRUPTION` |
| Explicit partial/pagination/lazy-load/timeout behavior | `BEHAVIORAL_DRIFT` |
| Explicit network/provider error evidence | `NETWORK_DRIFT` |
| Unmapped evidence or multiple classes without a safe single interpretation | `UNKNOWN` |

The classifier does not claim to diagnose general semantic corruption. It returns `UNKNOWN` or a bounded candidate-class set when the evidence is ambiguous.

## Diagnostician seams

`DeterministicDiagnostician` is the default implementation. `TestDoubleDiagnostician` runs the same bounded rules but marks `diagnosis_provenance=TEST_DOUBLE`. `StructuredModelDiagnostician` accepts an injected structured backend for future model use, validates the returned class and qualitative certainty against typed enums, and marks the result `MODEL_ASSISTED`. No model backend is required by the test suite, and no model output receives approval, commit, or provider-execution authority.

## Repair objective

For affected fields `author`, the generated objective is of the form:

> Restore extraction of author without changing the output schema, while preserving title, url, points, and comment_count.

The request additionally preserves the frozen ExtractionContract, known invariants, unaffected fields, target input, and evidence. An unknown diagnosis instead produces a bounded investigation objective and explicitly prohibits inferring an unobserved failure class.

## Recorded Bright Data integration path

The Mission 001 recorded 59-row Bright Data artifact was passed through the existing Mission 002 path without contacting Bright Data:

```text
recorded Bright Data output
    → Bright Data-provenance Observation
    → deterministic DetectionResult
    → deterministic Diagnosis
    → provider-neutral RepairRequest
    → no-execution acknowledgement
```

The provider provenance, collector ID, observation ID, evidence references, detection ID, correlation ID, affected fields, contract, and target input survive the transition. The integration test does not claim a live healing result.

## Safety boundary

Mission 003 cannot approve or commit a repair. No class or method creates a candidate, calls `bdata scraper heal`, calls `bdata scraper approve`, changes provider state, activates a version, or writes a commit decision. The furthest reachable state is `REPAIR_REQUESTED`. The no-execution boundary returns `execution_started=False` and `provider_operation_reference=None`.

## Tests and results

The following command passed without Bright Data credentials:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
26 passed in 0.07s
```

Mission 003 tests cover deterministic schema, statistical, semantic, silent-corruption, and unknown classification; ambiguity handling; affected-field extraction; evidence and provenance propagation; contract preservation; immutable RepairRequest construction; explicit `TEST_DOUBLE` provenance; injected structured-model seam; no-execution safety; healthy/no-diagnosis behavior; and the recorded Bright Data artifact integration path.

## Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/diagnosis.py` | Added immutable diagnosis and repair-request models, bounded failure classes, certainty/provenance/status enums, deterministic classifier, diagnostician protocol, model seam, and no-execution repair boundary. |
| `src/aegis/__init__.py` | Exported Mission 003 interfaces. |
| `tests/unit/test_mission003.py` | Added 13 unit tests for diagnosis, repair requests, ambiguity, provenance, model seam, and safety. |
| `tests/integration/test_mission003_recorded_artifact.py` | Added recorded Bright Data Observation → DetectionResult → Diagnosis → RepairRequest integration coverage without provider calls. |
| `experiments/AEGIS-MISSION-003-DIAGNOSIS-REPAIR-REQUEST.md` | Added this evidence report. |
| `docs/11_API_CONTRACTS.md` | Appended Mission 003 internal contract notes. |
| `docs/12_DATA_MODEL.md` | Appended Diagnosis, RepairRequest, and bounded attempt-handle logical fields. |
| `docs/13_DECISION_LOG.md` | Appended the Mission 003 decision. |
| `docs/16_TESTING_STRATEGY.md` | Appended Mission 003 test evidence and safety boundary. |
| `docs/18_BRIGHT_DATA_INTEGRATION.md` | Appended the provider-neutral request boundary and explicit no-execution status. |

The user-modified Mission 002 report was not overwritten; its current file is empty and remains an unresolved documentation-integrity issue to be handled by the project owner rather than silently reconstructed in this mission.

## Unresolved questions

The exact Bright Data healing request shape, polling/callback behavior, candidate retrieval, approval semantics, version identity, rollback operation, and raw evidence access remain the Mission 001 `UNKNOWN` or partial findings. Mission 003 does not change those labels.

The model seam still needs a selected model, prompt, structured-output configuration, timeout, and audit policy before use in a benchmark or production path. No such choices are invented here.

The lifecycle does not yet have a durable event store. Mission 003 preserves correlation IDs, timestamps, evidence references, and provenance in immutable records; persistence and append-only audit storage remain later implementation work.

## Exact recommended Mission 004

Mission 004 should implement the verified Bright Data healing adapter boundary only: translate `RepairRequest` into the documented authenticated CLI operation, persist an approval-gated provider attempt, poll asynchronously, and capture the returned candidate envelope without approving, verifying, activating, or committing it. Any missing provider behavior must remain `UNKNOWN`, and all candidate outputs must remain quarantined until the later verification and risk-governor mission.
