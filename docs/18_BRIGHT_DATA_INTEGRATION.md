# 18 — Bright Data Integration

**Status:** Integration contract and experiment plan.  
**Critical rule:** Do not pretend an API, CLI command, healing workflow, approval operation, rollback behavior, raw-response capability, WARC capability, or coding-agent integration exists until verified in an experiment.  
**Labels:** `VERIFIED`, `TARGET`, `HYPOTHESIS`, `UNKNOWN`, `MEASURED`.

## Integration objective

Bright Data Scraper Studio remains central to AEGIS. AEGIS owns collection observation, detection, diagnosis, verification, risk decisions, quarantine, post-commit watch, rollback orchestration, memory, and benchmarking. Bright Data is the actual scraper execution and healing layer. The boundary must make provider behavior observable without letting provider success bypass AEGIS safety gates.

## Scraper Studio and custom collector

**TARGET integration shape:** A custom collector has a stable project reference, declared structured output, a version or revision identifier, and a repeatable execution path. AEGIS records collector reference, contract version, provider operation ID, collection timestamps, structured output, and available raw evidence.

**OPEN TECHNICAL ASSUMPTION BD-001:** The exact Scraper Studio collector creation, execution, inspection, and versioning interface is unknown.

**Day-1 experiment:** Create or locate the smallest permitted custom collector against a controlled/public target; execute it twice; capture the UI/CLI/API action, output schema, run ID, error behavior, and version/revision metadata. Record raw evidence and redact credentials.

**Fallback:** Use a contract-preserving local adapter only for laboratory and safety tests, label it `TEST_DOUBLE`, and do not use it to claim Bright Data capability.

## CLI and authentication

The documentation requires a provider adapter with conceptual operations `create`, `run`, `inspect`, `heal`, `approve_if_authorized`, and `resolve_known_good`. These are internal adapter operations, not claims about Bright Data verb names.

**OPEN TECHNICAL ASSUMPTION BD-002:** Authentication mechanism, token scope, CLI availability, and machine-readable output are unknown.

**Day-1 experiment:** Verify the official access path provided to the team, run a read-only inspection, identify the minimum credential scope, and capture the exact command/request and response schema. Test missing/expired credentials.

**Fallback:** Store provider interaction behind a manually configured adapter and use a recorded, truthful provider trace for the demo while integration remains explicitly incomplete.

## Healing

AEGIS sends a structured repair request containing collector reference, failure class, observed evidence references, extraction contract, affected fields/entities, mutation context when in the lab, and bounded constraints. A provider response becomes a RepairAttempt and one or more RepairCandidates. A candidate is never committed from provider success alone.

**OPEN TECHNICAL ASSUMPTION BD-003:** Healing trigger, prompt/input format, candidate delivery, polling/callback behavior, latency, and failure states are unknown.

**Day-1 experiment:** Trigger one controlled repair, capture request/response/poll sequence, measure elapsed time, induce a timeout or malformed response if safe, and determine whether candidate versions or code artifacts are inspectable before activation.

**Fallback:** Implement an adapter that returns a deterministic candidate fixture and provider-like lifecycle statuses. Mark all outputs as test-double results.

## Approval and escalation

AEGIS can emit `ESCALATE` when evidence is insufficient or a high-risk event needs human review. This may connect to a Bright Data approval workflow if such a workflow is available and authorized.

**OPEN TECHNICAL ASSUMPTION BD-004:** Provider approval workflow and its permissions are unknown.

**Day-1 experiment:** Determine whether approval exists, what action it authorizes, how it is audited, and whether approval can bypass or only supplement AEGIS verification. The intended result is that human approval cannot make an unverified candidate eligible for commit.

## Versioning and rollback

Before a commit, AEGIS records a known-good version reference. A regression invokes a rollback operation through the provider adapter if supported, then independently validates the restored output.

**OPEN TECHNICAL ASSUMPTION BD-005:** Provider version identity, activation semantics, rollback operation, and atomicity are unknown.

**Day-1 experiment:** Create two distinguishable collector revisions in a controlled fixture, identify how active revision is selected, switch between revisions, and measure whether rollback can be verified after a failed candidate.

