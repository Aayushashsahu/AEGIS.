# Mission 042 — Read-Only Post-Heal Forensic Analysis

## Scope

This analysis used only preserved Mission 033, 040, 041A, and 041B artifacts. **No provider request or mutation occurred.**

## Evidence comparison

| Evidence stage | Confirmed artifact fact | What is not retained or proven |
| --- | --- | --- |
| Original extraction contract | Required fields were `title` (non-null string), `price` (non-null object), and `availability` (non-null string); the minimum row count was one. | No provider template source or output-schema configuration snapshot was retained. |
| Repair request | The repair prompt explicitly required restoring those three fields and preserving the output schema. | A prompt is not proof of persisted template configuration. |
| Heal candidate | The real provider preview returned all three required fields, including `price={currency: USD, value: 599}`. | The retained candidate has only a one-step diff summary; selector, field-mapping, and final template details are absent. |
| Approval | Mission 040 returned HTTP `200` and `RESUME_ACCEPTED`. | The response had no body, job ID, revision ID, or final-template content. |
| Completion | Mission 041A returned HTTP `200` and explicit status `done`, classified as `COMPLETED`. | No revision, job, or timestamp identifier was returned in retained safe metadata. |
| Post-heal rerun | Mission 041B returned HTTP `200`, one real-provider row, and schema `input: dict`. | The response cannot determine whether the loss arose in template persistence, output configuration, or provider response shaping. |

## Exact contract versus actual output

| Category | Expected | Actual post-heal output |
| --- | --- | --- |
| Target URL | `https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target` | Same URL, carried inside `input.url`. |
| Required fields | `title`, `price`, `availability` | `input` only. |
| Required schema | `title: str`, `price: dict`, `availability: str` | `input: dict`. |
| Semantic expectation | `AEGIS Verification Widget`; price USD `599`; `Available` | None of those extraction fields were returned. |
| Row count | Minimum `1` | `1`. |

The public target contract presents price as `$599.00`, while the frozen extraction contract requires a structured output object containing currency and numeric value. This is a representation distinction, not a contract conflict.

## Candidate conclusion

**`CANDIDATE_CONTAINS_REQUIRED_FIELDS: YES`** at the preview-output level. The candidate preview had all required fields and values, and the heal request explicitly demanded preservation of the schema. However, **selector/template changes and field mappings are `UNKNOWN`** because the preserved provider candidate contains no implementation diff beyond “proposed template has 1 step(s).”

## Root-cause classification

**`ROOT_CAUSE: H — UNKNOWN`**

**`ROOT_CAUSE_CONFIDENCE: LOW`**

The evidence proves an output-level discontinuity: a complete candidate preview was accepted and a completed post-approval run later returned only `input.url`. It does **not** prove whether the cause was provider repair incompleteness, a non-persisted template, changed output configuration, or incomplete response shaping. Selecting A–G would require provider configuration, revision, or template evidence that was not retained and is not inferred here.

## Safety assessment

**`AEGIS_DECISION: CORRECT_FAIL_CLOSED`**

The real output lacked all required extraction fields. Deterministic checks then failed nullability, semantic invariants, and independent entity consistency; the risk governor returned `REJECT`, commit was `BLOCKED`, and data was not shipped. The system did not treat HTTP `200` or provider completion as semantic success.

## Recommendation before any future provider action

Do not automatically heal or rerun. A future authorization should first permit a narrowly bounded **read-only** collection of the final provider template/output-configuration or revision evidence, with a comparison against the frozen three-field contract. A future repair acceptance policy should require both candidate preview success **and** evidence that the persisted post-approval template exposes the same field mapping and output schema before a rerun is authorized.

| Final field | Result |
| --- | --- |
| Expected fields | `title`, `price`, `availability` |
| Post-heal fields | `input` |
| Missing fields | `title`, `price`, `availability` |
| Candidate contains required fields | `YES` — preview level; implementation details unknown |
| Root cause / confidence | `H — UNKNOWN / LOW` |
| AEGIS decision | `CORRECT_FAIL_CLOSED` |
| Real provider calls this mission | `0` |
| New provider authorization required | `YES` |

## References

1. `experiments/mission_033_live_bright_data_success/repair_request.json`
2. `experiments/mission_033_live_bright_data_success/provider_operations/operation_001_heal.json`
3. `experiments/mission_033_live_bright_data_success/candidate_preview.json`
4. `experiments/mission_041a_post_approval_progress/progress_check.json`
5. `experiments/mission_041_post_heal_rerun/post_heal_output.json`
6. `experiments/mission_041_post_heal_rerun/verification.json`
