# AEGIS Mission 009 — Mutation Laboratory V1

**Date:** 2026-08-17
**Status:** **COMPLETE for the deterministic six-scenario harness floor**
**Scope:** Create known scraper failures with independent ground truth, drive the existing AEGIS collection/observation/detection/verification/risk/CommitGate path, and record immutable mutation/run evidence.
**Explicitly out of scope:** 540-run scaling, benchmark comparison, Bright Data capability changes, provider state modification, automatic repair, rollback, frontend/dashboard, and measured benchmark publication.

> **AI proposes. Evidence decides.**

## Mission result

Mission 009 introduces the first controlled adversarial proof surface:

```text
known baseline fixture
    → deterministic mutation(seed)
    → immutable MutationGroundTruth
    → TEST_DOUBLE Observation
    → existing evaluate_detection
    → existing verify_candidate
    → existing RiskGovernor
    → existing CommitGate / QuarantineLedger
    → immutable MutationRun
```

The mutation laboratory is the source of ground truth. Expected correct values are recorded independently from the mutated observation and are not inferred from AEGIS output.

## 1. Controlled staging strategy

The lab uses a local static `StagingFixture` rather than a public deployment. The fixture contains only public-looking test data and one canonical GPU product record:

```json
{
  "product_id": "gpu-1",
  "title": "DGX Spark",
  "price": 599,
  "availability": "in_stock",
  "rating": 4.8,
  "url": "https://example.test/gpu-1"
}
```

The baseline is fixture `gpu-price-staging` version `1`. Collection provenance is always `TEST_DOUBLE`; the harness does not represent Bright Data benchmark behavior. The extraction contract requires `product_id`, `title`, `price`, `availability`, `rating`, and `url`, with `price >= 0`, `0 <= rating <= 5`, one expected row, and valid URL/price invariants.

## 2. Mutation scenarios

| ID | Severity | Deterministic mutation | Affected field/state | Expected behavior |
| --- | --- | --- | --- | --- |
| `M001` | L1 | Rename an irrelevant CSS class token using the seeded RNG. | Presentation markup only. | Extraction remains correct; no detector alarm is expected. |
| `M002` | L2 | Remove the required availability field, representing a field node moved outside the target. | `availability` / schema. | Existing schema detection emits an L2 signal; verification/risk block the path. |
| `M003` | L3 | Change the canonical price to `-599`. | `price` / semantic numeric invariant. | Existing statistical/semantic detection emits an L3 signal; verification/risk block the path. |
| `M004` | L4 | Drop the complete deterministic page result, representing a pagination/lazy-loading failure. | Row count. | Existing statistical detection emits an L3 signal for an L4 ground-truth mutation; verification/risk reject incomplete output. |
| `M005` | L5 | Swap `price=599` to `price=29.99`. | `price` / semantic value. | Schema and numeric type remain valid; basic detection emits no signal, but history, semantic expectation, and independent ground truth make verification fail and RiskGovernor reject. |
| `M006` | L5 | Replace price with a deterministic plausible decoy in the `549.99–559.99` range. | `price` / semantic value. | Schema and type remain valid; independent ground truth and semantic/history checks make verification fail and the candidate cannot be shipped. |

All six definitions include mutation ID, severity, baseline/mutated fixture references, expected correct/corrupted state, affected fields, detector expectation, safety expectation, seed, fixture version, mutation mechanism, and deterministic metadata.

## 3. Ground-truth model

`MutationGroundTruth` is immutable and contains:

| Field | Meaning |
| --- | --- |
| `mutation_id`, `severity`, `seed` | Stable scenario identity. |
| `baseline_fixture_reference` | Clean fixture/version reference. |
| `mutated_fixture_reference` | Mutation/seed-specific fixture reference. |
| `expected_correct_state` | Independent canonical records and markup. |
| `expected_corrupted_state` | Exact mutated records and markup. |
| `affected_fields` | Declared impact surface. |
| `expected_detector_behavior` | Whether schema, semantic, statistical, or verification evidence is expected. |
| `expected_safety_behavior` | Healthy preservation, rejection, or quarantine expectation. |
| `deterministic_metadata` | Fixture version, mutation mechanism, parameters, and seed. |

The mutation result is reversible through `MutatedFixture.revert()`, which returns the immutable baseline fixture. Applying the same mutation ID and seed to the same baseline yields identical mutated fixture data and metadata.

## 4. Existing AEGIS pipeline integration

The harness does not duplicate detection or verification. For each mutation it creates an immutable `Observation` with `TEST_DOUBLE` provenance, calls the existing `evaluate_detection`, constructs the existing `VerificationContext` with the baseline as history and independent evidence, calls the existing `verify_candidate`, calls the existing `RiskGovernor`, and evaluates the existing `CommitGate`.

Later-stage fields are explicit in `MutationRun`. The run records verification and risk references because this harness can produce them, but it does not invent provider repair or live commit data. `output_eligible` is hard-coded false for all Mission 009 runs; the candidate remains an uncommitted test-double proposal.

