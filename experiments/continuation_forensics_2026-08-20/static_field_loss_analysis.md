# Static Field-Loss Analysis

The repository-wide term search examined canonical `src/`, `scripts/`, `tools/`, and tests for field names and transformation terms. The result distinguishes **capture/persistence** boundaries from **intentional downstream verification projections**.

| Boundary | Code location | Field behavior | Can explain historical `input.url`-only persisted output? |
|---|---|---|---|
| HTTP response capture | `src/aegis/one_shot_rerun.py:178–181` | Reads bytes once. Historical Mission 041B did not retain these bytes. | Unknown; the evidence gap begins here. |
| JSON decoding | `one_shot_rerun.py:182–190` | Decodes one UTF-8 JSON value; malformed content fails closed. | No field allowlist. |
| Decoded row construction | `one_shot_rerun.py:191–205` | `tuple(dict(row) for row in payload)` copies every top-level mapping key. | No; this path has no top-level field filter. |
| Rerun evidence projection | `OneShotRerunResult.to_evidence_dict:55–58` | Emits the complete decoded rows; raw bytes are intentionally omitted from normal JSON evidence. | No top-level field filter, but historical raw bytes were not preserved. |
| Mission 041B persisted row artifact | `experiments/mission_041_post_heal_rerun/post_heal_output.json` | First retained row representation contains only `input.url`. | First observed loss point; provider-versus-pre-artifact source cannot be attributed retroactively. |
| Verification canonicalization | `scripts/mission033_verify_candidate.py:38–45`, called from `mission041b_verify_rerun.py:69` | Intentionally emits only `title`, `price`, and `availability`; price is narrowed to `currency` and `value`. | No; it executes only after the persisted row artifact exists. |
| Deterministic verifier | `src/aegis/verification.py:141–239` | Reads candidate rows, compares schema/required/type/nullability, returns checks. | No; it validates supplied rows and fails on missing fields. |
| Risk and commit | `mission041b_verify_rerun.py:77–83` | Consumes verification output and blocks release. | No row mutation. |
| Managed UI bridge | `scripts/mission032_lifecycle_api.py` | Does not read Mission 041B row evidence. | No. |

## Conclusion

No AEGIS-side top-level field-stripping path is evidenced **before** Mission 041B’s first persisted decoded row. The only explicit row projections are downstream baseline/verification normalizers, which correctly run after `post_heal_output.json` is present and cannot alter its contents. The historical classification is therefore strengthened to **evidence-retention gap with an unobservable upstream/pre-artifact loss location**, not an identified transport, verification, risk, commit, or UI projection bug.

The continuation also identified a future-coverage gap: error-body bytes were not preserved for `HTTPError` results, and the new lineage diagnostic required broader fixture coverage for non-list JSON, CSV/NDJSON-like content, null/empty values, nested fields, extra fields, and multi-row payloads. Those cases are assigned to the hardening phase and do not change historical evidence.
