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

## Mission 003 — Detection → Diagnosis → Repair Request

| Field | Record |
| --- | --- |
| Decision ID | OD-003 / Mission 003 |
| Date | 2026-08-17 |
| Context | Mission 002 provides immutable Observations, ExtractionContracts, and deterministic DetectionResults; the next safe boundary is structured diagnosis and repair intent. |
| Decision | Add bounded immutable Diagnosis and provider-neutral RepairRequest models, deterministic failure classification, an injected structured-model seam, and an explicitly non-executing repair boundary. |
| Evidence | `experiments/AEGIS-MISSION-003-DIAGNOSIS-REPAIR-REQUEST.md`; 26 passing unit/integration tests; recorded Mission 001 artifact integration. |
| Reason | Diagnosis must interpret evidence without authorizing provider execution. Repair intent must preserve the contract and remain independent of Bright Data routes. |
| Consequences | Mission 004 may plug the verified Bright Data CLI healing path into a separate adapter. Candidate verification, risk, approval, commit, and rollback remain later work. |
| Status | RESOLVED for Mission 003 scope; provider healing behavior remains OPEN/UNKNOWN where not verified |

## Mission 004 — Bright Data healing adapter

| Field | Record |
| --- | --- |
| Decision ID | OD-004 / Mission 004 |
| Date | 2026-08-17 |
| Context | Mission 001 verified the CLI self-healing request and approval-gated `awaiting_approval` envelope; Mission 003 created provider-neutral RepairRequest intent. |
| Decision | Extend the existing BrightDataCliAdapter with asynchronous heal submission, bounded polling, explicit provider-status handling, redacted envelope capture, and immutable `UNVERIFIED` RepairCandidate creation. |
| Evidence | `experiments/AEGIS-MISSION-004-BRIGHT-DATA-HEALING-ADAPTER.md`; 40 passing tests; no live Mission 004 heal execution. |
| Reason | Connect the verified provider path without allowing provider approval or a returned preview to bypass AEGIS verification and risk controls. |
| Consequences | Mission 005 can independently verify the candidate. Provider-native rollback, raw HTML, WARC artifact delivery, and candidate correctness remain unresolved as previously recorded. |
| Status | RESOLVED for Mission 004 scope; provider capabilities outside the tested CLI path remain OPEN/UNKNOWN |

## Mission 005 — RepairCandidate verification and Risk Governor

| Field | Record |
| --- | --- |
| Decision ID | OD-005 / Mission 005 |
| Date | 2026-08-17 |
| Context | Mission 004 captures an immutable provider proposal, but provider success and valid JSON do not establish semantic correctness. |
| Decision | Add four deterministic evidence channels, immutable VerificationCheck/VerificationResult records, and a RiskGovernor with explicit ACCEPT/REJECT/QUARANTINE policy. |
| Policy | ACCEPT requires contract, semantic/invariant, and genuinely independent evidence passes with no critical contradiction. History is optional strengthening evidence. Missing required evidence quarantines; deterministic failures reject. |
| Evidence | `experiments/AEGIS-MISSION-005-VERIFICATION-RISK-GOVERNOR.md`; 54 passing unit/integration tests; mandatory L5 silent-corruption fixture. |
| Safety consequence | A valid-schema candidate with expected price 599 changed to 29.99 fails semantic and independent evidence and is rejected. No candidate is committed. |
| Status | RESOLVED for Mission 005 scope; mutation-lab ground truth and durable persistence remain OPEN |

## Mission 006 — Fail-closed CommitGate and QuarantineLedger

