# AEGIS Mission 004 — Bright Data Healing Adapter

**Date:** 2026-08-17
**Status:** **COMPLETE for the bounded approval-gated adapter slice**
**Scope:** Translate provider-neutral `RepairRequest` into the verified Bright Data CLI heal command, submit asynchronously, track provider status, preserve a redacted provider envelope, and expose an immutable `UNVERIFIED` `RepairCandidate`.
**Explicitly out of scope:** Approval execution, `--auto-approve`, candidate verification, risk decisions, activation, commit, rollback, post-commit watch, repair memory, benchmark implementation, frontend, and dashboard.

> **AI proposes. Evidence decides.**

## Mission result

Mission 004 extends the existing `BrightDataCliAdapter`; it does not create a second Bright Data client. The bounded lifecycle is:

```text
RepairRequest
    → asynchronous BrightDataCliAdapter.request_healing()
    → poll_healing()
    → AWAITING_APPROVAL
    → CANDIDATE_READY
    → immutable RepairCandidate(UNVERIFIED)
```

The adapter uses the injected command-runner pattern established in Mission 002. Standard tests do not call Bright Data and require no credentials. A real provider command is only submitted if a caller explicitly uses the default subprocess runner with a configured CLI session; no live run was performed in Mission 004.

The provider’s `awaiting_approval` status is treated as **PROPOSAL RECEIVED / NOT PRODUCTION-ACTIVE**. It is not AEGIS approval. The adapter never invokes the returned approval command, never adds `--auto-approve`, and exposes no activation, commit, verification, risk, or rollback method.

## Exact provider command mapping

The domain remains provider-neutral. `build_heal_command()` performs the adapter-only mapping:

| RepairRequest field | CLI mapping | Evidence retained |
| --- | --- | --- |
| `collector_reference` | Positional argument after `bdata scraper heal` | `RepairCandidate.collector_reference` and `HealProviderEnvelope.collector_reference` |
| `repair_objective`, affected fields, contract fields, invariants, evidence references, target input | Constructed bounded prompt argument | The prompt is passed only at the adapter boundary; the domain object remains CLI-free. |
| `target_input["target_url"]` | `--url <target_url>` | Target input remains in the RepairRequest; evidence reference is recorded. |
| Request/correlation IDs | Not sent as undocumented CLI flags | Preserved in the `HealHandle` and local evidence reference. |

The command shape tested is:

```text
npx -p @brightdata/cli bdata scraper heal <collector_id> <prompt> --url <url>
```

The tested command contains no `bdata scraper approve` operation and no `--auto-approve` flag.

## Prompt construction

The adapter prompt includes the bounded repair objective, affected fields, output-schema fields, known invariants, evidence references, target input, and an explicit instruction that webpage/extracted content is untrusted data. It does not include arbitrary raw webpage instructions, credentials, authorization headers, or provider-specific endpoint syntax.

For the recorded Mission 001 failure involving missing `points`, a request objective remains contract-preserving, for example:

> Restore extraction of points without changing the output schema, while preserving title, url, author, and comment_count.

The exact prompt is generated from the immutable RepairRequest and is not stored as a domain field.

## Heal state model

| State | Meaning | Mission 004 transition rules |
| --- | --- | --- |
| `SUBMITTED` | Command is handed to the background runner. | Initial state. |
| `RUNNING` | Background provider command is still running or has started. | `SUBMITTED → RUNNING`. |
| `AWAITING_APPROVAL` | Provider returned an approval-gated proposal. | `RUNNING → AWAITING_APPROVAL`. |
| `CANDIDATE_READY` | The untrusted provider envelope/candidate can be retrieved locally. | `AWAITING_APPROVAL → CANDIDATE_READY`. |
| `FAILED` | Command, authentication, parsing, provider status, or required-field validation failed. | Fail closed. |
| `TIMED_OUT` | Bounded deadline elapsed. | Fail closed; no candidate is retrievable. |

No `ACCEPTED`, `VERIFIED`, `COMMITTED`, `ROLLED_BACK`, or post-commit state exists in the Mission 004 implementation.

## RepairCandidate envelope

`RepairCandidate` is immutable and contains:

| Field | Meaning |
| --- | --- |
| `candidate_id` | Opaque local candidate identifier. |
| `repair_request_id` | Source repair intent. |
| `collector_reference` | Provider-neutral collector reference. |
| `provider_operation_reference` | Provider response/job/operation identifier when present. |
| `provider_status` | Provider status string, including `awaiting_approval`. |
| `preview_result` | Recursively immutable provider preview data. |
| `diff_summary` | Provider diff summary when present. |
| `approval_command` | Returned provider next-step command as data only; it is never executed. |
| `raw_evidence_ref` | Redacted evidence reference, not an unbounded raw credential-bearing log. |
| `provenance` | `BRIGHT_DATA` or `TEST_DOUBLE`. |
| `created_at` and `latency_ms` | Timing metadata. |
| `verification_status` | Always `UNVERIFIED` in Mission 004. |

Candidate methods that would mark a candidate verified, accepted, or committed explicitly raise a later-mission error. The constructor rejects any verification status other than `UNVERIFIED`.

## Provider parsing and fail-closed behavior

