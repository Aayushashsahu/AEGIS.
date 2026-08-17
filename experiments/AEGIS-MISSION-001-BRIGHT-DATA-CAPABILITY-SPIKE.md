# AEGIS Mission 001 — Bright Data Capability Spike

**Date:** 2026-08-17  
**Status:** **PARTIAL / LIVE CLI PATH VERIFIED**  
**Scope:** Bright Data capabilities required around Collection → Observation → Detection, plus adjacent healing, candidate, version, rollback, evidence, authentication, and latency questions.  
**Safety boundary:** No AEGIS application logic, healing implementation, UI, benchmark run, or provider-side heal approval was implemented or committed.

> **AI proposes. Evidence decides.**

## Executive result

The documented Bright Data CLI path was authenticated and live-tested against a disposable public-target Scraper Studio collector. The experiment verified collector creation, collector execution, structured output retrieval, stable Collector ID reuse, realtime-to-batch fallback behavior observed by the CLI, and an approval-gated self-healing proposal with a preview result. The pending heal was **not approved**, so no provider-side repair was committed.

The experiment did **not** verify provider-native programmatic version listing or rollback, raw HTML retrieval from the tested CLI path, WARC delivery, candidate correctness against independent ground truth, or any AEGIS verification result. These remain open decisions or bounded fallbacks.

## Capability matrix

| Capability | Status | Interface | Evidence | Observed behavior | Limitations | Latency | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Create/use Scraper Studio scraper | **VERIFIED for tested path** | CLI | Collector `c_msx16nef2jck24ag94`; create log; official CLI guide [1] | `bdata scraper create` returned `status: done`, a stable Collector ID, view URL, completed generation steps, and creation timestamp. | One collector, target, account, and run only; no general SLA. | 236,628 ms measured | Contract-preserving local test double. |
| Run a collector | **VERIFIED for tested path** | CLI | Run log; response ID `d2t1786959141390rqae4b7sq8q8`; batch job `j_msx1c7l14dx6gn69t` | CLI attempted realtime, reported `Realtime page limit exceeded`, switched to batch mode, polled, and completed. | Observed CLI behavior is not a general provider contract until repeated and pinned. | 198,844 ms measured | Bounded polling and quarantine on timeout. |
| Retrieve collector output | **VERIFIED for tested path** | CLI | `mission_001_collection_output.json`; 59 rows | Returned a JSON array with `title`, `url`, `points`, `author`, `comment_count`, and nested `input.url` fields. | Exact fields depend on the collector output schema; data remains untrusted. | Included in run latency | Immutable Observation plus raw provider evidence. |
| Identify collector information | **VERIFIED for tested path** | CLI | Create response and metadata | Stable `c_*` Collector ID was returned and reused for run and heal. | Provider version/revision identifier was not present in the tested CLI output. | N/A | Store Collector ID and all provider operation references. |
| Trigger/request self-healing | **VERIFIED for tested path** | CLI | Heal log; official CLI/self-healing docs [1] [2] | Heal accepted a bounded natural-language prompt and reached `awaiting_approval`. | Full provider request schema and patch artifact contract remain unresolved. | 69,956 ms measured | Store provider envelope as an untrusted RepairCandidate. |
| Obtain repair candidate | **PARTIALLY VERIFIED** | CLI | `preview_result`, `diff_summary`, pending heal envelope | Returned a preview row and `diff_summary: proposed template has 2 step(s)`. | Candidate correctness was not independently checked; full machine-readable diff was not captured. | Included in heal latency | Quarantine until deterministic AEGIS verification passes. |
| Approval gate | **VERIFIED for tested path** | CLI | Returned next-step command; no approval executed | Heal stopped before commit and returned `bdata scraper approve ...` as the next step. | Live approval was intentionally not executed; provider approval is not AEGIS commit authority. | Not measured | Keep candidate pending/rejected until AEGIS risk gate. |
| Versions / rollback | **PARTIALLY VERIFIED by documentation** | IDE/dashboard | Official self-healing page/search result [3] | Documentation indicates a Versions menu can roll back to an earlier version. | No CLI/API route, version schema, atomicity, or live rollback result verified. | Unknown | AEGIS-level known-good-version registry and adapter routing. |
| Raw response / HTML | **UNKNOWN for tested collector** | CLI/IDE | No raw HTML artifact in the live CLI run | Structured output was available; raw HTML/response was not established. | No tested retrieval operation or artifact. | Unknown | Controlled fixture HTML snapshots and local fingerprints. |
| WARC | **PARTIALLY VERIFIED by documentation** | IDE/delivery | Official WARC documentation [4] | WARC is documented for Browser worker scrapers through `warc_snapshot` and configured delivery. | No WARC artifact, delivery test, retention, cost, or latency measured. | Unknown | Treat WARC as optional; use local evidence snapshots. |
| CLI/API authentication | **VERIFIED for tested CLI path** | CLI device flow | `bdata login --device` session; browser approval | Device flow authenticated the CLI and created `cli_unlocker` and `cli_browser` zones. | Token scope and rotation/CI behavior were not independently tested. | Not separately measured | Environment/secret-store injection; never source code. |
| Direct API operations | **PARTIALLY VERIFIED by documentation** | HTTP API | Official API quickstart [5] and CLI mapping [1] | Official docs describe `/dca/trigger`, `/dca/dataset`, and CLI-to-API mappings including realtime routes. | Direct HTTP calls were not separately executed; endpoint/schema claims are documentation-backed only. | Official docs give typical timing ranges; no direct API measurement. | Use CLI adapter first; isolate direct HTTP behind contract tests. |

