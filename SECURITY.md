# Security and Trust

AEGIS treats scraped webpage content, extracted content, raw responses, and model output as untrusted input. Website text must never become an instruction that overrides AEGIS policy, verification rules, access controls, or code. Prompt injection is an explicit threat boundary.

Credentials and tokens must remain outside source files, fixtures, logs, benchmark artifacts, and documentation. Use local environment configuration only after the relevant integration contract has been confirmed. Do not commit real secrets or private data.

Repair proposals are untrusted until independently verified. Verification and risk-decision gates must not be bypassed, and a single LLM opinion cannot authorize a production commit. When deterministic evidence is insufficient, AEGIS should fail closed through quarantine or escalation rather than guess.

## Responsible reporting

Do not publish sensitive details, credentials, private data, or an exploitable proof of concept in an issue or pull request. Preserve the evidence needed for reproducibility while redacting secrets. A project-owner reporting contact is not yet specified; until one is documented, use the repository’s approved project communication channel and do not disclose sensitive details publicly.