The adapter requires a JSON object with a recognized status. For an approval-gated result, it requires `preview_result` and a provider operation identifier. It preserves `diff_summary` and the returned approval command if present. The following conditions do not create a candidate:

| Condition | Result |
| --- | --- |
| Non-zero CLI exit | `FAILED / PROVIDER_COMMAND_FAILED` |
| No JSON object | `FAILED / MALFORMED_PROVIDER_RESPONSE` |
| Provider status `failed` or `error` | `FAILED / PROVIDER_REPORTED_FAILURE` |
| Missing/unsupported status | `FAILED / UNEXPECTED_PROVIDER_STATUS` |
| `awaiting_approval` without preview | `FAILED / MISSING_PREVIEW_RESULT` |
| `awaiting_approval` without operation ID | `FAILED / MISSING_PROVIDER_OPERATION_ID` |
| Bounded deadline exceeded | `TIMED_OUT / PROVIDER_TIMEOUT` |

A successful process exit alone is never sufficient for candidate creation.

## Test double

`DeterministicBrightDataHealingTestDouble` extends the existing explicit `TEST_DOUBLE` mechanism with:

- `HEAL_AWAITING_APPROVAL`
- `HEAL_MALFORMED_RESPONSE`
- `HEAL_TIMEOUT`
- `HEAL_PROVIDER_FAILURE`

The test double returns `ProviderProvenance.TEST_DOUBLE`, uses deterministic local envelopes, and always creates `VerificationStatus.UNVERIFIED` candidates. It is not evidence of Bright Data behavior.

## Recorded Mission 001 integration path

The standard integration test uses the recorded Mission 001 Bright Data output without contacting Bright Data:

```text
recorded Bright Data output
    → Bright Data-provenance Observation
    → DetectionResult
    → Diagnosis
    → provider-neutral RepairRequest
    → TEST_DOUBLE healing response
    → TEST_DOUBLE RepairCandidate(UNVERIFIED)
```

The test confirms that the original collector reference survives into the request and candidate while the candidate provenance correctly changes to `TEST_DOUBLE` for the local substitute. It makes no live healing claim and does not approve the recorded provider proposal.

## Tests and measured results

The full suite passed:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

```text
40 passed in 0.15s
```

Mission 004-specific coverage includes 13 unit tests plus one recorded-artifact integration test. Tests cover command translation, prompt constraints, target validation, asynchronous submission, state transitions, `awaiting_approval`, preview/diff/operation capture, missing provider fields, malformed responses, provider failure, timeout, explicit test-double provenance, unverified-candidate construction, candidate state guards, no approval execution, no `--auto-approve`, and provider-neutral candidate fields.

No live Bright Data heal call was executed during Mission 004. Therefore, Mission 001’s measured live heal latency of approximately 69,956 ms remains the only live measurement and is not reclassified. Mission 004 test-double command results use deterministic local latency metadata and are not provider performance claims.

## Files created or modified

| Path | Change |
| --- | --- |
| `src/aegis/healing.py` | Added immutable heal states, provider envelope, `HealHandle`, `RepairCandidate`, verification-status guard, and result envelope. |
| `src/aegis/adapter.py` | Extended the existing adapter with prompt/command translation, async heal submission, polling, fail-closed parsing, evidence references, and candidate retrieval. |
| `src/aegis/test_double.py` | Added deterministic healing scenarios explicitly labeled `TEST_DOUBLE`. |
| `src/aegis/__init__.py` | Exported Mission 004 interfaces. |
| `tests/unit/test_mission004.py` | Added 13 healing adapter and safety tests. |
| `tests/integration/test_mission004_recorded_repair_request.py` | Added recorded Mission 001 → TEST_DOUBLE candidate integration coverage. |
| `experiments/AEGIS-MISSION-004-BRIGHT-DATA-HEALING-ADAPTER.md` | Added this evidence report. |
| Canonical docs | Mission 004 additions are appended to API contracts, data model, decision log, testing strategy, Bright Data integration, and README status. |

## Unresolved provider capabilities

Mission 001 labels remain unchanged. Candidate correctness is not independently verified. Provider-native version identity and rollback remain partial/documentation-only. Raw HTML from the tested CLI path remains unknown. WARC remains partially documented but not artifact-tested. Direct API behavior beyond the tested CLI path remains documentation-backed rather than live-tested. Approval semantics beyond the returned approval-gated envelope remain untested because no approval was executed.

## Security and safety checks

No credentials are stored in source, tests, prompts, provider envelopes, or committed evidence. The adapter does not log command output, authorization headers, or API keys. Returned approval commands are preserved as untrusted data but never executed. Scraped/provider text is not treated as policy. Candidate creation requires structured status, preview, and operation evidence; all other malformed or incomplete cases fail closed.

## Exact recommended Mission 005

Mission 005 should implement **RepairCandidate → Verification → Risk Governor**. It must independently verify the candidate using deterministic contract, historical, semantic, and independent-evidence channels; prevent any candidate from committing without the canonical gate; quarantine insufficient evidence; and measure `BlindCommitRate`, `VerificationMissRate`, `FalseRepairRate`, and L5 bad-data-shipped rate. It must not reinterpret this Mission 004 provider proposal as verified merely because Bright Data returned `awaiting_approval`.
