# AEGIS

## Autonomous Extraction Reliability & Verification System

> **AEGIS detects when a web scraper has silently become wrong, uses Bright Data to repair it, independently verifies the repair with evidence, watches the repaired pipeline for regression, and proves its reliability through a controlled adversarial mutation laboratory.**

AEGIS is the Scrape-Verse 2026 project for the **Web-Slinger / Best Use of Bright Data** track. Its sole optimization objective is to maximize the probability of winning the **NVIDIA DGX Spark** grand prize. The strategy is frozen: AEGIS is a reliability control loop around web extraction, not a generic AI scraper or a SaaS product.

## Problem

A conventional scraper failure is visible: the site changes, a selector breaks, and no data is returned. A more dangerous failure is **silent corruption**: the scraper keeps returning structurally valid data, but the value has changed meaning. For example, a product price field may contain a valid-looking subscription price after a page redesign. The pipeline is technically green while downstream users receive incorrect data.

## Why existing self-healing is not enough

Returning data is not evidence that the data is correct. A repair that restores JSON, fields, or selector matches can still select the wrong entity, wrong unit, wrong field, or a plausible decoy value. AEGIS therefore separates repair proposal from deployment authority. Bright Data is the execution and healing layer; AEGIS supplies detection, evidence-based verification, risk decisions, quarantine, monitoring, rollback, and reproducible measurement.

## How AEGIS works

```text
OBSERVE → DETECT → DIAGNOSE → REPAIR → VERIFY → RISK DECISION
       → COMMIT / RETRY / QUARANTINE → POST-COMMIT WATCH
       → ROLLBACK IF NECESSARY → RECORD MEMORY
```

The governing principle is:

> **AI proposes. Evidence decides.**

Deterministic contracts, invariants, statistical tests, response evidence, and risk rules—not a single LLM opinion—control commit, quarantine, retry, and rollback decisions.

## Architecture

AEGIS is a **modular monolith with an event/state-driven core**. Its principal modules are Collection, Observation, Detection, Diagnosis, Repair Orchestration, Verification, Risk Governor, Quarantine, Commit, Post-Commit Watch, Rollback, Repair Memory, Mutation Laboratory, Benchmark Engine, and a minimal downstream product surface.

Bright Data Scraper Studio remains central. The system must preserve a strong Bright Data integration while making all unverified external behavior explicit as an open technical decision until a Day-1 experiment verifies it.

## Silent corruption

The mutation laboratory creates controlled failures with known ground truth. L5 mutations include column swaps, unit swaps, plausible decoys, wrong semantic fields, and wrong entity associations. L5 is not ordinary recovery: the safety objective is to detect, quarantine, re-extract or repair, verify, and ensure that incorrect data is not shipped.

## Verification

A candidate repair is not accepted merely because HTTP succeeds, JSON exists, fields exist, or a selector returns something. AEGIS may combine extraction contracts, historical consistency, statistical consistency, independent evidence, a second extraction path, raw response evidence, and semantic checks. The minimum commit gate is at least two independent deterministic verification channels, with no blind commits.

## Mutation laboratory and benchmark

The laboratory represents five severity levels: L1 Cosmetic, L2 Structural, L3 Semantic, L4 Behavioral, and L5 Silent Corruption. Headline reliability metrics are computed against controlled ground truth, not arbitrary live production websites. The minimum credible benchmark has six mutation classes, all five severity levels, at least two L5 modes, ten trials per class, three frozen baselines, fixed seeds, and complete metrics. **No measured results are claimed in this repository until experiments produce them.**

## Results

Results are intentionally placeholders until measured:

| Metric | Target | Measured result |
| --- | ---: | --- |
| Detection Rate | ≥90% | `[MEASURED_RESULT]` |
| Alarm Precision | ≥90% | `[MEASURED_RESULT]` |
| Verified Recovery | ≥85% | `[MEASURED_RESULT]` |
| Verification Miss Rate | <1% | `[MEASURED_RESULT]` |
| Blind Commit Rate | 0% | `[MEASURED_RESULT]` |
| L5 bad-data-shipped rate | Safety objective | `[MEASURED_RESULT]` |

Targets are not results. The benchmark report must include per-severity results and the exact environment, seeds, configurations, and output artifacts needed for reproduction.

## Bright Data integration

