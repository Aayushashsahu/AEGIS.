# 20 — Mission 034 Future Approval-Boundary Amendment

**Status:** Owner-authorized implementation amendment, fixture-only.
**Authority:** Owner authorization dated 2026-08-20; this document preserves the frozen Mission 004 contract.
**Real-provider mutation budget:** `0`.

## Decision

AEGIS adds a **future approval adapter boundary** named `FixtureOnlyApprovalGate.approve_candidate(candidate_id, collector_id, authorization_context)`. The boundary is deliberately unable to invoke a provider: it contains no subprocess runner, HTTP client, CLI command construction, or frontend route. It records only controlled `TEST_DOUBLE` approval semantics and cannot promote a fixture record to `REAL_PROVIDER` provenance.

Mission 004 remains unchanged: its adapter captures an approval instruction as untrusted provider data and exposes no provider approval action. This amendment neither reinterprets that instruction nor authorizes any real approval, rerun, heal, collector creation, commit, or rollback.

## Credential contract

The sole future CLI credential interface is server-side `BRIGHTDATA_API_KEY`. The DCA bearer-token interface, `BRIGHT_DATA_API_TOKEN`, is intentionally **not** treated as an alias. The read-only diagnostic established that the managed DCA token reaches the DCA endpoint but lacks the required CLI account permissions when mapped to the CLI credential name. The validator retains only the configured variable name, never the value.

| Input | Boundary result |
| --- | --- |
| Non-empty `BRIGHTDATA_API_KEY` | Configuration fact accepted; no provider call occurs. |
| Only `BRIGHT_DATA_API_TOKEN` | Fail closed; DCA scope is not silently assumed to satisfy CLI approval scope. |
| Missing credential configuration | Fail closed. |

## Fixture-only authorization contract

The gate requires the exact canonical scope:

| Field | Required value or rule |
| --- | --- |
| Candidate | `candidate_m033_a0d9aa5a0d056720` |
| Collector | `c_mt09pib13nxqz1coi` |
| Provenance | `TEST_DOUBLE` only |
| Operator, authorization reference, correlation ID | Non-empty |
| Time window | Timezone-aware, currently valid authorization |
| Operation budget | `0` prior operations; one fixture record maximum |
| Retry budget | Exactly `0` |
| Automatic commit / rollback | Both disabled |

Every accepted fixture record includes candidate and collector identifiers, operator, authorization timestamp/reference, correlation ID, fixed fixture operation identifier, redacted fixture response metadata, result, provenance, and an SHA-256 evidence hash. It contains no credential or real-provider response.

## Explicit non-goals and re-entry conditions

The amendment does not establish collector access, account/workspace access for the target collector, provider approval permissions, endpoint behavior, or a post-approval rerun transport. `ReadOnlyCollectorAccessBoundary` returns `COLLECTOR_ACCESS=UNKNOWN` with `provider_called=false` for the exact canonical collector because the reviewed interfaces do not establish a harmless metadata lookup. A future real-provider integration requires a separately reviewed amendment that documents a supported read-only collector lookup, confirms exact workspace permissions, verifies the provider operation, and retains all current verification, risk, commit, rollback, provenance, and evidence gates.

## Test requirements

The focused tests prove credential redaction, missing/DCA-only configuration failure, candidate/collector mismatch rejection, missing/expired/unsafe authorization rejection, single-operation budget, zero retries, commit/rollback prohibition, and immutable `TEST_DOUBLE` provenance. Tests must not call Bright Data or construct a real provider operation.
