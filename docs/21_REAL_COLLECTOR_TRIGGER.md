# 21 — Real Collector Trigger Boundary

**Status:** Implementation note for an explicit, bounded collection trigger. It does not change AEGIS lifecycle, verification, risk, approval, commit, or rollback semantics.

## Purpose

`scripts/trigger_collector.py` is the narrow command boundary for one real run of collector `c_mt09pib13nxqz1coi`. It uses the documented batch collection path: one `POST /dca/trigger` request with `[{'url': target_url}]`, followed by bounded `GET /dca/dataset?id=<collection_id>` polling. The provider-generated `collection_id` is retained unchanged only when actually returned. It is never replaced with an AEGIS-local operation ID.[1] [2]

Mission 068 observed HTTP `202` with provider status `collecting` from the retrieval path. AEGIS persists that response before parsing and treats it as in-progress, not as output or a terminal failure. `resume_batch_collection_once()` can then continue bounded dataset retrieval for that known provider collection ID with a **zero** trigger budget; it never creates another provider collection.

The same boundary is exposed through `scripts/trigger_collector.py --execute --resume-collection-id <provider-id>`. This mode records `trigger_budget: 0` in its new request evidence and writes its own raw responses in a fresh run directory.

The command requires `BRIGHT_DATA_API_TOKEN` at runtime. The token is used only for a bearer header and is excluded from metadata, correlation records, console output, and committed files. `BRIGHTDATA_API_KEY` remains the separate CLI credential convention; it is not silently substituted for the DCA transport token.

| Boundary | Behavior |
| --- | --- |
| Trigger budget | Exactly one trigger request per `--execute` invocation. |
| Retry budget | Zero trigger retries. Dataset polling is bounded status retrieval, not a second trigger. |
| Raw evidence | A controlled sink writes every received trigger or dataset response once under the new run directory **before JSON parsing or observation normalisation**. |
| Observation | Completed rows become an existing immutable `Observation` with `UNTRUSTED_UNTIL_VERIFIED` status and an append-only audit event. |
| Detection | Existing `evaluate_detection()` evaluates the established Mission 033 contract and writes an append-only audit event. |
| Verification / risk / commit | `NOT_APPLICABLE`, `NOT_APPLICABLE`, and `BLOCKED`: a direct collection is not a repaired candidate. |
| Prohibited actions | No self-heal, approval, save/publish, commit, rollback, benchmark, NVIDIA, or Gemini operation exists in this command. |

## Safe execution

The command performs configuration-only preflight unless `--execute` is supplied. It requires an explicit operation ID, correlation ID, and a fresh output directory below `experiments/mission_068_real_collector_trigger/runs/`. Execution also requires either a known prior provider collection ID in the operational state file or the explicit `--allow-untracked-run` first-run flag. The latter is intentionally available only for separately authorised manual validation.

```bash
export BRIGHT_DATA_API_TOKEN='server-only-token'
export AEGIS_TRIGGER_TARGET_URL='https://approved.example/product'

PYTHONPATH=src python3 scripts/trigger_collector.py \
  --execute \
  --operation-id mission068-live-001 \
  --correlation-id mission068-live-001 \
  --state-path /secure/operational/aegis-live-trigger-state.json \
  --allow-untracked-run
```

`--allow-untracked-run` is for the separately authorised first manual validation only. Scheduled execution must provide a prior state file. If that state contains a known collection ID, AEGIS calls the documented job-metadata endpoint exactly once; `building`, `running`, or unresolved status blocks a new trigger.[3] The public API does not document a collector-scoped active-job discovery request, so AEGIS does not claim it can detect runs started outside its own state record.

## Daily workflow

`.github/workflows/aegis-live-trigger.yml` includes `workflow_dispatch` and a daily cron, but the cron is disabled until repository variable `AEGIS_DAILY_TRIGGER_ENABLED` is explicitly set to `true`. When enabled, the scheduled path performs **preflight only**; it never triggers a new provider collection. This is deliberate: the documented job-status route can inspect an already-known collection ID but cannot discover every active job for a collector, so a scheduled trigger without a durable AEGIS-managed state store could duplicate an external run. Manual dispatch remains the only live trigger path until such state persistence is separately designed and authorised. The workflow never stores a token in the repository and is not a prerequisite for the manual live validation.

## References

[1]: https://docs.brightdata.com/api-reference/scraper-studio-api/Trigger_a_scraper_for_batch_collection_method "Bright Data — Trigger async batch collection"
[2]: https://docs.brightdata.com/datasets/scraper-studio/quickstart "Bright Data — Scraper Studio API quickstart"
[3]: https://docs.brightdata.com/api-reference/scraper-studio-api/job-data "Bright Data — Get job metadata"