The integration contract covers Scraper Studio collectors, structured output, execution, healing, approval, versioning, rollback, raw response evidence, WARC where available, and coding-agent interaction. The current documentation deliberately distinguishes project strategy from unverified platform behavior. See [`docs/18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md).

## Demo

The primary artifact is a deterministic two-minute recorded video. It opens with a green-but-wrong extraction, shows detection, diagnosis, Bright Data healing, candidate verification, commit or rejection, benchmark evidence, and a small GPU-price intelligence surface. Captions, large text, muted-video comprehension, and actual measured values are mandatory. See [`docs/08_DEMO_SCRIPT.md`](docs/08_DEMO_SCRIPT.md).

## Quick start

Mission 002 implements the first vertical slice: a narrow Bright Data CLI adapter seam, asynchronous collection state snapshots, immutable untrusted Observations, a typed ExtractionContract, deterministic schema/statistical/semantic detection, and a clearly labeled `TEST_DOUBLE` path. Healing, candidate verification, risk decisions, rollback, memory, benchmarking, and UI remain out of scope for this mission.

```bash
cd AEGIS
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The live Bright Data artifact from Mission 001 is converted into an untrusted Observation by `tests/integration/test_mission001_artifact_to_observation.py`. The provider adapter uses injected command execution so tests do not require credentials or provider credits. Implementation agents must first read [`docs/00_PROJECT_INFO.md`](docs/00_PROJECT_INFO.md), [`docs/04_REQUIREMENTS.md`](docs/04_REQUIREMENTS.md), and [`docs/09_AGENT_OPERATING_CONTRACT.md`](docs/09_AGENT_OPERATING_CONTRACT.md). They must not invent platform capabilities, measured results, endpoints, or schema behavior.

## Repository structure

```text
README.md
docs/              Canonical internal documentation
experiments/       Day-1 spikes and experiment records
mutations/         Controlled mutation fixtures and manifests
benchmarks/        Frozen baselines, runs, and reports
scripts/           Reproducible commands and operational tooling
src/               Mission 002 collection/observation/detection implementation
tests/             Mission 002 unit and integration tests
```

## Limitations and open decisions

The repository does not claim a completed healing API integration, candidate verification, risk governor, rollback, recovery rate, benchmark result, or production deployment. Mission 002 uses the Bright Data CLI path verified in Mission 001 only as an adapter boundary and preserves the provider output as untrusted. Provider-native version/rollback, raw response access, WARC availability, and exact LLM configuration remain open decisions tracked in [`docs/18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md).

## AI usage disclosure

AI agents may assist with implementation, diagnosis, semantic interpretation, repair-request generation, documentation, and test generation. AEGIS policy remains deterministic at verification, risk decision, commit, quarantine, and rollback boundaries. The final submission must disclose the actual tools and models used by the team and must not claim work that was not performed.

## License

`[PROJECT_OWNER_LICENSE_DECISION]`

## Canonical documentation

| Area | Document |
| --- | --- |
| Identity and strategy | [`00_PROJECT_INFO.md`](docs/00_PROJECT_INFO.md) |
| Product requirements | [`01_PRD.md`](docs/01_PRD.md) |
| Architecture | [`02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md) |
| Technology decisions | [`03_TECH_STACK.md`](docs/03_TECH_STACK.md) |
| Requirements catalog | [`04_REQUIREMENTS.md`](docs/04_REQUIREMENTS.md) |
| Mutations and benchmarks | [`05_MUTATION_TAXONOMY.md`](docs/05_MUTATION_TAXONOMY.md), [`06_BENCHMARK_METHODOLOGY.md`](docs/06_BENCHMARK_METHODOLOGY.md), [`07_METRICS.md`](docs/07_METRICS.md) |
| Agent and execution rules | [`09_AGENT_OPERATING_CONTRACT.md`](docs/09_AGENT_OPERATING_CONTRACT.md), [`10_EXECUTION_PLAN.md`](docs/10_EXECUTION_PLAN.md) |
| Contracts and data | [`11_API_CONTRACTS.md`](docs/11_API_CONTRACTS.md), [`12_DATA_MODEL.md`](docs/12_DATA_MODEL.md) |
| Trust and operations | [`15_SECURITY_AND_TRUST.md`](docs/15_SECURITY_AND_TRUST.md), [`16_TESTING_STRATEGY.md`](docs/16_TESTING_STRATEGY.md), [`17_OBSERVABILITY.md`](docs/17_OBSERVABILITY.md) |
| Bright Data and submission | [`18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md), [`19_SUBMISSION_CHECKLIST.md`](docs/19_SUBMISSION_CHECKLIST.md) |
