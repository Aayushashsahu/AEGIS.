# AEGIS Mission 007 — Post-Commit Watch + Regression Detection

**Date:** 2026-08-17
**Status:** **COMPLETE for the bounded post-commit watch slice**
**Scope:** Evaluate later observations after a future accepted/committed state, reuse the existing deterministic detection engine, identify `HEALTHY`, `REGRESSION`, or `UNKNOWN`, and route serious regressions into the existing `QuarantineLedger`.
**Explicitly out of scope:** Bright Data rollback, provider activation, repair, re-diagnosis, automatic retries, memory learning, mutation laboratory, benchmark execution, frontend/dashboard, and production commit.

> **AI proposes. Evidence decides.**

## Mission result

Mission 007 adds the post-commit watch boundary without pretending that provider-native rollback is available:

```text
TEST_DOUBLE committed eligibility
    → WatchRegistration
    → WatchCycle
    → existing evaluate_detection(Observation, ExtractionContract)
    → HEALTHY / REGRESSION / UNKNOWN
    → QuarantineLedger on serious regression
    → [later rollback or re-diagnosis remains deferred]
```

A repair that passed verification once is not assumed to remain healthy forever. A later observation is evaluated with the same deterministic schema, statistical, and semantic detection engine used before repair. The watch layer records evidence and state; it never repairs the collector or changes provider state.

## 1. Watch models

| Model | Purpose |
| --- | --- |
| `WatchRegistration` | Immutable registration containing pipeline reference, candidate reference, committed verification reference, AEGIS-level known-good version, expected extraction contract, correlation ID, watch policy, provenance, and state. Registration requires an existing `CommitDecision=ELIGIBLE`, passing verification, verified candidate, matching known-good reference, and matching correlation. |
| `WatchCycle` | Immutable cycle record containing cycle ID, pipeline reference, observation reference, detection reference, timestamp, status, evidence references, correlation ID, and provenance. |
| `WatchResult` | Immutable `HEALTHY`, `REGRESSION`, or `UNKNOWN` result with detection result, affected fields, severity, evidence, provenance, and correlation. |
| `RegressionEvent` | Immutable regression evidence containing regression ID, pipeline, candidate, watch cycle, failed evidence, affected fields, severity, timestamp, provenance, and correlation. |
| `WatchPolicy` | Bounded policy controlling evidence requirements and the minimum severity that creates a quarantine record. Missing optional evidence does not automatically quarantine. |

All models are recursively immutable at their boundaries. The input `Observation` is not changed by watch evaluation.

## 2. State machine

The valid watch state transitions are:

```text
COMMITTED → WATCHING
WATCHING → HEALTHY
WATCHING → REGRESSION
WATCHING → UNKNOWN
REGRESSION → QUARANTINED
```

There is no `ROLLBACK`, `REPAIR`, `RE-DIAGNOSIS`, `ACTIVATED`, or provider state transition in Mission 007. A registration can only be created from an already eligible AEGIS commit decision. Tests use an explicitly marked `TEST_DOUBLE` committed state; no production commit is faked.

## 3. Detection reuse

`WatchEngine.evaluate(...)` calls the existing `evaluate_detection(observation, expected_contract)` boundary. It does not duplicate schema, statistical, or semantic detector logic. Every returned `DetectionResult` is retained inside `WatchResult`, and its evidence references, affected fields, severity, and detector provenance flow into any `RegressionEvent`.

The watch layer interprets the existing result as follows:

| Existing detection result | Watch result |
| --- | --- |
| No deterministic signals and required observation evidence is present | `HEALTHY` |
| One or more deterministic signals | `REGRESSION` |
| Required watch evidence is unavailable | `UNKNOWN` |

`UNKNOWN` never becomes `HEALTHY`. The default policy does not quarantine an unknown result solely because optional evidence is absent; it preserves the unknown state for later review.

## 4. Regression behavior

A regression is a previously accepted extraction becoming unhealthy again. The current deterministic test double covers:

| Scenario | Detection evidence | Result |
| --- | --- | --- |
| `HEALTHY_AFTER_COMMIT` | No schema, statistical, or semantic signal | `HEALTHY` |
| `REGRESSION_SCHEMA` | Required `price` field disappears | `REGRESSION` + `L2` |
| `REGRESSION_SEMANTIC` | Numeric invariant becomes negative | `REGRESSION` + `L3` |
| `REGRESSION_STATISTICAL` | Row count exceeds the configured maximum | `REGRESSION` + `L3` |
| `UNKNOWN_EVIDENCE` | Observation evidence references are unavailable | `UNKNOWN`, no automatic quarantine |

