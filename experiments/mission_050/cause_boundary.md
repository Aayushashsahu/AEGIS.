# Mission 050 — Causal Boundary

> **Evidence boundary:** The provider execution returned incomplete structured output, while the active production template and schema visible in Scraper Studio contain the required fields. The exact runtime template or revision responsible for the observed execution is not exposed or uniquely bound by the available evidence.

## Known facts

| Fact | Evidence record | Status |
|---|---|---|
| Collector | `c_mt09pib13nxqz1coi` | Recorded |
| Real approval | Mission 040 | Completed |
| Provider self-healing state | Mission 041A | Completed |
| Real post-approval rerun | Mission 041B | HTTP 200; `input.url` only |
| Required output | `title`, `price`, `availability` | Missing from the observed provider output |
| Active schema | Mission 044 | Required fields active |
| Dashboard production template | Mission 046 | Required fields visible |
| AEGIS verification and decision | Missions 041B and 048C | FAIL → REJECT → BLOCKED; data shipped NO |

## Unknown facts

The available evidence does **not** establish the exact provider runtime template or revision for the observed execution. It also does not establish the provider-internal reason for the missing fields. Mission 049’s documented read-only diagnostics exposed a template reference for a collector-matching job, but no unique identifier links that job to the synchronous real response. Timestamp proximity is not accepted as a substitute for correlation.

Therefore `CAUSE=UNKNOWN` and `CONFIDENCE=LOW`. This does not weaken the safety decision: the preserved output itself establishes that the data is unsafe, so AEGIS correctly failed verification, rejected risk acceptance, blocked commit, and prevented shipment.

## Provenance separation

Mission 041B, Mission 044, Mission 046, and Mission 049 remain separate records in the evidence ledger. The controlled silent-corruption downstream proof is explicitly `TEST_DOUBLE`; it is not a continuation of, nor an explanation for, the real-provider failure.
