# 10 — Seven-Day Execution Plan

**Planning assumption:** Seven consecutive work days are available.  
**Priority order:** Detection → Verification → Video → Baselines → Benchmark expansion → Memory → Network/WARC → Fragility scoring.  
**Kill rule:** Cut optional breadth before cutting the core reliability proof or video.

## Day plan

| Day | Objectives and P0 tasks | P1 tasks | Owners | Dependencies | Artifacts | Exit criteria | Kill criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Day 1 | Run Bright Data collector, healing, latency, staging, silent-corruption injection, and detector risk spikes. | WARC/raw-response exploration; model/provider comparison. | BD, detection, infra | Credentials and test site/fixture | Spike reports, capability matrix, first evidence bundle, detector prototype | Every critical external unknown has a verified behavior or bounded fallback; one L5 detector path demonstrates signal. | Stop optional WARC/model work if it threatens collector, healing, or detector spike. |
| Day 2 | Implement detection channels, mutation lab v1, benchmark harness foundation. | Add response fingerprint and baseline statistics. | Detection, benchmark | Day-1 fixture and observation shape | Mutation manifests, seeded runner, detector tests | All five severity levels represented in fixtures; six-class floor is feasible. | Cut expansion if reset determinism or L5 injection is unstable. |
| Day 3 | Implement repair orchestration, verification, risk governor, and freeze baselines. | Repair memory schema and retrieval stub. | Repair, verification, benchmark | Day-1 Bright Data boundary; Day-2 contracts | Candidate lifecycle, commit gate, safety tests, frozen A/B/C configs | Candidate cannot commit without two deterministic channels; baseline files are committed. | Cut memory and advanced provider features before verification. |
| Day 4 | Expand benchmark, implement product surface, run optional network/WARC spike. | Improve evidence display and independent extraction path. | Benchmark, product, BD | Core lifecycle and frozen baselines | Benchmark runs, product view, raw evidence adapter | Minimum benchmark floor runs end-to-end; product never shows quarantined current data. | Stop benchmark expansion or WARC if core run is unreliable. |
| Day 5 | Calibrate thresholds, lock metrics, begin video production. | Add watch/rollback trace and polish captions. | QA, metrics, demo | Benchmark floor and stable lifecycle | Metrics spec output, threshold decision, first video take | Formulas and targets locked; actual-vs-target review passes; video sequence rehearses. | Cut optional features, not safety tests or video. |
| Day 6 | Complete final benchmark, harden, record final video, validate submission package. | Re-run selected regressions and environment setup. | All, integrator | Metrics lock and final fixture | Final run/report, video, README, evidence bundle | Final metrics reproducible; video is readable/muted; release gate passes. | Reduce benchmark toward floor; never fabricate missing results. |
| Day 7 | Submission only: final links, eligibility, repository, video, disclosure, review. | None unless a submission blocker is found. | Owner, submission lead | All artifacts complete | Submitted links and archive | Every checklist item has owner/sign-off; no code strategy changes. | Do not introduce new features. |

## Work-in-progress limits

At most one active P0 task per core subsystem should be merged at a time. Benchmark and demo work may consume stable outputs but must not change detector, verifier, or metric behavior without a documented decision and rerun.

## Go/no-go gates

* **Gate 1, end of Day 1:** Bright Data and staging assumptions are known or isolated behind explicit adapters.
* **Gate 2, end of Day 2:** A seeded L5 mutation produces a reproducible safety test.
* **Gate 3, end of Day 3:** No unverified candidate can commit; baselines are frozen.
* **Gate 4, end of Day 4:** Benchmark floor and product surface work end-to-end.
* **Gate 5, end of Day 5:** Metrics are locked and demo is recordable.
* **Gate 6, end of Day 6:** Final artifacts are reproducible and submission-ready.

## Dependency and reporting cadence

Start each day with a 15-minute plan against the gates and end with a written evidence report. Blocked work must state the decision needed, the impact on P0, and the fallback. The integrator maintains the decision log, risk register, and final consistency audit.
