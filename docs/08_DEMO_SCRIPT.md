# 08 — Two-Minute Demo Script

**Primary artifact:** Recorded submission video.  
**Target runtime:** 02:00.  
**Evidence rule:** Replace all placeholders with measured output before recording.  
**Live-system rule:** Keep the live system available separately from the recording.

## Production requirements

The sequence must be deterministic, captioned, readable when muted, and rehearsed to the exact timing. The screen should show large values, clear state labels, evidence references, and no unexplained internal identifiers. If Bright Data healing is slow or unavailable during capture, use a pre-recorded but truthful trace from a completed run; do not imply that a test double is live Bright Data.

## Timeline

| Time | Screen | Narration | Caption | Backend event | Expected result | Fallback |
| --- | --- | --- | --- | --- | --- | --- |
| 00:00–00:03 | GPU price card: expected `$599`, extracted `$29.99/month`, status `GREEN`. | “This scraper is green.” | `GREEN ≠ CORRECT` | Load recorded Observation and contract status. | Viewer sees valid-looking but wrong data. | Use a static evidence frame from a measured L5 run. |
| 00:03–00:10 | Highlight mismatch and entity/unit evidence. | “It’s also wrong. Most scrapers would ship this.” | `SILENT CORRUPTION DETECTED` | DetectionEvent emitted. | The problem is understood without audio. | Keep captions and values on screen. |
| 00:10–00:18 | Detection channels panel. | Explain schema, statistical, semantic, and response evidence. | `EVIDENCE, NOT EMPTY OUTPUT` | Findings attached to Observation. | At least two relevant findings visible. | Show a pre-rendered event timeline. |
| 00:18–00:28 | Diagnosis panel with failure class and repair request. | Explain that AEGIS asks Bright Data for a specific repair. | `AI PROPOSES` | Diagnosis and RepairAttempt created. | Repair request references evidence. | Show request artifact if provider UI is unavailable. |
| 00:28–00:40 | Bright Data healing/execution evidence. | Explain Bright Data remains the scraper/healing layer. | `BRIGHT DATA HEALS` | Provider run/poll events. | Candidate appears with correlation ID. | Use truthful captured provider trace. |
| 00:40–00:50 | Candidate verification panel. | “A candidate returning data is not enough.” | `DATA RETURNED — VERIFICATION FAILED` then `EVIDENCE PASSED` | VerificationRun for rejected candidate, then accepted candidate. | Candidate #1 fails semantic check; candidate #2 passes contract/history/independent evidence. | Show two static candidate cards. |
| 00:50–01:00 | Risk decision and commit gate. | Explain quarantine beats guessing and only verified candidates commit. | `COMMIT: 2+ DETERMINISTIC CHANNELS` | RiskDecision ACCEPT and Commit event. | New version becomes known-good. | Show the exact audit event. |
| 01:00–01:10 | Mutation levels L1–L5. | Explain controlled adversarial testing. | `GROUND TRUTH IN THE LAB` | Benchmark manifest displayed. | Viewer sees L5 separated from normal recovery. | Static benchmark summary. |
| 01:10–01:20 | Baseline comparison chart/table. | State actual DetectionRate, VerificationMissRate, BlindCommitRate. | `MEASURED RESULTS ONLY` | Benchmark report loaded. | No target is mislabeled as result. | If results are unavailable, do not record final demo. |
| 01:20–01:35 | GPU price intelligence surface. | Show product impact: product, price, change, last verified, status. | `TRUSTWORTHY STRUCTURED OUTPUT` | Product query reads committed observation only. | Quarantined data is not shown as current. | Use a deterministic fixture-backed surface. |
| 01:35–01:48 | Post-commit watch and regression/rollback mini-trace. | Explain that one successful repair is not permanent success. | `WATCH → REGRESSION → ROLLBACK` | WatchCycle detects regression; RollbackEvent recorded. | Known-good version restored or safely held. | Use a recorded measured rollback trace. |
| 01:48–02:00 | Thesis and final metrics. | “We don’t just build scrapers that survive change. We measure whether they survived correctly.” | `AI PROPOSES. EVIDENCE DECIDES.` | Final evidence links and repository URL. | End on memorable thesis and actual results. | Never substitute invented numbers. |

## Shot list and recording checklist

Before recording, verify that the selected fixture, mutation ID, seed, run ID, benchmark report, and product output all refer to the same measured scenario. Burn in captions. Test muted playback. Check that provider credentials and internal secrets are not visible. Record a clean backup take and preserve the raw capture, final encoded video, subtitles, and evidence manifest.
