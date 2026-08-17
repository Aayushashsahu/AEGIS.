# 13 — Decision Log / ADRs

**Purpose:** Record architectural and strategy decisions without inventing historical events.  
**Status convention:** `FROZEN`, `PROPOSED`, `OPEN`, `SUPERSEDED`.  
**Date convention:** Use the date of the actual decision; entries marked `[OWNER_CONFIRMATION_DATE]` are not historical claims.

## ADR-001 — Modular monolith

| Field | Record |
| --- | --- |
| Decision ID | ADR-001 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | AEGIS must demonstrate a closed reliability loop in a one-week sprint. |
| Problem | Microservices would add deployment, network, and coordination risk without improving the core proof. |
| Decision | Use a modular monolith with an event/state-driven core and explicit internal boundaries. |
| Alternatives | Microservices; single script; external workflow platform. |
| Why chosen | Preserves testable modules and one audit trail while minimizing infrastructure. |
| Consequences | Requires disciplined module contracts; future extraction remains possible. |
| Status | FROZEN strategy; implementation details OPEN |

## ADR-002 — Deterministic plus bounded model hybrid

| Field | Record |
| --- | --- |
| Decision ID | ADR-002 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | Semantic interpretation is useful, but deployment safety cannot depend on one model. |
| Problem | An LLM can propose a plausible but wrong repair. |
| Decision | Use deterministic checks for evidence, risk, commit, quarantine, and rollback; permit bounded model assistance for diagnosis and semantic interpretation. |
| Alternatives | LLM-only agent; multi-agent debate; deterministic-only extraction. |
| Why chosen | Preserves semantic flexibility without surrendering deployment authority. |
| Consequences | Requires explicit evidence channels and model traceability. |
| Status | FROZEN strategy |

## ADR-003 — Bright Data as healing execution layer

| Field | Record |
| --- | --- |
| Decision ID | ADR-003 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | The project competes in the Best Use of Bright Data track. |
| Problem | Replacing the platform with a local scraper would violate the project strategy. |
| Decision | AEGIS orchestrates detection, requests, verification, and risk; Bright Data remains the actual collection/healing layer. |
| Alternatives | Local scraper; generic provider abstraction without Bright Data centrality. |
| Why chosen | Preserves strong track alignment and demonstrates reliability around real extraction. |
| Consequences | Platform behavior and integration details must be verified early. |
| Status | FROZEN strategy |

## ADR-004 — Verification before commit

| Field | Record |
| --- | --- |
| Decision ID | ADR-004 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | Returning data does not establish correctness. |
| Problem | Self-healing systems can silently deploy wrong candidates. |
| Decision | No candidate can commit without a completed verification run and at least two deterministic passing channels. |
| Alternatives | First candidate wins; human-only verification; one channel. |
| Why chosen | Directly enforces the core reliability thesis and BlindCommitRate = 0%. |
| Consequences | Some correct repairs will be quarantined when evidence is insufficient. |
| Status | FROZEN |

## ADR-005 — Quarantine is a successful safety outcome

| Field | Record |
| --- | --- |
| Decision ID | ADR-005 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | Uncertainty is safer than shipping corrupted data. |
| Problem | Optimizing only for recovery can reward unsafe guesses. |
| Decision | Quarantine blocks shipment and preserves evidence; it is reported separately from ordinary recovery. |
| Alternatives | Always retry; ship last output; fail silently. |
| Why chosen | Aligns safety outcome with silent-corruption risk. |
| Consequences | Product surface must show withheld/uncertain status clearly. |
| Status | FROZEN |

## ADR-006 — Controlled mutation laboratory

| Field | Record |
| --- | --- |
| Decision ID | ADR-006 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | Live production pages do not reliably expose ground truth for every failure. |
| Problem | Reliability claims would otherwise be anecdotal or irreproducible. |
| Decision | Use seeded controlled mutations with known truth for headline benchmark metrics. |
| Alternatives | Live-site-only evaluation; synthetic data without realistic mutations. |
| Why chosen | Enables objective, reproducible measurement while preserving realistic website evolution. |
| Consequences | Mutation quality and reset determinism become critical risks. |
| Status | FROZEN strategy |

## ADR-007 — Frozen baselines and canonical metric formulas

