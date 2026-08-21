# Mission 064 — Bright Data to AEGIS Lifecycle Mapping

The mapping is a **future-operation safety model**, not evidence that the currently retained collector passed any unobserved state. Bright Data UI promotion and AEGIS risk/commit authority remain distinct boundaries.

| Bright Data state | AEGIS state | Required evidence | Allowed next operation |
|---|---|---|---|
| Development draft | `OBSERVED_DRAFT_BASELINE` | Visible development status/draft identity, collector ID, code/schema fingerprint | Request Self-Healing only with separate owner authorization. |
| Self-Healing request submitted | `REPAIR_REQUESTED` | Provider-returned operation ID or `NOT_RETURNED_BY_PROVIDER`, raw response, correlation ID, prompt hash | Wait; no retry unless separately authorized. |
| AI diff generated | `CANDIDATE` | Provider diff/preview evidence and provider state `awaiting_approval` | Deterministic candidate verification. |
| Accepted diff saved to draft | `UNVERIFIED_DRAFT_CANDIDATE` | Visible accept result, draft ID/version if provider exposes it, raw operation evidence | Run preview only with separate authorization. |
| Preview complete | `READY_FOR_VERIFICATION` | Preview input, output, logs, raw/format distinction, required-field evidence | Run deterministic verification and risk assessment. |
| Verification PASS and risk ACCEPT | `COMMIT_ELIGIBLE` | Verification report, risk decision, no double-counted evidence, explicit owner release authority | Save to Production only under separate provider-mutation authorization. |
| Saved to Production | `PRODUCTION_PERSISTENCE_BOUNDARY` | Provider-visible production version/revision/template binding and save receipt | Capture exact version and request one version-bound run only with separate authorization. |
| Production version identified | `PRODUCTION_VERSION_BOUND` | Exact provider version value, production identity, timestamp, correlation record | One version-bound run under exact authorization. |
| Post-promotion run | `PROVIDER_OUTPUT` | Command contains `--version X`, provider run/response ID, raw response and hash, explicit binding to X | Canonical observation, detection, verification, and risk evaluation. |
| Verification completes | `VERIFIED` or `REJECTED` | Deterministic verification and risk results | Commit/release only if separately authorized; otherwise quarantine/reject. |

> **Non-equivalence rule:** Bright Data’s **Save to Production** persists a provider template. It does not itself authorize AEGIS to ship data or declare a repair safe. AEGIS commit authority stays downstream of independent verification and risk.

## Future version-bound run

The prepared, unexecuted CLI shape is:

```text
bdata scraper run <collector_id> <target_url> --version <explicit_version> --json
```

This syntax is verified against local **0.3.5** help. It may be used only after a future preflight confirms the exact version value from provider evidence and a separate owner authorization permits one run. No API parameter is asserted because this mission did not verify one.

The future claim — *“This run executed production version X”* — requires more than the requested command: the preserved provider run/response metadata must independently bind the provider-returned run or response identifier to `X`. Otherwise the result is `VERSION_EXECUTION_UNPROVEN`.

## Source record

See `official_findings.md` for the official documentation URLs, version-pinned local help results, and their limitations.
