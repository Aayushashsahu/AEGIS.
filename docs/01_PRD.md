# 01 — Product Requirements Document

**Document status:** Canonical baseline.  
**Product status:** Documentation only; implementation not claimed.  
**Primary objective:** Win the NVIDIA DGX Spark by proving trustworthy Bright Data extraction.  
**Owner:** `[PRODUCT_OWNER]`

## Executive summary

AEGIS protects downstream consumers from silent corruption in web extraction. It observes each collection, detects anomalies across schema, statistical, semantic, and response-level channels, diagnoses the likely failure, requests a Bright Data repair, verifies candidates with evidence, and chooses among accept, retry, quarantine, and escalation. It then monitors accepted repairs, rolls back regressions, and records verified repair experience. A controlled mutation laboratory makes the reliability claim measurable.

## Problem and why now

A scraper can remain operational while becoming semantically wrong. Existing success indicators—HTTP success, non-empty JSON, field presence, or selector matches—do not establish correctness. The project must prove that a Bright Data-based extraction system can detect this class of failure and refuse to ship uncertain data. The hackathon deadline creates a strict sequencing constraint: proof of detection and verification comes before benchmark breadth or optional infrastructure.

## Target users

The primary user is an engineer responsible for a web-extraction pipeline whose output feeds a decision or product surface. The secondary user is a reliability or QA engineer who needs reproducible evidence of whether a repair worked. A judge is a third user: the demo and repository must make the reliability distinction understandable without requiring access to internal implementation details.

## User scenarios

| Scenario | Expected AEGIS behavior | Acceptance criterion |
| --- | --- | --- |
| Healthy collection | Record output and evidence; retain the pipeline in healthy/watch state. | A collection produces an immutable Observation and a traceable decision. |
| Explicit breakage | Detect missing or invalid fields and create a DetectionEvent. | A seeded structural mutation is detected or the miss is recorded with evidence. |
| Silent corruption | Detect semantic/value inconsistency, quarantine uncertain output, and prevent shipment. | An L5 fixture cannot produce a committed bad-data result in the safety test. |
| Candidate repair | Submit a structured repair request through the Bright Data boundary and evaluate returned candidates. | Every candidate has a RepairCandidate and VerificationRun before commit consideration. |
| Insufficient evidence | Retry within a bound or quarantine/escalate. | No candidate with fewer than two passing deterministic channels can commit. |
| Regression | Detect post-commit deterioration and roll back. | A seeded regression causes a RollbackEvent and returns to a known-good version. |
| Benchmark run | Execute frozen baselines and AEGIS against known mutations. | Run metadata contains seed, mutation, baseline version, configuration, outputs, and metrics. |
| Demo | Show a deterministic green-but-wrong story and evidence. | The final recording completes in two minutes with captions and no placeholder claims. |

## Primary workflow

```text
Collection
  → Observation
  → Detection
  → [healthy → Watch]
  → [anomalous → Diagnosis]
  → Repair request
  → Bright Data candidate
  → Verification
  → Risk decision
       ├─ Accept → Commit → Post-commit watch
       ├─ Retry → bounded repair attempt
       ├─ Quarantine → no downstream shipment
       └─ Escalate → human/approval workflow where available
```

## Functional requirements summary

The detailed catalog is in `04_REQUIREMENTS.md`. The product must support the following functional capabilities: collection integration, immutable observations, contract evaluation, multi-channel detection, diagnosis, structured repair requests, candidate lifecycle management, deterministic verification, risk decisions, quarantine, commit/versioning, post-commit watch, rollback, repair memory, mutation injection, benchmark execution, metric calculation, evidence export, and demo instrumentation.

## Non-functional requirements

The system must be deterministic where safety depends on it, auditable from event history, reproducible in the benchmark environment, bounded in retries and timeouts, explicit about external capability uncertainty, and small enough to implement in a one-week sprint. The modular monolith should permit isolated modules and test seams without requiring distributed deployment.

## Reliability requirements

The system must never commit an unverified repair, must treat data-returning-but-wrong as a failure, must require at least two deterministic verification channels for a commit, must support quarantine, and must support rollback from a regression. The benchmark must distinguish L5 safety from ordinary recovery and must publish measured outcomes rather than targets.

## Safety requirements

Scraped content is untrusted data. It cannot modify AEGIS policy, verification rules, access controls, or code. Secrets must remain outside fixtures and logs. External repair actions must pass an authorization boundary. Fail-closed behavior is required when the commit gate cannot establish sufficient evidence.

## Benchmark requirements

The benchmark must use controlled staging fixtures, known mutation seeds, frozen baseline configurations, fixed model settings for the naive baseline, and complete per-severity metrics. The minimum credible benchmark is the floor; the 540-run count is a target that may be reduced if it threatens core reliability or the final video.

## Demo requirements

The recorded demo must run for two minutes and include: green-but-wrong extraction in the first ten seconds; detection, diagnosis, healing, and candidate verification by 00:50; benchmark evidence by 01:20; a minimal downstream product surface and closing statement by 02:00. Captions, large typography, muted comprehension, deterministic data, and actual results are mandatory.

## Out of scope

Authentication, accounts, billing, multi-tenancy, mobile clients, a generic analytics suite, generalized browser-agent behavior, large microservice decomposition, and unbounded LLM orchestration are out of scope.

## Acceptance criteria

The product is acceptable for implementation handoff when all P0 requirements in `04_REQUIREMENTS.md` have owners, tests, and evidence paths; the Day-1 platform spikes have resolved or bounded Bright Data unknowns; the safety tests demonstrate zero blind commits on the tested path; the benchmark baselines are frozen before comparative runs; the demo sequence is deterministic; and the final repository contains no fabricated result or capability claim.

## MVP and stretch

| Tier | Scope |
| --- | --- |
| MVP | One representative collector; observation store; schema/statistical/semantic detection sufficient for the demo; diagnosis; Bright Data integration boundary; one or more repair candidates; two-channel verification; risk governor; quarantine; commit/watch/rollback; six mutation classes; three baselines; per-severity metrics; demo surface. |
| Stretch | More mutation classes, larger benchmark toward 540 runs, WARC evidence, independent second extraction path, richer repair memory retrieval, fragility scoring, and expanded downstream views. |

## Success and failure definitions

**Success** means AEGIS demonstrates, with measured controlled evidence, that it detects and safely handles silent corruption, does not blind-commit unverified repairs, can verify a correct repair, can quarantine uncertainty, and can detect and roll back a regression while preserving Bright Data centrality.

**Failure** means any unverified or wrong repair is committed, an L5 bad-data event is shipped without detection or quarantine in a claimed safety path, a single LLM opinion controls deployment, benchmark results cannot be reproduced, or the final submission relies on fabricated metrics or unverified platform claims.