## Exact operations actually tested

The following commands were executed after authenticating through the documented device flow. They are evidence of this experiment, not a recommendation to run them against an unapproved production collector.

```bash
npx -p @brightdata/cli bdata --version

npx -p @brightdata/cli bdata login --device

npx -p @brightdata/cli bdata --timing scraper create \
  https://news.ycombinator.com \
  "Extract top stories: title, url, points, author, comment count"

npx -p @brightdata/cli bdata --timing scraper run \
  c_msx16nef2jck24ag94 \
  https://news.ycombinator.com \
  --pretty

npx -p @brightdata/cli bdata --timing scraper heal \
  c_msx16nef2jck24ag94 \
  "The points and comment_count fields may be missing or incorrect after a page change. Propose a repair that re-captures these existing fields from the current Hacker News markup without changing the output schema." \
  --url https://news.ycombinator.com
```

The provider returned this approval command, but it was deliberately **not executed**:

```bash
bdata scraper approve c_msx16nef2jck24ag94 --url https://news.ycombinator.com
```

## Evidence artifacts

| Artifact | Contents |
| --- | --- |
| `experiments/mission_001_official_findings.md` | Official-documentation findings and live observations. |
| `experiments/mission_001_collection_metadata.json` | Collector ID, create/run latency, response ID, batch job ID, target, row count, and observed fallback. |
| `experiments/mission_001_collection_output.json` | The 59-row structured output returned by the live collector run. |
| `/tmp/aegis_mission001_create.log` | Raw create command log, including CLI timing and terminal response; not committed because it is transient. |
| `/tmp/aegis_mission001_run.log` | Raw run command log and structured output; the normalized JSON artifact is committed, while the transient log remains outside the repository. |
| `/tmp/aegis_mission001_heal.log` | Raw self-healing command log, pending approval envelope, preview result, and timing; not committed because it is transient. |

The live collector was created at `2026-08-17T09:28:09.207Z`. The experiment did not expose the API key in chat, source code, or repository artifacts.

## Official documentation evidence

The official quickstart documents a published collector with a stable `c_*` Collector ID, bearer authentication, trigger and dataset retrieval operations, status-object polling, JSON-array output, and typical timing ranges [5]. The collection/delivery guide confirms that production-saved scrapers can be initiated by API, manually, or on a schedule, and distinguishes batch from realtime collection [6].

The official CLI reference documents `scraper create`, `scraper run`, `scraper heal`, `scraper approve`, and `status`, including the default approval gate for healing [1]. The official CLI guide documents the authenticated login flow, create/run/heal/approve sequence, Collector ID stability, realtime-to-batch behavior, and CLI-to-API route mapping [2].

The official self-healing documentation describes an IDE diff, review, preview, and save-to-production flow, with refactoring that can take up to 15 minutes [3]. The official WARC documentation describes `warc_snapshot` for Browser worker scrapers and delivery through API download or configured destinations [4].

