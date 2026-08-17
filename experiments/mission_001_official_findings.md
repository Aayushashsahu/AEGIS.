# AEGIS Mission 001 — Official Bright Data Findings (initial)

**Research date:** 2026-08-17
**Source status:** Official Bright Data documentation viewed in the authenticated browser session.
**Experiment status:** Documentation evidence only; no Bright Data operation has been executed yet.

## Source 1 — Scraper Studio API quickstart

URL: https://docs.brightdata.com/datasets/scraper-studio/quickstart

The quickstart documents a published Scraper Studio collector identified by a stable `c_...` Collector ID. It describes bearer-token authentication using `Authorization: Bearer ...`, a `POST https://api.brightdata.com/dca/trigger?collector=<collector_id>&queue_next=1` operation with a JSON array body, and a response containing `collection_id` with a `j_...` value. It then documents `GET https://api.brightdata.com/dca/dataset?id=<snapshot_id>` for polling and retrieval. While building, the response is a status object such as `{ "status": "building" }`; when ready, it is a JSON array whose exact fields depend on the collector output schema.

The page explains that the trigger response field `collection_id` is the same string later called `snapshot_id`. It reports typical first-record timing of about three minutes for one to ten inputs in a collector, with a more detailed typical range of 30–90 seconds for one to ten URLs, 2–5 minutes for 11–100 URLs, and 5+ minutes for 100+ URLs. It documents an alternative push-delivery path for long-running jobs and mentions a synchronous real-time option as a next step, but those paths were not yet independently inspected or executed.

## Source 2 — Initiate collection and delivery

URL: https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options

This page states that a scraper must be saved to production before external initiation; unsaved drafts remain in Draft status and cannot be initiated outside the IDE. It documents API, manual, and scheduled initiation, and states that the API trigger response includes `collection_id`. With API-download delivery, a separate Receive data API endpoint is used; webhook and cloud-storage delivery push results to the configured destination.

The page distinguishes batch and real-time collection. Batch results are returned after job completion and are retained for 16 days; real-time responses are returned in real time and are retained for 7 days. It states batch concurrency up to 100 concurrent jobs per scraper and a real-time limit of 50K requests/min per customer. These are documentation facts, not AEGIS measurements.

## Initial AEGIS interpretation

The documentation evidence supports a provisional Collection adapter contract with `collector_id`, input payload, `collection_id`/`snapshot_id`, provider status, structured output, timestamps, and a delivery mode. It does not yet verify account access, an actual collector, provider-side version identity, self-healing, candidate retrieval, rollback, raw HTML, or WARC behavior for this session.

## Source 3 — Self-Healing tool

URL: https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool

The official IDE documentation describes Self-Healing as an AI-powered code-refactor assistant for an existing scraper saved in development mode. It accepts a plain-language prompt and produces a code diff in the editor. The documented sequence is: open the tool, describe the fix, review the generated diff, accept or decline, run a preview, then save to production. Accepting saves the change to a draft; declining leaves the original code unchanged. The page states refactoring can take up to 15 minutes and sends an email when the diff is ready. The documentation does not describe a public API endpoint, CLI verb, machine-readable repair-candidate schema, polling API, or provider-native rollback operation for this IDE flow.

This supports a provisional status of **PARTIALLY VERIFIED by official documentation** for human-in-the-loop IDE healing. It does not verify programmatic healing or candidate retrieval for an AEGIS adapter.

## Source 4 — WARC snapshots

URL: https://docs.brightdata.com/datasets/scraper-studio/warc-ide

The official documentation states that WARC output can archive full HTTP responses captured during a browser-worker scrape. WARC is available only on Browser worker scrapers, not Code worker scrapers. It is enabled in the IDE output schema through an additional `warc_snapshot` field, then produced when a production scraper is run. Retrieval/delivery follows the scraper’s configured delivery method: API download, webhook, S3, GCS, Azure, SFTP, or email. The page states browser-side request/response traffic is captured during page load; `wait_network_idle()` and relevant scrolling/loading operations may be needed for completeness. This is official capability evidence, not a local AEGIS measurement.

This supports **PARTIALLY VERIFIED by official documentation** for WARC evidence, conditional on Browser worker, schema configuration, and delivery configuration. It does not yet establish an actual WARC artifact, latency, cost, or retention result in the current account.

## Source 5 — CLI command reference

URL: https://docs.brightdata.com/cli/commands

The official command reference documents these exact commands:

```text
brightdata scraper create <url> <description>
brightdata scraper run <collector_id> [url]
brightdata scraper heal <collector_id> <prompt>
brightdata scraper approve <collector_id>
brightdata status <job-id>
```

The same page documents global flags including `-k/--api-key` and `--timing`. It states that the Collector ID remains stable across runs and self-healing. It documents `scraper heal` as stopping at an approval gate by default and returning `status: "awaiting_approval"` with a `preview_result`; `scraper approve` commits or rejects the pending heal. It documents `status` for asynchronous snapshot jobs.

## Source 6 — Build with the Bright Data CLI

URL: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli

The official guide documents `npx -p @brightdata/cli bdata --version`, `bdata login` with browser authorization and local API-key storage, `bdata scraper create <url> <description>`, `bdata scraper run <collector_id> <url> --pretty`, `bdata scraper heal <collector_id> <prompt> --url <url>`, and `bdata scraper approve <collector_id> --url <url>` with `--reject` for rejection. It states that create returns a stable `c_*` Collector ID, create commonly takes 5–15 minutes and can take up to 25 minutes, and run returns a JSON array. The guide says heal keeps the same Collector ID, stops at approval by default, returns an envelope with `awaiting_approval` and `preview_result`, and can be re-run after approval. It documents `--auto-approve` as an unattended option but this was not used in the spike because AEGIS must preserve an external proposal/evidence boundary.

