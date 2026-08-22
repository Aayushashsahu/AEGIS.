# AEGIS Final-Day Judge Demo Script

**Target duration:** 2 minutes 30 seconds.
**Message:** **HTTP 200 does not mean your scraper is correct.**
**Closing line:** **AI proposes. Evidence decides.**

| Time | Screen | Presenter action | Evidence-safe takeaway |
|---|---|---|---|
| 00:00–00:20 | Landing page | State the problem and point to the lifecycle graphic. | A scraper can return valid JSON and still silently ship the wrong `title`, `price`, or `availability`. AEGIS is a reliability layer around Bright Data Scraper Studio, not another generic scraper. |
| 00:20–00:40 | Bright Data collector / documented evidence page | Show the real collector reference and Scraper Studio context. | Bright Data is central: it provides the collector, execution substrate, and Self-Healing capability. AEGIS observes, verifies, and governs release. |
| 00:40–01:00 | Real provider case: baseline and drift | Open the real lifecycle from collection to deterministic detection/diagnosis. | The same collector saw a real markup drift. AEGIS detected missing required fields and constructed deterministic evidence before any repair decision. |
| 01:00–01:20 | Real provider heal candidate | Show the Mission 033 candidate boundary. | Bright Data produced a real candidate preview. AEGIS treated it as a proposal, not a fact: deterministic contract, history, semantic, and independent checks evaluated it before risk. |
| 01:20–01:45 | Judge Mode real failure lane | Show Mission 040 approval then Mission 041B rerun. | This is the decisive real outcome: Bright Data approval and rerun returned `HTTP 200`, but the output contained only `input.url`. `title`, `price`, and `availability` were missing. AEGIS verification failed, RiskGovernor rejected, CommitGate blocked, and data was **not shipped**. |
| 01:45–02:05 | Controlled replay / downstream | Clearly point to the `TEST_DOUBLE` / `CONTROLLED_REPLAY` label. | The controlled replay demonstrates both deterministic branches: complete required fields lead to PASS/ACCEPT but remain owner-controlled; input-only or plausible wrong values lead to FAIL/REJECT/BLOCK. It is not represented as provider output. |
| 02:05–02:20 | Downstream value | Show price intelligence / monitoring / analytics explanation. | Trusted structured data powers monitoring and decision support only after AEGIS proves the evidence chain. AEGIS prevents a green-but-wrong scraper from contaminating downstream products. |
| 02:20–02:30 | Landing or Judge Mode conclusion | Return to the governing rule. | **AI proposes. Evidence decides.** The provider-side refactor gap is honestly visible; AEGIS’s safety gate still held. |

## Presenter guardrails

Do **not** say that a real self-heal loop completed, that Mission 041B produced corrected structured output, or that a `TEST_DOUBLE` is `REAL_PROVIDER`. Do state that Mission 040 recorded one real approval and Mission 041B recorded a real post-approval rerun, then show the actual fail-closed result: HTTP 200 plus incomplete output was rejected and blocked.

Do **not** spend time on mission numbers, source code, benchmark internals, or unverified provider-root-cause theories. If asked why no final successful self-heal is shown, say that repeated provider refactor attempts failed before candidate generation, Bright Data support was contacted, and AEGIS refused to fabricate success or weaken verification.
