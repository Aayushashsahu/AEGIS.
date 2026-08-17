# 04 — Requirements Catalog

**Status:** Canonical baseline.  
**Priority:** P0 is required for the core proof; P1 supports credibility or demo quality; P2 is optional breadth.  
**Status values:** `PROPOSED`, `IN_PROGRESS`, `VERIFIED`, `BLOCKED`, `CUT`.

## Requirement format

Every requirement has an acceptance criterion and validation method. Owners are role placeholders until the team assigns names. A requirement is not `VERIFIED` because its code exists; it is verified only when the stated evidence is produced.

## Functional requirements

| ID | Description | Priority | Dependencies | Acceptance criteria | Validation | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR-001 | The system shall execute or receive a collection result through a Bright Data adapter. | P0 | Bright Data spike | A collection can be correlated to a collector and produce a terminal result or classified error. | Integration test and run artifact | Collection owner | PROPOSED |
| FR-002 | The system shall persist an immutable Observation for every collection. | P0 | FR-001 | Observation contains output, timestamps, metadata, and available evidence; it is queryable by collection ID. | Unit/integration test | Data owner | PROPOSED |
| FR-003 | The system shall evaluate an ExtractionContract for required fields, types, nullability, and semantic invariants. | P0 | FR-002 | Contract violations produce channel-level findings with evidence. | Unit tests with fixtures | Detection owner | PROPOSED |
| FR-004 | The system shall support schema, statistical, semantic, and response-level detection channels. | P0 | FR-003 | Each enabled channel emits a typed finding and can be disabled only through recorded configuration. | Unit/system tests | Detection owner | PROPOSED |
| FR-005 | The system shall classify an anomaly and create a structured repair request. | P0 | FR-004 | A DetectionEvent links to a Diagnosis and includes failure class, evidence references, and requested action. | Integration test | Diagnosis owner | PROPOSED |
| FR-006 | The system shall submit a repair request through the Bright Data healing boundary. | P0 | FR-005, Bright Data spike | Real adapter or explicitly labeled test double returns a tracked attempt and candidate/error. | Integration test | BD owner | BLOCKED |
| FR-007 | The system shall persist every RepairAttempt and RepairCandidate. | P0 | FR-006 | Attempts include deadlines, retries, provider status, and candidate references. | Unit/integration tests | Repair owner | PROPOSED |
| FR-008 | The system shall run deterministic verification before any commit. | P0 | FR-007 | No commit is possible without a completed VerificationRun. | Safety test | Verification owner | PROPOSED |
| FR-009 | A commit shall require at least two independent deterministic verification channels to pass. | P0 | FR-008 | A candidate with zero or one passing deterministic channel is rejected, retried, quarantined, or escalated. | Safety test | Verification owner | PROPOSED |
| FR-010 | The system shall implement ACCEPT, RETRY, QUARANTINE, and ESCALATE risk decisions. | P0 | FR-008 | Every terminal candidate receives one recorded decision. | State transition tests | Risk owner | PROPOSED |
| FR-011 | The system shall prevent quarantined data from downstream shipment. | P0 | FR-010 | A quarantined episode has no active committed output and exposes its reason/evidence. | End-to-end safety test | Risk owner | PROPOSED |
| FR-012 | The system shall record a known-good version before commit. | P0 | FR-009 | Commit references a version and prior known-good state. | Integration test | Commit owner | PROPOSED |
| FR-013 | The system shall watch accepted repairs after commit. | P0 | FR-012 | A subsequent watch cycle records validation and can emit regression. | System test | Watch owner | PROPOSED |
| FR-014 | The system shall roll back a regression to a known-good version. | P0 | FR-013 | Seeded regression creates RollbackEvent and restored version passes safety checks or remains quarantined. | System/safety test | Rollback owner | PROPOSED |
| FR-015 | The system shall store verified RepairEpisodes. | P1 | FR-008, FR-010 | Episode links failure, evidence, candidate, verification, decision, timing, cost, and mutation when known. | Data test | Memory owner | PROPOSED |
| FR-016 | The system shall apply seeded mutations with known ground truth. | P0 | Staging spike | Each mutation manifest contains ID, severity, seed, expected output, and injection record. | Mutation tests | Benchmark owner | PROPOSED |
| FR-017 | The system shall run three frozen baselines. | P0 | FR-016 | Baselines are committed before comparative execution and emit equivalent run artifacts. | Benchmark protocol test | Benchmark owner | PROPOSED |
| FR-018 | The system shall calculate canonical metrics and per-severity results. | P0 | FR-017 | Metric outputs include formulas, numerator, denominator, and raw run references. | Unit/benchmark test | Metrics owner | PROPOSED |
| FR-019 | The system shall export evidence for the demo and final submission. | P0 | FR-018 | A run can export event timeline, candidate decisions, benchmark summary, and measured placeholders/results. | Demo rehearsal | Demo owner | PROPOSED |
| FR-020 | The product surface shall display structured output, last verified time, status, and confidence/risk. | P1 | FR-012 | Displayed values link to the active verified observation and do not display quarantined output as current. | UI/system test | Product owner | PROPOSED |

