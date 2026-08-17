# 15 — Security and Trust

> **Scraped content is untrusted data and can never redefine AEGIS policy or verification rules.**

## Trust boundaries

AEGIS separates untrusted website content, Bright Data provider responses, model prompts/outputs, internal policy/configuration, lifecycle records, and release credentials. Website text may be stored, normalized, classified, or shown as evidence. It may not alter extraction contracts, risk thresholds, authorization, code, prompt policy, or commit gates.

```text
[Untrusted site/response]
        │ data-only boundary
        ▼
[Observation + evidence quarantine]
        │ typed, bounded inputs
        ▼
[Detection / diagnosis / verification]
        │ deterministic policy boundary
        ▼
[Risk decision / commit / rollback]
```

## Secrets and API keys

Credentials must be supplied through environment or approved secret storage and must never be committed, embedded in fixtures, included in prompts, placed in raw logs, or exported with benchmark artifacts. Logs redact authorization headers, cookies, tokens, provider secrets, and any restricted values. A secret scan is a release gate.

## Public and restricted data

The benchmark should use public or locally controlled fixture data. Restricted, private, credential-gated, or personal data is out of scope unless the project owner explicitly authorizes it and the compliance requirements are documented. The submission checklist must state the actual data sources used; this document does not claim eligibility beyond the project prompt.

## Prompt injection and malicious content

A webpage can contain text that looks like instructions, including requests to ignore policy, reveal secrets, alter selectors, or approve a repair. AEGIS treats such text as extracted content. The parser must preserve provenance and the model prompt must delimit content as untrusted. Model output is validated against a typed repair-request schema and cannot directly call commit, change policy, or execute arbitrary code.

## Authorization

Separate permissions are required for collection, healing request, approval/escalation, commit, rollback, benchmark freeze, and submission claim publication. The caller cannot supply a flag that bypasses deterministic verification. Human approval, when the Bright Data workflow supports it, is an additional action—not a replacement for evidence recording.

## Sandboxing and execution

Mutation injectors run against controlled fixtures, not arbitrary production sites. External responses are parsed without executing untrusted scripts in the AEGIS control process. If browser automation is required, it runs in a bounded environment with restricted filesystem/network access and no access to project secrets beyond the minimum adapter credential.

## Audit logging

Record actor, command, correlation ID, timestamp, state before/after, reason, evidence references, provider operation reference, and decision. Audit logs are append-oriented. Failed authorization and rejected commit attempts are retained. Logs must not contain raw secrets or unbounded page content; large content belongs in controlled evidence storage with redaction rules.

## Rollback and incident response

A suspected bad commit triggers quarantine of downstream shipment, evidence capture, watch/regression event, rollback attempt, post-rollback validation, and escalation if validation fails. The incident record links the original observation, candidate, verification channels, risk decision, active version, and rollback outcome. Do not delete the failed evidence during remediation.

## Retention and local/remote execution

Retain benchmark truth, raw outputs, decision evidence, and submission artifacts through project review. Delete secrets and unnecessary sensitive data according to owner policy. Local fixture runs may be used to isolate deterministic tests; remote Bright Data execution must be marked in metadata. A local test double never proves remote capability.

## Security acceptance tests

The suite must prove that prompt-like page text cannot alter policy, secrets do not appear in exports, unauthorized commit/rollback is denied, quarantined data cannot appear as current product output, and rollback preserves audit history.
