"""Provider-free recommendations from a normalized support diagnosis.

The return value is a bounded recommendation only.  No recommendation is
connected to a transport, CLI command, approval, rerun, commit, or rollback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .support_evidence import SupportAnalysis, SupportDiagnosisClass


class SupportNextAction(str, Enum):
    NO_ACTION = "NO_ACTION"
    READ_ONLY_DIAGNOSTIC = "READ_ONLY_DIAGNOSTIC"
    ONE_HEAL = "ONE_HEAL"
    ONE_APPROVAL = "ONE_APPROVAL"
    ONE_RERUN = "ONE_RERUN"
    ACCOUNT_CONFIGURATION_REQUIRED = "ACCOUNT_CONFIGURATION_REQUIRED"
    PROVIDER_SUPPORT_REQUIRED = "PROVIDER_SUPPORT_REQUIRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SupportActionRecommendation:
    action: SupportNextAction
    rationale: str
    requires_new_owner_authorization: bool
    may_execute_provider_operation: bool = False

    def __post_init__(self) -> None:
        if self.may_execute_provider_operation:
            raise ValueError("support action recommendations cannot execute provider operations")


def recommend_support_action(
    analysis: SupportAnalysis | None,
    *,
    candidate_present: bool,
    candidate_verified: bool,
    rerun_output_available: bool,
) -> SupportActionRecommendation:
    """Recommend conservatively; untrusted text never directly grants mutation."""

    if analysis is None:
        return SupportActionRecommendation(
            SupportNextAction.PROVIDER_SUPPORT_REQUIRED,
            "No actual support response exists; the provider lane remains frozen.",
            False,
        )
    if analysis.diagnosis in {SupportDiagnosisClass.ACCOUNT_CONFIGURATION, SupportDiagnosisClass.ACCOUNT_PERMISSION}:
        return SupportActionRecommendation(
            SupportNextAction.ACCOUNT_CONFIGURATION_REQUIRED,
            "Support evidence indicates an account-side prerequisite; do not retry before it is resolved.",
            False,
        )
    if analysis.diagnosis in {SupportDiagnosisClass.PROVIDER_CODE_FIXER_FAILURE, SupportDiagnosisClass.SELF_HEAL_SERVICE_FAILURE}:
        return SupportActionRecommendation(
            SupportNextAction.PROVIDER_SUPPORT_REQUIRED,
            "Support evidence indicates a provider-side refactor/service issue; no blind retry is justified.",
            False,
        )
    if candidate_present and candidate_verified and not rerun_output_available:
        return SupportActionRecommendation(
            SupportNextAction.ONE_APPROVAL,
            "A verified candidate exists, but any approval requires a separate exact owner authorization.",
            True,
        )
    if rerun_output_available:
        return SupportActionRecommendation(
            SupportNextAction.NO_ACTION,
            "A rerun output is already available; evaluate evidence rather than issue another provider operation.",
            False,
        )
    if analysis.diagnosis is SupportDiagnosisClass.DOCUMENTED_WORKAROUND and analysis.retry_recommendation == "ONE_HEAL":
        return SupportActionRecommendation(
            SupportNextAction.ONE_HEAL,
            "A real support response explicitly recommends one heal; separate owner authorization remains required.",
            True,
        )
    return SupportActionRecommendation(
        SupportNextAction.UNKNOWN,
        "The support diagnosis does not justify a bounded provider action.",
        False,
    )