The guide maps the CLI to documented API routes: create uses `POST /dca/collector` followed by `POST /dca/collectors/{c_*}/automate_template`; small-input run uses `POST /dca/trigger_immediate` followed by `GET /dca/get_result`; larger-input run uses `POST /dca/trigger` followed by `GET /dca/dataset?id=j_*`. These route mappings are documented-source evidence, not yet live request observations.

The guide does not document provider-native version listing or rollback commands. It says self-healing commits to the existing scraper after approval and that the Collector ID does not change. AEGIS must therefore treat provider version identity and rollback semantics as unresolved until an experiment or further official documentation verifies them.

## Version and rollback follow-up

The self-healing page itself only exposes an FAQ label in the extracted page text, but the official Bright Data search result for the same page states: “If you already saved to production, open the Versions menu on the scraper dashboard to roll back to an earlier version.” This is official documentation/search-result evidence that a dashboard Versions menu and rollback-to-earlier-version workflow exist, but it does not yet establish an API/CLI operation, version identifier schema, atomicity, or a live rollback result. Record this as **PARTIALLY VERIFIED by official documentation**, not as a verified adapter operation.

The controlled spike must not claim a provider-native rollback adapter until a documented programmatic interface or a live authorized experiment is available.

## Live experiment 1 — CLI collector creation

**Exact command tested:**

```bash
npx -p @brightdata/cli bdata --timing scraper create https://news.ycombinator.com "Extract top stories: title, url, points, author, comment count"
```

**Observed result:** The command completed successfully. It created Collector ID `c_msx16nef2jck24ag94`, returned name `cli-scraper-1786958886`, status `done`, all nine documented generation/preview steps, view URL `https://brightdata.com/cp/scrapers/c_msx16nef2jck24ag94`, and `created_at` `2026-08-17T09:28:09.207Z`.

**Measured latency:** `236,628 ms` wall-clock from the wrapper timer. The CLI printed per-operation timing and completed after 130 polling attempts. This is a measured observation for this collector/account/target at this time, not a general Bright Data SLA.

## Live experiment 2 — CLI collector execution and output retrieval

**Exact command tested:**

```bash
npx -p @brightdata/cli bdata --timing scraper run c_msx16nef2jck24ag94 https://news.ycombinator.com --pretty
```

**Observed result:** The command returned structured JSON output with `59` rows. Each observed row contained fields including `title`, `url`, `points`, `author`, `comment_count`, and nested `input.url`. The run first attempted realtime execution, reported `Realtime page limit exceeded — switching to batch mode...`, submitted batch job `j_msx1c7l14dx6gn69t`, and completed through batch polling. The initial response identifier was `d2t1786959141390rqae4b7sq8q8`.

**Measured latency:** `198,844 ms` wall-clock. This is measured for the tested run, not a general latency claim. The output is retained in `mission_001_collection_output.json`; metadata is retained in `mission_001_collection_metadata.json`.

**AEGIS interpretation:** Collection creation and structured output retrieval are **VERIFIED for the tested CLI path**. The fallback from realtime to batch is **VERIFIED as observed CLI behavior** for this run. The run demonstrates an adapter must preserve collector ID, collection/response/batch identifiers, status transitions, mode/fallback, output schema, row count, timestamps, and raw CLI evidence.

## Live experiment 3 — self-healing request and candidate preview

**Exact command tested:**

```bash
npx -p @brightdata/cli bdata --timing scraper heal c_msx16nef2jck24ag94 "The points and comment_count fields may be missing or incorrect after a page change. Propose a repair that re-captures these existing fields from the current Hacker News markup without changing the output schema." --url https://news.ycombinator.com
```

**Observed result:** The command completed with `Heal ready — awaiting approval`. It returned the same Collector ID, status `awaiting_approval`, completed healing steps, a `next_step` approval command, a `preview_result` containing one candidate preview row, and `diff_summary: proposed template has 2 step(s)`. The preview row contained `title`, `url`, `points`, `author`, and `comment_count`. No approval command was executed, so the proposed change was not committed.

**Measured latency:** `69,956 ms` wall-clock. This is a measured observation for this request and not a general SLA. The CLI log records the command and result; the returned view URL was `https://brightdata.com/cp/scrapers/c_msx16nef2jck24ag94`.

**AEGIS interpretation:** Programmatic self-healing request and a candidate preview envelope are **VERIFIED for the tested CLI path**. The approval gate is **VERIFIED as observed**. Candidate correctness is **NOT VERIFIED**: the preview was not independently checked against a mutated ground truth, and the proposal was intentionally not approved.

## Authentication and tool access

The documented device flow was tested with `npx -p @brightdata/cli bdata login --device`. The CLI displayed a device code and approval URL; the already authenticated Bright Data browser session approved it. The CLI then reported successful login and created the required `cli_unlocker` and `cli_browser` zones. The API key was not copied into repository files or chat.

The Bright Data MCP connector was enabled for this task and its available tools were inspected. It exposes search/scrape/assistant capabilities, not the Scraper Studio collector create/run/heal/approve operations used above. The Scraper Studio CLI was therefore the live experiment interface.
