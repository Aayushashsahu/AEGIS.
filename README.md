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

## Evidence at a glance

AEGIS distinguishes **live provider evidence** from **controlled-harness measurement**. The following records are preserved facts, not generalized SLAs or production reliability claims.

| Evidence stream | Verified fact | Boundary |
| --- | --- | --- |
| Mission 029 Bright Data collection | Fresh collector `c_msyo46bp1slx64351` produced 150 structured Hacker News rows; the CLI observed realtime-to-batch fallback. | One public-target demonstration; output remained untrusted. |
| Mission 030 compact heal | The provider transport projection was reduced from 1,187 to 676 characters, under the documented 1,000-character limit. The single authorized heal then failed with provider HTTP 500 before candidate creation. | No candidate, approval, verification, commit, shipment, or retry by AEGIS. |
| Missions 033–041B owned-target recovery chain | Collector `c_mt09pib13nxqz1coi` captured a real baseline and same-URL drift, produced an `awaiting_approval` candidate with the required fields, and passed deterministic candidate verification/risk assessment. Mission 040 then recorded one real approval (`HTTP 200`, `RESUME_ACCEPTED`); Mission 041B recorded one real post-approval rerun (`HTTP 200`). | The rerun returned only `input.url`; `title`, `price`, and `availability` were missing. AEGIS therefore produced verification `FAIL`, risk `REJECT`, commit `BLOCKED`, and `data_shipped=NO`. This is a real fail-closed outcome, **not** a successful recovery. |
| Mission 028 recovery benchmark | 180 opportunities were preserved: 179 completed, 1 provider failure, and 38 metric artifacts. | The AEGIS metric scope is the controlled `TEST_DOUBLE` harness, not live Bright Data reliability. |
| Controlled AEGIS safety metrics | DetectionRate `50/50`; L5DetectionRate `20/20`; L5BadDataShipped `0/20`. | Measured against frozen controlled mutation ground truth only. |

The NVIDIA NIM baseline uses `openai/gpt-oss-20b` under a **benchmark-side** 6 RPM, 10-second minimum interval, concurrency-1 throttle. The provider limit is explicitly **UNKNOWN**.

## Bright Data integration

