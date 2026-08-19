# AEGIS — Submission Description

## Problem

Scrapers do not have to crash to become dangerous. A page can return HTTP 200, valid JSON, and correctly typed fields while a price, unit, product, or entity is silently wrong. Those failures are especially risky because ordinary uptime checks report green.

## Solution

AEGIS is an evidence-first reliability control layer around Bright Data Scraper Studio. Bright Data provides collection and healing infrastructure. AEGIS preserves the output as untrusted evidence, detects anomalies, builds a bounded repair request, independently verifies a candidate, makes an explicit risk decision, and blocks anything that cannot satisfy the Commit Gate.

## Authentic Bright Data use

The demo includes recorded `REAL_PROVIDER` Bright Data evidence: Mission 029 collected 150 public Hacker News rows from a named collector. Mission 030 then submitted one authorized compact healing request using a 676-character transport prompt. Bright Data returned HTTP 500 before a candidate existed. The product displays that failure truthfully rather than claiming success.

## Self-healing with verification

The candidate-to-decision path is a separately labeled `TEST_DOUBLE` controlled replay. It uses the canonical AEGIS verification, Risk Governor, and Commit Gate modules: a plausible observed price of `29.99` conflicts with expected `599`; contract passes but history, semantic, and independent evidence fail; Risk rejects; Commit is blocked; downstream output is withheld.

## Impact and technical novelty

AEGIS treats output correctness as an evidence problem, not a selector-success problem. The final downstream price-intelligence surface demonstrates the practical result: bad scraped data never reaches a consumer decision. Mission 028 adds read-only, reproducible controlled-harness evidence while preserving the distinction between benchmark results and live-provider reliability.

## Honest limits

AEGIS does not claim that AI guarantees correctness, that every scraper can be repaired, or that the Mission 030 provider heal succeeded. It does claim—and demonstrates—that unverified repair candidates are not trusted blindly.
