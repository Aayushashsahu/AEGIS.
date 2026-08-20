# Mission 043 — Read-Only Final Template / Schema Inspection

## Scope

This report uses only preserved artifacts. **Bright Data calls, provider mutations, retries, and configuration changes are all zero.**

## Persisted schema evidence

| Stage | Persisted schema or mapping evidence | `title` | `price` | `availability` | Template/revision details |
| --- | --- | --- | --- | --- | --- |
| Original contract | Frozen extraction contract requires `title: str`, `price: dict`, `availability: str`; all are required and non-null; minimum one row. | Required | Required | Required | No saved selector/template source. |
| Original collector creation | Creation prompt asks for exactly those fields; creation pipeline includes `output_schema_generator` and `code_generator`. | Requested | Requested | Requested | Collector ID and name retained; generated output-schema source, field mapping, selector map, and revision ID are not retained. |
| Heal candidate preview | Provider preview returns `title`, structured `price`, and `availability`; repair prompt explicitly says to preserve existing output schema. | Present | Present | Present | One-step diff summary only; no selector/template implementation or final revision. |
| Approval | HTTP `200`, `RESUME_ACCEPTED`. | Not provided | Not provided | Not provided | No body, revision, schema, template, field map, selector map, job ID, or persisted repair artifact. |
| Completion | Explicit progress status `done`/`COMPLETED`. | Not provided | Not provided | Not provided | Job ID, revision, template, schema, output definition, timestamp, and change summary absent from retained metadata. |
| Real post-heal rerun | One real-provider row, schema `input: dict`. | Absent | Absent | Absent | Actual final template/schema not retained; only observed output is available. |

## Field-mapping comparison

| Field | Pre-heal contract | Candidate preview | Approval / persisted state | Post-heal rerun |
| --- | --- | --- | --- | --- |
| `title` | Required non-null string | `AEGIS Verification Widget` | `NOT_PROVIDED` | Missing |
| `price` | Required non-null object | `{currency: USD, value: 599}` | `NOT_PROVIDED` | Missing |
| `availability` | Required non-null string | `Available` | `NOT_PROVIDED` | Missing |
| `input.url` | Input provenance, not an extraction field | Not returned by preview | `NOT_PROVIDED` | Present as the only returned field |

## First point of incompleteness

**`FIRST_POINT_OF_SCHEMA_LOSS: UNKNOWN`**

The first **evidence gap** is the boundary from the successful candidate preview to the post-approval persisted template. The approval response and subsequent completion status establish acceptance and completion, but provide neither an output schema nor a final template/revision identifier. Therefore the artifacts cannot establish where the three field mappings disappeared.

## Classification

**`ROOT_CAUSE: PROVIDER_STATE_UNAVAILABLE`**

**`CONFIDENCE: HIGH`** for the evidence-state classification; **the underlying technical cause remains unknown.** The retained record has no final persisted template, output definition, revision ID, selector map, or field map. It is therefore unsupported to assert candidate-schema loss, output-configuration change, non-persisted template, wrong-template rerun, default schema, or an AEGIS mapping error.

## AEGIS contract validation

AEGIS compared the required fields `title`, `price`, and `availability` to the actual output schema `input: dict`. It deterministically produced verification `FAIL`, risk `REJECT`, commit `BLOCKED`, and no shipped data. This is **`CORRECT_FAIL_CLOSED`**.

## Minimum evidence before future provider authorization

The minimum missing evidence is a read-only snapshot of the **final persisted collector template or output configuration**, including a revision/template identifier and its declared field mapping/schema. That artifact must be compared to the frozen contract before any future repair or rerun is authorized.

| Final field | Result |
| --- | --- |
| Expected schema | `title: str`, `price: dict`, `availability: str` |
| Candidate schema | All three fields observed in preview; implementation mapping `NOT_PROVIDED` |
| Approved schema | `NOT_PROVIDED` |
| Post-heal schema | `input: dict` |
| First point of schema loss | `UNKNOWN`; first evidence gap is candidate preview → persisted post-approval template |
| Root cause / confidence | `PROVIDER_STATE_UNAVAILABLE / HIGH` for missing-state classification |
| AEGIS decision | `CORRECT_FAIL_CLOSED` |
| Provider calls / mutations / retries | `0 / 0 / 0` |
| New provider authorization required | `YES` |

## References

1. `experiments/mission_033_live_bright_data_success/repair_request.json`
2. `experiments/mission_033_live_bright_data_success/collector_creation.json`
3. `experiments/mission_033_live_bright_data_success/candidate_preview.json`
4. `experiments/mission_033_live_bright_data_success/provider_operations/operation_001_heal.json`
5. `experiments/mission_041a_post_approval_progress/progress_check.json`
6. `experiments/mission_041_post_heal_rerun/post_heal_output.json`
7. `experiments/mission_041_post_heal_rerun/verification.json`