| Field | Record |
| --- | --- |
| Decision ID | ADR-007 |
| Date | `[OWNER_CONFIRMATION_DATE]` |
| Context | Comparative claims are vulnerable to moving targets and metric redefinition. |
| Problem | Changing baselines or formulas after seeing results undermines credibility. |
| Decision | Commit A/B/C configurations before runs and calculate metrics only from `07_METRICS.md`. |
| Alternatives | Tune baselines during benchmark; aggregate-only reporting. |
| Why chosen | Makes comparison reproducible and auditable. |
| Consequences | Weak results must be reported rather than optimized away. |
| Status | FROZEN strategy |

## Open-decision record template

```text
Decision ID: OD-<NUMBER>
Date opened:
Owner:
Unknown:
Why it matters:
Experiment:
Decision deadline:
Fallback:
Evidence location:
Status: OPEN | RESOLVED | DEFERRED
```

## Mission 001 — Bright Data capability spike

| Field | Record |
| --- | --- |
| Decision ID | OD-001 / Mission 001 |
| Date | 2026-08-17 |
| Context | The first AEGIS vertical slice requires a verified collection, observation, and detection boundary around Bright Data Scraper Studio. |
| Evidence | `experiments/mission_001_official_findings.md`, `mission_001_collection_metadata.json`, `mission_001_collection_output.json` |
| Decision | Use the documented Bright Data CLI as the first live adapter seam for collector creation, execution, structured-output retrieval, and approval-gated self-healing proposal capture. Preserve provider identifiers and status envelopes as evidence. |
| Reason | The CLI path was authenticated and live-tested. It created a collector, executed it, returned structured rows, fell back from realtime to batch, and produced an `awaiting_approval` self-healing preview without requiring an unverified endpoint guess. |
| Consequences | Collection and proposal capture can proceed behind a bounded adapter. Provider-native version/rollback, raw HTML, WARC retrieval, and candidate correctness remain unresolved. The AEGIS commit gate remains independent and must not be replaced by Bright Data approval. |
| Status | CONFIRMED for the tested path; broader provider capabilities remain OPEN |

### Open decisions created or updated

| ID | Unknown | Evidence / next experiment | Fallback |
| --- | --- | --- | --- |
| OD-001-BD-VERSION | CLI output did not expose a version/revision identifier or a programmatic rollback operation. | Inspect the authenticated Scraper Studio Versions UI or official API reference; do not approve a heal while unresolved. | AEGIS-level known-good version registry and adapter routing. |
| OD-001-BD-RAW | The tested CLI run returned structured JSON but no raw HTML/response artifact. | Test a Browser worker collector with documented `warc_snapshot` delivery or inspect configured delivery output. | Controlled local fixture snapshots and locally computed fingerprints. |
| OD-001-BD-CANDIDATE | A preview result and diff summary were returned, but candidate correctness and full patch retrieval were not independently verified. | Preserve the pending heal; compare a future approved candidate against controlled mutation ground truth. | Quarantine all provider proposals until AEGIS deterministic verification passes. |
| OD-001-BD-LATENCY | The measured create/run/heal timings are single-run observations. | Repeat only after the adapter contract and controlled fixture are frozen; record p50/p95 separately. | Bound timeouts, retries, and demo claims to measured traces. |

## Mission 002 — Collection → Observation → Detection

| Field | Record |
| --- | --- |
| Decision ID | OD-002 / Mission 002 |
| Date | 2026-08-17 |
| Context | Mission 001 verified a narrow Bright Data CLI path but left provider healing, rollback, raw evidence, and candidate correctness unresolved. |
| Decision | Implement only the first vertical slice behind a provider-neutral adapter: asynchronous collection states, immutable untrusted Observations, typed ExtractionContract evaluation, deterministic schema/statistical/semantic detection, and a labeled `TEST_DOUBLE`. |
| Evidence | `experiments/AEGIS-MISSION-002-COLLECTION-OBSERVATION-DETECTION.md`; 12 passing unit/integration tests; Mission 001 collection artifact conversion test. |
| Reason | The adapter preserves verified provider behavior without scattering CLI calls, while deterministic local tests establish the Collection → Observation → Detection seam without provider credits or unverified capabilities. |
| Consequences | A real recorded Bright Data result can be represented and flagged as untrusted/detected. Healing, candidate verification, risk, rollback, memory, benchmarks, and UI remain later missions. |
| Status | RESOLVED for Mission 002 scope; later lifecycle stages remain OPEN |