**Fallback:** Keep an AEGIS-level active-version registry and route collection through a known-good adapter version. Do not claim provider-native rollback if the provider cannot verify it.

## Structured output and raw evidence

AEGIS should preserve provider structured output and normalize it into Observation records without changing meaning. When available, raw HTML/response snapshots and response fingerprints support diagnosis and verification.

**OPEN TECHNICAL ASSUMPTION BD-006:** Raw response access, response headers, fingerprint stability, and WARC support are unknown.

**Day-1/Day-4 experiment:** Inspect the collection result and available evidence channels; compare clean and mutated fixture responses; determine whether WARC is available and reliable enough for the core path.

**Fallback:** Store raw HTML/response snapshots from the controlled fixture and compute AEGIS fingerprints locally. WARC remains optional and cannot threaten the core timeline.

## Coding-agent integration

A coding agent may prepare a repair request, inspect evidence, or create a candidate patch through a bounded adapter. It may not receive unrestricted credentials, execute arbitrary provider operations, change policy, or commit a candidate. Every agent action is logged with task ID, actor, request hash, evidence references, and result.

**OPEN TECHNICAL ASSUMPTION BD-007:** Whether Bright Data exposes a safe coding-agent or programmatic healing interface is unknown.

**Day-1 experiment:** Verify the documented integration path and permissions using a disposable/test collector. Confirm that the agent can propose but cannot bypass AEGIS verification or commit gates.

## Integration evidence checklist

Before claiming integration is `VERIFIED`, retain the exact collector reference, execution command/request, input, provider output, schema, timestamps, provider operation ID, error behavior, retry/poll behavior, revision/version evidence, redacted screenshots or raw payloads, and a human-readable experiment report. If any item is missing, label the relevant capability `UNKNOWN` or `HYPOTHESIS`.

## Mission 001 results — 2026-08-17

**Experiment status:** Partially complete. Live CLI access was authenticated and tested against a disposable public-target collector. No AEGIS implementation was added.

| Capability | Status | Interface | Evidence | Observed behavior | Limitations | Latency | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Create Scraper Studio scraper | VERIFIED for tested path | CLI | `experiments/mission_001_official_findings.md`, Collector ID `c_msx16nef2jck24ag94` | `bdata scraper create` returned `status: done`, stable Collector ID, view URL, completed steps, and creation timestamp. | One collector, one public target, one account; no general SLA. | 236,628 ms measured | Contract-preserving test double for local tests. |
| Run collector | VERIFIED for tested path | CLI | Run log and metadata; response ID `d2t1786959141390rqae4b7sq8q8`; batch job `j_msx1c7l14dx6gn69t` | CLI attempted realtime, reported page-limit overflow, then switched to batch mode and completed. | Fallback policy is CLI behavior observed for this run; provider-level mode semantics remain adapter work. | 198,844 ms measured | Bounded polling; quarantine on timeout. |
| Retrieve structured output | VERIFIED for tested path | CLI | `mission_001_collection_output.json` with 59 rows | JSON array rows included title, URL, points, author, comment_count, and nested input URL. | Output schema is collector-specific; data is untrusted until AEGIS verification. | Included in run latency | Store immutable Observation plus raw CLI evidence. |
| Collector identity | VERIFIED for tested path | CLI | Collector ID and creation response | Stable `c_*` Collector ID was returned and reused for run and heal. | Provider version/revision identity not returned by tested CLI output. | N/A | AEGIS records collector ID and all provider references. |
| Self-healing request | VERIFIED for tested path | CLI | Heal log and returned envelope | Heal completed with `status: awaiting_approval`, same Collector ID, preview result, diff summary, and next-step approval command. | Candidate correctness was not independently verified; proposal was not approved. | 69,956 ms measured | Keep pending candidate quarantined until deterministic verification. |
| Repair candidate | PARTIALLY VERIFIED | CLI | `preview_result` and `diff_summary` in heal response | Candidate preview output was returned in the approval envelope. | No machine-readable full patch artifact or independent ground-truth verification was captured. | Included in heal latency | Persist provider envelope as candidate evidence; use local candidate fixture if unavailable. |
| Approval | VERIFIED for tested path | CLI | Documented `bdata scraper approve`; live approval intentionally not executed | Heal stops at approval by default. | Commit/approval semantics were not live-tested because doing so would alter the disposable collector. | Not measured | AEGIS approval boundary remains separate from deterministic commit gate. |
| Versions / rollback | PARTIALLY VERIFIED by documentation | IDE/dashboard | Official self-healing documentation and search result mention a Versions menu and rollback to an earlier version. | Provider UI rollback is documented. | No CLI/API operation, version schema, atomicity, or live rollback result verified. | Unknown | Maintain AEGIS-level known-good version registry and adapter operation `resolve_known_good`. |
| Raw response / HTML | UNKNOWN for tested collector | CLI/IDE | No raw HTML artifact returned by the tested CLI run. | Structured output was available. | Raw response access was not established for this collector. | Unknown | Capture controlled fixture HTML locally; do not claim provider raw access. |
| WARC | PARTIALLY VERIFIED by documentation | IDE/delivery | Official WARC documentation | WARC is available for Browser worker scrapers via `warc_snapshot` and configured delivery. | No WARC artifact, delivery test, retention, cost, or latency measured. | Unknown | Treat WARC as optional; use local raw-response snapshots. |
| Authentication | VERIFIED for tested CLI path | CLI device flow | `bdata login --device` session log; browser approval completed | Device flow authenticated the CLI and created required zones. | Key scope and CI/headless token-rotation behavior not independently tested. | Not separately measured | Environment/secret-store injection only. |

