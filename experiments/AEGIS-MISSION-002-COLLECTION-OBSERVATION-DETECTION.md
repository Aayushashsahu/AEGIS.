# AEGIS Mission 002 — Collection → Observation → Detection

**Date:** 2026-08-17  
**Status:** **COMPLETE for the defined vertical slice**  
**Scope:** Bright Data adapter boundary, asynchronous collection state, immutable untrusted Observation, typed ExtractionContract, deterministic schema/statistical/semantic detection, and labeled `TEST_DOUBLE` coverage.  
**Explicitly out of scope:** Healing implementation, LLM diagnosis, repair candidates, candidate verification, risk governor, rollback, memory, mutation benchmark, frontend, and dashboard.

> **AI proposes. Evidence decides.**

## Mission result

Mission 002 implements the first real AEGIS vertical slice:

```text
Bright Data collection boundary
    → asynchronous collection state
    → immutable untrusted Observation
    → deterministic ExtractionContract evaluation
    → schema/statistical/semantic DetectionResult
```

The implementation does not scatter provider commands through the application. The `BrightDataCliAdapter` is the single provider boundary for the verified Mission 001 CLI path. It supports injected command execution for tests, returns immediately from `run_collector`, preserves provider identifiers and evidence references, records observed realtime-to-batch fallback, and classifies bounded timeout/failure outcomes. The adapter does not approve healing, commit candidates, verify repairs, or resolve provider rollback.

Observations are frozen dataclasses with recursively immutable input/output mappings, explicit `UNTRUSTED_UNTIL_VERIFIED` status, provider provenance, row count, schema, latency, mode, operation identifiers, and evidence references. A completed collection is required before an Observation can be created; timed-out and failed collections cannot become healthy Observations.

The deterministic detection path contains three channels:

| Channel | Implemented checks |
| --- | --- |
| Schema | Missing required fields, unexpected fields, unexpected nulls, and invalid types. |
| Statistical | Minimum/maximum row counts, expected row-count drift, non-finite numeric values, and numeric bounds. |
| Semantic/invariant | HTTP(S) URL validity, non-negative `points` and `comment_count`, and a simple title/author relationship invariant. |

No LLM is used by Mission 002. Every detector returns structured `DetectionSignal` evidence, and the orchestrator returns an immutable `DetectionResult` containing severity, affected fields, evidence references, and detector provenance.

## Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/adapter.py` | Added the narrow Bright Data CLI adapter seam, command runner injection, asynchronous job tracking, bounded polling, status transitions, realtime-to-batch observation, output parsing, and provider evidence references. |
| `src/aegis/contracts.py` | Added the default ExtractionContract and deterministic contract checks. |
| `src/aegis/detection.py` | Added deterministic three-channel detection orchestration. |
| `src/aegis/immutability.py` | Added recursive freezing/thawing helpers for JSON-like values. |
| `src/aegis/models.py` | Added collection states/modes, provider provenance, collector/collection/result/observation contracts, field contracts, detection signals, and immutable result models. |
| `src/aegis/test_double.py` | Added deterministic, explicitly labeled `TEST_DOUBLE` scenarios: `HEALTHY`, `MISSING_FIELD`, `TYPE_CORRUPTION`, `STATISTICAL_DRIFT`, `SEMANTIC_CORRUPTION`, and `TIMEOUT`. |
| `src/aegis/__init__.py` | Replaced the initialization-only placeholder with the Mission 002 public interface. |
| `tests/unit/test_mission002.py` | Added 11 unit tests for detection, safe timeout behavior, mode/provenance preservation, immutability, and CLI adapter parsing. |
| `tests/integration/test_mission001_artifact_to_observation.py` | Added one integration test that converts the recorded Mission 001 Bright Data output into a Bright Data-provenance untrusted Observation and evaluates it deterministically. |
| `README.md` | Updated the quick start and implementation-status text without claiming later missions. |

No canonical architecture, metric formula, severity taxonomy, or safety invariant was changed.

## Tests and results

