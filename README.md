# AEGIS

## Autonomous Extraction Reliability & Verification System

> **A scraper can be green and still be wrong.**

AEGIS is a reliability control layer around **Bright Data Scraper Studio**. It detects obvious extraction failures and silent semantic corruption, evaluates repair candidates with deterministic evidence, and fails closed when the evidence is incomplete. Bright Data provides collection and Self-Healing capabilities; AEGIS supplies detection, verification, risk control, evidence retention, and the final release boundary.

> **AI proposes. Evidence decides.**

## Current status

The repository is a complete, cloneable judge-facing release. It contains real Bright Data evidence, controlled mutation evidence, a provider-free web application, and deterministic safety gates. It **does not** claim a successful real post-heal recovery or shipment of corrected provider output.

| Area | Current evidence-backed status |
| --- | --- |
| Real collector and extraction | **Recorded** |
| Real drift, candidate, verification, and risk | **Recorded** |
| Real approval and post-approval rerun | **Recorded** |
| Corrected real provider output | **Not established** |
| Verification, risk, commit, and shipment after incomplete output | **FAIL / REJECT / BLOCKED / NO** |
| Silent-corruption demonstration | **Controlled replay — explicitly `TEST_DOUBLE`** |
| Provider recovery lane | **Frozen pending a documented Bright Data support remedy** |

## The problem

Many scraper failures are visible: a selector breaks and no data is returned. The more dangerous class is **silent corruption**: JSON is valid and fields exist, but the value has the wrong meaning. A price can become a subscription value, a decoy offer, or a value from the wrong entity while the scraper still appears healthy.

AEGIS treats HTTP success, parse success, and field presence as observations—not proof of correctness. A candidate cannot be committed solely because a model or a provider believes it repaired the scraper.

## Lifecycle and authority boundary

```text
Collection → Observation → Detection → Diagnosis → Repair request
          → Candidate → Verification → Risk decision → Commit / Reject / Quarantine
          → Post-commit watch → Rollback if a separately authorized release regresses
```

The normal path is intentionally light: a healthy observation continues monitoring. The repair path activates only when evidence indicates a meaningful failure. Deterministic contracts, semantic invariants, historical checks, raw-response evidence, and risk policy decide whether a candidate is eligible for a later release stage.

`ACCEPT` is **not** a provider approval, production publish, shipment, or rollback. Those actions require separate owner authority and provider-specific evidence.

## What the real evidence shows

The preserved evidence is the source of truth. These rows describe individual records, not generalized service-level claims.

| Evidence stream | Observed fact | Safety boundary |
| --- | --- | --- |
| [Mission 029 collection](experiments/mission_029/) | A real Bright Data collector produced 150 structured Hacker News rows. | A later compact heal failed before candidate creation; no repair outcome was inferred. |
| [Missions 033–041B owned-target chain](experiments/mission_033_live_bright_data_success/) | A real candidate was produced after controlled drift and passed deterministic candidate verification/risk. Mission 040 recorded one approval; Mission 041B recorded one post-approval rerun. | The rerun returned only `input.url`; required `title`, `price`, and `availability` were missing. AEGIS returned `FAIL / REJECT / BLOCKED / data_shipped=NO`. |
| [Mission 050 causal boundary](experiments/mission_050/) | The provider response was incomplete despite HTTP 200. | AEGIS marks the provider-internal cause `UNKNOWN` with low confidence rather than inventing a root cause. |
| [Mission 028 benchmark](benchmarks/) | Controlled mutation evidence preserved 180 opportunities, including 179 completed and one provider failure. | Benchmark metrics belong to the frozen controlled harness; they are not claims about live Bright Data reliability. |
| Controlled silent-corruption replay | Canonical deterministic verification, risk, and commit-gate modules reject a plausible but incorrect value. | The replay is labeled `TEST_DOUBLE` / `CONTROLLED_REPLAY`, never real provider output. |

## How AEGIS verifies a candidate

AEGIS does not rely on an LLM alone. Depending on the contract and available evidence, verification can combine:

- schema and required-field checks;
- historical and statistical consistency;
- semantic invariants and independent owned-target evidence;
- raw-response and alternate-extraction evidence; and
- explicit provenance and correlation checks.

The Risk Governor and CommitGate consume those records. Missing evidence, unknown causal state, unverified candidates, invalid authorization, and absent known-good references fail closed to **BLOCKED**, **REJECT**, or **QUARANTINE**.

## Real provider versus controlled replay

