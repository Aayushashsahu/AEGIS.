# Mission 016 Floor Summary

**Status:** `STOPPED_PREFLIGHT`
**Recommendation:** `FIX`
**Run ID:** `mission_016_floor_f48ec5c5792b`

Mission 016 did not execute the minimum credible benchmark floor. Preflight stopped before the Baseline B smoke test because the frozen Mission 015 configuration contains the invalid Baseline A/B implementation revision `0e8bcc4a2c2184cae9a50b291054ec47d83fc895`. The actual committed implementation revision is `0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47`. AEGIS resolves correctly to `7de2bc65ed9eeb9f4abd24017543f3f366990738`.

The configuration hash, fixture, mutation set, seed, participant readiness, fairness, metric formula, artifact paths, and clean fixture checks passed. The revision identity check failed, so the mandatory stop condition applied. The frozen configuration was not modified in place.

| Quantity | Result |
| --- | ---: |
| Planned runs | 180 |
| Completed runs | 0 |
| Failed runs | 0 |
| Timed-out runs | 0 |
| Invalidated runs | 0 benchmark trials; preflight status invalid |
| Baseline B smoke | Not run due to preflight stop |
| Metric results | 0 |
| Benchmark execution authorized | false |

See `benchmarks/runs/mission_016_floor_f48ec5c5792b/preflight_blocker.json` for machine-readable evidence and `experiments/AEGIS-MISSION-016-BENCHMARK-FLOOR.md` for the full report. No benchmark, Bright Data, healing, approval, commit, rollback, or metric operation was performed.