For a serious regression at or above the policy threshold, `WatchEngine` creates a `RegressionEvent` and appends a `QuarantineRecord` through the existing Mission 006 `QuarantineLedger`. It does not create a second quarantine implementation. The quarantine record preserves the registration, committed verification, failed checks, evidence, candidate provenance, timestamp, and correlation linkage.

## 5. Quarantine integration

Regression quarantine uses `QuarantineLedger.record_watch_regression(...)` and `QuarantineRecord.from_watch_regression(...)`. The record is `OPEN` and retained as forensic evidence. The watch engine does not release it, repair it, re-diagnose it, or roll it back. Any future release representation must still re-enter verification before a future output-eligibility decision.

## 6. Test-double scenarios

All watch fixtures use `TEST_DOUBLE` provenance and a deterministic eligible baseline. The baseline itself is produced through the existing Mission 006 CommitGate rather than by directly fabricating a production commit. No fixture calls Bright Data.

## 7. Metric hooks

`WatchMetricHooks` records watch-result, regression, unknown, and watch-quarantine events for later calculation of `RegressionRate`, `WatchFailureRate`, and `UnsafeRefusalRate`. It does not run a benchmark or report production metrics. With no watch cycles, rates are `NOT_APPLICABLE`; after controlled fixture events they are `INSTRUMENTED_NOT_BENCHMARKED`.

The current implementation interprets `WatchFailureRate` as unknown watch results divided by watch cycles, and `UnsafeRefusalRate` as quarantined regressions divided by regression events. These are instrumentation definitions for later controlled measurement, not benchmark claims.

## 8. Tests and results

The full suite was run with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
82 passed in 0.23s
```

Mission 007 tests cover healthy post-commit observations, schema regression, semantic regression, statistical regression, unknown evidence, state transition guards, registration requirements, existing-detection reuse, QuarantineLedger integration, immutable records, unchanged Observations, metric hooks, no automatic repair, no provider rollback, no provider calls, and disabled-watch fail-closed behavior.

## 9. Safety checks

Python compilation and the existing full regression suite pass. Mission 007 contains no Bright Data call, approval command, provider activation, rollback method, repair method, re-diagnosis method, memory learning, benchmark execution, or production sink. It does not modify an Observation and does not override the existing RiskGovernor or CommitGate.

## 10. Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/watch.py` | Added immutable watch models, state machine, detection reuse, regression event, existing-ledger integration, and metric hooks. |
| `src/aegis/watch_double.py` | Added explicit Mission 007 `TEST_DOUBLE` watch scenarios. |
| `src/aegis/commit_gate.py` | Added watch-regression constructors and ledger recording through the existing quarantine boundary. |
| `src/aegis/__init__.py` | Exported Mission 007 watch and metric interfaces. |
| `tests/unit/test_mission007.py` | Added 11 watch, regression, quarantine, state, immutability, and safety tests. |
| `experiments/AEGIS-MISSION-007-POST-COMMIT-WATCH-REGRESSION.md` | Added this evidence report. |
| `docs/07_METRICS.md` | Added watch metric-hook interpretation. |
| `docs/11_API_CONTRACTS.md` | Added watch and regression internal contracts. |
| `docs/12_DATA_MODEL.md` | Added watch and regression logical records. |
| `docs/13_DECISION_LOG.md` | Added Mission 007 decision record. |
| `docs/16_TESTING_STRATEGY.md` | Added Mission 007 test evidence and safety boundary. |
| `docs/18_BRIGHT_DATA_INTEGRATION.md` | Preserved the unresolved provider rollback boundary. |

## 11. Unresolved provider capabilities

Provider-native rollback remains unverified/partial as documented in Mission 001. Mission 007 does not attempt to resolve it. A regression is only quarantined locally; no provider collector is rolled back, activated, or modified. Raw HTML/WARC capabilities, provider version identity, approval semantics, and candidate correctness remain at their prior canonical statuses.

## Exact recommended Mission 008

Mission 008 should implement the **durable audit/evidence store and read-only watch/quarantine history** around the current immutable in-memory records. It should persist WatchRegistration, WatchCycle, WatchResult, RegressionEvent, QuarantineRecord, CommitDecision, RiskDecision, and evidence references append-only; provide redacted status queries; and preserve the no-side-effect watch boundary. It must not implement provider rollback, automatic repair, memory learning, or benchmark execution automatically.