| Field | Record |
| --- | --- |
| Decision ID | OD-006 / Mission 006 |
| Date | 2026-08-17 |
| Context | Mission 005 produces deterministic `RiskDecision` records, but downstream safety still needs an enforceable boundary that distinguishes future eligibility from production commit. |
| Decision | Add a deterministic provider-neutral `CommitGate`, an AEGIS-level `KnownGoodVersion`, an immutable append-only `QuarantineLedger`, and an output-eligibility result with no production sink. |
| Policy | `ACCEPT + PASS + VERIFIED + known-good + valid authorization + complete evidence + matching correlation` is required for `ELIGIBLE`; all other cases are `BLOCKED`. `REJECT`, `QUARANTINE`, `UNKNOWN`, and `UNVERIFIED` never become eligible. |
| Safety consequence | Quarantined or blocked candidates are retained as forensic records and cannot enter downstream output. A represented `RELEASED` status still requires a new verification re-entry. |
| Provider boundary | No Bright Data approval, activation, provider commit, or rollback is implemented. Provider-native version/rollback remains partial/documentation-only. |
| Status | RESOLVED for Mission 006 scope; durable persistence and real production commit remain OPEN |

## Mission 007 — Post-commit watch and regression detection

| Field | Record |
| --- | --- |
| Decision ID | OD-007 / Mission 007 |
| Date | 2026-08-17 |
| Context | Passing verification once does not prove that a repaired extraction remains healthy on later collections. Provider-native rollback remains unresolved. |
| Decision | Add immutable WatchRegistration, WatchCycle, WatchResult, and RegressionEvent models that reuse the existing deterministic detection engine and the existing Mission 006 QuarantineLedger. |
| Policy | A later observation is `HEALTHY` only when required watch evidence is present and existing detection emits no signals. Any detection signal is `REGRESSION`; missing required evidence is `UNKNOWN`. Serious regression is quarantined locally. |
| Safety consequence | Watch never repairs, re-diagnoses, activates, approves, commits, or rolls back. Unknown does not silently become healthy, and optional missing evidence does not automatically quarantine. |
| Provider boundary | Bright Data provider-native rollback remains partial/documentation-only and is not implemented. |
| Status | RESOLVED for Mission 007 scope; durable watch history and rollback remain OPEN |

## Mission 008 — Durable audit/evidence store and read-only history

| Field | Record |
| --- | --- |
| Decision ID | OD-008 / Mission 008 |
| Date | 2026-08-17 |
| Context | Missions 001–007 produce immutable evidence-bearing records, but the current persistence boundary is in-memory only. |
| Decision | Use a provider-neutral append-only audit event envelope and local SQLite implementation with redacted payloads and read-only aggregate/correlation/type queries. |
| Reason | The canonical stack leaves storage open, the workspace has no dependency manifest or selected distributed database, and Python standard-library SQLite supplies lightweight local durability without introducing unnecessary infrastructure. |
| Invariants | No update, delete, evidence mutation, secret persistence, or lifecycle side effect. Corrections are new events referencing prior events. |
| Evidence | `experiments/AEGIS-MISSION-008-DURABLE-AUDIT-EVIDENCE-STORE.md`; 89 passing unit/integration tests; on-disk reopen durability test. |
| Status | RESOLVED for local boundary; production deployment, backup, encryption, migrations, and object storage remain OPEN |

## Mission 009 — Mutation Laboratory V1

| Field | Record |
| --- | --- |
| Decision ID | OD-009 / Mission 009 |
| Date | 2026-08-17 |
| Context | AEGIS needs controlled ground truth to prove detection and safety, especially for valid-looking L5 corruption. |
| Decision | Add a small deterministic local mutation harness with six scenarios across L1–L5 and two L5 modes. Drive the existing AEGIS pipeline; do not build a parallel detector/verification system or full benchmark. |
| Ground truth | Immutable `MutationGroundTruth` is created from the clean staging fixture and mutation definition, not candidate output. |
| Safety | M005 `599 → 29.99` and M006 plausible decoy remain schema/type valid but fail deterministic verification, RiskGovernor, and CommitGate output eligibility. |
| Provider boundary | All collection is explicit `TEST_DOUBLE`; Bright Data state is not modified and no provider capability is added. |
| Status | RESOLVED for V1 harness floor; benchmark scaling and metric calculation remain OPEN |

## Mission 010 — Deterministic mutation manifest and metric calculator

