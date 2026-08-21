# Official Read-Only Observability Capability Matrix

| Capability | Officially documented behavior | Historical Mission 041B applicability | Safe continuation conclusion |
|---|---|---|---|
| Runs page | Run rows expose an ID, trigger, template version, inputs, records, failed crawls, timestamps, and related metrics. | The exact one-input API run was correlated as `vj_mt1pakyc14nagbhvo5`. | Existing row-level metadata is a valid read-only correlation source. |
| Quick View | The dashboard can preview up to 100 collection records as JSON. | The browser bridge timed out before the correlated run detail rendered. | Potentially useful, but no new provider fact exists until the actual detail view can be opened. |
| Dashboard download | Real-time output is stored provider-side but cannot be downloaded from the dashboard. | Mission 041B was a real-time, one-input rerun. | Dashboard download cannot recover the historical output. |
| API/download delivery | API download or configured delivery retrieves structured result data with the relevant collection/snapshot identifier. | The historical rerun artifact has no retained provider run/snapshot identifier. | No documented retrospective retrieval is available from retained AEGIS evidence; do not invent a lookup. |
| IDE Raw versus Formatted output | Preview Raw output is before schema formatting; Formatted output applies output-schema formatting. | Starting a preview would execute provider work and is prohibited. | This distinction explains a possible future diagnostic method but cannot be used now. |
| Browser network capture | Browser workers support response tagging and WARC snapshots; Code workers do not record browser traffic. | WARC was not enabled in the historical output configuration and cannot be created retroactively. | Historical raw browser response recovery is unavailable. |
| WARC delivery | WARC requires enabling `warc_snapshot`, saving to production, running a job, and retrieving via configured delivery. | Each step after documentation review would alter configuration or initiate a new run. | Not authorized; future-only instrumentation. |

The matrix records capabilities rather than claims they were used for Mission 041B. It supports the narrower conclusion that the exact historical raw response cannot be recovered through a documented dashboard-download route for a real-time job, while an existing Quick View may still provide a read-only rendered record if the browser becomes available.

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/features "Bright Data Scraper Studio dashboard features"
[2]: https://docs.brightdata.com/datasets/scraper-studio/quickstart "Bright Data Scraper Studio API quickstart"
[3]: https://docs.brightdata.com/datasets/scraper-studio/scraper-studio-ide-interface "Scraper Studio IDE interface reference"
[4]: https://docs.brightdata.com/datasets/scraper-studio/warc-ide "WARC snapshots in Scraper Studio"
[5]: https://docs.brightdata.com/datasets/scraper-studio/worker-types "Scraper Studio worker types"
