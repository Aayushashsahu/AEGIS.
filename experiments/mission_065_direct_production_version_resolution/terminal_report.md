# Mission 065 — Direct Production Version Resolution + Conditional Version-Bound Preflight

## Final report

| Required field | Result |
|---|---|
| PRODUCTION_VERSION | `UNKNOWN` |
| VERSION_SOURCE | `UNKNOWN` |
| CORRELATION_ID | `NOT_CREATED_BECAUSE_RUN_NOT_AUTHORIZED` |
| RUN_ID | `NOT_RETURNED_BY_PROVIDER` — no run occurred. |
| RESPONSE_ID | `NOT_RETURNED_BY_PROVIDER` — no run occurred. |
| COLLECTION_ID | `NOT_RETURNED_BY_PROVIDER` — no run occurred. |
| OPERATION_ID | `NOT_RETURNED_BY_PROVIDER` — no run occurred. |
| EXPLICIT_VERSION_USED | `NOT_USED` |
| HTTP | `NOT_AVAILABLE` — no version-bound provider request occurred. |
| TITLE | `NOT_APPLICABLE` — no exact version-bound output exists. |
| PRICE | `NOT_APPLICABLE` — no exact version-bound output exists. |
| AVAILABILITY | `NOT_APPLICABLE` — no exact version-bound output exists. |
| RAW_RESPONSE | `NOT_AVAILABLE` — no run occurred. |
| RAW_HASH | `NOT_AVAILABLE` — no raw provider response exists. |
| VERSION_BOUND | `NO` |
| PROVIDER_CALLS | `0` collection/run operations; the conditional run budget was never consumed. |
| MUTATIONS | `0` |
| RETRIES | `0` |
| HISTORICAL_EVIDENCE | `UNCHANGED` |
| GIT | `mission-065-direct-production-version-resolution` — commit pending final validation. |

## Stop decision

Mission 065 authorizes one run only if an exact provider-recognized production version is obtained. The collected evidence exposes the human-readable label `v1 (prod)` but no exact selector value, version ID, revision, template ID, or provider binding. The authenticated Code IDE route timed out while loading, and the current documented collector list, API quickstart, and CLI help did not yield a documented read-only production-version lookup contract. AEGIS therefore **did not guess** that `v1` is runnable and did not invoke `scraper run`.

The outcome is a safe stop, not a failed heal or failed collection: `FAILED_EXACT_PRODUCTION_VERSION_UNKNOWN`. Mission 041B was not retroactively linked. No provider identifier, correlation ID, target, response, or output was fabricated.

## Validation

The full canonical provider-free suite passed **530 tests**. Mission 065 modified only its new evidence directory. Protected historical mission evidence remains unchanged.

## Next necessary evidence

Obtain a stable authenticated IDE version selector or a documented provider response that directly shows the exact version value and its production association. A future one-run authorization can then supply the canonical target and create a raw-first correlation record before a single `scraper run ... --version <exact_value>` execution.