### Exact live commands tested

```bash
npx -p @brightdata/cli bdata --version
npx -p @brightdata/cli bdata login --device
npx -p @brightdata/cli bdata --timing scraper create https://news.ycombinator.com "Extract top stories: title, url, points, author, comment count"
npx -p @brightdata/cli bdata --timing scraper run c_msx16nef2jck24ag94 https://news.ycombinator.com --pretty
npx -p @brightdata/cli bdata --timing scraper heal c_msx16nef2jck24ag94 "The points and comment_count fields may be missing or incorrect after a page change. Propose a repair that re-captures these existing fields from the current Hacker News markup without changing the output schema." --url https://news.ycombinator.com
```

The approval command returned by the provider was recorded but intentionally **not executed**:

```bash
bdata scraper approve c_msx16nef2jck24ag94 --url https://news.ycombinator.com
```

This experiment does not claim provider-native rollback, raw HTML retrieval, WARC delivery, candidate correctness, AEGIS verification success, or a general performance SLA.

## Mission 002 implementation outcome — 2026-08-17

Mission 002 implements the smallest compatible adapter boundary from the verified Mission 001 CLI path. The application does not scatter provider commands and does not implement healing, approval, rollback, candidate verification, or raw-response retrieval.

| Capability | Status | Mission 002 evidence |
| --- | --- | --- |
| Provider-neutral create/run/poll/retrieve seam | VERIFIED for implementation boundary | `src/aegis/adapter.py`; injected command runner; unit test for the documented CLI-shaped response. |
| Asynchronous collection state | VERIFIED in local implementation | `SUBMITTED → RUNNING → COMPLETED/FAILED/TIMED_OUT`; bounded deadline; timeout cannot produce an Observation. |
| Realtime-to-batch preservation | VERIFIED in local implementation against Mission 001 trace shape | Adapter records `BATCH` when the observed CLI trace reports realtime fallback. This does not claim deterministic provider behavior beyond Mission 001 evidence. |
| Bright Data Observation conversion | VERIFIED for recorded artifact path | `tests/integration/test_mission001_artifact_to_observation.py` preserves Bright Data provenance, provider IDs, latency, mode, row count, and untrusted status. |
| Deterministic detection | VERIFIED in local implementation | Schema, statistical, and semantic/invariant signals produce immutable `DetectionResult` evidence. |
| Test double | VERIFIED in local implementation | `DeterministicBrightDataTestDouble` is explicitly labeled `TEST_DOUBLE`; it never proves provider capability. |

The recorded Mission 001 output is intentionally not treated as healthy merely because it is structured JSON. The integration test converts it to an untrusted Observation and detects missing contract-required fields. This is a safety result, not a new live-provider claim.

## Mission 003 provider boundary — 2026-08-17

