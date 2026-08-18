# AEGIS Mission 026 — Replace Gemini Baseline B with NVIDIA NIM

**Status:** Capability verified; one smoke passed; new NVIDIA participant remains `NOT_READY` pending owner review.
**Branch:** `mission-026-replace-gemini-with-nvidia-nim`
**Base:** Mission 025 main at `3af9298d374193b81ff34c7a58d1337571c040be`
**Date:** 2026-08-18

## Executive conclusion

Mission 026 verified that NVIDIA’s hosted NIM API can serve the selected candidate model through an OpenAI-compatible chat-completions interface. The official NVIDIA documentation identifies the hosted base URL as `https://integrate.api.nvidia.com`, the operation as `POST /v1/chat/completions`, and the API Catalog as the source for available models [1]. NVIDIA’s official `gpt-oss-20b` page identifies the candidate model, its text-only modalities, 131,072-token context, structured-output/function-calling/reasoning capabilities, and the same hosted base URL [2].

The implementation adds a provider-neutral catalog and caller seam. It does not replace the historical Gemini configuration or smoke evidence. Instead, it creates a new immutable NVIDIA candidate proposal and configuration whose participant slot remains `NOT_READY` until owner approval. The exact naive Baseline B semantics remain unchanged: one model call, tools disabled, first candidate only, bounded safe candidate recording, no AEGIS verification, no RiskGovernor, no CommitGate, no quarantine, no watch, and no rollback.

Exactly **one** real NVIDIA smoke operation was performed against `openai/gpt-oss-20b`. The response was HTTP 200, the model was reachable, one candidate was received/selected/accepted, and the bounded application recorded `generated_code_executed=false`. The smoke did not execute a benchmark trial, did not use runtime ground truth, and did not authorize production execution.

## Official capability matrix

| Capability | Evidence | Status |
|---|---|---|
| Hosted NVIDIA NIM API | NVIDIA LLM API reference | **VERIFIED** |
| OpenAI-compatible chat endpoint | `https://integrate.api.nvidia.com/v1/chat/completions` | **VERIFIED** |
| API-key authentication | NVIDIA API Catalog quickstart and model page | **VERIFIED** |
| `openai/gpt-oss-20b` catalog entry | NVIDIA LLM API catalog and Build model page | **VERIFIED_CATALOG_ENTRY** |
| Text input/output | Official model specification | **VERIFIED** |
| Structured output, function calling, reasoning | Official model capability specification | **DOCUMENTED**; tools disabled for AEGIS |
| Free hosted endpoint | NVIDIA Build model page reports Free Endpoint available | **DOCUMENTED** |
| Exact universal RPM/free-tier limit | No primary-source numeric limit found | **UNKNOWN**; not assumed |
| Model reachability | One controlled smoke, HTTP 200 | **VERIFIED** |
| First-candidate policy | One candidate received, selected, accepted | **VERIFIED** |
| Benchmark readiness | Owner approval and immutable promotion still required | **NOT_READY** |

The NVIDIA FAQ states that Developer Program access is intended for prototyping, research, development, and testing, while production use requires the appropriate enterprise entitlement [3]. The API trial terms state that access is subject to use limits and credits and is for limited trial purposes, so Mission 026 deliberately records rate-limit policy as `UNKNOWN_UNTIL_ACCOUNT_RESPONSE` rather than inventing the brief’s proposed 40 RPM value [4]. The implemented limiter supports configured RPM, minimum interval, and concurrency controls without hard-coding an unverified provider limit.

## Frozen NVIDIA candidate