| Field | Record |
| --- | --- |
| Decision ID | OD-010 / Mission 010 |
| Date | 2026-08-17 |
| Context | Mission 009 supplies immutable six-scenario mutation runs and independent ground truth, but no reproducible export or canonical calculation layer. |
| Decision | Add a deterministic redacted manifest projection and immutable metric calculator over existing `MutationRun`/`MutationGroundTruth` records. Do not create a second run model or scale the benchmark. |
| Measurement | Calculate canonical DetectionRate and AlarmPrecision overall, by severity, and by mutation ID where meaningful; calculate explicit L5 safety fields; return `NOT_APPLICABLE` for absent denominators and unavailable repair/commit paths. |
| Reproducibility | Sort records and results deterministically, pin a formula version, preserve run evidence references, and keep generated timestamp optional/null so the substantive JSON is byte-stable for identical input. |
| Safety | Ground truth comes only from `MutationGroundTruth`; no LLM opinion authorizes a result; Mission 009 output eligibility remains false; L5 bad-data-shipped count is reported as 0 only within the controlled harness. |
| Redaction | Reuse the Mission 008 audit-store normalization/redaction mechanism and fail closed for secret-bearing evidence-reference strings. |
| Evidence | `experiments/AEGIS-MISSION-010-MUTATION-MANIFEST.json`; `experiments/AEGIS-MISSION-010-METRICS.json`; `docs/generated/mission_010_metrics.md`; `experiments/AEGIS-MISSION-010-MANIFEST-METRICS.md`; Mission 010 unit tests. |
| Consequences | The measurement gap is closed for deterministic V1 evidence. Full benchmark trials, baselines, model freeze, production repair outcomes, and headline metrics remain future work. |
| Status | RESOLVED for Mission 010 measurement infrastructure; benchmark execution and real repair metrics remain OPEN |

## Mission 011 — Benchmark configuration freeze and validation-only dry run

| Field | Record |
| --- | --- |
| Decision ID | OD-011 / Mission 011 |
| Date | 2026-08-17 |
| Context | Mission 010 provides deterministic manifest and metric infrastructure, but benchmark execution still lacks a frozen experiment definition, baseline slots, environment/revision pinning, artifact contract, and reproducibility gate. |
| Decision | Add immutable `BenchmarkConfig`/`BaselineSpec` records, fail-closed validation, canonical configuration hashing, and a validation-only dry-run planner. Preserve M001–M006 and their existing severities and use the Mission 009 seed behavior. |
| Freeze | The committed validation configuration uses code/repository revision `3dea1cb103a331568f4853a56316ce22d13bd2c2`, fixture `gpu-price-staging` version `1`, seed `12345`, Mission 010 formula version `mission-010-metrics-v1`, and configuration hash `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3`. Any changed hashed field with the old hash fails validation. |
| Baselines | `BASELINE_A`, `BASELINE_B`, and `AEGIS` slots are explicit and complete in shape, but all are `NOT_READY`; no baseline result or model/prompt configuration is invented. |
| Dry run | Twice-run validation produced byte-identical substantive output and an 18-step plan (`3 × 6 × 1`) with `NOT_EXECUTED` steps. No benchmark collection, provider operation, healing, metric calculation, approval, commit, or rollback occurred. |
| Metric integrity | Mission 010 remains the sole metric calculator. Mission 011 reports calculator availability only and generates zero metric values. No headline benchmark result is published. |
| Artifact contract | Future configs, manifests, runs, results, and reports are declared under `benchmarks/`; only configuration and validation-plan artifacts are committed now. |
| Consequences | The benchmark definition and reproducibility gate are frozen for review, but full benchmark execution remains blocked until baseline A/B/AEGIS implementations/configurations are genuinely ready and a later mission authorizes execution. |
| Status | RESOLVED for configuration freeze and dry-run validation; benchmark execution, baseline readiness, and headline results remain OPEN |

## Mission 012 — Common baseline participant contract and validation-only runner

