# AEGIS Mission 031 — Judge-readiness audit and live-provider authorization protocol

**Status:** Audit complete; no Mission 031 provider operation has executed.
**Branch:** `mission-031-judge-winning-aegis`
**Rule:** Historical evidence is immutable. Live provider output, controlled mutation evidence, and test-double replay must remain visually and technically distinct.

## Executive finding

AEGIS already contains the technical ingredients of a credible reliability-control demonstration: a real Bright Data collector creation and run, an evidence-only mutation, deterministic detection, a bounded repair boundary, deterministic verification, explicit risk decisions, a fail-closed commit gate, and a reproducible controlled-harness benchmark. What is missing is **one coherent, provenance-safe presentation layer**. The current public Evidence Ledger is honest but narrow: it has a browser-side dependency on pinned GitHub raw URLs, it ends at the true provider failure, and it does not show the already-existing controlled verification path needed to demonstrate the core thesis.

> **Design decision:** Mission 031 will not turn a historical HTTP 500 into a success narrative. It will show the real termination exactly, then offer an explicitly labeled, provenance-separated `TEST_DOUBLE / CONTROLLED REPLAY` that demonstrates why a plausible candidate can be rejected and withheld.

## Dependency map

| Layer | Existing source of truth | What is verified | Mission 031 action |
|---|---|---|---|
| Bright Data collection | `experiments/mission_029/` and Mission 001 evidence | Real `c_*` collector, structured output, and realtime-to-batch fallback are preserved | Keep collector identifiers and operation counts visible; do not recreate historical facts |
| Provider healing | Mission 001 result; `experiments/mission_030/operation_001.json` | Mission 001 captured `awaiting_approval`; Mission 030 captured a corrected 676-character prompt followed by terminal 500 before candidate | Explain the two states separately; do not infer candidate success from either |
| Observation / detection / diagnosis | `src/aegis/detection.py`, `diagnosis.py`, Mission 029 artifacts | Controlled evidence mutation and deterministic detection are real AEGIS artifacts | Create a high-contrast corruption moment from the committed mutation only |
| Verification / risk / commit gate | `verification.py`, `risk.py`, `commit_gate.py`, `verification_double.py` | A deterministic TEST_DOUBLE candidate can fail independent semantic evidence and be rejected/quarantined without shipment | Materialize an immutable replay snapshot through the actual modules and label it `TEST_DOUBLE` |
| Evidence loader | `mission030_evidence.py` and current TypeScript loader | Read-only validation rejects malformed/unsafe evidence and exposes unreached states | Replace browser-side raw-GitHub primary dependency with a pinned, build-time bundled snapshot and a local normalizer |
| Benchmark | Mission 028 recovery artifacts | 180 planned/terminal opportunities, 179 completed and 1 provider failure; controlled AEGIS metric scope only | Present a compact summary with no unsupported baseline comparison claim |
| Product surface | Current Evidence Ledger | Read-only historical timeline and raw artifact inspector | Replace it with dedicated Judge Mode, evidence drawers, source labels, replay switch, and a benchmark card |

## Evidence-backed gaps and priority

| Priority | Gap | Evidence | Consequence if unaddressed | Corrective boundary |
|---:|---|---|---|---|
| P0 | Historical demo mutation does not change the Bright Data collector or external page | Mission 029 mutation marks `AEGIS_EVIDENCE_ONLY` | A live heal request against that collector is not a repair of a demonstrably broken live scraper | Never describe the mutation as a live provider defect; use it only as controlled detection evidence |
| P0 | The Mission 030 500 is terminal before candidate creation | One provider envelope records 676 characters and `heal_trigger_failed` | The UI cannot honestly show live verification, risk, or commit | Represent those stages as `NOT_CREATED` / `NOT_RUN`; do not add fake completion controls |
| P0 | Current web UI fetches GitHub raw artifacts in the browser | `mission029Evidence.ts` pins a raw GitHub URL | Offline/demo reliability and source availability depend on a third party at page-load time | Bundle a verified, immutable snapshot during the build and preserve source hashes/provenance |
| P1 | Current page is a historical ledger, not a judge-oriented product story | `Home.tsx` focuses one case file and one raw panel | A judge must infer the system’s central safety distinction | Add a first-screen thesis, visible safety chain, corruption comparison, decision drawer, benchmark summary, and an explicit replay lane |
| P1 | README is historically stale | It still labels all metrics as placeholders despite preserved recovery evidence and omits Missions 029–030 | The repository’s first 30 seconds understate its credible work and overstate old unknowns | Rewrite only factual, evidence-backed README sections and retain explicit limitations |
| P2 | Existing demo runner stops at live provider failure | `mission029_live_demo.py` hard-stops before downstream stages | The real failure hides the strongest verification and no-shipment behavior | Add a separately invoked replay mode; never make it a silent fallback for a live operation |