## 5. MutationRun evidence

Each immutable `MutationRun` contains:

- run ID, mutation ID, and seed;
- collector/test-double reference;
- observation and detection references;
- verification and risk references when produced;
- ground-truth reference;
- `detected` and `detected_by_existing_detection` flags;
- outcome;
- `TEST_DOUBLE` provenance;
- detection, verification, risk, and total timing fields;
- verification status, risk decision, CommitGate eligibility, output-eligibility flag;
- quarantine reference when a record is created; and
- evidence references and timestamp.

`detected` represents the combined existing AEGIS outcome. `detected_by_existing_detection` is retained separately so the harness makes the L5 distinction visible: a valid-looking `price=29.99` can pass schema/type detection while deterministic verification catches the silent corruption.

## 6. L5 critical proof

The first critical proof is `M005`:

```text
BASELINE: price = 599
MUTATED:  price = 29.99
```

The mutated row remains valid JSON, preserves the exact extraction schema, and retains a numeric price. The basic DetectionResult is intentionally not alarmed by schema/type alone. The same mutated observation then reaches deterministic verification with:

- history containing the known-good `price=599` observation;
- semantic expectation `price=599`; and
- independent mutation-lab ground-truth rows containing `price=599`.

Verification returns `FAIL`, RiskGovernor returns `REJECT`, CommitGate returns `BLOCKED`, and `output_eligible=False`. The run is recorded as a detected rejected/quarantined safety outcome; the incorrect value cannot be treated as healthy or shipped.

`M006` proves the same safety property for a deterministic plausible decoy. No provider operation, repair, approval, commit, or rollback is executed.

## 7. Determinism and reversibility

The harness records the seed and fixture version in both mutation metadata and ground truth. The mutation definitions use only deterministic transformations and a seeded `random.Random(seed)` instance where a cosmetic token or decoy value requires variation. Repeated application with the same mutation ID and seed produces identical fixture state, metadata, and expected truth. Every mutation returns to the exact baseline fixture through `revert()`.

## 8. Tests and results

The full suite was run with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

Result:

```text
120 passed in 0.31s
```

Mission 009 adds 31 tests covering baseline determinism, six mutation definitions, all five severity levels, two L5 modes, same-seed reproducibility, reversibility, explicit ground truth, L1–L4 behavior, L5 schema/type preservation, ground-truth linkage, `TEST_DOUBLE` provenance, existing detection consumption, L5 non-health/non-shipment, no benchmark runner, no provider operation, and no automatic rollback/approval.

## 9. Safety checks

The mutation lab does not call Bright Data, modify provider state, create a public deployment, execute approval, perform repair, invoke rollback, run a benchmark, or claim measured metrics. It drives the existing AEGIS deterministic boundaries and records blocked output eligibility for known corruption. No credentials or secret-bearing provider logs are persisted.

## 10. Benchmark gaps

This is not the full benchmark. Mission 009 intentionally runs only deterministic harness tests. It does not provide ten trials per class, frozen baselines A/B/C, pinned model configuration, complete run manifests, 540 runs, headline DetectionRate, AlarmPrecision, VerifiedRecovery, VerificationMissRate, FalseRepairRate, UnsafeRefusalRate, or BlindCommitRate results. Those remain later measurement work and must be derived from immutable run artifacts.

## 11. Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/mutation_lab.py` | Added staging fixture, six mutation definitions, immutable ground truth/run records, seeded transformations, and existing-pipeline harness. |
| `src/aegis/__init__.py` | Exported Mission 009 mutation interfaces. |
| `tests/unit/test_mission009.py` | Added 31 mutation-lab determinism, severity, L5, integration, provenance, and safety tests. |
| `experiments/AEGIS-MISSION-009-MUTATION-LAB-V1.md` | Added this evidence report. |
| `docs/05_MUTATION_TAXONOMY.md` | Added Mission 009 V1 mutation manifest/evidence. |
| `docs/06_BENCHMARK_METHODOLOGY.md` | Added harness floor and non-claim boundary. |
| `docs/07_METRICS.md` | Added mutation-run metric-hook boundary. |
| `docs/11_API_CONTRACTS.md` | Added mutation-lab API/data contracts. |
| `docs/12_DATA_MODEL.md` | Added mutation fixture/ground-truth/run records. |
| `docs/13_DECISION_LOG.md` | Added Mission 009 decision. |
| `docs/16_TESTING_STRATEGY.md` | Added Mission 009 evidence tests. |

## 12. Exact recommended Mission 010

Mission 010 should implement a **redacted mutation-run manifest/export and deterministic metric calculator over immutable MutationRun records**, including per-severity DetectionRate, AlarmPrecision, L5 quarantine/bad-data-shipped safety fields, and `NOT_APPLICABLE` zero-denominator handling. It should not scale to 540 runs, add new provider capabilities, or alter the frozen AEGIS architecture until the V1 evidence is reviewed.
