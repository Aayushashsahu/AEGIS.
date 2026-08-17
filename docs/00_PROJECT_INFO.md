# 00 — Project Information

**Status:** Documentation baseline created; implementation status is not claimed.  
**Strategy status:** Frozen by the project-owner prompt.  
**Evidence status:** No benchmark or platform-capability claims are measured in this repository yet.  
**Owner:** `[PROJECT_OWNER]`  
**Last reviewed:** 2026-08-15

## Project identity

| Field | Canonical value | Evidence status |
| --- | --- | --- |
| Name | AEGIS | VERIFIED from project prompt |
| Full name | Autonomous Extraction Reliability & Verification System | VERIFIED from project prompt |
| Competition | Scrape-Verse 2026 | VERIFIED from project prompt |
| Track | Web-Slinger / Best Use of Bright Data | VERIFIED from project prompt |
| Primary objective | Maximize probability of winning the NVIDIA DGX Spark grand prize | VERIFIED from project prompt |
| Architecture direction | Modular monolith with event/state-driven core | FROZEN strategy |
| Current implementation | Not established by this documentation task | UNKNOWN |

## Frozen thesis

> **AEGIS detects when a web scraper has silently become wrong, uses Bright Data to repair it, independently verifies the repair with evidence, watches the repaired pipeline for regression, and proves its reliability through a controlled adversarial mutation laboratory.**

This thesis is immutable without explicit project-owner approval. Agents may refine implementation details only when they preserve the thesis, lifecycle, scope, and reliability invariants.

## Problem statement

An explicit scraper failure occurs when a website changes, a selector or extraction step breaks, and the pipeline returns no data or an obvious schema error. This is detectable because the output itself is missing or malformed.

Silent corruption is more dangerous. The website changes, the scraper continues to run, structured data continues to arrive, and the schema still appears valid; however, the extracted value is now wrong. A price may become a monthly subscription rate, a field may point to a different entity, a unit may change, or a plausible decoy may be selected. Successful extraction therefore proves transport and shape, not semantic correctness.

## Solution summary

### Executive language

AEGIS is a safety system for web data pipelines. It detects when a scraper is confidently wrong, asks Bright Data to repair the extraction, refuses to publish a repair without independent evidence, watches accepted repairs for regression, and demonstrates reliability using adversarial test cases with known answers.

### Technical language

AEGIS is a closed-loop reliability controller around Bright Data Scraper Studio. Each collection produces an Observation containing output, raw evidence where available, timestamps, and collection metadata. Detection evaluates schema, statistical, semantic, and response-level signals against an ExtractionContract and historical state. Diagnosis classifies the event and creates a structured repair request. Bright Data produces candidate repairs. Verification evaluates each candidate with deterministic evidence channels and optional semantic interpretation. The Risk Governor chooses accept, retry, quarantine, or escalate. Accepted candidates are committed only after the commit gate passes and are then monitored. Regression triggers rollback to a known-good version and re-diagnosis. Verified repair episodes are stored as memory. The Mutation Laboratory creates controlled failures and supplies ground truth to the Benchmark Engine.

## Core differentiators

AEGIS differentiates through silent-corruption detection, verification-before-commit, risk-aware decisions, quarantine, post-commit monitoring, rollback, verified repair memory, a controlled mutation laboratory, and ground-truth benchmarking. No differentiator is satisfied by a dashboard alone; each must have executable evidence and an acceptance test.

## Frozen philosophy and invariants

> **AI proposes. Evidence decides.**

1. Never commit an unverified repair.
2. Never declare extraction healthy merely because data was returned.
3. Never allow a single LLM opinion to control deployment.
4. When evidence is insufficient, quarantine beats guessing.
5. Ground-truth metrics are computed in the controlled mutation laboratory.
6. Targets are not measured results; final metrics must be actuals.
7. Silent corruption is a first-class failure category.
8. Post-commit monitoring is mandatory for accepted repairs.
9. A regression must be capable of triggering rollback.
10. Quarantine is a successful safety decision, not simply a failure.
11. Blind Commit Rate must remain 0%.

