# Mission 057 — Why Bright Data Self-Heal Fails: Read-Only Forensics

**Scope:** Preserved artifact comparison only.
**Mission 057 provider operations / mutations / retries:** `0 / 0 / 0`.

> The evidence supports a **provider refactor failure before candidate generation**. It does not expose an HTTP status, provider error code, provider-generated job ID, refactor trace, or a unique link between the user-provided email and a particular heal operation.

## Required classification

| Requested field | Evidence-backed result |
| --- | --- |
| `ROOT_CAUSE` | `PROVIDER_REFRACTOR_FAILURE` |
| `CONFIDENCE` | `MEDIUM` |
| `TARGET_INDEPENDENT` | `YES — LIKELY` |
| `CANDIDATE_GENERATION_REACHED` | `NO` for Mission 056; `NO` for Mission 053 |
| `PROVIDER_SIDE` | `YES` for the observed terminal failure |
| `AEGIS_SIDE` | `NO` for the observed terminal failure; no candidate or provider structured result existed for AEGIS to normalize, verify, or risk-score |
| `MUTATIONS_THIS_MISSION` | `0` |
| `NEXT_ACTION` | Stop. Preserve evidence. Do not retry. A future action requires new authorization and an officially documented read-only diagnostic keyed by an observed provider identifier. |

## Extracted provider facts

| Record | HTTP / error code | Terminal provider message | Latency | Lifecycle evidence | Candidate boundary |
| --- | --- | --- | ---: | --- | --- |
| Mission 030 | HTTP `500`; `PROVIDER_COMMAND_FAILED` | Provider CLI reported transient 500s and an `ide_automation` format error. | 407,029 ms | Failed during self-healing start after internal CLI retries. | Not reached; `HEAL_FAILED_BEFORE_CANDIDATE`. |
| Mission 033 | HTTP not exposed; no error | `awaiting_approval` | 66,413 ms | Planner → control preview → code fixer → step preview → request validation → step advance. | Reached; complete `preview_result` and candidate ID. |
| Mission 053 | HTTP and error code not exposed | `Self-healing finished with status "error".` | 450,143 ms | Planner, control preview, code fixer, step preview, request validation, CSS selector extraction. | Not reached; no candidate preview. |
| Mission 056 | HTTP and error code not exposed | `Self-healing finished with status "error".` | 464,455 ms | Planner, control preview, code fixer; then terminal error. | Not reached; raw response has no candidate, `preview_result`, candidate ID, or `awaiting_approval`; the candidate artifact is absent. |

Mission 056’s exact raw response was saved before parsing: **766 bytes**, SHA-256 `a0bba0d6b4d1c5dcd7271519a6ade77f3135385afe2cf8d211c75f3c0ec9e9b7`. Its safe metadata records process return code `1`, `timed_out=false`, provider status `error`, zero retries, AEGIS correlation `mission056-heal-c_mt09pib13nxqz1coi-20260821T153830Z`, and no provider-generated job ID. The identifier `m056-heal-20260821T153830Z` is AEGIS-generated, not an observed provider operation ID.

## Stage and target comparison

Mission 053 and Mission 056 did **not** expose enough telemetry to prove the same exact internal provider substage failed. Mission 053 proceeded farther through the visible provider sequence. They did share the same **macro lifecycle stage**: both entered planning/control-preview and the refactor pipeline, then terminated with status `error` **before candidate materialization**.

The Mission 053 failure occurred on the historical controlled target. The Mission 056 failure occurred on a different standalone static controlled target that passed independent direct baseline and drift health checks before the heal. This makes a target-independent provider failure **likely**, but not certain: the evidence does not exclude prompt-, template-, version-, account-, or provider-workflow-conditioned behavior.

The user-provided email text—“we were unable to generate working code for the changes you requested.”—is consistent with the provider refactor-failure classification. It is retained as unverified user-provided text because it has no timestamp, provider job ID, HTTP status, or error code for unique correlation to Mission 056.

## What the evidence does not support

Neither Mission 053 nor Mission 056 contains an authentication denial, account-scope denial, rate-limit signal, quota signal, Retry-After value, local transport timeout, or structured provider error code. The provider accepted both workflows, emitted lifecycle progress, and returned terminal payloads. Consequently, `AUTHENTICATION`, `ACCOUNT_SCOPE`, `RATE_LIMIT`, `QUOTA`, `TRANSPORT`, and `PROVIDER_TIMEOUT` are not selected classifications.

The source evidence SHA-256 values are recorded in `source_integrity_manifest.json`; all matched immediately after the read-only analysis.
