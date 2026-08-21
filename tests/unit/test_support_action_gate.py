from __future__ import annotations

from aegis.support_action_gate import SupportNextAction, recommend_support_action
from aegis.support_evidence import SupportAnalysis, SupportDiagnosisClass


def _analysis(diagnosis: SupportDiagnosisClass, *, retry: str | None = None) -> SupportAnalysis:
    return SupportAnalysis(
        diagnosis=diagnosis, confidence="MEDIUM", evidence_phrases=("fixture",),
        provider_job_id=None, provider_operation_id=None, error_code=None,
        documented_remedy=None, account_action=None, collector_action=None,
        retry_recommendation=retry, support_recommended_command=None,
        raw_message_sha256="a" * 64,
    )


def test_missing_support_response_keeps_provider_support_required() -> None:
    recommendation = recommend_support_action(None, candidate_present=False, candidate_verified=False, rerun_output_available=False)
    assert recommendation.action is SupportNextAction.PROVIDER_SUPPORT_REQUIRED
    assert not recommendation.may_execute_provider_operation


def test_code_fixer_failure_does_not_authorize_blind_retry() -> None:
    recommendation = recommend_support_action(
        _analysis(SupportDiagnosisClass.PROVIDER_CODE_FIXER_FAILURE),
        candidate_present=False, candidate_verified=False, rerun_output_available=False,
    )
    assert recommendation.action is SupportNextAction.PROVIDER_SUPPORT_REQUIRED
    assert not recommendation.requires_new_owner_authorization


def test_explicit_documented_one_heal_still_requires_new_authorization() -> None:
    recommendation = recommend_support_action(
        _analysis(SupportDiagnosisClass.DOCUMENTED_WORKAROUND, retry="ONE_HEAL"),
        candidate_present=False, candidate_verified=False, rerun_output_available=False,
    )
    assert recommendation.action is SupportNextAction.ONE_HEAL
    assert recommendation.requires_new_owner_authorization
    assert not recommendation.may_execute_provider_operation
