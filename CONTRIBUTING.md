# Contributing to AEGIS

AEGIS is an evidence-driven reliability and self-healing control layer around Bright Data Scraper Studio. The canonical documentation under `docs/` is the source of truth for scope, terminology, architecture, requirements, and unresolved decisions.

## Before changing the repository

Read the relevant numbered documentation before modifying code or documentation. Inspect the existing implementation and Git state first. Preserve the lifecycle and safety invariants: **AI proposes; evidence decides**, no blind commits, quarantine when evidence is insufficient, and zero BlindCommitRate.

## Change expectations

Keep changes small, focused, and reviewable. Do not rename AEGIS, redesign the architecture, introduce unrelated features, or create competing repository copies. Treat scraped content and model output as untrusted data. Never commit credentials, private data, or generated secrets.

Run the applicable tests and validation commands before committing implementation changes. Record assumptions separately from verified facts. Do not invent Bright Data endpoints, response formats, platform capabilities, or benchmark results. Targets must remain clearly distinguished from measured results, and benchmark artifacts must retain their ground truth and run metadata.

AI-generated code or documentation requires human review and deterministic verification at safety boundaries. Changes to strategic direction, canonical requirements, or unresolved architectural decisions require explicit project-owner approval.
