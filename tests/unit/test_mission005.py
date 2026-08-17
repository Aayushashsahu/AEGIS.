from __future__ import annotations

from dataclasses import fields

import pytest

from aegis.risk import RiskDecisionType, RiskGovernor, RiskReason, SafetyMetricHooks
from aegis.verification import CheckStatus, EvidenceChannel, VerificationOverallStatus, verify_candidate
from aegis.verification_double import VerificationFixture, build_verification_fixture


def evaluate(fixture: VerificationFixture):
    context = build_verification_fixture(fixture)
    result = verify_candidate(context)
    decision = RiskGovernor().decide(result, context.candidate, correlation_id=context.correlation_id)
    return context, result, decision


def statuses(result):
    return {check.channel: check.status for check in result.checks}


def test_good_candidate_passes_all_required_channels_and_is_accepted_for_future_commit() -> None:
    context, result, decision = evaluate(VerificationFixture.GOOD_CANDIDATE)
    assert result.overall_status is VerificationOverallStatus.PASS
    assert all(statuses(result)[channel] is CheckStatus.PASS for channel in (
        EvidenceChannel.CONTRACT,
        EvidenceChannel.HISTORY,
        EvidenceChannel.SEMANTIC_INVARIANT,
        EvidenceChannel.INDEPENDENT_EVIDENCE,
    ))
    assert decision.decision is RiskDecisionType.ACCEPT
    assert decision.reason_code is RiskReason.SUFFICIENT_EVIDENCE
    assert decision.eligible_for_future_commit is True
    assert decision.production_commit_performed is False


def test_schema_invalid_candidate_fails_and_cannot_be_accepted() -> None:
    _, result, decision = evaluate(VerificationFixture.BAD_SCHEMA)
    assert statuses(result)[EvidenceChannel.CONTRACT] is CheckStatus.FAIL
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert decision.decision is RiskDecisionType.REJECT
    assert decision.reason_code is RiskReason.DETERMINISTIC_FAILURE


def test_bad_semantic_candidate_fails_even_with_valid_simple_types() -> None:
    _, result, decision = evaluate(VerificationFixture.BAD_SEMANTIC)
    assert statuses(result)[EvidenceChannel.CONTRACT] is CheckStatus.PASS
    assert statuses(result)[EvidenceChannel.SEMANTIC_INVARIANT] is CheckStatus.FAIL
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert decision.decision is RiskDecisionType.REJECT


def test_l5_silent_corruption_has_schema_pass_but_semantic_and_independent_failure() -> None:
    context, result, decision = evaluate(VerificationFixture.SILENT_CORRUPTION)
    assert statuses(result)[EvidenceChannel.CONTRACT] is CheckStatus.PASS
    assert statuses(result)[EvidenceChannel.SEMANTIC_INVARIANT] is CheckStatus.FAIL
    assert statuses(result)[EvidenceChannel.INDEPENDENT_EVIDENCE] is CheckStatus.FAIL
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert decision.decision is RiskDecisionType.REJECT
    assert decision.production_commit_performed is False


def test_missing_independent_evidence_quarantines_instead_of_guessing() -> None:
    _, result, decision = evaluate(VerificationFixture.MISSING_EVIDENCE)
    assert statuses(result)[EvidenceChannel.CONTRACT] is CheckStatus.PASS
    assert statuses(result)[EvidenceChannel.SEMANTIC_INVARIANT] is CheckStatus.PASS
    assert statuses(result)[EvidenceChannel.INDEPENDENT_EVIDENCE] is CheckStatus.UNKNOWN
    assert result.overall_status is VerificationOverallStatus.INCONCLUSIVE
    assert decision.decision is RiskDecisionType.QUARANTINE
    assert decision.reason_code is RiskReason.UNKNOWN_EVIDENCE


def test_contradictory_independent_evidence_rejects() -> None:
    _, result, decision = evaluate(VerificationFixture.CONTRADICTORY_EVIDENCE)
    assert statuses(result)[EvidenceChannel.INDEPENDENT_EVIDENCE] is CheckStatus.FAIL
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert decision.decision is RiskDecisionType.REJECT
    assert decision.reason_code is RiskReason.CRITICAL_CONTRADICTION


def test_unknown_evidence_never_becomes_pass() -> None:
    _, result, decision = evaluate(VerificationFixture.UNKNOWN_EVIDENCE)
    assert result.overall_status is VerificationOverallStatus.INCONCLUSIVE
    assert result.unknown_checks
    assert decision.decision is RiskDecisionType.QUARANTINE


def test_history_is_optional_but_required_acceptance_channels_are_not() -> None:
    context = build_verification_fixture(VerificationFixture.GOOD_CANDIDATE)
    context = __import__("dataclasses").replace(context, history=())
    result = verify_candidate(context)
    decision = RiskGovernor().decide(result, context.candidate, correlation_id=context.correlation_id)
    assert statuses(result)[EvidenceChannel.HISTORY] is CheckStatus.UNKNOWN
    assert result.overall_status is VerificationOverallStatus.PASS
    assert decision.decision is RiskDecisionType.ACCEPT
    assert decision.eligible_for_future_commit is True


def test_correlated_history_and_independent_source_are_not_double_counted() -> None:
    context = build_verification_fixture(VerificationFixture.GOOD_CANDIDATE)
    independent = __import__("dataclasses").replace(context.independent_evidence, source_group="history-path")
    context = __import__("dataclasses").replace(context, independent_evidence=independent)
    result = verify_candidate(context)
    decision = RiskGovernor().decide(result, context.candidate, correlation_id=context.correlation_id)
    assert statuses(result)[EvidenceChannel.INDEPENDENT_EVIDENCE] is CheckStatus.UNKNOWN
    assert decision.decision is RiskDecisionType.QUARANTINE


def test_llm_opinion_cannot_override_deterministic_failure() -> None:
    context = build_verification_fixture(VerificationFixture.SILENT_CORRUPTION)
    assert context.model_opinion["overall"] == "PASS"
    result = verify_candidate(context)
    decision = RiskGovernor().decide(result, context.candidate, correlation_id=context.correlation_id)
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert decision.decision is RiskDecisionType.REJECT


def test_verification_and_risk_records_are_immutable() -> None:
    context, result, decision = evaluate(VerificationFixture.GOOD_CANDIDATE)
    with pytest.raises((AttributeError, TypeError)):
        result.overall_status = VerificationOverallStatus.FAIL  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        decision.decision = RiskDecisionType.REJECT  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.checks[0].details["x"] = "y"  # type: ignore[index]


def test_metric_hooks_record_events_and_keep_blind_commit_rate_zero() -> None:
    context, result, decision = evaluate(VerificationFixture.SILENT_CORRUPTION)
    hooks = SafetyMetricHooks()
    hooks.record_verification(result)
    hooks.record_risk_decision(decision)
    assert len(hooks.events) == 2
    assert hooks.blind_commit_count == 0
    assert hooks.total_commit_count == 0
    assert hooks.blind_commit_rate == 0.0
    assert hooks.blind_commit_rate_status == "NOT_APPLICABLE"
    assert not hasattr(hooks, "commit")
    assert not hasattr(decision, "commit")


def test_risk_decision_cannot_claim_production_commit() -> None:
    context, result, decision = evaluate(VerificationFixture.GOOD_CANDIDATE)
    assert decision.production_commit_performed is False
    assert all(field.name != "production_version" for field in fields(decision))
