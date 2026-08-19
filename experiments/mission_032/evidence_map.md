# AEGIS Final Evidence Map

| Demo claim | Provenance | Canonical source | UI route | Boundary |
| --- | --- | --- | --- | --- |
| Public Bright Data collection | `REAL_PROVIDER` | `experiments/mission_029/` | `/judge`, `/cases/mission_029_real_provider` | 150 Hacker News rows; output remains untrusted. |
| L3 observation/detection/diagnosis context | `CONTROLLED_DEMONSTRATOR` linked to historical evidence | Mission 029 normalized artifacts | `/cases/mission_029_real_provider` | A visual and explanatory projection, not a new provider operation. |
| Compact heal attempt | `REAL_PROVIDER` | `experiments/mission_030/live_heal_result.json` | `/judge`, historical case | 676-character transport prompt; HTTP 500; no candidate. |
| Candidate through Commit Gate | `TEST_DOUBLE` / `CONTROLLED_REPLAY` | `src/aegis/verification_double.py`, verification, risk, and commit modules | `/cases/controlled_silent_corruption`, `/downstream` | Candidate price `29.99` is rejected against canonical expected value `599`. |
| Downstream price output | `TEST_DOUBLE` / `CONTROLLED_REPLAY` | `scripts/mission032_lifecycle_api.py` | `/downstream` | Output eligibility is false; the consumer value is withheld. |
| Benchmark | `TEST_DOUBLE_CONTROLLED_HARNESS` | `benchmarks/runs/mission_028_recovery_floor_4812160675146552/` | `/benchmark` | Read-only: 180 planned, 179 completed, one provider failure, 60 provider operations. |

The evidence-integrity CI gate verifies the SHA-256 fingerprints for the immutable Mission 028–031 artifacts used by these routes. A missing artifact produces an unavailable state; the frontend does not substitute a result.
