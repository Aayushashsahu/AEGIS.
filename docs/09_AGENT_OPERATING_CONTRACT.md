# 09 — Agent Operating Contract

**Purpose:** Coordinate Antigravity, Manus, Claude Code, Codex, Freebuff, Hermes, and human contributors as one engineering organization.  
**Authority:** Frozen project strategy and this contract.  
**Merge rule:** No direct commits to `main` by task agents.

## Required onboarding

Every agent reads `00_PROJECT_INFO.md`, `04_REQUIREMENTS.md`, and this document before changing files. Engineering agents also read `02_ARCHITECTURE.md`, `03_TECH_STACK.md`, `11_API_CONTRACTS.md`, `12_DATA_MODEL.md`, and `16_TESTING_STRATEGY.md`. Benchmark agents read `05_MUTATION_TAXONOMY.md`, `06_BENCHMARK_METHODOLOGY.md`, and `07_METRICS.md`. Demo/product agents read `01_PRD.md`, `08_DEMO_SCRIPT.md`, `17_OBSERVABILITY.md`, and `19_SUBMISSION_CHECKLIST.md`. Bright Data agents read `02_ARCHITECTURE.md`, `03_TECH_STACK.md`, and `18_BRIGHT_DATA_INTEGRATION.md`.

## MUST rules

Agents must preserve the thesis, lifecycle, state names, metric formulas, severity taxonomy, verification-before-commit invariant, quarantine behavior, rollback capability, and frozen baseline definitions. They must work in isolated branches or worktrees, report tests and risks, keep evidence with changes, and mark unknown behavior as `OPEN DECISION`, `UNKNOWN`, or `HYPOTHESIS` rather than filling gaps with plausible details.

## MUST NOT rules

Agents must not change the thesis, redefine metrics, weaken verification, bypass quarantine, commit directly to main, change baselines after freeze, invent benchmark results, claim Bright Data behavior without verification, expose secrets, or modify submission claims without evidence. They must not turn the project into a generic scraper, SaaS platform, multi-agent debate, or giant microservice system.

## Task assignment format

```yaml
task_id: AEGIS-<AREA>-<NUMBER>
objective: measurable outcome
files_or_components:
  - path or module
inputs_and_dependencies:
  - required prior work
acceptance_criteria:
  - executable or reviewable condition
tests_required:
  - test command or evidence
output_expectations:
  - files, report, or decision
owner: human-or-agent-id
risk_if_delayed: P0|P1|P2
```

No task is complete without a status report and evidence links.

## Completion report

```text
STATUS: COMPLETE | PARTIAL | BLOCKED
TASK ID: ...
WORK COMPLETED:
FILES CHANGED:
TESTS RUN:
RESULTS:
EVIDENCE ARTIFACTS:
RISKS:
UNRESOLVED ISSUES:
OPEN DECISIONS CREATED:
RECOMMENDATION:
```

## Branch and review protocol

Agents create one isolated branch/worktree per task, rebase only with coordination, and keep commits small enough to review. Before handoff, run the relevant tests, inspect the diff, compare contracts against canonical docs, and identify any changed assumptions. A human or designated integrator reviews changes that touch architecture, requirements, metrics, API contracts, data model, security policy, baseline manifests, or submission claims.

## Conflict resolution

When implementation and documentation disagree, stop and identify the conflict. Do not silently reconcile it. The conflict is recorded in `13_DECISION_LOG.md` or `14_RISK_REGISTER.md`, the owner decides, and the canonical document is updated before dependent work resumes. Safety invariants take precedence over convenience.

## Evidence standard

A claim is `VERIFIED` only with a source or completed experiment. A result is `MEASURED` only with raw artifacts and a reproducible command. A desired value is `TARGET`. A testable but unresolved belief is `HYPOTHESIS`. Unknown external behavior stays `UNKNOWN`.
