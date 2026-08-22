# Mission 065 — Direct Production Version Resolution

## Decision

> **PRODUCTION_VERSION: UNKNOWN**

The retained direct dashboard label is `v1 (prod)`. It is not treated as an exact provider-recognized version identifier because the inspected evidence does not expose a corresponding version selector value, version ID, revision, template ID, or provider-returned binding. Mission 065 therefore applies its explicit stop condition and does **not** execute the conditionally authorized version-bound run.

## Read-only evidence reviewed

| Evidence source | Result | Exact production version obtained? |
|---|---|---|
| Authenticated Code IDE route | The page was opened read-only; the browser extension timed out during loading and no action control was activated. | No. |
| Retained Mission 062/063 dashboard evidence | Shows `v1 (prod)` on existing run rows, without a version ID/revision/template binding. | No. |
| Canonical `GET /dca/collectors_list` adapter | The documented collector-list transport preserves collector IDs only. | No. |
| Current official Scraper Studio API quickstart | Documents published-collector trigger and dataset calls, but no read-only production-version metadata endpoint. | No. |
| Local Bright Data CLI 0.3.5 help | Confirms `scraper run --version <version>` but no verified version-list/metadata command. | No. |

The public documentation describes drafts, Save to Production, and a dashboard Versions menu. It does not provide a verified CLI or HTTP contract for retrieving this collector’s exact current production version. No undocumented endpoint was attempted.[1] [2] [3]

## Conditional run outcome

| Required condition | Result |
|---|---|
| Exact provider-recognized production version | **FAILED — UNKNOWN** |
| AEGIS correlation ID before run | **NOT CREATED** — no authorized run exists. |
| Canonical target use | **NOT EVALUATED** — run blocked before target selection. |
| Version-bound run | **NOT ATTEMPTED** |
| Provider run operations | `0` |
| Provider mutations | `0` |
| Retries | `0` |
| Mission 041B relink | **NOT ATTEMPTED** |
| Historical evidence | **UNCHANGED** |

## Required next evidence

The next safe step is a read-only provider response or stable authenticated IDE view that directly exposes both the exact selectable/runnable version value and its production association for collector `c_mt09pib13nxqz1coi`. Only then can a future authorization create its correlation record and permit one `scraper run ... --version <exact_value>` invocation.

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/initiate-collection-and-delivery-options
[2]: https://docs.brightdata.com/datasets/scraper-studio/quickstart
[3]: https://docs.brightdata.com/datasets/scraper-studio/develop-a-scraper
