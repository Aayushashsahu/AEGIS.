# Mission 029 Target and Live-Demo Protocol

## Target

The selected public target is [Hacker News](https://news.ycombinator.com). It is publicly accessible without login or paywall, contains easy-to-explain structured story fields, and was used in Mission 001 only as historical evidence. Mission 029 will create a fresh collector and will not reuse the historical Mission 001 collector.

The selected fields are `title`, `url`, `points`, `author`, and `comment_count`. The extraction objective is: `Extract top stories: title, url, points, author, comment count`.

## Public-data justification

The target contains publicly visible story metadata and no personal or private account data is required for the demonstration. The target is appropriate for a short judge-facing explanation because the structured rows map directly to the visible story list.

## Fresh-provider policy

Mission 029 will create exactly one fresh Bright Data Scraper Studio collector through the documented CLI path. The live target operation budget is approximately one collector creation, one collector run, and one healing request. If evidence already exists, the demo runner will reuse the preserved collector/run/healing evidence rather than repeat provider operations.

## Controlled failure

The live Bright Data output will be preserved unchanged. A reversible `DEMO_MUTATION` will then be applied only to the AEGIS evidence boundary: the first row with a numeric `points` value will be changed to `-1`, while the original value remains in the preserved provider snapshot and the mutation record. This is a known-ground-truth semantic invariant violation: points must be non-negative. The external website and Bright Data collector will not be modified.

The existing deterministic detector will evaluate the mutated AEGIS Observation. The resulting severity is expected to be the detector’s actual semantic/statistical result, not a forced L5 claim. The demo will continue through the existing diagnosis, provider-neutral RepairRequest, Bright Data approval-gated heal request, untrusted RepairCandidate, verification, RiskGovernor, CommitGate, and OutputEligibility boundaries.

The returned approval command is data only. Mission 029 will not execute Bright Data approval, auto-approve, activate, commit, rollback, or production output. If independent evidence is insufficient, the expected safe outcome is `QUARANTINE` and `BLOCKED`; the actual result will be reported from the preserved evidence.

## Exact documented live command shapes

```text
npx -p @brightdata/cli bdata scraper create https://news.ycombinator.com "Extract top stories: title, url, points, author, comment count"
npx -p @brightdata/cli bdata scraper run <fresh_c_*_collector_id> https://news.ycombinator.com --pretty
npx -p @brightdata/cli bdata scraper heal <fresh_c_*_collector_id> <bounded-repair-prompt> --url https://news.ycombinator.com
```

Credentials remain in the authenticated local CLI session. They will not be written to artifacts, command arguments, or reports.