## Unknowns and integration risks

The most important unresolved issue is **provider version and rollback control**. AEGIS requires a known-good version before commit and an auditable rollback path, but this spike did not verify a CLI/API operation or machine-readable version identifier. Until verified, AEGIS must own a known-good registry and route collection through an adapter that can fail closed.

The second unresolved issue is **evidence completeness**. The live CLI run returned structured output, but no raw HTML, headers, screenshots, or WARC artifact was captured. Since silent corruption requires independent evidence, the first vertical slice should use controlled fixture snapshots and local fingerprints while a Browser worker/WARC experiment remains optional.

The third unresolved issue is **candidate correctness**. Bright Data returned a pending preview candidate, but no mutation ground truth or independent deterministic checks were available in this spike. The candidate must remain quarantined from any AEGIS commit until schema, semantic, historical, and independent evidence channels are evaluated without double-counting correlated signals.

The observed wall-clock behavior is a material operational risk. Creation took approximately 3.9 minutes, the run took approximately 3.3 minutes and fell back to batch mode, and the heal proposal took approximately 70 seconds. These are single-run measurements and must not be generalized; nevertheless, they imply that AEGIS must use asynchronous state tracking, bounded deadlines, a truthful recorded trace for demos, and quarantine on timeout.

## Recommended AEGIS adapter interface

The adapter should be intentionally narrow and provider-neutral:

```text
create_collector(request) -> CollectorHandle
run_collector(collector_handle, inputs, mode) -> CollectionHandle
poll_collection(collection_handle) -> CollectionStatus
retrieve_output(collection_handle) -> StructuredOutput
request_heal(collector_handle, RepairRequest) -> RepairAttempt
poll_heal(repair_attempt) -> RepairStatus
retrieve_candidate(repair_attempt) -> RepairCandidate
inspect_provider_reference(handle) -> ProviderMetadata
resolve_known_good(pipeline_id) -> VersionReference
rollback_to(version_reference) -> RollbackResult
retrieve_raw_evidence(collection_handle) -> EvidenceBundle
```

Every operation must return or persist a correlation ID, provider reference, timestamps, status, retryability, latency, redacted request/response evidence, and a clear `TEST_DOUBLE` versus `BRIGHT_DATA` provenance label. The adapter must never expose a direct “commit candidate” operation. Approval may be represented as a provider-side action, but AEGIS’s deterministic verification and risk decision remain authoritative.

## Exact minimum capability to begin Collection → Observation → Detection

AEGIS can begin the first vertical slice with the following minimum verified path:

1. A published Scraper Studio collector can be identified by a stable Collector ID.
2. A documented CLI or API operation can start a collection with a declared input shape.
3. The operation returns a collection/response reference and a terminal status can be polled.
4. Structured JSON output can be retrieved and stored as an immutable, untrusted Observation.
5. Collector ID, operation ID, timestamps, output schema, raw provider evidence, and latency can be recorded.
6. A bounded timeout and retry policy can classify provider failure without committing or shipping data.
7. A local ExtractionContract can evaluate the returned Observation through the first schema/statistical/semantic detection seam.

Self-healing, candidate verification, provider-native rollback, WARC, and UI are **not required to begin Collection → Observation → Detection**. They remain adjacent capabilities for later slices and must not block the first observation/detection proof, provided the adapter preserves explicit unknowns and evidence provenance.

## Next experiment

The next spike should use the authenticated Scraper Studio UI or an official API reference to identify whether the created collector exposes a version/revision identifier and whether a provider-native rollback operation is available. In parallel, a disposable Browser worker collector should test `warc_snapshot` delivery. Neither experiment should approve a heal or modify AEGIS code.

## References

[1]: https://docs.brightdata.com/cli/commands "Bright Data CLI command reference"
[2]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli "Build a scraper with the Bright Data CLI"
[3]: https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool "Fix scrapers with the Self-Healing tool"
[4]: https://docs.brightdata.com/datasets/scraper-studio/warc-ide "WARC snapshots in Scraper Studio"
[5]: https://docs.brightdata.com/datasets/scraper-studio/quickstart "Bright Data Scraper Studio API quickstart"
[6]: https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options "Initiate collection and delivery"
