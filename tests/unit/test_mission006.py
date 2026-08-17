from __future__ import annotations

from dataclasses import replace

import pytest

from aegis.commit_gate import (
    AuthorizationContext,
    CommitBlockReason,
    CommitDecision,
    CommitEligibility,
    CommitGate,
    CommitSafetyMetricHooks,
    OutputEligibilityBoundary,
    QuarantineLedger,
    QuarantineStatus,
)
from aegis.commit_gate_double import CommitGateFixture, build_commit_gate_fixture
from aegis.models import ProviderProvenance
from aegis.risk import RiskDecisionType


def evaluate(scenario: CommitGateFixture):
    candidate, context, verification, risk_decision, known_good, authorization = build_commit_gate_fixture(scenario)
    decision = CommitGate().evaluate(
        candidate,
        verification,
        risk_decision,
        context.contract,
        known_good,
        authorization,
        correlation_id=context.correlation_id,
    )
    return candidate, context, verification, risk_decision, known_good, authorization, decision


def test_accept_pass_verified_known_good_and_authorized_is_eligible() -> None:
    _, _, verification, risk_decision, known_good, authorization, decision = evaluate(CommitGateFixture.COMMIT_ELIGIBLE)
    assert verification.overall_status.value == "PASS"
    assert risk_decision.decision is RiskDecisionType.ACCEPT
    assert known_good is not None
    assert authorization is not None
    assert decision.eligibility is CommitEligibility.ELIGIBLE
    assert decision.block_reasons == ()
    assert decision.production_commit_performed is False


def test_reject_is_blocked() -> None:
    _, _, _, risk_decision, _, _, decision = evaluate(CommitGateFixture.BLOCKED_REJECT)
    assert risk_decision.decision is RiskDecisionType.REJECT
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.RISK_NOT_ACCEPT in decision.block_reasons


def test_quarantine_is_blocked_and_persisted() -> None:
    candidate, context, verification, risk_decision, _, _, decision = evaluate(CommitGateFixture.BLOCKED_QUARANTINE)
    assert risk_decision.decision is RiskDecisionType.QUARANTINE
    assert decision.eligibility is CommitEligibility.BLOCKED
    ledger = QuarantineLedger().record_for_decision(candidate, verification, risk_decision, decision)
    record = ledger.latest_for_candidate(candidate.candidate_id)
    assert record is not None
    assert record.status is QuarantineStatus.OPEN
    assert record.candidate_id == candidate.candidate_id
    assert record.verification_id == verification.verification_id
    assert record.correlation_id == context.correlation_id


def test_unknown_evidence_is_blocked() -> None:
    _, _, verification, _, _, _, decision = evaluate(CommitGateFixture.BLOCKED_UNKNOWN)
    assert verification.unknown_checks
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.REQUIRED_EVIDENCE_MISSING in decision.block_reasons


def test_verification_not_pass_is_blocked() -> None:
    _, _, verification, _, _, _, decision = evaluate(CommitGateFixture.BLOCKED_MISSING_VERIFICATION)
    assert verification.overall_status.value == "PASS"
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.CANDIDATE_NOT_VERIFIED in decision.block_reasons


def test_unverified_candidate_is_blocked_even_when_risk_accepts() -> None:
    candidate, _, _, risk_decision, _, _, decision = evaluate(CommitGateFixture.BLOCKED_MISSING_VERIFICATION)
    assert candidate.verification_status.value == "UNVERIFIED"
    assert risk_decision.decision is RiskDecisionType.ACCEPT
    assert decision.eligibility is CommitEligibility.BLOCKED


def test_missing_known_good_is_blocked() -> None:
    _, _, _, _, known_good, _, decision = evaluate(CommitGateFixture.BLOCKED_MISSING_KNOWN_GOOD)
    assert known_good is None
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.KNOWN_GOOD_MISSING in decision.block_reasons


def test_invalid_authorization_is_blocked() -> None:
    _, _, _, _, _, authorization, decision = evaluate(CommitGateFixture.BLOCKED_UNAUTHORIZED)
    assert authorization is not None and not authorization.valid
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.INVALID_AUTHORIZATION in decision.block_reasons


def test_missing_evidence_is_blocked_even_with_verified_candidate() -> None:
    _, _, _, _, _, _, decision = evaluate(CommitGateFixture.BLOCKED_MISSING_EVIDENCE)
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.REQUIRED_EVIDENCE_MISSING in decision.block_reasons


