# AEGIS Mission 005 — RepairCandidate → Verification → Risk Governor

**Date:** 2026-08-17
**Status:** **COMPLETE for the bounded trust-evaluation slice**
**Scope:** Evaluate an immutable `RepairCandidate` with deterministic contract, history, semantic/invariant, and independent-evidence channels, then emit an explicit `ACCEPT`, `REJECT`, or `QUARANTINE` `RiskDecision`.
**Explicitly out of scope:** Provider approval, `--auto-approve`, activation, production commit, rollback, post-commit watch, repair memory, benchmark execution, and frontend work.

> **AI proposes. Evidence decides.**

## Mission result

Mission 005 is the first AEGIS trust-evaluation slice. It proves that a provider proposal that merely returns valid-looking data is not automatically correct. The bounded lifecycle is:

```text
RepairCandidate + ExtractionContract + history + evidence
    → VerificationCheck × 4 conceptual channels
    → VerificationResult
    → RiskGovernor
    → ACCEPT / REJECT / QUARANTINE
    → [eligible for a later commit stage only]
```

`ACCEPT` means **accepted for future commit evaluation**, not production activation. No method in this mission calls Bright Data, executes the returned approval command, activates a collector, writes a production version, rolls back, starts a watch cycle, or commits data.

## Verification models

| Model | Purpose |
| --- | --- |
| `VerificationCheck` | Immutable channel-level result with check ID, candidate ID, category, `PASS`/`FAIL`/`UNKNOWN`, evidence references, provenance, timestamp, correlation ID, affected fields, criticality, and details. |
| `VerificationContext` | Typed input containing candidate output, frozen contract, optional observation history, optional independent evidence, correlation/evidence references, semantic expectations, source-correlation metadata, and an ignored auxiliary model opinion. |
| `VerificationResult` | Immutable verification run with verification ID, candidate ID, all checks, overall status, failed/unknown checks, evidence references, provenance, timestamps, and future-commit eligibility. |
| `IndependentEvidence` | Explicit distinct source/path with source group, rows, provenance, evidence references, and correlation ID. It is never inferred from the provider preview. |
| `RiskDecision` | Immutable deterministic policy result with decision, reason code, verification reference, evidence, provenance, and explicit `production_commit_performed=False`. |

Channel states are `PASS`, `FAIL`, and `UNKNOWN`. Unknown is preserved at channel level and cannot be silently rewritten as pass.

## Evidence channels

### Contract channel

The contract channel verifies that candidate output is a non-empty row sequence with the expected schema, required fields, exact field types, nullability, and configured unaffected-field preservation where matching history entities are available. A schema or type failure is critical and prevents acceptance.

### History channel

The history channel compares candidate entities and values against supplied known-good `Observation` records. It checks entity continuity and field-value continuity. If no history exists, it returns `UNKNOWN`; history is optional for acceptance when the required contract, semantic, and independent channels all pass. History is not treated as ground truth when absent.

### Semantic/invariant channel

The semantic channel verifies deterministic URL validity, numeric finiteness and bounds, simple relation invariants, and explicitly supplied semantic expectations. It does not infer broad semantic correctness from a model opinion. A semantic contradiction is a critical failure.

### Independent-evidence channel

The independent channel compares the candidate against a genuinely distinct supplied source/path. If no evidence is supplied, it returns `UNKNOWN`. If its source group is the same as the history source group, it returns `UNKNOWN` rather than double-counting correlated evidence. Entity or value disagreement is a critical failure.

## Deterministic policy

No additive confidence weights are used. There is no formula such as `0.2 + 0.2 + 0.3`. The policy is an explicit gate:

| Condition | Verification result | Risk decision |
| --- | --- | --- |
| Contract, semantic/invariant, and independent evidence pass; no critical failure | `PASS` | `ACCEPT`, eligible for a later commit stage only |
| Any deterministic contract/semantic/independent failure | `FAIL` | `REJECT` |
| Critical contradiction in independent evidence | `FAIL` | `REJECT` with `CRITICAL_CONTRADICTION` |
| Required evidence missing or unknown | `INCONCLUSIVE` | `QUARANTINE` with `UNKNOWN_EVIDENCE` or `INSUFFICIENT_EVIDENCE` |
| History missing but all required channels pass | `PASS`; history remains `UNKNOWN` | `ACCEPT`, because history is strengthening evidence rather than a required gate |
| Auxiliary LLM/model opinion says pass while deterministic evidence fails or is unknown | Deterministic result unchanged | `REJECT` or `QUARANTINE`; model output has no authority |

The required acceptance channels are exactly `CONTRACT`, `SEMANTIC_INVARIANT`, and `INDEPENDENT_EVIDENCE`. The `HISTORY` channel strengthens the decision when available but does not replace independent evidence.

## Mandatory L5 silent-corruption test

The deterministic `SILENT_CORRUPTION` fixture encodes:

```text
Expected price:   599
Candidate price:  29.99
```

The candidate preserves valid JSON shape, required schema, and numeric type. The contract channel therefore passes. The semantic channel fails because the explicit semantic expectation is violated, and the independent-evidence channel fails because the distinct evidence source reports `599`. The resulting verification is `FAIL`, and the Risk Governor emits `REJECT`. No production commit method exists, so the observed blind-commit count remains zero.