Mission 003 does not execute Bright Data healing. It introduces a provider-neutral `HealingRequester` protocol and `RepairAttemptHandle` acknowledgement so Mission 004 can connect the already verified CLI path without leaking provider details into domain records.

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| Convert DetectionResult into repair intent | VERIFIED in local implementation | `src/aegis/diagnosis.py`; immutable Diagnosis and RepairRequest preserve evidence, provenance, contract, and affected fields. |
| Provider-neutral healing seam | VERIFIED in local implementation | `HealingRequester.request_healing`; `NoExecutionRepairBoundary` returns `execution_started=False` and no provider operation reference. |
| Bright Data healing execution in Mission 003 | NOT EXECUTED | Deliberately deferred to Mission 004; no new provider capability claim is made. |
| Candidate retrieval/verification/approval/commit | UNKNOWN / DEFERRED | Mission 001 labels remain unchanged; Mission 003 cannot reach these states. |

A future provider adapter must translate `RepairRequest` into a documented provider operation, preserve request hashes and evidence, poll asynchronously, and return an untrusted candidate envelope. It must not authorize AEGIS verification, risk, or commit decisions.

## Mission 004 implementation outcome — 2026-08-17

Mission 004 connects the existing provider-neutral RepairRequest to the verified Mission 001 CLI heal path without executing approval or claiming candidate correctness.

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| RepairRequest → documented CLI heal command | VERIFIED for adapter mapping | `build_heal_command()` constructs `npx -p @brightdata/cli bdata scraper heal <collector_id> <prompt> --url <url>`; unit-tested with contract-preserving prompt content. |
| Asynchronous heal submission | VERIFIED in local implementation | Existing `ThreadPoolExecutor`/injected runner boundary returns a `HealHandle` before provider completion. |
| `awaiting_approval` recognition | VERIFIED for tested response shape in local adapter | Root provider status is preserved and mapped to `AWAITING_APPROVAL`; no approval operation is called. |
| Preview/diff/operation envelope | VERIFIED for tested response shape in local adapter | `preview_result`, `diff_summary`, operation identifier, approval command as data, latency, provenance, and evidence reference are preserved. |
| RepairCandidate | VERIFIED in local implementation as untrusted envelope | Candidate is immutable and always `UNVERIFIED`; no accepted/committed transition exists. |
| Live Mission 004 heal execution | NOT EXECUTED | No live provider state was changed; Mission 001 live result remains the only provider heal evidence. |
| Provider-native rollback, raw HTML, WARC, candidate correctness | UNKNOWN/PARTIAL as previously recorded | Mission 004 does not change Mission 001 labels. |

The approval command returned by Bright Data is treated as untrusted provider data. It is not executed, and `--auto-approve` is absent from the adapter and tests. A future verification/risk mission owns the authority to decide whether any candidate may proceed.

## Mission 006 provider boundary — 2026-08-17

Mission 006 does not add a Bright Data operation. It adds only an AEGIS-level `CommitGate` and `KnownGoodVersion` record after candidate verification and risk decision. The provider-native version/rollback capability remains `PARTIALLY VERIFIED by documentation` as recorded in Mission 001; no provider activation, approval, commit, or rollback command is introduced or claimed.

A provider proposal remains untrusted until deterministic verification passes. Even a `RiskDecision=ACCEPT` does not authorize Bright Data approval or production activation. The gate requires an AEGIS known-good reference, valid authorization evidence, complete identifiers, complete verification evidence, `VerificationStatus=VERIFIED`, and matching correlation IDs before returning future `ELIGIBLE`. Otherwise the result is `BLOCKED`, and a quarantine record may be retained.

## Mission 007 provider boundary — 2026-08-17

Mission 007 adds no Bright Data operation. It evaluates later AEGIS observations through the existing deterministic detection boundary and stores local regression/quarantine evidence. Provider-native rollback remains `PARTIALLY VERIFIED by documentation` as recorded in Mission 001; no rollback, activation, approval, or provider mutation is attempted.

The watch registration requires an AEGIS-level eligible commit decision, known-good reference, passing verification, verified candidate, expected contract, and matching correlation. A regression is quarantined locally according to watch policy. Later rollback or re-diagnosis remains a separate mission and cannot be inferred from a watch result.