def test_mismatched_correlation_is_blocked() -> None:
    _, context, _, _, _, authorization, decision = evaluate(CommitGateFixture.BLOCKED_CORRELATION)
    assert authorization is not None and authorization.correlation_id != context.correlation_id
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert CommitBlockReason.INVALID_AUTHORIZATION in decision.block_reasons


def test_output_boundary_allows_only_eligible_commit_decision() -> None:
    _, _, _, _, _, _, eligible = evaluate(CommitGateFixture.COMMIT_ELIGIBLE)
    allowed = OutputEligibilityBoundary.evaluate(eligible)
    assert allowed.eligible is True
    _, _, _, _, _, _, blocked = evaluate(CommitGateFixture.BLOCKED_REJECT)
    denied = OutputEligibilityBoundary.evaluate(blocked)
    assert denied.eligible is False


def test_quarantine_release_does_not_directly_create_eligibility() -> None:
    candidate, _, verification, risk_decision, _, _, blocked = evaluate(CommitGateFixture.BLOCKED_QUARANTINE)
    ledger = QuarantineLedger().record_for_decision(candidate, verification, risk_decision, blocked)
    record = ledger.latest_for_candidate(candidate.candidate_id)
    assert record is not None
    released_without_reentry = record.with_status(QuarantineStatus.RELEASED)
    hypothetical = CommitDecision(
        candidate_id=candidate.candidate_id,
        verification_id="verification-after-release",
        risk_decision_id="risk-after-release",
        eligibility=CommitEligibility.ELIGIBLE,
        evidence_refs=("evidence://reverification",),
        known_good_version_reference="known-good-after-release",
        authorization_reference="auth-after-release",
        correlation_id=record.correlation_id,
        provenance=ProviderProvenance.TEST_DOUBLE,
    )
    denied = OutputEligibilityBoundary.evaluate(hypothetical, quarantine_record=released_without_reentry)
    assert denied.eligible is False
    released_with_reentry = record.with_status(QuarantineStatus.RELEASED, reentry_verification_id=hypothetical.verification_id)
    allowed = OutputEligibilityBoundary.evaluate(hypothetical, quarantine_record=released_with_reentry)
    assert allowed.eligible is True


def test_quarantine_ledger_is_append_only_and_immutable() -> None:
    candidate, _, verification, risk_decision, _, _, blocked = evaluate(CommitGateFixture.BLOCKED_QUARANTINE)
    ledger = QuarantineLedger().record_for_decision(candidate, verification, risk_decision, blocked)
    record = ledger.records[0]
    with pytest.raises((AttributeError, TypeError)):
        record.status = QuarantineStatus.REJECTED  # type: ignore[misc]
    updated = record.with_status(QuarantineStatus.REVIEWED)
    ledger2 = ledger.append(updated)
    assert len(ledger.records) == 1
    assert len(ledger2.records) == 2
    assert ledger2.current(record.quarantine_id).status is QuarantineStatus.REVIEWED


def test_commit_decision_is_immutable() -> None:
    _, _, _, _, _, _, decision = evaluate(CommitGateFixture.COMMIT_ELIGIBLE)
    with pytest.raises((AttributeError, TypeError)):
        decision.eligibility = CommitEligibility.BLOCKED  # type: ignore[misc]


def test_metric_hooks_report_not_applicable_without_commit_denominator() -> None:
    hooks = CommitSafetyMetricHooks()
    assert hooks.quarantine_rate is None
    assert hooks.unsafe_refusal_rate is None
    assert hooks.metric_status == "NOT_APPLICABLE"


def test_metric_hooks_record_refusal_and_quarantine_events_without_benchmark() -> None:
    candidate, _, verification, risk_decision, _, _, blocked = evaluate(CommitGateFixture.BLOCKED_QUARANTINE)
    hooks = CommitSafetyMetricHooks()
    hooks.record_commit_decision(blocked)
    ledger = QuarantineLedger().record_for_decision(candidate, verification, risk_decision, blocked)
    hooks.record_quarantine(ledger.records[0])
    assert hooks.unsafe_refusal_count == 1
    assert hooks.quarantine_count == 1
    assert hooks.unsafe_refusal_rate == 1.0
    assert hooks.quarantine_rate == 1.0
    assert len(hooks.events) == 2
    assert not hasattr(hooks, "approve")
    assert not hasattr(hooks, "rollback")
    assert not hasattr(hooks, "commit")
