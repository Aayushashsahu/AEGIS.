# Mission 064 — Fresh Version-Explicit Scraper Studio Reconciliation

## Exact requested outcomes

| Field | Result |
|---|---|
| INSTALLED_CLI_VERSION | `0.3.5` (version-pinned local help package) |
| RUN_VERSION_SELECTOR | **SUPPORTED** — local 0.3.5 help: `--version <version>` / `Scraper version (e.g. "dev")`. |
| APPROVE_AUTO_SAVE | **SUPPORTED** — local 0.3.5 help: `--auto-save` saves the approved template automatically after successful completion and sends `auto_save` to the resume call. |
| EXPLICIT_PRODUCTION_VERSION_IDENTIFIABLE | **NO** for the current collector without a mutation-capable request: retained evidence contains only the visible label `v1 (prod)`, not a version ID/revision/template ID/selector value. |
| FUTURE_VERSION_BOUND_RUN | **PREPARED** — unexecuted CLI shape, correlation contract, raw-first evidence gate, and provider-free run-intent primitive are preserved. |
| MISSION_041B_RECONSTRUCTION | **ABANDONED_AS_UNDER_INSTRUMENTED**. |
| NEXT_REAL_EXPERIMENT | Separately authorize exactly one version-bound run only after direct provider evidence supplies the exact version value and the future preflight passes. |
| PROVIDER_CALLS | `0` |
| MUTATIONS | `0` |
| RETRIES | `0` |

## Documented version model

The current official documentation distinguishes an IDE **development draft** from a production scraper. IDE edits auto-save to a development draft; an existing scraper requires **Save to production** before it can be initiated outside the IDE. In the documented Self-Healing workflow, the AI produces a diff, accepting it saves the change to draft, Preview tests output, and Save to Production makes the refactored configuration live. A **version** is the CLI run selector value; the local 0.3.5 help gives `dev` as an example but does not define a stable version-ID schema. A **promotion** is therefore treated in AEGIS as a provider-side persistence boundary, not an AEGIS data-release authorization.[1][2][3]

## Prepared future run

The only prepared future CLI shape is:

```text
bdata scraper run <collector_id> <target_url> --version <explicit_version> --json
```

It is not authorized or executed. The run intent refuses missing collector, absolute HTTP(S) target, explicit version, correlation ID, SHA-256 prompt hash, positive timeout, exact one-operation budget, or zero retry budget. It preserves the required correlation fields and never substitutes an AEGIS-local ID for a provider operation/run/response ID. The exact claim *“This run executed production version X”* requires both the approved `--version X` command and provider-returned run/response metadata independently binding the output to `X`; otherwise the outcome is `VERSION_EXECUTION_UNPROVEN`.

## Validation

The focused version-bound safety suite passed **7 tests**. The full canonical provider-free suite passed **530 tests**. Historical evidence paths were not modified.

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options
[2]: https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool
[3]: https://docs.brightdata.com/datasets/scraper-studio/develop-a-scraper
