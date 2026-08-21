# Mission 056 Controlled Target Assessment

**Decision:** `SELECTED_FOR_LOCAL_SIMULATION_ONLY`
**Provider operations:** `0`
**Provider output claims:** `0`

## Decision rationale

The immutable Mission 033 target contract remains historical evidence but its historical managed preview route currently returns the AEGIS application 404 view. It is therefore unsuitable for a fresh experiment at this time. No historical target evidence was edited, relabeled, or reinterpreted.

Mission 056 restores a separate, minimal public target at `/mission-056/target`. It is server-rendered HTML, does not require JavaScript, has no login or personal data, and has no customer-review content. The target is operationally separate from the frozen judge-facing visual baseline: it is an extraction fixture, not a redesign or a new judge-facing screen.

| Criterion | Historical Mission 033 target | Mission 056 controlled target |
| --- | --- | --- |
| Publicly reachable now | No — rendered managed 404 | Yes — baseline and drift returned HTTP `200`. |
| Required visible facts | Not visible in the current 404 result | `AEGIS Recovery Widget`, `$599.00`, and `Available`. |
| JavaScript dependency | Not assessed; current route is unavailable | None; static server response contains no script tag. |
| Stable baseline selectors | Historical only | `data-aegis-field=title`, `data-aegis-field=price`, `data-aegis-field=availability`. |
| Controlled drift | Historical v2 evidence only | Same facts at same path, but baseline selectors and element relationships are absent in `?variant=drift`. |
| Provider claim | Historical provider evidence only | None. This route has not been collected, healed, approved, or rerun by Bright Data. |

## Read-only reachability evidence

| URL | HTTP evidence | Markers observed |
| --- | --- | --- |
| `/mission-056/target` | `200`, `text/html; charset=utf-8`, `cache-control: no-store` | `data-aegis-variant="baseline"` and all three declared field markers. |
| `/mission-056/target?variant=drift` | `200`, `text/html; charset=utf-8`, `cache-control: no-store` | `data-aegis-variant="drift"`, `item-name`, `amount`, and `inventory-state`; baseline field markers absent. |

The selected target is intentionally simple. The baseline makes the expected facts inspectable and repeatable. The drift preserves the facts but changes only the retrieval relationships that a parser must learn. This provides a meaningful recovery exercise without a live third-party site, consumer content, or externally changing inventory.

## Provider-free local lifecycle result

The canonical local simulation labels every scenario `TEST_DOUBLE` and makes zero provider operations. It exercises the existing AEGIS domain logic, not duplicate React or fixture logic.

| Scenario | Detection | Verification | Risk | Commit | Downstream |
| --- | --- | --- | --- | --- | --- |
| Baseline complete output | `NOT_DETECTED` | Not a repair candidate | Not applicable | Not applicable | Not applicable |
| Controlled drift with input URL only | `DETECTED` | Not a repair candidate | Not applicable | Not applicable | Not applicable |
| Complete candidate with deterministic independent evidence | Not applicable | `PASS` | `ACCEPT` | `BLOCKED` | Ineligible |
| Input-only incomplete candidate | Not applicable | `FAIL` | `REJECT` | `BLOCKED` | Ineligible |

> The passing TEST_DOUBLE candidate demonstrates gate behavior only. It is not a real provider candidate and must never be presented as one.

## Phase-gated re-entry conditions

No provider action is authorized by target selection alone. A fresh candidate-only experiment must first record the exact collector, selected public target URL, explicit CLI version behavior, prompt and hash, one-heal budget, zero-retry rule, correlation ID, fresh raw-first path, candidate fields required for a pass gate, and explicit stop conditions. The experiment must also begin with a current read-only health check of this target. Approval and post-heal rerun stay outside this target-selection decision.

## Evidence files

| File | Purpose |
| --- | --- |
| `target_reachability_observation.json` | Read-only historical target 404 observation. |
| `target_selection.json` | Machine-readable selection facts and target contract. |
| `local_lifecycle_simulation.json` | Canonical TEST_DOUBLE lifecycle outcomes. |
| `server/mission056ControlledTarget.test.ts` | Managed provider-free target contract test: `3 passed`. |
| `tests/unit/test_mission056_simulation.py` | Canonical provider-free lifecycle test: `1 passed`. |