| Field | Record |
| --- | --- |
| Decision ID | OD-012 / Mission 012 |
| Date | 2026-08-17 |
| Context | Mission 011 froze the benchmark configuration and deterministic plan, but the three participants did not yet share an executable evidence contract or readiness boundary. |
| Decision | Define common provider-neutral participant adapters for `BASELINE_A`, `BASELINE_B`, and `AEGIS`; normalize raw evidence into one schema; enforce freeze equality; and expose a validation-only `--dry-run` runner. |
| Baseline A | Static selector contract with no AEGIS detection, verification, RiskGovernor, or CommitGate controls. Contract readiness is testable against all M001–M006; benchmark readiness remains tied to a real frozen READY slot. |
| Baseline B | Readiness validator only. Model, prompt, configuration, implementation revision, and first-candidate policy cannot be selected automatically. Missing owner-approved values remain `NOT_READY`. |
| AEGIS | Existing Mission 009 lifecycle is normalized through a TEST_DOUBLE adapter. The benchmark slot remains `NOT_READY_FOR_BENCHMARK`; safety policy is unchanged. |
| Fairness | Every participant receives equal mutation ID, severity, seed, fixture version, evaluator ground-truth reference, trial metadata, timeout, retry, code/environment, and artifact-root inputs. Ground-truth content is not supplied as runtime participant data. |
| Freeze enforcement | Configuration hash, code revision, fixture version, mutation IDs/severity, seeds, baseline hashes, metric formula version, timeout, and retry policy are compared against `FreezeSnapshot`; any drift fails closed before `RUNNING`. |
| Dry run | The runner returns `BLOCKED_NOT_READY`, constructs 18 deterministic `PLANNED` manifests, and reports zero benchmark/provider/healing operations and zero metric results. It does not substitute AEGIS for either missing baseline. |
| Metric integrity | Mission 010 remains the sole metric calculator; Mission 012 emits raw evidence/plan records only. |
| Status | RESOLVED for the common contract and validation-only runner; participant readiness and benchmark execution remain OPEN |

## Mission 013 — Human-reviewed participant freeze and readiness promotion

| Field | Record |
| --- | --- |
| Decision ID | OD-013 / Mission 013 |
| Date | 2026-08-17 |
| Context | Mission 012 established the common participant contract, but all three participant slots remained not benchmark-ready. Mission 013 requires human-reviewed metadata before readiness promotion. |
| Decision | Add immutable participant proposals, explicit owner-review decisions, participant configuration hashes, fail-closed completeness checks, append-only readiness-promotion evidence, and a `READY_TO_EXECUTE` planning status that never launches execution. |
| Baseline A | Static selector extraction only. Healing, AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, and rollback are explicitly `NOT_USED`. No final implementation/configuration approval was supplied, so status remains `NOT_READY`. |
| Baseline B | Owner decision required for model/provider, exact system and repair prompts, sampling/max-output/tools, timeout/retry, first-candidate policy, implementation revision, and participant hash. No values are selected automatically; status remains `NOT_READY`. |
| AEGIS | Requires code/fixture/mutation/seed/configuration references, adapter/artifact schema, deterministic TEST_DOUBLE, timeout/retry, provenance, Mission 010 compatibility, and unchanged safety. It remains `NOT_READY` without reviewed participant metadata. |
| Current review | `owner_review_status=NOT_PROVIDED`; `promotion_status=NOT_PERFORMED`; readiness transitions are empty. This is a deliberate fail-closed result, not a guessed approval. |
| Hash behavior | Source Mission 011 configuration hash `fdf3b632...` is preserved. Participant metadata changes invalidate that old hash; approved promotion would regenerate a new hash. |
| Fairness | Same participant-independent mutation, seed, fixture, evaluator reference, trial metadata, timeout, and retry input; runtime ground-truth payload remains `NOT_PROVIDED`. |
| Dry run | `BLOCKED_NOT_READY`, 18 planned steps, zero benchmark/provider/healing/metric operations, and `execution_authorized=false`. |
| Status | RESOLVED for promotion workflow and fail-closed validation; owner approvals, readiness promotion, and benchmark execution remain OPEN |

## Mission 014 — Owner-approved input validation result

