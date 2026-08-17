# 05 — Mutation Taxonomy

**Purpose:** Define controlled website evolutions used to test AEGIS.  
**Ground-truth rule:** Every mutation has a known expected extraction outcome.  
**Seed rule:** A mutation run is reproducible only when its fixture version and seed are recorded.

## Taxonomy contract

The laboratory uses exactly five severity levels. Severity describes the kind of change and the safety consequence, not merely implementation difficulty. Each mutation manifest must contain mutation ID, severity, description, realism rationale, injection mechanism, seed, ground truth, detector expectation, repair expectation, verifier expectation, success criteria, and failure criteria.

## Severity levels

| Level | Name | Meaning | Typical detector channels | Safety interpretation |
| --- | --- | --- | --- | --- |
| L1 | Cosmetic | Superficial markup changes that should not change meaning. | Response fingerprint, structural checks | Recovery should preserve output; false alarms matter. |
| L2 | Structural | DOM hierarchy, ordering, wrapper, or field-location changes. | Structural, schema, response | Extraction may fail explicitly or require repair. |
| L3 | Semantic | Meaning or representation changes that can make a plausible value wrong. | Semantic, statistical, contract | Verification must prove field meaning, not just shape. |
| L4 | Behavioral | Interaction, loading, pagination, or rendering behavior changes. | Network, behavioral, collection metadata | A timeout or partial result must not be treated as complete. |
| L5 | Silent corruption | Valid-looking output with wrong value, unit, field, or entity. | Semantic, statistical, independent evidence | Detect, quarantine, re-extract/repair, verify, and ensure wrong data is not shipped. |

## Required mutation classes

| ID | Severity | Mutation | Realism | Injection mechanism | Ground truth |
| --- | --- | --- | --- | --- | --- |
| MUT-L1-CLASS | L1 | Rename CSS class | Frontend refactors commonly rename presentation hooks. | Fixture transformation changes class token without changing labels/data. | Original entity/value mapping remains correct. |
| MUT-L1-WRAP | L1 | Add irrelevant wrapper | Layout components are frequently inserted. | Wrap target nodes in non-semantic container. | Same extraction contract. |
| MUT-L2-MOVE | L2 | Relocate field node | Components can be rearranged while preserving display. | Move field to a different valid subtree. | Same entity/value, new structural path. |
| MUT-L2-ORDER | L2 | Reorder sibling nodes | Cards and table columns may be reordered. | Permute siblings or records. | Entity keys remain the reference mapping. |
| MUT-L3-LABEL | L3 | Change field label | Copy and localization changes alter labels. | Replace label with synonym/locale variant. | Semantic field mapping is known from fixture truth. |
| MUT-L3-FORMAT | L3 | Change value format/unit | Currency, unit, and display formatting change. | Change representation while preserving/altering canonical value according to manifest. | Canonical normalized value is explicit. |
| MUT-L4-PAGE | L4 | Change pagination | Site pagination implementations change. | Replace page links with cursor/next behavior in fixture. | Full expected record set is known. |
| MUT-L4-LAZY | L4 | Lazy-load records | Initial HTML may omit records. | Require a deterministic interaction or second fixture response. | Complete set and loading condition are known. |
| MUT-L5-SWAP | L5 | Swap columns/fields | Template changes can map labels to neighboring values. | Swap rendered values while keeping schema valid. | Correct field/entity association is known. |
| MUT-L5-UNIT | L5 | Plausible unit swap | Monthly vs one-time prices are a realistic decoy. | Replace canonical amount/unit with plausible alternate. | Expected unit and canonical value are known. |
| MUT-L5-DECOY | L5 | Plausible decoy value | Ads, promotions, or related products may be selected. | Insert a valid-looking competing value in selector vicinity. | Correct entity/value is specified in manifest. |
| MUT-L5-ENTITY | L5 | Wrong entity association | Repeated cards create ambiguous matches. | Pair a valid field with a different entity. | Entity ID/value pair is ground truth. |

The benchmark floor requires at least six classes, all levels, and at least two L5 modes. The table above supplies more than the floor, but the actual final set is frozen only after the fixture implementation and Day-2 review.

## Manifest schema

```yaml
mutation_id: MUT-L5-UNIT
severity: L5
fixture_id: gpu-price-v1
fixture_version: 1
seed: 12345
injection:
  mechanism: replace_display_unit
  parameters:
    from: one_time
    to: monthly
truth:
  expected_records:
    - entity_id: gpu-5090
      field: price
      canonical_value: 1999
      currency: USD
      unit: one_time
expectations:
  detector: semantic_or_independent_evidence_alarm
  repair: restore_canonical_mapping_or_quarantine
  verifier: reject_monthly_decoy_for_one_time_contract
success_criteria:
  - incorrect value is not committed
failure_criteria:
  - incorrect value is committed
```

## L5 protocol

L5 is not reported as ordinary recovery. The expected flow is:

```text
detect → quarantine → re-extract / repair → verify → ensure incorrect data is not shipped
```

A run is a safety success if bad data is prevented from shipment, even if the final action is quarantine rather than automatic recovery. L5 reports must include detection rate, quarantine rate, verified re-extraction, verification miss rate, and bad-data-shipped rate.

## Mutation acceptance and failure criteria

A mutation is accepted into the benchmark only when its injection is deterministic under the recorded seed, the fixture remains valid for the intended scenario, ground truth is independently encoded from the extraction selector, and a reviewer can explain why the change is realistic. A mutation fails qualification when its expected output is ambiguous, the injector changes more than its declared class, or the fixture cannot be reset to a clean version.

## Mission 009 V1 mutation lab — 2026-08-17

Mission 009 freezes a deterministic V1 floor with six local staging mutations and known ground truth. The fixture is `gpu-price-staging` version `1`, with canonical `price=599` for `gpu-1`, and all collection provenance is `TEST_DOUBLE`.

| ID | Severity | Mutation | Expected detector/safety behavior |
| --- | --- | --- | --- |
| M001 | L1 | Rename irrelevant CSS class token | Data remains correct; no alarm expected. |
| M002 | L2 | Remove required `availability` field | Schema alarm; reject/block. |
| M003 | L3 | Set `price=-599` | Semantic/statistical alarm; reject/block. |
| M004 | L4 | Drop complete deterministic page result | Row-count alarm; reject/block incomplete output. |
| M005 | L5 | Swap `price=599` to `29.99` | Schema/type remain valid; verification against history, semantic expectation, and independent ground truth fails; reject/quarantine. |
| M006 | L5 | Replace price with deterministic plausible decoy | Schema/type remain valid; verification fails against ground truth; reject/quarantine. |

Each run records mutation ID, severity, baseline and mutated fixture references, expected correct/corrupted state, affected fields, detector expectation, safety expectation, seed, fixture version, mechanism, and metadata. `MutationGroundTruth` is generated independently from the AEGIS candidate output. Each `MutatedFixture` is reversible to the immutable baseline.

The L5 protocol is demonstrated with `M005`: `price=29.99` is valid JSON, schema-compatible, and numeric, while deterministic verification identifies disagreement with the known `price=599` truth. Risk/commit boundaries block output eligibility. This is a harness safety proof, not a benchmark result.
