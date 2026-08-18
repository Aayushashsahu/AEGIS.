# AEGIS Judge Mode — 2:30 script

## 00:00–00:15 — The problem

> “Scrapers do not just break. They silently become wrong. This collector returned structured data and looked healthy—but that does not prove the data is trustworthy.”

Show the opening Judge Mode thesis and the real Bright Data case file. Point out the visible `c_msyo46bp1slx64351` collector ID, 150 structured rows, and the `REAL PROVIDER EVIDENCE` label.

## 00:15–00:35 — Collection becomes observation

> “Bright Data creates and runs the scraper. AEGIS records that output as an untrusted observation. It never promotes valid JSON into trusted data by default.”

Show the first two stages of the vertical evidence spine and open the live-evidence drawer. Mention the documented realtime-to-batch result, without claiming a general provider guarantee.

## 00:35–00:55 — The corruption moment

> “Now watch the value change from 402 to minus 1. The website and collector were not changed. This is a reversible, controlled AEGIS evidence mutation—and that label matters.”

Show the preserved live value, the controlled observed value, and the note that schema/type checks alone cannot establish semantic correctness.

## 00:55–01:15 — Detection and repair request

> “AEGIS detects the anomaly deterministically, preserves its ambiguity where evidence is insufficient, and asks Bright Data for a bounded repair. AI proposes; evidence still decides.”

Follow the spine from detection through the repair request. Do not imply that diagnosis certainty is higher than the committed artifact records.

## 01:15–01:35 — The real provider boundary

> “The first request hit Bright Data’s 1,000-character prompt limit. We fixed that boundary: the corrected request was 676 characters. Bright Data then returned HTTP 500 before any candidate was created.”

Show `HEAL_FAILED_BEFORE_CANDIDATE`, `676 / 1000`, and `HTTP 500`. State the consequence exactly: no candidate, no verification, no approval, no commit, no data shipped.

## 01:35–02:00 — Evidence over AI

> “Because the real provider did not return a candidate, this next panel is explicitly a controlled TEST_DOUBLE replay—not a live Bright Data repair.”

Show the brass replay label, the candidate price `29.99` against the known-good `599`, and the model’s auxiliary `PASS` opinion. Then show the deterministic history, semantic-invariant, and independent-evidence failures.

> “The proposal looks plausible. The evidence rejects it. Output is blocked.”

## 02:00–02:20 — Measurement boundary

> “We also measured AEGIS in a controlled mutation harness: 180 opportunities, three participants, six mutation classes, and ten trials per class. The AEGIS figures shown here are TEST_DOUBLE controlled-harness measurements, not live Bright Data reliability metrics.”

Show the audited benchmark ledger. Mention L5 detection `20/20` and L5 bad data shipped `0/20`; call the NVIDIA NIM 6 RPM setting a conservative benchmark-side throttle and state that the provider limit is unknown.

## 02:20–02:30 — Close

> “Bright Data heals. AEGIS decides whether the healing deserves to be trusted. AI proposes. Evidence decides.”

Leave the final shipment-locked statement on screen. Do not click any approval or provider action, because Judge Mode contains none.