The following command passed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
12 passed in 0.04s
```

The source and test trees also passed Python bytecode compilation:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

The final validation found no secret-pattern matches in `src/` or `tests/`, and no unrequested healing, verification, risk, rollback, memory, benchmark, frontend, dashboard, LLM, or candidate-commit implementation classes or operations.

## Real Bright Data path used

The real-provider path uses the provider behavior verified in Mission 001, without repeating the capability spike. The adapter constructs the documented CLI shape internally and accepts an injected command runner:

```text
create_collector(request)
run_collector(collector, target_url, mode, timeout_seconds)
poll_collection(handle)
retrieve_output(handle)
```

The committed Mission 001 collection artifact was used in the integration test:

- Collector ID: `c_msx16nef2jck24ag94`
- Provider provenance: `BRIGHT_DATA`
- Observed mode: `BATCH`, after the CLI’s observed realtime-to-batch fallback
- Row count: `59`
- Evidence: `experiments/mission_001_collection_output.json` and `mission_001_collection_metadata.json`

The real artifact is not treated as healthy merely because it contains JSON. The test found deterministic schema evidence because the observed output contains rows missing the contract-required `points` field and includes an `input` field outside the initial contract. This is a correct safety outcome: the Observation is recorded as untrusted and detection raises an alarm.

This test does not re-run Bright Data, claim a new live platform result, or claim candidate verification. The provider session and credentials remain outside source code and test fixtures.

## Test-double path used

`DeterministicBrightDataTestDouble` uses only local, fixed data and is labeled `ProviderProvenance.TEST_DOUBLE` and `CollectionMode.TEST_DOUBLE`. It does not call Bright Data and cannot support a Bright Data capability claim. Its scenarios are deterministic and allow the detector tests to exercise missing fields, type corruption, statistical drift, semantic invalidity, healthy output, and bounded timeout behavior without consuming provider credits.

## Known limitations

Mission 002 intentionally does not implement the healing path, LLM diagnosis, repair candidates, candidate verification, risk decisions, commit gates, quarantine store, rollback, repair memory, mutation lab, benchmark runner, or UI. These remain later missions.

The CLI adapter’s parser is bounded to the response/log shapes observed in Mission 001. It records response and batch identifiers when present, but it does not claim that every Bright Data operation exposes the same identifiers. Provider-native version/rollback and raw-response/WARC access remain unresolved exactly as documented in Mission 001.

The statistical detector currently supports explicit contract bounds and expected row counts; it does not infer historical distributions or automatically establish baselines. The semantic detector is intentionally simple and deterministic; it does not claim to catch general silent semantic corruption. L5 detection and shipment safety require the later controlled mutation and verification missions.

The real-provider adapter uses an injected runner in tests. No test invokes the live provider, and no credentials are required to run the test suite. A production process still needs a secret-store/environment configuration decision, provider retry policy, durable persistence, and a real evidence-store implementation.

## Acceptance criteria

| Criterion | Result |
| --- | --- |
| Collection represented through adapter | PASS |
| Real recorded collection result becomes Observation | PASS |
| Test-double result becomes Observation | PASS |
| ExtractionContract evaluation works | PASS |
| Schema detection works | PASS |
| Statistical detection works | PASS |
| Semantic/invariant detection works | PASS |
| Healthy test-double observation has no false alarm | PASS |
| Provider/test-double timeout fails safely | PASS |
| Realtime/batch mode is preserved | PASS |
| Observation is immutable | PASS |
| Tests pass | PASS — 12 passed |
| No benchmark results fabricated | PASS |
| Unresolved Bright Data capabilities remain unresolved | PASS |

## Next recommended mission

Mission 003 should implement the smallest **Detection → Diagnosis → Repair request boundary** only after the owner accepts this Mission 002 evidence. It may use the existing `TEST_DOUBLE` lifecycle to define structured diagnosis and repair-request records, but it must not add candidate verification or commit behavior until the verification mission is separately scoped. The next mission must preserve the same fail-closed timeout behavior, evidence provenance, and distinction between provider output and AEGIS trust decisions.
