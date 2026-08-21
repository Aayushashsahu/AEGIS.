# Future Bounded Rerun Authorization Package — Not Executed

> **Status:** `NOT_AUTHORIZED / NOT_EXECUTED`. This document is a required owner-authorization template, not permission to contact Bright Data.

| Parameter | Required value |
|---|---|
| Collector | `c_mt09pib13nxqz1coi` only |
| Target | The exact canonical Mission 033 target URL, supplied from the approved script; no user-provided substitution |
| Provider operation | One documented synchronous collector rerun only |
| Provider retries | `0` |
| Heal, approval, collector change, publish, commit, rollback | `0` |
| NVIDIA, Gemini, benchmark | `0` |
| Operation identity | A newly authorized opaque `AEGIS_OPERATION_ID`; it must not reuse any earlier identifier |
| Raw response | Capture response bytes once to a **new** path under `experiments/`; retain only its path, byte length, and SHA-256 in ordinary evidence |
| Correlation | Append one correlation record under `experiments/`, including collector, target URL SHA-256, start timestamp, provider run ID when returned, template version when returned, operation type, and AEGIS correlation ID |
| Verification | Canonical deterministic contract, historical, semantic, and independent-evidence verification required |
| Risk | Canonical risk decision required |
| Commit | `BLOCKED` by default. No automatic production commit or rollback is permitted. |

## Required Owner Authorization Text

The owner must explicitly authorize all of the following in one message before execution: the exact collector above; exactly one rerun; zero retries; a real current UTC authorization time; the new operation identity; the preselected new raw-response and correlation-record paths; required verification and risk evaluation; and commit/rollback remaining disabled. The authorization must state that no approval, healing, collector mutation, or extra provider operation is permitted.

## Required Preflight

The execution agent must refuse to send a provider request unless all checks pass: the exact collector is configured; the target remains canonical; the authorization scope and current UTC time are valid; the configured credential is present server-side without exposure; operation budget is one; retry count is zero; raw-response path and correlation directory are new and resolve below canonical `experiments/`; the operation ID is safe and unused; historical evidence hashes are unchanged; and automatic commit/rollback are disabled.

## Required Artifact Sequence

The future authorized operation must persist these distinct boundaries without overwriting an existing artifact:

```text
RAW_PROVIDER_RESPONSE_BYTES
  -> PARSED_PROVIDER_RESPONSE_ROWS
  -> NORMALIZED_AEGIS_OUTPUT + FIELD_LINEAGE
  -> CONTRACT_VALIDATION
  -> RISK_DECISION
  -> COMMIT_ELIGIBILITY (BLOCKED unless separately authorized)
  -> SHIPPED_OUTPUT (not permitted by this package)
```

If the provider response is non-JSON, malformed, async, or an HTTP error, its available response bytes must still be retained once and hashed. The operation then stops with the documented failure state. No polling, second request, or retry is permitted.