The integration contract covers Scraper Studio collectors, structured output, execution, healing, approval, versioning, rollback, raw response evidence, WARC where available, and coding-agent interaction. The current documentation deliberately distinguishes project strategy from unverified platform behavior. See [`docs/18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md).

## What is real, what is controlled, and how agents participated

**REAL_PROVIDER** evidence is preserved only where Bright Data actually created, executed, healed, approved, or reran a collector. The decisive real failure case is Mission 041B: a provider `HTTP 200` rerun returned incomplete structured output and AEGIS blocked shipment. **TEST_DOUBLE** and **CONTROLLED_REPLAY** paths are deterministic local fixtures used to prove expected PASS/ACCEPT and FAIL/REJECT behavior; they are intentionally labeled and never presented as provider output. Coding agents participated as implementation and inspection operators through the documented Bright Data CLI/IDE workflow, but agent suggestions never authorize a provider change or a data release: deterministic verification, RiskGovernor, CommitGate, and explicit owner authorization remain required.

## Downstream value

AEGIS turns trusted structured extraction into a safer input for **price intelligence, change monitoring, structured analytics, and decision support**. Its downstream value is not a second generic dashboard: it is the evidence boundary that prevents silently corrupted `title`, `price`, or `availability` values from reaching any downstream product. A passed extraction remains untrusted until the verification and risk gates establish an admissible evidence chain.

## Web application and demo

`webapp/` is the frozen supplied frontend with a narrow tRPC boundary. It reads **canonical** `src/aegis/`, `benchmarks/`, `experiments/`, and `scripts/` from the repository root; it does not contain a second AEGIS implementation or copied evidence. Mission 029/030, Mission 033–041B, and later provider diagnostics are read-only `REAL_PROVIDER` evidence. Judge Mode presents the decisive Mission 041B causal boundary — provider `HTTP 200`, incomplete output, verification `FAIL`, risk `REJECT`, commit `BLOCKED`, data shipped `NO` — without offering a live action. Candidate through commit eligibility is also available as a separately labeled `TEST_DOUBLE` replay. The web UI exposes no live provider, benchmark, approval, commit, or rollback action.

The default web mode is provider-free. Public demo case creation persists only a bounded configuration contract; it never persists lifecycle decisions or invokes a provider. Its input and in-memory rate limits are deliberately modest demonstration safeguards rather than an identity system.

### Linux and macOS

```bash
git clone <repository-url> AEGIS
cd AEGIS/webapp
pnpm install
pnpm dev
```

### Windows PowerShell

```powershell
git clone <repository-url> AEGIS
cd AEGIS\webapp
pnpm install
$env:AEGIS_PYTHON = "python"
$env:AEGIS_ROOT = (Resolve-Path ..).Path
pnpm dev
```

The adapter uses `AEGIS_PYTHON` first, then discovers `python3`/`python`, and resolves the repository through `AEGIS_ROOT` or canonical root markers. From the repository root, run `PYTHONPATH=src:. python3 scripts/run_demo.py` for the provider-free replay DemoSession. Use [`experiments/mission_031/judge_script.md`](experiments/mission_031/judge_script.md) for the approximately 2:30 narration and [`experiments/mission_031/architecture.mmd`](experiments/mission_031/architecture.mmd) for the architecture diagram source.

## Final hackathon package

The final judge path is documented in [`experiments/mission_032/final_demo_script.md`](experiments/mission_032/final_demo_script.md) and strengthened by the [Mission 033 real-provider evidence summary](experiments/mission_033_live_bright_data_success/summary.json) plus the [Mission 041B post-heal rerun summary](experiments/mission_041_post_heal_rerun/summary.json). It can show Mission 029/030’s terminal no-candidate lane, Mission 033’s real candidate-through-verification lane, the real Mission 040 approval and Mission 041B fail-closed rerun, and a `TEST_DOUBLE` controlled replay for silent-corruption refusal. The package also includes the [architecture](experiments/mission_032/architecture.md), [evidence map](experiments/mission_032/evidence_map.md), [demo checklist](experiments/mission_032/demo_checklist.md), and [submission description](experiments/mission_032/submission_description.md).

The demo-video location is **TBD by the project owner**. The release is deployment-ready but not publicly deployed by this task; see [`webapp/DEPLOYMENT.md`](webapp/DEPLOYMENT.md). Scraper Studio workflow details and the AI-use disclosure remain bounded by the authenticated evidence and policy records in this repository; no provider action occurs on page load.

## Canonical Python quick start

Missions 002–030 extend the stable collection path through immutable Observation, deterministic Detection, Diagnosis, provider-neutral RepairRequest, bounded Bright Data healing, candidate Verification, RiskGovernor decisions, a fail-closed CommitGate, frozen benchmark execution, live-provider evidence capture, compact prompt projection, and read-only evidence loading. Mission 031 adds the provider-free Judge Mode snapshot and explicit controlled replay boundary. `ACCEPT` means eligible for a later commit stage only; it does not approve Bright Data, activate a provider version, commit production data, or perform rollback.

```bash
cd AEGIS
PYTHONPATH=src pytest -q tests/unit tests/integration
```

The recorded Bright Data artifact from Mission 001 is tested through `Observation → DetectionResult → Diagnosis → RepairRequest → RepairCandidate → Verification → RiskDecision → CommitGate`; it remains provider evidence and does not claim candidate correctness or provider-native commit behavior. Mission 006 tests use deterministic local `TEST_DOUBLE` scenarios and do not require credentials or provider credits. Implementation agents must first read [`docs/00_PROJECT_INFO.md`](docs/00_PROJECT_INFO.md), [`docs/04_REQUIREMENTS.md`](docs/04_REQUIREMENTS.md), and [`docs/09_AGENT_OPERATING_CONTRACT.md`](docs/09_AGENT_OPERATING_CONTRACT.md). They must not invent platform capabilities, measured results, endpoints, or schema behavior.

## Repository structure

```text
README.md
docs/              Canonical internal documentation
experiments/       Immutable provider and controlled evidence records
mutations/         Controlled mutation fixtures and manifests
benchmarks/        Frozen baselines, runs, and reports
scripts/           Reproducible provider-free projections and tooling
src/               Canonical AEGIS collection, detection, verification, risk, commit, benchmark, and evidence modules
tests/             Canonical unit and integration evidence/safety coverage
webapp/            Frozen supplied frontend, tRPC API, configuration persistence, and canonical-root adapter
```

## Limitations and open decisions

The repository does not claim a successful real self-heal loop, corrected live output shipment, provider-native commit, provider-native rollback, or production deployment. Mission 040 records a real provider approval and Mission 041B records a real post-approval rerun, but that rerun failed AEGIS’s required-field contract and remained blocked. The Mission 030 HTTP 500 root cause remains unresolved; later Mission 053, 056, and 059 healing attempts reached provider terminal errors before candidate generation, and no support response is fabricated. `REJECT`, `QUARANTINE`, unknown evidence, missing known-good references, invalid authorization, and `UNVERIFIED` candidates remain blocked. Exact current production-version binding, provider-native version/rollback behavior, raw response access, WARC delivery, and exact LLM configuration remain open decisions tracked in [`docs/18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md).

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
