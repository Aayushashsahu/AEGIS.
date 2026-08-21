# Bright Data Development-versus-Production Workflow — Official Evidence

## Official documentation observations

Bright Data’s official Self-Healing documentation states that an existing Scraper Studio scraper must be **saved in development mode** and describes the UI lifecycle as:

1. Self-Healing produces a diff in the IDE.
2. **Accept** saves the changes to a **draft**.
3. The user runs a **preview** and inspects its output.
4. The user clicks **Save to Production**; if fields changed, the UI can require **Update Schema** before publishing.

The same documentation says that accepted changes only affect production after **Save to Production**. The IDE guide distinguishes preview from production use and says that an existing production scraper receives code changes when the user clicks **Save to production**.

The CLI guide documents a different automation-oriented sequence: `heal` → review `preview_result` → `approve` → rerun. It states that approval commits the fix to the existing scraper, but does not establish that its API approval is identical to the IDE’s development-draft acceptance or UI production-publish boundary.

## Read-only dashboard observation

At `2026-08-21T18:00:00Z`, the authenticated browser navigated to the canonical collector editor route for `c_mt09pib13nxqz1coi`. The page remained in a loading state and a subsequent browser bridge read timed out. No editor state, version label, save control, code, run, heal, approval, schema, or publication control was clicked.

Therefore, the dashboard-specific facts requested in the development-versus-production check remain **UNKNOWN** until the editor can be observed in a functioning read-only session. This record does not infer draft state from the historical `v1 (prod)` observation or from documentation alone.

A subsequent read-only navigation to the authenticated Scraper Studio list view also remained in a loading state. No collector rows, version metadata, development draft metadata, editor code, or Save to Production control became observable. This was a browser-rendering limitation rather than evidence that the collector lacks a development draft.

## Sources

1. https://docs.brightdata.com/datasets/scraper-studio/self-healing-tool
2. https://docs.brightdata.com/datasets/scraper-studio/develop-a-scraper
3. https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli
