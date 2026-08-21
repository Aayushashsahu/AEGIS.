"""Provider-free normalization for eventual Bright Data support correspondence.

This module never contacts Bright Data, parses mailboxes, or authorizes a
provider operation.  It only classifies a text response supplied by an
explicit caller, preserves its hash, and refuses to infer a recommendation
that is absent from the response.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping

from .immutability import freeze_mapping


class SupportDiagnosisClass(str, Enum):
    ACCOUNT_CONFIGURATION = "ACCOUNT_CONFIGURATION"
    ACCOUNT_PERMISSION = "ACCOUNT_PERMISSION"
    SELF_HEAL_SERVICE_FAILURE = "SELF_HEAL_SERVICE_FAILURE"
    PROVIDER_CODE_FIXER_FAILURE = "PROVIDER_CODE_FIXER_FAILURE"
    TARGET_COMPATIBILITY = "TARGET_COMPATIBILITY"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    QUOTA = "QUOTA"
    RATE_LIMIT = "RATE_LIMIT"
    TRANSIENT_PROVIDER_FAILURE = "TRANSIENT_PROVIDER_FAILURE"
    DOCUMENTED_WORKAROUND = "DOCUMENTED_WORKAROUND"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SupportResponseInput:
    """Untrusted support correspondence supplied after a real response exists."""

    support_case_id: str | None
    message_id: str | None
    received_at: str | None
    sender: str
    subject: str
    body: str
    attachments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "attachments", tuple(self.attachments))
        if not self.sender.strip() or not self.subject.strip() or not self.body.strip():
            raise ValueError("sender, subject, and body are required for a real support response")


@dataclass(frozen=True)
class SupportAnalysis:
    """Cautious, evidence-bearing interpretation that cannot execute an action."""

    diagnosis: SupportDiagnosisClass
    confidence: str
    evidence_phrases: tuple[str, ...]
    provider_job_id: str | None
    provider_operation_id: str | None
    error_code: str | None
    documented_remedy: str | None
    account_action: str | None
    collector_action: str | None
    retry_recommendation: str | None
    support_recommended_command: str | None
    raw_message_sha256: str
    provenance: str = "UNTRUSTED_SUPPORT_RESPONSE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_phrases", tuple(self.evidence_phrases))
        if self.confidence not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError("confidence must be HIGH, MEDIUM, or LOW")
        if self.provenance != "UNTRUSTED_SUPPORT_RESPONSE":
            raise ValueError("support evidence must remain untrusted until separately verified")

    def to_evidence_dict(self) -> dict[str, object]:
        return asdict(self)


_EXPLICIT_CLASSIFIERS: tuple[tuple[SupportDiagnosisClass, tuple[str, ...]], ...] = (
    (SupportDiagnosisClass.ACCOUNT_PERMISSION, ("permission", "not authorized", "access denied")),
    (SupportDiagnosisClass.ACCOUNT_CONFIGURATION, ("account configuration", "workspace configuration", "enable self-healing")),
    (SupportDiagnosisClass.UNSUPPORTED_FEATURE, ("not supported", "unsupported")),
    (SupportDiagnosisClass.QUOTA, ("quota", "credit limit")),
    (SupportDiagnosisClass.RATE_LIMIT, ("rate limit", "too many requests")),
    (SupportDiagnosisClass.TARGET_COMPATIBILITY, ("target compatibility", "target is not compatible")),
    (SupportDiagnosisClass.PROVIDER_CODE_FIXER_FAILURE, ("code_fixer", "unable to generate working code")),
    (SupportDiagnosisClass.SELF_HEAL_SERVICE_FAILURE, ("self-healing service", "self healing service")),
    (SupportDiagnosisClass.TRANSIENT_PROVIDER_FAILURE, ("transient", "temporary service")),
    (SupportDiagnosisClass.DOCUMENTED_WORKAROUND, ("workaround", "use this command")),
)


def normalize_support_response(
    response: SupportResponseInput,
    *,
    extracted_metadata: Mapping[str, str | None] | None = None,
) -> SupportAnalysis:
    """Classify only explicit response language; uncertainty stays UNKNOWN.

    ``extracted_metadata`` is caller-supplied, safe, and optional.  The
    function does not regex-invent provider identifiers, commands, or remedies
    from the support body.  Those values are retained only when a trusted
    ingestion layer has extracted them from a real response.
    """

    metadata = freeze_mapping(extracted_metadata or {})
    body_lower = response.body.lower()
    for diagnosis, phrases in _EXPLICIT_CLASSIFIERS:
        matched = tuple(phrase for phrase in phrases if phrase in body_lower)
        if matched:
            return SupportAnalysis(
                diagnosis=diagnosis,
                confidence="MEDIUM",
                evidence_phrases=matched,
                provider_job_id=metadata.get("provider_job_id"),
                provider_operation_id=metadata.get("provider_operation_id"),
                error_code=metadata.get("error_code"),
                documented_remedy=metadata.get("documented_remedy"),
                account_action=metadata.get("account_action"),
                collector_action=metadata.get("collector_action"),
                retry_recommendation=metadata.get("retry_recommendation"),
                support_recommended_command=metadata.get("support_recommended_command"),
                raw_message_sha256=hashlib.sha256(response.body.encode("utf-8")).hexdigest(),
            )
    return SupportAnalysis(
        diagnosis=SupportDiagnosisClass.UNKNOWN,
        confidence="LOW",
        evidence_phrases=(),
        provider_job_id=metadata.get("provider_job_id"),
        provider_operation_id=metadata.get("provider_operation_id"),
        error_code=metadata.get("error_code"),
        documented_remedy=metadata.get("documented_remedy"),
        account_action=metadata.get("account_action"),
        collector_action=metadata.get("collector_action"),
        retry_recommendation=metadata.get("retry_recommendation"),
        support_recommended_command=metadata.get("support_recommended_command"),
        raw_message_sha256=hashlib.sha256(response.body.encode("utf-8")).hexdigest(),
    )