## Scope

| Scope tier | Included |
| --- | --- |
| MUST HAVE | Bright Data custom collector path; collection and observation records; multi-channel detection; diagnosis and structured repair request; Bright Data healing integration or a clearly isolated verified stub for testing; candidate verification; risk governor; quarantine; commit gate; post-commit watch; rollback path; repair episodes; deterministic mutation laboratory; frozen baselines; reproducible benchmark harness; per-severity metrics; two-minute demo; public README and submission evidence. |
| SHOULD HAVE | Raw HTML/response snapshots; response fingerprints; independent extraction path; configurable statistical baselines; bounded retries; human escalation record; compact product surface; optional WARC spike; seeded benchmark expansion. |
| OPTIONAL | WARC ingestion if platform access is reliable; fragility scoring; expanded memory retrieval; benchmark target of 540 runs; richer downstream views. |
| CUT | Authentication, accounts, billing, multi-tenancy, mobile apps, generic analytics, giant microservices, generic browser-agent features, unrelated LLM debate, and any breadth that threatens detection, verification, or the video. |

## Non-goals

AEGIS is not a generic AI scraper, selector-generation wrapper, browser agent, observability-only dashboard, RAG system, data-extraction assistant, multi-agent debate demo, predictive-maintenance research project, SaaS platform, or multi-tenant infrastructure. It is not a promise that every live website can be repaired automatically. It must quarantine uncertainty rather than claim universal healing.

## Judging and grand-prize alignment

The project-owner prompt requires alignment to six judging criteria, but does not provide their official wording. The mapping below therefore uses capability categories as a proof plan and marks the official criterion wording as an open decision.

| Judging criterion | AEGIS capability | Proof mechanism | Status |
| --- | --- | --- | --- |
| `[OFFICIAL_CRITERION_1]` | Silent-corruption problem and novel reliability thesis | Recorded green-but-wrong opening and controlled L5 fixtures | OPEN DECISION |
| `[OFFICIAL_CRITERION_2]` | Strong Bright Data / Scraper Studio use | Working custom collector, healing trace, integration notes, and public reproducibility | OPEN DECISION |
| `[OFFICIAL_CRITERION_3]` | Technical execution | Closed-loop lifecycle, state machine, safety tests, and live run | TARGET |
| `[OFFICIAL_CRITERION_4]` | Evidence and benchmark credibility | Frozen baselines, fixed seeds, ground truth, per-severity report | TARGET |
| `[OFFICIAL_CRITERION_5]` | Impact and understandability | Minimal GPU-price intelligence product surface | TARGET |
| `[OFFICIAL_CRITERION_6]` | Submission quality/compliance | Captions, measured results, AI disclosure, links, and checklist | TARGET |

**Open decision:** obtain the official judging rubric and replace placeholders without changing the project thesis.

The Web-Slinger alignment is direct: AEGIS uses a custom Bright Data Scraper Studio collector as the collection path, retains Bright Data as the actual scraper execution/healing layer, and demonstrates why reliable web extraction requires more than obtaining a syntactically valid response.

## Fact-status vocabulary

| Label | Meaning | Rule |
| --- | --- | --- |
| VERIFIED | Established by an authoritative source or completed experiment | Cite or link the evidence. |
| TARGET | Desired future outcome | Never present as achieved. |
| HYPOTHESIS | Testable expectation | Attach an experiment. |
| UNKNOWN | Not established | Do not invent behavior. |
| MEASURED | Obtained from actual execution | Preserve raw artifacts and commands. |

## References

All project-specific facts in this document are transcribed from the supplied project-owner master prompt, `pasted_content_2.txt`. External Bright Data behavior remains unverified and is tracked in `18_BRIGHT_DATA_INTEGRATION.md`.