## Bright Data healing analysis

Mission 001’s successful request and Mission 030’s failed request share the documented CLI shape: `bdata scraper heal <collector_id> <prompt> --url <url>`. Mission 001’s request was a concrete claim of missing fields after a page change and returned `awaiting_approval` with preview data. Mission 030’s request was within the documented 1,000-character prompt ceiling, but the stored stderr records status 500 and a `sprintf invalid format %j` provider/CLI message before a candidate was created.

The current official documentation confirms that the `--url` flag is used to weave the target into the next-step hint rather than being sent to the heal call; it also documents `--max-retries` only for concurrent-job 429 handling, not general 500 remediation. [1] [2] Consequently, the available evidence does **not** prove that the compact prompt, the `--url` flag, or an AEGIS parser caused the 500. It also does not prove the service itself was the root cause. The only defensible current classification is **provider-or-CLI execution failure, root cause unresolved**.

## Conditional live-validation protocol

Any new Bright Data operation is gated by the following protocol. This is a proposed authorization procedure, not a completed execution record.

| Gate | Required evidence before moving on | Result if unmet |
|---|---|---|
| G1 — Immutable-history guard | Mission 001, 015–028, 029, and 030 hashes recorded; no historical path is a test-cleanup target | Stop: `BLOCKED_EVIDENCE_INTEGRITY` |
| G2 — Environment guard | Current CLI version and authenticated status are captured without echoing credentials; no API key enters source, artifacts, or logs | Stop: `BLOCKED_PROVIDER_ENVIRONMENT` |
| G3 — Request rationale | New collector is justified as a documented create → run → heal capability validation, not as a repair of the evidence-only Mission 029 mutation | Stop: `BLOCKED_INVALID_LIVE_CLAIM` |
| G4 — Budget guard | At most one new collector, two total new runs, and three total new heals; each operation has its own preflight record | Stop: `BLOCKED_PROVIDER_BUDGET` |
| G5 — Safety guard | No `--auto-approve`, no approval command, no production commit, no rollback, no benchmark, and no looped retry | Stop: `BLOCKED_SAFETY_POLICY` |
| G6 — Candidate guard | A returned preview becomes `UNVERIFIED`; deterministic verification runs only on a locally preserved candidate envelope and cannot approve a provider change | If absent, end at `FAILED_BEFORE_CANDIDATE` |

The most useful controlled validation, if all gates pass, is a **minimal public-target scraper whose initial schema is intentionally limited**, followed by one documented request to add a non-destructive field. This matches Bright Data’s published create → run → heal → preview workflow without claiming that the Mission 029 evidence mutation altered provider state. [1] [3] Any returned candidate remains untrusted and is never approved.

## Benchmark presentation boundary

The reproducible Mission 028 recovery identity is `mission_028_recovery_floor_4812160675146552`. Its terminal execution log records 180 opportunities: 179 completed, 1 failed, 60 provider operations, zero healing operations, and 38 generated metric records. The metric report scopes detection, alarm, and L5 shipment measures to 60 AEGIS controlled-harness `TEST_DOUBLE` records; it explicitly excludes Baseline A and Baseline B from those AEGIS metrics. NVIDIA Baseline B is accurately described as `openai/gpt-oss-20b` through NVIDIA NIM under a **benchmark-side** 6 RPM, 10-second minimum interval, concurrency-1 throttle; the provider limit remains `UNKNOWN`.

Mission 031 will show the protocol and the real provider failure, but will not equate controlled-harness AEGIS metrics with live Bright Data reliability.

## Implementation sequence selected from the audit

1. Generate a read-only, validated demo snapshot from committed artifacts and materialize a deterministic `SILENT_CORRUPTION` verification replay through existing AEGIS modules.
2. Build a dedicated Judge Mode around that snapshot with immutable provenance tags, a transparent real-provider lane, and a separate controlled replay lane.
3. Refactor the demo runner into safe `replay` and explicitly authorized `live` modes; preserve the one-operation cap and terminal replay semantics.
4. Replace stale README claims, create a judge script, a submission quick-start, and a deterministic architecture graphic after the implemented surfaces are validated.
5. Execute no provider call until G1–G5 are recorded. If a candidate is unavailable, deliver the failure-safe product story rather than fabricate repair completion.

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli "Bright Data — Build a scraper with the CLI"
[2]: https://docs.brightdata.com/cli/commands "Bright Data — CLI command reference"
[3]: https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool "Bright Data — Scraper Studio Self-Healing tool"
