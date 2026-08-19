# AEGIS Final Demo Checklist

## Before recording

- [ ] Run `PYTHONPATH=src:. pytest -q tests/unit tests/integration` from the repository root.
- [ ] Run `cd webapp && AEGIS_ROOT=.. pnpm test && pnpm check && pnpm build`.
- [ ] Run `python .github/scripts/verify_evidence_integrity.py` and `python .github/scripts/scan_tracked_secrets.py`.
- [ ] Start the provider-free demo and confirm `GET /healthz` returns `200`.
- [ ] Confirm the banner and ledger call Mission 029/030 `REAL_PROVIDER` evidence, not a provider success.
- [ ] Confirm every candidate/replay panel says `TEST_DOUBLE` or `CONTROLLED_REPLAY`.
- [ ] Confirm `/downstream` says `BLOCKED` and `data shipped: no`.
- [ ] Confirm `/benchmark` says `CONTROLLED HARNESS` and does not expose an execution control.

## Judge walkthrough

- [ ] Home answers the product thesis within ten seconds.
- [ ] Historical case answers Bright Data’s real role within one minute.
- [ ] Controlled replay explains why a structurally valid price can still be wrong.
- [ ] Verification, Risk Governor, and Commit Gate visibly reject the candidate.
- [ ] The downstream output proves why the trust layer matters.
- [ ] Close with: **Bright Data heals. AEGIS decides.**

## Integrity guardrails

- [ ] Do not create, run, heal, approve, activate, commit, roll back, or benchmark from the UI.
- [ ] Do not retry the Mission 030 provider operation.
- [ ] Do not represent controlled replay, benchmark values, or visuals as `REAL_PROVIDER` evidence.
- [ ] Do not claim public deployment until the project owner publishes the checked release.
