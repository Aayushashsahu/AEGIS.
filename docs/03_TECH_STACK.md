# 03 — Technology Stack

**Status:** Directional stack contract. Specific libraries are open until Day-1 spikes and repository constraints are known.  
**Selection rule:** Minimize infrastructure; every technology must support detection, verification, reproducibility, or the demo.

## Stack decision matrix

| Technology area | Candidate direction | Purpose | Status |
| --- | --- | --- | --- |
| Frontend | Minimal server-rendered or lightweight web UI | Show trustworthy GPU-price output, status, evidence, and benchmark summary | OPEN DECISION |
| Backend | Single modular service | Orchestrate lifecycle, APIs, state, and safety gates | TARGET |
| Database | Relational persistence or append-only local store for MVP | Store entities, relationships, state, and audit trail | OPEN DECISION |
| Cache/queue | In-process bounded queue initially; external queue only if required by Bright Data latency | Schedule asynchronous repair and watch work | HYPOTHESIS |
| Browser automation | Only if required by the selected collector/fixture | Support controlled staging behavior | OPEN DECISION |
| Bright Data | Scraper Studio custom collector and healing boundary | Collection and actual scraper repair execution | REQUIRED; platform behavior UNKNOWN until verified |
| LLM | One pinned model/configuration for naive baseline; optional bounded model for diagnosis | Semantic interpretation and repair-request proposal | OPEN DECISION |
| Storage | Local/object storage for raw evidence and benchmark artifacts | Preserve HTML, fingerprints, outputs, and reports | OPEN DECISION |
| Testing | Unit, integration, system, mutation, safety, regression, and demo tests | Verify contracts and invariants | REQUIRED |
| Benchmark tooling | Seeded runner with immutable manifests | Execute baselines and calculate metrics | REQUIRED |
| Deployment | Simplest reproducible environment that supports the demo | Run live system and recorded capture | OPEN DECISION |
| Observability | Structured logs, lifecycle events, correlation IDs, and evidence links | Debug and prove behavior | REQUIRED |

## Technology evaluation template

Each adopted technology must have a record with the following fields:

| Field | Required content |
| --- | --- |
| Technology | Exact name and version once selected. |
| Purpose | One responsibility in AEGIS. |
| Why selected | Evidence that it reduces risk or time. |
| Alternatives considered | At least one credible alternative. |
| Why alternatives rejected | Concrete project-specific reason. |
| Dependencies | Runtime, credentials, network, or platform dependencies. |
| Known risks | Failure modes and unknown behavior. |
| Fallback | How the MVP proceeds if it fails. |

## Selection constraints

The stack must support immutable observations, deterministic verification, bounded retries, version-aware rollback, seeded mutation execution, and exportable benchmark artifacts. A technology that makes those properties harder is rejected regardless of popularity. A distributed system is not justified merely for prestige.

## Bright Data constraints

Bright Data is not replaceable by a generic local scraper in the product thesis. A local fixture collector may be used for deterministic laboratory testing, but the submission path must preserve the custom Scraper Studio collector and documented healing interaction. API routes, CLI commands, authentication, approval, response evidence, and versioning remain unknown until verified; the integration document must not state them as facts prematurely.

## LLM constraints

The LLM may diagnose, classify, interpret semantics, generate a repair request, or critique a candidate. It must not be the sole authority for verification, risk, commit, quarantine, or rollback. The benchmark’s naive LLM baseline must pin model identity, prompt, configuration, and first-candidate behavior before the benchmark begins. AEGIS and the baseline must be distinguishable in code and artifacts.

## Database and event rules

Whatever persistence technology is selected, lifecycle records must be append-friendly and queryable by pipeline, collection, episode, mutation, benchmark run, and correlation ID. State changes must be auditable. Destructive updates are prohibited for evidence and benchmark artifacts; corrections should be represented as new events or versioned records.

## Fallback strategy

If an external dependency is unavailable, the system may use a contract-preserving adapter backed by deterministic fixtures for development and safety tests. The fallback must be labeled as a test double, must not be presented as Bright Data behavior, and must not be used to claim a completed integration. The core evidence and decision interfaces should remain identical across real and test adapters.