## Non-functional requirements

| ID | Description | Priority | Acceptance criteria | Validation |
| --- | --- | --- | --- | --- |
| NFR-001 | The MVP shall run as a modular monolith. | P0 | All core modules run in one deployable process or clearly bounded local command. | Architecture review |
| NFR-002 | Lifecycle actions shall be auditable. | P0 | Every state transition has actor, time, correlation ID, reason, and evidence references. | Audit test |
| NFR-003 | Benchmark runs shall be reproducible. | P0 | Re-running the documented command with the same seed and versions yields comparable artifacts. | Reproduction run |
| NFR-004 | External calls shall have bounded timeout and retry behavior. | P0 | No external attempt can loop without a deadline and terminal classification. | Fault-injection test |
| NFR-005 | The system shall fail closed at the commit gate. | P0 | Missing verification or authorization cannot result in commit. | Safety test |
| NFR-006 | The project shall minimize infrastructure. | P1 | Any new service has a documented risk/benefit decision and fallback. | Decision-log review |
| NFR-007 | Evidence artifacts shall be exportable without secrets. | P0 | Export scan detects and blocks credentials or sensitive fields. | Security test |
| NFR-008 | Demo behavior shall be deterministic. | P0 | Final sequence can be rehearsed repeatedly with stable event ordering and captions. | Demo test |

## Reliability requirements

| ID | Description | Priority | Acceptance criteria | Validation |
| --- | --- | --- | --- | --- |
| REL-001 | Never commit an unverified repair. | P0 | Commit endpoint rejects missing/incomplete VerificationRun. | Safety test |
| REL-002 | Never treat non-empty output as health. | P0 | A valid schema with seeded semantic corruption creates an anomaly or safety hold. | L5 system test |
| REL-003 | Never use one LLM opinion as deployment authority. | P0 | Removing deterministic evidence prevents commit even when model says pass. | Safety test |
| REL-004 | Quarantine insufficient evidence. | P0 | Ambiguous candidate becomes quarantined or escalated within bounded retries. | Fault-injection test |
| REL-005 | Post-commit watch is mandatory. | P0 | Every accepted commit schedules or records a watch cycle. | State test |
| REL-006 | Regression can trigger rollback. | P0 | Seeded post-commit regression creates RollbackEvent and restores/holds safely. | System test |
| REL-007 | Blind Commit Rate equals zero on the evaluated path. | P0 | Metric formula is enforced; any blind commit fails the release gate. | Benchmark/safety gate |

## Safety requirements

| ID | Description | Priority | Acceptance criteria | Validation |
| --- | --- | --- | --- | --- |
| SAFE-001 | Scraped content cannot redefine policy. | P0 | Prompt-like page content is stored as data and cannot alter rule configuration. | Prompt-injection test |
| SAFE-002 | Secrets shall not enter fixtures, logs, or exports. | P0 | Secret scanning passes repository and artifacts. | Security test |
| SAFE-003 | Repair authorization shall be explicit. | P0 | Unauthorized repair/commit attempts are denied and audited. | Integration test |
| SAFE-004 | Quarantine shall preserve evidence. | P0 | Quarantined output and reason remain retrievable. | Data test |
| SAFE-005 | Rollback shall be auditable and verifiable. | P0 | Rollback records prior/target versions, reason, evidence, and result. | System test |

## Benchmark, demo, and submission requirements

| ID | Description | Priority | Acceptance criteria | Validation |
| --- | --- | --- | --- | --- |
| BENCH-001 | Include all five severity levels. | P0 | Benchmark manifest contains L1–L5. | Manifest test |
| BENCH-002 | Include at least six mutation classes and two L5 modes. | P0 | Minimum floor is present before final claims. | Benchmark review |
| BENCH-003 | Use at least ten trials per class and fixed seeds. | P0 | Run manifest records counts and seeds. | Benchmark review |
| BENCH-004 | Freeze three baselines before comparison. | P0 | Git/config evidence predates benchmark execution. | Repository review |
| BENCH-005 | Report per-severity metrics and L5 bad-data-shipped rate. | P0 | Report has separate L1–L5 sections. | Metrics test |
| DEMO-001 | Produce a two-minute recorded sequence. | P0 | Duration and required timestamps pass rehearsal checklist. | Demo test |
| DEMO-002 | Demonstrate green-but-wrong extraction. | P0 | Opening includes expected and extracted values plus GREEN status. | Video review |
| DEMO-003 | Use captions, large text, and muted comprehension. | P0 | Reviewers can follow without audio. | Video review |
| DEMO-004 | Use actual measured values only. | P0 | No target is presented as result. | Release review |
| SUB-001 | Submit a public repository with README, canonical docs, structured output, and reproducibility commands. | P0 | All links and artifacts are checked before submission. | Submission checklist |
| SUB-002 | Include AI-use disclosure and public-data compliance. | P0 | Disclosure and compliance review are complete. | Owner sign-off |

## Change control

Changes to thesis, reliability invariants, metric formulas, benchmark baseline behavior, severity definitions, or commit gates require project-owner approval and an ADR. Agents may not make such changes independently.