| Field | Frozen candidate value |
|---|---|
| Participant slot | `BASELINE_B` replacement proposal; `prior_status=NOT_READY` |
| Provider | `NVIDIA_NIM` |
| Model ID | `openai/gpt-oss-20b` |
| Model revision | `gpt-oss-20b-v1.0-2025-08-05` |
| Endpoint | `https://integrate.api.nvidia.com/v1` |
| Prompt revision | `mission-026-baseline-b-prompts-v1` |
| Prompt SHA-256 | `8ec87b237f687f39d4dd1f1240670e74402877a7e3d45c364d1f8010cbec85b1` |
| Sampling | `temperature=NOT_APPLICABLE`, `top_p=NOT_APPLICABLE`, `top_k=NOT_APPLICABLE` |
| Max output | `8192` tokens |
| Tools | Disabled |
| Candidate policy | `FIRST_CANDIDATE`, maximum one candidate, auto-accept only inside the bounded smoke/test-double application boundary |
| Retry policy | `max_attempts=1`, `retry_count=0`, `backoff=0` |
| Timeout | `300` seconds |
| Rate limit | Provider RPM remains unknown; concurrency limit `1` |
| Participant proposal hash | `4602d935860cbc864248d6c870a0fce597ecf6ffe1be07326f7a1b2a04321e7f` |
| New candidate configuration hash | `52618538bdffaba5edeadcf29257848f1f7e0744079e1f7cb9d4de22db5f859e` |
| Old Mission 017 configuration hash | `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b` |
| Owner review | Required; no promotion performed |

The old frozen Mission 017 configuration remains unchanged: its Baseline B remains `GOOGLE_GEMINI_API` with model `gemini-3.6-flash`, its configuration hash remains `59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b`, and the historical Mission 019 Gemini smoke evidence remains preserved.

## Smoke evidence

| Field | Observed value |
|---|---|
| Smoke status | `PASS` |
| Provider operation count | `1` |
| HTTP status | `200` |
| Model reachable | `true` |
| Candidate received | `true` |
| Candidate selected | `true` |
| Candidate accepted | `true` |
| Provider latency | `26,105 ms` |
| Tools enabled | `false` |
| Runtime ground truth | `NOT_PROVIDED` |
| Generated code executed | `false` |
| AEGIS verification invoked | `false` |
| RiskGovernor invoked | `false` |
| CommitGate invoked | `false` |
| Benchmark runs executed | `0` |
| Healing operations executed | `0` |
| Metric results generated | `0` |
| Execution authorized | `false` |

The model response is stored as smoke evidence only. The candidate is untrusted data; no model-generated scraper code was executed, and no webpage or candidate text was allowed to override AEGIS policy. No API key, Authorization header, or other secret is written to the smoke artifact, proposal, configuration, logs, or report.

## Implementation boundary

`src/aegis/nvidia_provider.py` provides the model descriptor, catalog, environment-key lookup, OpenAI-compatible caller, response normalization, redacted metadata, provider error taxonomy, configurable rate limiter, prompt hashing, and NVIDIA Baseline B registry. The CLI selects this registry only when the candidate configuration explicitly declares `NVIDIA_NIM`; dry-run remains provider-free. The new candidate configuration is deliberately `NOT_READY`, so it cannot authorize the 180-run benchmark.

`BASELINE_B` remains semantically naive. It does not gain AEGIS verification, RiskGovernor, CommitGate, quarantine, watch, or rollback. Mission 022 remains the sole evidence-to-Mission-010 metric compatibility boundary. Mission 026 did not generate benchmark metrics and did not alter Mission 010 formulas.

## Validation

The provider-free focused suite passed with **18 tests**, and the complete repository suite passed with **287 tests**. The candidate CLI help exposes `--run` and `--output`. The candidate configuration dry-run returned `BLOCKED_NOT_READY`, with `expected_run_count=18` in the existing validation-plan representation, `execution_authorized=false`, and zero provider, benchmark, healing, and metric counters. The real 180-run command was not invoked.

The exact future benchmark command remains deferred until owner review, promotion, and a separately authorized execution decision:

```powershell
$env:PYTHONPATH="src"
python scripts/benchmark_runner.py `
  --config benchmarks/configs/mission_026_nvidia_nim_candidate_config.json `
  --run `
  --output benchmarks/runs/mission_026_nvidia_nim_candidate
```

This report contains no benchmark result. It records capability and smoke evidence only.

## References

[1]: https://docs.api.nvidia.com/nim/reference/llm-apis "NVIDIA NIM LLM APIs"

[2]: https://build.nvidia.com/openai/gpt-oss-20b "NVIDIA Build — gpt-oss-20b Model Page"

[3]: https://docs.api.nvidia.com/nim/docs/product "NVIDIA General NIM FAQ"

[4]: https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf "NVIDIA API Trial Terms of Service"
