# Mission 032 Browser Validation

The provider-free clone-local server was opened on 2026-08-19 after the final build and route checks.

| Route | Observed result |
| --- | --- |
| `/downstream` | The page identifies `TEST DOUBLE / CONTROLLED REPLAY`, shows canonical expected price `599` and observed candidate price `29.99`, lists the contract/history/semantic/independent channels, and ends `Verification FAIL → Risk REJECT → Commit BLOCKED` with `data shipped: no`. |
| `/judge` | The page begins with Mission 029 historical provider evidence, states that a candidate and downstream decisions belong to a separate controlled replay, and refuses to infer a provider candidate, verification, risk, commit, or shipment state from the selected historical record. |

No browser interaction triggered Bright Data, NVIDIA, Gemini, approval, commit, rollback, or benchmark execution.
