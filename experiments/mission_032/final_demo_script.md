# AEGIS Final Judge Demo Script

**Duration:** approximately 2 minutes 30 seconds.
**Audio:** optional; every decisive label is visible.
**Rule:** `REAL_PROVIDER`, `TEST_DOUBLE`, and `CONTROLLED_REPLAY` are spoken and visible exactly as shown.

| Time | Screen | Action | What the judge should understand |
| --- | --- | --- | --- |
| 00:00 | `/` | Open the headline and the case-protection entry point. | A scraper can be green and still be wrong. AEGIS protects an extraction contract rather than trusting successful JSON. |
| 00:12 | `/judge` | Point to the two `REAL_PROVIDER` lanes. | Bright Data participated in real collection and healing operations; AEGIS preserves evidence and distinguishes terminal failure from a candidate. |
| 00:22 | `/cases/mission_033_real_provider_candidate` | Open the newest real-provider lifecycle graph. | A fresh Bright Data collector captured a baseline, then the same collector saw an AEGIS-owned markup drift at the same URL. |
| 00:36 | Same case | Read `OBSERVATION → DETECTION → DIAGNOSIS`. | The second real run returned only its input URL. Canonical detection identifies `title`, `price`, and `availability` as missing; diagnosis is deterministic `SCHEMA_DRIFT`. |
| 00:50 | Same case | Highlight `REPAIR` and `CANDIDATE`. | Exactly one compact 324-character Bright Data heal produced a real `awaiting_approval` preview. The provider proposal is still untrusted. |
| 01:05 | Same case | Highlight `VERIFICATION`, `RISK`, and `COMMIT`. | Contract, history, semantic, and independent owned-target evidence pass; risk is `ACCEPT`. Yet Commit remains `BLOCKED`: no provider approval, post-heal run, or downstream output occurs without separate authorization. |
| 01:25 | `/cases/mission_029_real_provider` | Contrast the original real-provider lane. | Mission 029 produced 150 rows but its compact heal ended HTTP 500 before candidate creation. AEGIS keeps that failure visible rather than rewriting history. |
| 01:40 | `/cases/controlled_silent_corruption` | Open the explicit `TEST_DOUBLE` silent-corruption case. | A plausible wrong value moves through verification and is rejected. This controlled ground-truth lane is never relabeled as Bright Data output. |
| 01:55 | `/downstream` | Compare expected `599` with observed `29.99`; show the checks. | Contract can pass while history, semantic, and independent evidence fail. Bad data is blocked before consumption. |
| 02:08 | `/benchmark` | Read the immutable harness counts and caveat. | Mission 028 records 180 opportunities, 179 completions, one provider failure, and 60 controlled-harness NVIDIA operations; it is not a Bright Data production metric. |
| 02:20 | `/` | Close on the product thesis. | **Bright Data proposes and heals. AEGIS verifies and decides.** |

## Presenter guardrails

Do not say that the Mission 030 heal succeeded or that controlled-harness results are live-provider metrics. Mission 033 has a real Bright Data `awaiting_approval` preview whose deterministic verification passed, but do not say it was approved, activated, rerun, committed, shipped, or proven as corrected live output. If asked about Mission 030, state that the compact 676-character request reached the provider and ended HTTP 500 before candidate creation. If asked about Mission 033, state that the one 324-character heal returned a preview, AEGIS verified the preview independently, and the commit boundary remained blocked pending separately authorized provider approval and a new post-approval run.
