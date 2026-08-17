# 14 — Risk Register

**Scoring:** Probability and impact use Low/Medium/High/Critical.  
**Owner rule:** Replace role placeholders with named owners before Day 1.  
**Status:** Initial risks are proposed controls, not evidence that an incident occurred.

| ID | Risk | Probability | Impact | Detection method | Mitigation | Fallback | Owner | Trigger | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Bright Data healing latency threatens demo and retry budget. | High | Critical | Measure p50/p95 in Day-1 spike. | Async polling, deadline, pre-record truthful trace. | Use completed trace and fixture adapter; quarantine on timeout. | BD lead | p95 exceeds demo/episode budget. | OPEN |
| R-002 | Bright Data automation/API behavior is unknown or changes. | Medium | Critical | Contract spike with captured requests/responses. | Adapter boundary; no unverified claims; pin working path. | Local contract-preserving test double, clearly labeled. | BD lead | Required operation cannot be verified. | OPEN |
| R-003 | Staging mutation injection is nondeterministic. | Medium | Critical | Repeat same seed/reset and compare fixture hashes. | Versioned fixtures, fixed seeds, reset validation. | Reduce mutation set to qualified floor. | Benchmark lead | Same seed yields different truth/output. | OPEN |
| R-004 | False alarms reduce trust and product usability. | Medium | High | AlarmPrecision by severity and channel. | Calibrate thresholds, preserve channel evidence, report trade-off. | Quarantine high-risk events; cut weak channel from MVP. | Detection lead | Precision below target or unexplained alarms. | OPEN |
| R-005 | Silent-corruption detector misses L5 events. | Medium | Critical | L5 mutation trials and bad-data-shipped rate. | Independent evidence, semantic/unit checks, targeted fixtures. | Fail closed for high-risk fields; narrow claim. | Verification lead | Any committed L5 bad data. | OPEN |
| R-006 | Verification passes a wrong candidate. | Medium | Critical | VerificationMissRate and adversarial L5 tests. | Require two deterministic channels; add regression test for every miss. | Quarantine and rollback; block release if non-zero unexplained. | Verification lead | Verification miss detected. | OPEN |
| R-007 | Rollback restores an incorrect or unavailable version. | Low | Critical | Seeded rollback test and post-rollback validation. | Register known-good before commit; retain version artifacts. | Quarantine and escalate; do not mark healthy. | Platform lead | Rollback validation fails. | OPEN |
| R-008 | Benchmark lacks credibility or reproducibility. | Medium | High | Manifest/revision/seed audit and independent rerun. | Freeze baselines, preserve raw artifacts, publish formulas. | Publish only valid floor results and explain exclusions. | Benchmark lead | Missing seed, config, or raw output. | OPEN |
| R-009 | Benchmark expansion overruns schedule. | High | High | Daily gate review against Day-5 video start. | Prioritize detection, verification, video; cap target at floor. | Cut trial count toward floor. | Integrator | Core artifacts slip by one checkpoint. | OPEN |
| R-010 | Video capture fails or is unintelligible. | Medium | Critical | Muted playback, timing, caption, and link review. | Rehearsals, backup take, deterministic trace. | Use truthful captured trace; do not record with placeholders. | Demo lead | Any required scene or caption fails review. | OPEN |
| R-011 | Agent merge conflicts or contract drift. | High | High | Diff review and consistency audit. | Isolated branches, task IDs, owner review, canonical docs. | Pause parallel work and integrate sequentially. | Integrator | Conflicting API/metric/state changes. | OPEN |
| R-012 | External dependency changes undocumented. | Medium | High | Lockfile/config audit and Day-1 capability recheck. | Pin versions/configs; capture provider behavior; maintain fallbacks. | Freeze known-good environment and narrow claim. | DevOps lead | Provider/runtime differs from recorded evidence. | OPEN |
| R-013 | Secrets leak into fixtures or demo artifacts. | Low | Critical | Secret scanning and manual review. | Environment-only secrets, redaction, export allowlist. | Rotate credentials and discard artifact. | Security lead | Scanner or reviewer finds secret. | OPEN |
| R-014 | Product surface displays quarantined data as current. | Low | Critical | End-to-end status/visibility test. | Query only committed verified observations; explicit status. | Disable surface and show quarantine state. | Product lead | Quarantined record appears current. | OPEN |

## Risk review cadence

Review risks at the start/end of each day. A risk becomes a release blocker when it threatens zero blind commits, L5 bad-data prevention, reproducibility, Bright Data track alignment, or the recorded demo. Mitigations must produce evidence; verbal confidence does not close a risk.

## Mission 001 evidence update — 2026-08-17

The live spike produced evidence for R-001, R-002, and R-012: collector creation measured 236,628 ms, collection measured 198,844 ms and required a CLI realtime-to-batch fallback, and self-healing proposal generation measured 69,956 ms. These are single-run observations, not closed risks or general performance claims. R-005 and R-006 remain open because no L5 mutation or independent candidate verification was executed. R-007 remains open because provider-native version/rollback was not live-verified. R-013 had no secret findings in repository artifacts; credentials remained outside source and logs, but the release scan requirement remains.
