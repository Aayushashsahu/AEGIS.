# Mission 026 — NVIDIA capability sources

Research date: 2026-08-18.

| Capability | Evidence | Status |
|---|---|---|
| Provider | NVIDIA hosted NIM/API Catalog | VERIFIED |
| Hosted endpoint | `https://integrate.api.nvidia.com/v1` | VERIFIED |
| Chat operation | `POST /v1/chat/completions` | VERIFIED |
| Authentication | NVIDIA Developer/API key flow from Build model page | VERIFIED |
| Candidate model | `openai/gpt-oss-20b` appears in the official LLM API catalog and Build page | VERIFIED_CATALOG_ENTRY |
| Candidate model revision | NVIDIA model page documents `gpt-oss-20b` v1.0 (August 5, 2025) | DOCUMENTED_MODEL_IDENTIFIER |
| Text capability | Text input/output; model page documents 131,072-token context | VERIFIED_DOCUMENTATION |
| Structured output/tool support | Model page documents function calling and structured output; Mission 026 disables tools | DOCUMENTED_CAPABILITY |
| Account access | NVIDIA Developer Program provides free access for prototyping/development/testing according to FAQ | VERIFIED_DOCUMENTATION |
| Exact free credits/RPM | Not stated as a universal numeric value in sources read | UNKNOWN |
| 40 RPM claim | No primary-source confirmation found | UNKNOWN; DO NOT ASSUME |
| Candidate reachability | Requires one real smoke with a configured NVIDIA key | NOT_YET_VERIFIED |

## Primary URLs

- NVIDIA LLM API reference: https://docs.api.nvidia.com/nim/reference/llm-apis
- NVIDIA API Catalog quickstart: https://docs.api.nvidia.com/nim/docs/api-quickstart
- NVIDIA General NIM FAQ: https://docs.api.nvidia.com/nim/docs/product
- NVIDIA gpt-oss-20b model page: https://build.nvidia.com/openai/gpt-oss-20b
- NVIDIA hosted catalog: https://build.nvidia.com/models
- NVIDIA API Trial Terms: https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf

## Policy consequence

The benchmark participant uses one exact candidate model, endpoint, prompts, sampling configuration, disabled tools, first-candidate policy, timeout, and zero-retry policy. The rate limiter keeps `max_requests_per_minute` explicitly UNKNOWN until a primary account/model response verifies it; it does not hard-code 40 RPM. The product-facing catalog accepts multiple model descriptors, while the benchmark proposal freezes one model and remains `NOT_READY` until the smoke and owner review are complete.
