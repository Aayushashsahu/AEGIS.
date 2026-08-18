# AEGIS Mission 027 — NVIDIA Baseline B Owner Review and Freeze

**Status:** Complete. NVIDIA Baseline B was promoted from `NOT_READY` to `READY` through the existing explicit owner-review and append-only readiness workflow. No benchmark, NVIDIA provider call, Gemini call, Bright Data call, healing operation, or metric calculation was executed in Mission 027.

**Branch:** `mission-027-nvidia-participant-freeze`

**Base:** Mission 026 commit `4bf3e17f1a32fdeab2c44f79359d9ee2c5949359`

## Executive conclusion

The project owner supplied the missing benchmark-side NVIDIA throttle policy. AEGIS now distinguishes that conservative benchmark policy from NVIDIA’s still-unknown provider RPM/free-tier ceiling:

> **Provider limit:** `UNKNOWN`.
>
> **AEGIS benchmark-side policy:** 6 requests per minute, 10-second minimum interval, concurrency 1.

The policy is included in the promoted participant metadata and therefore contributes to the promoted participant hash and the new immutable benchmark configuration hash. The historical Mission 026 proposal hash is preserved as the reviewed source proposal hash; it is not silently rewritten.

## Owner review and promotion

The complete `OwnerReviewDecision` for `BASELINE_B` records `approved=true`, `owner=PROJECT_OWNER`, `reviewer=PROJECT_OWNER`, the explicit timestamp `2026-08-18T10:40:27+00:00`, correlation ID `2a1d3d0b-9f61-4b9f-a995-a3d6d32b1d90`, and an owner-approved rationale. The reviewed source proposal hash is `4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f`.

The append-only readiness record is:

| Participant | Prior status | New status | Source proposal hash | Promoted participant hash |
| --- | --- | --- | --- | --- |
| `BASELINE_B` | `NOT_READY` | `READY` | `4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f` | `9b630269de415be0f69b92e7abd62dcaf4a3a535c3e8f3df982017a50ba25c14` |

The Mission 026 proposal artifact remains unchanged. Mission 027 adds a new approved proposal artifact and a new promotion record; it does not edit the earlier `NOT_READY` record.

## Exact approved NVIDIA configuration

| Field | Frozen value |
| --- | --- |
| Provider | `NVIDIA_NIM` |
| Model | `openai/gpt-oss-20b` |
| Model revision | `gpt-oss-20b-v1.0-2025-08-05` |
| Endpoint | `https://integrate.api.nvidia.com/v1` |
| Prompt revision | `mission-026-baseline-b-prompts-v1` |
| Prompt hash | `8ec87b237f687f39d4dd1f1240670e74402877a7e3d45c364d1f8010cbec85b1` |
| Candidate policy | `FIRST_CANDIDATE`, maximum 1, auto-accept first candidate |
| Tools | Disabled |
| Timeout | 300 seconds |
| Retry | 0 retries, 0 backoff |
| AEGIS verification | `NOT_USED` by the naive baseline |
| RiskGovernor | `NOT_USED` by the naive baseline |
| CommitGate | `NOT_USED` by the naive baseline |
| Runtime evaluator ground truth | `NOT_PROVIDED` |
| Generated code execution | `false` |

## Rate policy

The owner-approved AEGIS benchmark-side policy is frozen as follows:

| Policy field | Value |
| --- | ---: |
| `benchmark_requests_per_minute` | 6 |
| `benchmark_min_interval_seconds` | 10 |
| `concurrency_limit` | 1 |
| `provider_limit` | `UNKNOWN` |
| `provider_limit_status` | `UNKNOWN_UNTIL_ACCOUNT_RESPONSE` |

The value `6` is **not** represented as NVIDIA’s provider limit. It is an AEGIS-side conservative throttle. The provider’s universal RPM/free-tier ceiling remains unknown and is not estimated.

## New immutable benchmark configuration

The new configuration contains `BASELINE_A`, promoted NVIDIA `BASELINE_B`, and `AEGIS`. The generated canonical configuration hash is:

```text
8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4
```

The historical Mission 017 Gemini configuration remains the superseded, immutable configuration with hash:

```text
59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b
```

The new configuration preserves the canonical M001–M006 mutation set, L1–L5 mapping, `gpu-price-staging` v1 fixture, seed `12345`, 300-second timeout, zero retries, zero backoff, `NOT_PROVIDED` runtime ground truth, and `mission-010-metrics-v1`. The existing configuration schema retains `trial_count=1` for its deterministic seed invariant; the explicit execution protocol records `trials_per_mutation=10`, giving the future `3 × 6 × 10 = 180` opportunity floor.

## Fairness

Fairness passed. The validation checks confirm identical mutations, seed, fixture, trial policy, timeout, retry, backoff, ground-truth reference structure, and evaluator isolation. The only intentional participant-specific execution difference is the provider/model boundary for NVIDIA Baseline B. No participant receives runtime ground-truth content.

## Validation-only dry run

The provider-free dry run returned `READY_TO_EXECUTE`. This is a planning result, not an authorization to execute. The validation runner generated its existing 18-step planning representation (`3 × 6 × 1` participant/ mutation/ seed combinations); the separate future execution protocol records 10 trials per mutation and 180 total opportunities.

| Boundary | Result |
| --- | --- |
| Participants | `BASELINE_A READY`, `BASELINE_B READY`, `AEGIS READY` |
| Fairness | `PASS` |
| Configuration | `VALID` |
| Configuration hash | `MATCH` |
| Execution authorized | `false` |
| Benchmark runs executed | `0` |
| Provider operations executed | `0` |
| Healing operations executed | `0` |
| Metric results generated | `0` |
| Future benchmark root | Absent |

No NVIDIA caller was constructed by the dry-run path. The `--run` boundary was not invoked.

## Testing

Mission 027 adds 14 focused tests using local deterministic objects and no provider credentials. They cover complete and incomplete owner reviews, deterministic promotion, append-only readiness, rate-policy hashing, unknown provider limits, fairness, new configuration hashing, historical Gemini preservation, dry-run execution freedom, no NVIDIA/Gemini/Bright Data operation, historical evidence preservation, and absence of a benchmark run root.

The focused tests passed:

```text
14 passed
```

The complete existing suite plus Mission 027 passed:

```text
301 passed
```

## Safety and execution boundary

Mission 027 produced no benchmark result and no metric result. It did not execute the 180-run executor, did not invoke NVIDIA, did not invoke Gemini, did not invoke Bright Data, did not execute healing, did not approve a provider repair, did not commit or roll back a scraper, and did not create the future benchmark run root.

AI proposes. Evidence decides.