| Field | Record |
| --- | --- |
| Decision ID | OD-014 / owner-input validation |
| Date | 2026-08-17 |
| Context | Owner supplied participant configuration values, but revision/hash fields were declared as values to be generated later and review evidence fields were not supplied. |
| Decision | Validate exact input and fail closed before constructing OwnerReviewDecision, ReadinessPromotion, or a new BenchmarkConfig. |
| Baseline A | Exact selectors/controls/fixture/seed values pass; implementation revision and participant hash remain unresolved placeholders. |
| Baseline B | Exact model/prompt/first-candidate/no-AEGIS-control values pass; implementation revision and participant hash remain unresolved placeholders. |
| AEGIS | Exact TEST_DOUBLE lifecycle/safety/fixture/seed/formula values pass; implementation revision, participant hash, and the AEGIS mutation field mapping require completion. |
| Owner review | `approved=true` and `reviewer=PROJECT_OWNER` are present, but approval timestamp, rationale, correlation ID, and final approved configuration hash are absent. No fake identity or timestamp is created. |
| Fairness | Mutation, seed, fixture, runtime-ground-truth, retry, and backoff checks pass. Timeout equality fails: A=30, B=60, AEGIS=300. |
| Result | `BLOCKED_NOT_READY`; promotions=0; new hash not generated; new-config dry run not run; all execution counters remain zero. |
| Status | RESOLVED for exact validation; OPEN for owner-supplied final revisions/hashes/review metadata and a common timeout decision |


## Mission 015 — real participant freeze and validation-only readiness

**Decision:** Finalize the minimum comparative participant set using only the owner-approved values, real implementation revisions, deterministic participant hashes, explicit owner review, and append-only readiness promotion. Do not execute the benchmark in this mission.

**Participants and implementation revisions:** Baseline A uses deterministic fixed-selector extraction at `0e8bcc4a2c2184cae9a50b291054ec47d83fc895`; Baseline B uses the approved `GOOGLE_GEMINI_API` model `gemini-3.6-flash` at stable revision with disabled tools and first-candidate-only behavior at the same committed participant-adapter revision; AEGIS uses the existing TEST_DOUBLE lifecycle adapter at `7de2bc65ed9eeb9f4abd24017543f3f366990738`.

**Participant configuration hashes:** Baseline A `fc95be9ae66b859ab770d23ab46c2ce82dcad645325f833f5fac88959dc3e5d6`; Baseline B `20f90c001f061683c91acc65a2031f07651678041f88db064ad68157084bfb1b`; AEGIS `76e4553696d6f6e8dca4d3b08d126b42d04f9cac3e8537836c19d86943a90a75`. All three hashes were computed from the complete proposal payload and reproduced deterministically.

**Owner review:** Each participant has `approved=true`, `owner=PROJECT_OWNER`, `reviewer=PROJECT_OWNER`, a current UTC approval timestamp, the deterministic mission rationale, a generated UUID correlation ID, and the corresponding participant hash. Each promotion records the immutable transition `NOT_READY → READY`; no historical Mission 013 or Mission 014 record was modified.

**Benchmark configuration:** Starting from the Mission 011 validation floor, Mission 015 replaces the participant slots and applies the common 300-second timeout, zero-retry, zero-backoff policy. The resulting canonical configuration hash is `f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96`, which differs from the old Mission 011 hash `fdf3b63244051f7bfc6867cc53b774285edacdd045a9b7870b9290e5974929c3`. M001–M006, the L1–L5 severity mapping, seed `12345`, fixture `gpu-price-staging` v1, and `mission-010-metrics-v1` remain unchanged.

**Readiness and safety decision:** Participant validation, freeze validation, fairness, and deterministic fixture/seed checks pass. The runner returns `READY_TO_EXECUTE` with 18 planned manifests. This is not authorization to benchmark. The final counters are `benchmark_runs_executed=0`, `provider_operations_executed=0`, `healing_operations_executed=0`, `metric_results_generated=0`, and `execution_authorized=false`. No provider, healing, approval, commit, rollback, or metric operation was invoked. Mission 016 is not started.
