# AEGIS Mission 029 — Live Bright Data Self-Healing Demonstration

## Outcome

Mission 029 executed a bounded, sponsor-native live demonstration against the public Hacker News front page. A fresh Bright Data Scraper Studio collector was created and run successfully. The one authorized healing request was rejected before candidate creation because the generated bounded repair prompt measured 1,187 characters and the provider reported a 1,000-character limit. The failure was preserved as evidence. No retry, approval, production commit, or fabricated candidate occurred.

> **AI proposes. Evidence decides.** The demonstration therefore terminates at `FAILED_BEFORE_CANDIDATE`; verification, RiskGovernor, and CommitGate were not invoked because no real RepairCandidate exists.

## Target and live provider evidence

| Field | Recorded value |
| --- | --- |
| Public target | `https://news.ycombinator.com` |
| Reason | Public, unauthenticated, no-paywall listing with immediately legible story metadata. |
| Fresh collector | `c_msyo46bp1slx64351` |
| Collector create | `operation_001`; exit `0`; `178,696 ms` |
| Collector run | `operation_002`; exit `0`; `108,112 ms` |
| Run IDs | `response_id=d2t1787058048204rt325p1dbgjg`; `batch_job_id=j_msyo82sl1yrlfgm5x9` |
| Mode | Realtime attempted; provider evidence recorded fallback to `BATCH`. |
| Structured output | `150` live rows, normalized to title, URL, points, author, and comment count fields. |
| Healing request | `operation_003`; exit `1`; `1,163 ms` |
| Healing failure | `PROVIDER_COMMAND_FAILED`: heal prompt `1187` characters; provider limit `1000`. |

The exact documented CLI family used was `bdata scraper create`, `bdata scraper run`, and `bdata scraper heal`. The provider output and CLI status traces are preserved under `experiments/mission_029/provider_operations/`; no credential, Authorization header, or API key is stored. The raw live collection output remains separate from the AEGIS-only mutation evidence. Bright Data documents the CLI create/run/heal flow and an approval-gated healing boundary; approval was deliberately not called. [1] [2]

## AEGIS lifecycle evidence

| Stage | Evidence-backed state |
| --- | --- |
| Observation | A live Bright Data result became `UNTRUSTED_UNTIL_VERIFIED`. |
| Controlled mutation | `DEMO_MUTATION` changed row `0` field `points` from preserved value `402` to `-1` only in the copied AEGIS evidence snapshot. |
| Detection | `detected=true`, severity `L3`, with schema, statistical, and semantic provenance. The evidence includes the controlled negative-points violation and independently observed missing-field signals in live rows. |
| Diagnosis | `UNKNOWN`, `AMBIGUOUS`: the existing deterministic diagnoser correctly refused to assert one class when signals mapped to more than one class. |
| Repair request | A bounded provider-neutral request was created with the existing no-approve/no-commit constraints. |
| Bright Data heal | Failed before candidate creation at the provider prompt-length boundary. |
| Candidate | Not created. No approval command was returned or executed. |
| Verification | Not invoked; it requires a real candidate. |
| Risk Governor | Not invoked; it requires verification plus a real candidate. |
| Commit Gate | Not invoked; no candidate/verification/risk decision exists. |
| Shipment | `false`; `production_commit_performed=false`. |

This is not evidence of a successful repair or an unsafe rejection. It is evidence that the live collection/detection/repair-request path reached Bright Data and that the bounded provider request was rejected before the candidate boundary. The UI shows the unreached stages explicitly rather than relabeling them as a risk decision.

## Provider-operation boundary

| Operation | Count |
| --- | ---: |
| Fresh collector creation | 1 |
| Fresh collector run | 1 |
| Healing request | 1 |
| Approval | 0 |
| Production commit | 0 |
| Gemini calls | 0 |
| NVIDIA benchmark calls | 0 |
| Benchmark execution | 0 |
| Comparative metric calculation | 0 |

## Reconciliation and evidence integrity

The initial adapter release read realtime-to-batch fallback text only from stdout. The live Bright Data CLI emitted that metadata on stderr. A provider-free reconciliation read the preserved `operation_002` envelope, produced a new `collection_handle_reconciled.json` and `collection_summary_reconciled.json`, and did not issue a provider operation. The adapter was corrected to parse provider status identifiers and mode fallback from the combined stdout/stderr trace.

`pipeline_termination.json` records `FAILED_BEFORE_CANDIDATE`, all unreached downstream boundaries, zero retry, zero approval, zero production commit, and zero data shipment. `artifact_hashes.json` provides SHA-256 values for the important evidence artifacts.

## Judge-facing demonstration surface

The static Evidence Ledger is in `/home/ubuntu/aegis-mission029-demo`. It exposes a case-file rail, a sourced lifecycle spine, evidence identifiers, and an explicit brass `UNVERIFIED / NO CANDIDATE` stamp. It contains no provider approval or production-commit control. The surface uses static sanitized evidence values from this report and does not access Bright Data credentials or MCP tools.

## Repeat policy and launch command

The completed bundle has `demo_manifest.json`, so subsequent invocations replay the preserved state rather than call Bright Data again. The exact launch command is:

```bash
cd /tmp/aegis-mission029
PYTHONPATH=src:. python3 scripts/mission029_live_demo.py --live
```

For this completed run, the command returns replay-only evidence. A new live create/run/heal sequence must not be started without explicit owner approval because the bounded live-operation budget is already consumed.

## References

[1]: https://docs.brightdata.com/cli/commands "Bright Data CLI command reference"
[2]: https://docs.brightdata.com/datasets/scraper-studio/build-with-the-cli "Build with the Bright Data CLI"
