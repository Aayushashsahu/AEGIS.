# 19 — Submission Checklist

**Objective:** Submit a credible, reproducible AEGIS entry for the NVIDIA DGX Spark grand prize.  
**Rule:** Actual results and verified capabilities only.  
**Owner:** `[SUBMISSION_OWNER]`

## Registration and eligibility

| Check | Evidence | Owner | Status |
| --- | --- | --- | --- |
| Account and team created | Registration confirmation | `[OWNER]` | `[ ]` |
| Track selected: Web-Slinger / Best Use of Bright Data | Track confirmation | `[OWNER]` | `[ ]` |
| Eligibility rules reviewed | Saved official rules/rubric | `[OWNER]` | `[ ]` |
| Credits/access verified | Provider/account evidence | `[OWNER]` | `[ ]` |
| Dates and submission deadline confirmed | Official schedule | `[OWNER]` | `[ ]` |
| Official judging criteria copied into `00_PROJECT_INFO.md` | Owner review | `[OWNER]` | `[ ]` |

## Project and Bright Data proof

| Check | Evidence | Status |
| --- | --- | --- |
| Custom Scraper Studio collector exists and is referenced | Collector ID/version/run evidence | `[ ]` |
| Bright Data collection path is demonstrated | Run trace and structured output | `[ ]` |
| Healing path is demonstrated or capability accurately marked | Healing evidence or limitation note | `[ ]` |
| AEGIS detection and verification are shown | Event timeline and safety test | `[ ]` |
| Quarantine prevents bad data shipment | L5 test artifact | `[ ]` |
| Post-commit watch and rollback are shown or accurately bounded | Watch/Rollback evidence | `[ ]` |
| Product surface shows current verified data only | Screenshot/run artifact | `[ ]` |

## Repository

| Check | Evidence | Status |
| --- | --- | --- |
| Repository is public if required | Final URL | `[ ]` |
| README explains thesis, problem, architecture, limits, quick start, and disclosure | README review | `[ ]` |
| All 20 canonical docs are present | File list | `[ ]` |
| Structured output example is included and labeled | Example artifact | `[ ]` |
| Mutation manifests and ground truth are included | `mutations/` review | `[ ]` |
| Frozen baseline configurations are committed before benchmark runs | Git history/config review | `[ ]` |
| Reproduction commands work in a clean environment | Clean-room run log | `[ ]` |
| No secrets or restricted data are present | Secret scan/compliance review | `[ ]` |

## Benchmark and metrics

| Check | Evidence | Status |
| --- | --- | --- |
| All five severity levels represented | Manifest | `[ ]` |
| At least six classes and two L5 modes | Manifest | `[ ]` |
| At least ten trials per class or floor exception documented | Run manifest | `[ ]` |
| Three baselines are frozen | Config commit | `[ ]` |
| Fixed seeds and fixture versions recorded | Run metadata | `[ ]` |
| Metrics follow `07_METRICS.md` formulas | Report audit | `[ ]` |
| Per-severity results are reported | Final report | `[ ]` |
| L5 bad-data-shipped rate is reported | Final report | `[ ]` |
| No target is presented as measured | Claim review | `[ ]` |
| Blind Commit Rate is zero on the evaluated path | Safety/metric artifact | `[ ]` |

## Video

| Check | Evidence | Status |
| --- | --- | --- |
| Final video is approximately two minutes and within official limit | Duration check | `[ ]` |
| Green-but-wrong opening appears in first 10 seconds | Review timestamp | `[ ]` |
| Detection, diagnosis, repair, verification, and decision are visible | Review timestamps | `[ ]` |
| Benchmark evidence appears by 01:20 | Review timestamp | `[ ]` |
| Product surface and final line appear before 02:00 | Review timestamp | `[ ]` |
| Captions and large text are readable | Muted review | `[ ]` |
| Video uses measured results only | Evidence cross-check | `[ ]` |
| Bright Data use is explained | Script review | `[ ]` |
| Live system remains available separately | URL/launch instructions | `[ ]` |

## Compliance and disclosure

Confirm AI-use disclosure, public-data use, absence of prohibited/private data, absence of pre-kickoff project code where applicable, explainability of submitted code, repository license, third-party notices, and any required attribution. These items require project-owner review against the official rules; this document does not assert eligibility by itself.

## Final validation

Before submission, verify every link, command, collector reference, benchmark artifact, metric denominator, screenshot, caption, environment instruction, and claim. Archive the exact submitted repository revision, final video checksum, final report, and owner approvals. If any requirement is unknown, mark it and resolve or remove the corresponding claim rather than guessing.
