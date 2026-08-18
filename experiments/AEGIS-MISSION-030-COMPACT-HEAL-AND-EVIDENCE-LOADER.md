# AEGIS Mission 030 — Compact heal validation and artifact-backed Evidence Ledger

## Outcome

Mission 030 corrected the **provider-transport compatibility boundary** discovered in Mission 029 without changing the canonical `RepairRequest`. The deterministic projection `mission-030-compact-heal-prompt-v1` produced a 676-character Bright Data transport prompt, below the previously observed 1,000-character provider limit. Its SHA-256 was `d766547e1991faa67fccfdc58ed2ffe09a2b7cfc8e4a03418243db2cc407d9b5`.

The one explicitly authorized Bright Data validation heal was then submitted against the existing Mission 029 collector `c_msyo46bp1slx64351`. Bright Data accepted the compact transport prompt but returned a terminal provider-side 500 failure before any candidate was created. AEGIS made exactly one external heal submission and issued no retry, approval, verification, RiskGovernor evaluation, CommitGate evaluation, production commit, activation, or shipment. Provider/CLI stderr contains internal provider retry diagnostics; these are preserved as provider behavior and are not an AEGIS retry.

| Boundary | Evidence-backed result |
|---|---|
| Canonical RepairRequest | Unchanged; Mission 030 adds only a transport projection |
| Compact transport prompt | 676 / 1,000 characters; `within_limit=true` |
| Bright Data create/run operations | 0 / 0 |
| Bright Data heal submissions | 1 |
| Heal latency | 407,029 ms |
| Candidate | Not created |
| Verification / risk / commit | Not invoked / not invoked / not performed |
| Data shipped | False |
| Metrics | None; this is not a benchmark mission |

## Evidence Ledger loader

The static Evidence Ledger now fetches and normalizes the committed Mission 029 artifact bundle through a pinned Git commit reference. It reads the manifest, reconciled collection summary, original observation, mutation, detection, diagnosis, repair request, healing failure, and pipeline termination artifacts. It validates artifact identity, row counts, HTTPS target safety, and sensitive-field absence. Missing, malformed, inconsistent, or unsafe artifacts fail visibly rather than falling back to hardcoded lifecycle state.

The UI labels real provider collection and healing evidence separately from the controlled `DEMO_MUTATION` and deterministic detection. It represents candidate, verification, risk, and commit as not created or not run when the committed evidence does not contain those records. No page control can approve or commit a candidate. The unused public debug collector was removed after confirming it was not loaded by the static document entry point.

## Validation

The focused Mission 030 suite passed with `17 passed`; it covers prompt determinism, required-field preservation, redaction, over-limit fail-closed behavior before a runner call, preflight zero-operation behavior, artifact loading, missing/malformed/sensitive-artifact rejection, read-only loading, and replay suppression of a second Bright Data submission. The full AEGIS suite passed with `363 passed` while the single captured operation artifact remained byte-identical. The Evidence Ledger type check and production build passed.

The Mission 030 evidence hash manifest records SHA-256 values for the provider-free preflight, the single captured provider operation, and the terminal live-heal result. Mission 029 evidence remains immutable.