| Provenance label | Meaning |
| --- | --- |
| `REAL_PROVIDER` | A preserved Bright Data action or response actually occurred. |
| `AEGIS_DETERMINISTIC` | A canonical deterministic verification, risk, or commit decision evaluated evidence. |
| `TEST_DOUBLE` / `CONTROLLED_REPLAY` | A deterministic local fixture used to demonstrate expected safety behavior. It is not provider output. |

Coding agents assist with implementation, diagnosis, repair-request drafting, documentation, and inspection. They do not authorize provider operations or releases. The deterministic verification, risk, commit, and owner-authorization boundaries remain authoritative.

## Web application

`webapp/` is a provider-free, judge-facing tRPC application. It reads canonical repository records through a narrow adapter and does not embed a second AEGIS implementation.

Judge Mode starts with the real provider causal boundary: HTTP 200, `input.url` only, missing required fields, verification failure, risk rejection, commit blocked, and no shipped data. It also exposes the support-pending ledger and keeps the candidate-to-decision silent-corruption replay visually separate.

The public UI exposes **no** live Bright Data, benchmark, approval, commit, rollback, or provider-mutation control. New public cases persist only bounded configuration data and do not create lifecycle evidence.

### Run locally

```bash
git clone <repository-url> AEGIS
cd AEGIS/webapp
pnpm install
pnpm dev
```

The web adapter resolves the canonical repository through `AEGIS_ROOT` or root markers. Set `AEGIS_PYTHON` only when automatic `python3` / `python` discovery is unsuitable.

```bash
# Canonical provider-free tests
cd AEGIS
PYTHONPATH=.:src pytest -q

# Web application tests and production build
cd webapp
AEGIS_ROOT=.. AEGIS_PYTHON=python3 pnpm test
AEGIS_ROOT=.. AEGIS_PYTHON=python3 pnpm build
```

## Repository layout

```text
README.md        Project guide and release boundary
docs/            Canonical requirements, architecture, policy, and contracts
experiments/     Append-only real-provider and controlled evidence records
mutations/       Controlled mutation fixtures and manifests
benchmarks/      Frozen baselines, runs, and reports
scripts/         Reproducible provider-free projections and tooling
src/             Canonical AEGIS domain logic
tests/           Unit, integration, evidence, and safety coverage
webapp/          Cloneable judge-facing frontend, API, and canonical-root adapter
```

## Limitations

AEGIS does not claim a successful real Self-Healing loop, corrected real output shipment, provider-native production commit, provider-native rollback, public deployment, or an inferred provider-internal root cause. The exact production-version binding, version/rollback behavior, raw-response availability, WARC delivery, and support diagnosis remain open where the provider has not supplied evidence.

Do not authorize a new provider experiment unless a concrete documented Bright Data support remedy exists and a separate bounded authorization identifies the collector, operation, budget, raw-first capture rule, stop condition, and commit prohibition.

## Documentation and demo

The final judge narration is in [Mission 066’s final-day demo script](experiments/mission_066_final_day_release_hardening/final_day_demo_script.md). The latest validated release record is [Mission 066’s terminal report](experiments/mission_066_final_day_release_hardening/terminal_report.md).

| Area | Canonical document |
| --- | --- |
| Identity and strategy | [`docs/00_PROJECT_INFO.md`](docs/00_PROJECT_INFO.md) |
| Product requirements and architecture | [`docs/01_PRD.md`](docs/01_PRD.md), [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md) |
| Requirements, contracts, and data | [`docs/04_REQUIREMENTS.md`](docs/04_REQUIREMENTS.md), [`docs/11_API_CONTRACTS.md`](docs/11_API_CONTRACTS.md), [`docs/12_DATA_MODEL.md`](docs/12_DATA_MODEL.md) |
| Benchmarking and metrics | [`docs/05_MUTATION_TAXONOMY.md`](docs/05_MUTATION_TAXONOMY.md), [`docs/06_BENCHMARK_METHODOLOGY.md`](docs/06_BENCHMARK_METHODOLOGY.md), [`docs/07_METRICS.md`](docs/07_METRICS.md) |
| Security, testing, and operations | [`docs/15_SECURITY_AND_TRUST.md`](docs/15_SECURITY_AND_TRUST.md), [`docs/16_TESTING_STRATEGY.md`](docs/16_TESTING_STRATEGY.md), [`docs/17_OBSERVABILITY.md`](docs/17_OBSERVABILITY.md) |
| Bright Data integration and submission | [`docs/18_BRIGHT_DATA_INTEGRATION.md`](docs/18_BRIGHT_DATA_INTEGRATION.md), [`docs/19_SUBMISSION_CHECKLIST.md`](docs/19_SUBMISSION_CHECKLIST.md) |

## License

License selection remains a project-owner decision.