This is the intended safety behavior: structurally valid data can still be rejected as semantically wrong.

## Candidate fixtures

The local fixture factory is explicitly labeled `TEST_DOUBLE` and never claims Bright Data correctness or mutation-laboratory ground truth.

| Fixture | Intended result |
| --- | --- |
| `GOOD_CANDIDATE` | Required channels pass; Risk Governor returns `ACCEPT` for future commit evaluation. |
| `BAD_SCHEMA` | Contract fails; Risk Governor returns `REJECT`. |
| `BAD_SEMANTIC` | Simple types and schema pass, semantic invariants fail; Risk Governor returns `REJECT`. |
| `SILENT_CORRUPTION` | Schema/type pass, semantic and independent evidence fail; Risk Governor returns `REJECT`. |
| `MISSING_EVIDENCE` | Required independent evidence is unknown; Risk Governor returns `QUARANTINE`. |
| `CONTRADICTORY_EVIDENCE` | Independent evidence contradicts the candidate; Risk Governor returns `REJECT`. |
| `UNKNOWN_EVIDENCE` | History and independent evidence are unavailable; Risk Governor returns `QUARANTINE`. |

## Recorded Mission 001 artifact

The recorded Bright Data artifact is exercised as provider evidence, not ground truth. It enters the verifier as a `BRIGHT_DATA`/`UNVERIFIED` candidate. Without independent ground truth, the verifier does not accept it. This test does not prove candidate correctness and does not alter the provider collector.

## Risk Governor boundary

`RiskGovernor` accepts only a `VerificationResult`, candidate metadata, and an explicit policy. It has no provider adapter reference, approval method, activation operation, commit method, rollback method, watch method, or memory store. It cannot convert `UNKNOWN` into `PASS`, and it cannot override a deterministic failure.

`RiskDecision.ACCEPT` records `eligible_for_future_commit=True` and `production_commit_performed=False`. The later commit stage must still require its own commit gate, known-good version, authorization, and post-commit watch obligations.

## Metrics hooks

`SafetyMetricHooks` records verification-completed and risk-decision events so later metric calculation can use immutable event references. It does not run benchmarks or synthesize results. With no commit operation in Mission 005:

```text
blind_commit_count = 0
blind_commit_rate = 0.0 safety counter
blind_commit_rate_status = NOT_APPLICABLE (zero commit denominator)
```

The values above are implementation-state counters, not benchmark results or a claim about production history. Future benchmark runs must calculate canonical metrics from raw mutation-lab events according to `docs/07_METRICS.md`.

## Tests and results

The full suite was run with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
54 passed in 0.17s
```

Mission 005 coverage includes all four evidence channels, explicit unknown handling, optional history, correlated-source non-double-counting, deterministic L5 silent corruption, schema failure, semantic failure with valid types, missing evidence quarantine, contradictory evidence rejection, auxiliary model non-authority, immutable verification/risk records, zero blind-commit hooks, no provider approval, and the recorded Mission 001 provider-evidence path.

## Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/verification.py` | Added immutable verification context/check/result models and deterministic four-channel verifier. |
| `src/aegis/risk.py` | Added explicit `RiskGovernor`, `RiskDecision`, policy enums, and later-metric event hooks. |
| `src/aegis/verification_double.py` | Added explicit Mission 005 `TEST_DOUBLE` candidate/evidence fixtures. |
| `src/aegis/__init__.py` | Exported Mission 005 verification, risk, metric, and fixture interfaces. |
| `tests/unit/test_mission005.py` | Added 13 trust, L5, policy, immutability, and metric-hook tests. |
| `tests/integration/test_mission005_recorded_provider_candidate.py` | Added recorded Mission 001 provider-evidence integration coverage. |
| `experiments/AEGIS-MISSION-005-VERIFICATION-RISK-GOVERNOR.md` | Added this evidence report. |
| `docs/07_METRICS.md` | Mission 005 metric-hook interpretation. |
| `docs/11_API_CONTRACTS.md` | Verification and risk internal contract additions. |
| `docs/12_DATA_MODEL.md` | VerificationCheck, VerificationResult, RiskDecision, and metric-event fields. |
| `docs/13_DECISION_LOG.md` | Mission 005 policy decision. |
| `docs/16_TESTING_STRATEGY.md` | Mission 005 trust and L5 test evidence. |

## Known limitations

The verifier uses deterministic fixture evidence and controlled expectations; it does not establish live-site ground truth. The recorded Mission 001 artifact is provider evidence only. History continuity is currently in-memory and limited to the supplied observation set. Independent evidence requires an explicitly supplied distinct source/path; it is not automatically discovered. The semantic expectation map is bounded input, not a general semantic understanding system. No LLM call is required, and no model output has policy authority.

Ground-truth measurement, mutation-lab integration, durable evidence storage, candidate version comparison, provider-native version/rollback, commit execution, post-commit watch, and repair memory remain later work.

## Exact recommended Mission 006

Mission 006 should implement the **commit gate and quarantine ledger** around the existing `RiskDecision`: persist immutable verification/risk evidence, make `ACCEPT` eligible but not active, block all non-verified/unknown candidates from downstream output, record a known-good version before any future commit, and add a fail-closed commit boundary without invoking provider approval or rollback. Post-commit watch and rollback must remain separate later stages.
