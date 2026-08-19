# Mission 033 — Bounded Live Bright Data Validation

This directory records a **new**, isolated Bright Data Scraper Studio validation attempt. It does not replace, reinterpret, or edit the immutable Mission 028–032 records.

The provider operation budget is intentionally narrow: one new AEGIS-owned public target, one new collector creation, two collector runs, and exactly one heal request. A returned provider preview is only an `UNVERIFIED` candidate. No provider approval, automatic approval, production commit, rollback, benchmark, NVIDIA, or Gemini operation is authorized.

> **Safety invariant:** Bright Data may propose a change; only independently recorded AEGIS verification and an explicit risk decision may make output eligible for downstream use. Provider success is not an authorization to ship data.

The initial target is a public, AEGIS-owned three-field product page. The first run occurs against version `v1`. Only after its immutable baseline output is preserved will the page markup move to version `v2`, creating a controlled extraction-drift experiment while retaining the same URL and business facts. The external scraper and provider output are never fabricated or edited locally.

The implementation and command syntax are grounded in Bright Data’s documented Scraper Studio CLI lifecycle: create a collector, run it, request a heal with a prompt shorter than 1,000 characters, inspect the approval-gated preview, and re-run only if a change is separately approved. [1] [2]

## Artifact lifecycle

| Artifact | Purpose | Write policy |
| --- | --- | --- |
| `authorization.json` | Owner-approved operation scope and G1–G6 gate evaluation | Created before any mutation-capable provider call; never rewritten to hide results. |
| `collector_creation.json` | Complete redacted creation result | Provider response, written once after creation. |
| `initial_run.json` | Redacted baseline structured output | Provider response, written once after the first run. |
| `corruption_observation.json` | AEGIS-owned target change and observed output comparison | Written after the controlled markup drift and second run. |
| `detection.json` / `diagnosis.json` | Canonical AEGIS lifecycle evidence | Derived from preserved observations; no provider call. |
| `heal_request.json` / `heal_result.json` | Redacted single-attempt provider request and outcome | Written once; no retry. |
| `candidate_preview.json` / `verification.json` / `risk_decision.json` | Candidate boundary and deterministic decision evidence | Written only if the provider returns a candidate. |
| `approval.json` / `post_heal_run.json` | Explicitly records the unapproved boundary unless separately authorized | No automatic approval or re-run. |
| `artifact_hashes.json` | SHA-256 manifest for Mission 033 files plus revalidation of historical guard files | Finalized after the terminal outcome. |

## References

[1]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli "Bright Data — Build a scraper with the CLI"
[2]: https://docs.brightdata.com/cli/commands "Bright Data — CLI command reference"
