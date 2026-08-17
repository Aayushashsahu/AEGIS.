"""Deterministic Mission 006 commit-gate fixtures.

These scenarios are local safety tests only. They do not authorize or execute
provider approval, activation, production commit, or rollback.
"""

from __future__ import annotations

from dataclasses import replace
from enum import Enum

from .commit_gate import AuthorizationContext, KnownGoodVersion
from .healing import RepairCandidate, VerificationStatus
from .models import ProviderProvenance
from .risk import RiskGovernor
from .verification import VerificationContext, VerificationResult, verify_candidate
from .verification_double import VerificationFixture, build_verification_fixture


class CommitGateFixture(str, Enum):
    __test__ = False
    COMMIT_ELIGIBLE = "COMMIT_ELIGIBLE"
    BLOCKED_REJECT = "BLOCKED_REJECT"
    BLOCKED_QUARANTINE = "BLOCKED_QUARANTINE"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"
    BLOCKED_MISSING_VERIFICATION = "BLOCKED_MISSING_VERIFICATION"
    BLOCKED_MISSING_KNOWN_GOOD = "BLOCKED_MISSING_KNOWN_GOOD"
    BLOCKED_UNAUTHORIZED = "BLOCKED_UNAUTHORIZED"
    BLOCKED_MISSING_EVIDENCE = "BLOCKED_MISSING_EVIDENCE"
    BLOCKED_CORRELATION = "BLOCKED_CORRELATION"



def build_commit_gate_fixture(
    scenario: CommitGateFixture,
) -> tuple[RepairCandidate, VerificationContext, VerificationResult, object, KnownGoodVersion | None, AuthorizationContext | None]:
    verification_fixture = {
        CommitGateFixture.COMMIT_ELIGIBLE: VerificationFixture.GOOD_CANDIDATE,
        CommitGateFixture.BLOCKED_REJECT: VerificationFixture.BAD_SCHEMA,
        CommitGateFixture.BLOCKED_QUARANTINE: VerificationFixture.MISSING_EVIDENCE,
        CommitGateFixture.BLOCKED_UNKNOWN: VerificationFixture.UNKNOWN_EVIDENCE,
        CommitGateFixture.BLOCKED_MISSING_VERIFICATION: VerificationFixture.GOOD_CANDIDATE,
        CommitGateFixture.BLOCKED_MISSING_KNOWN_GOOD: VerificationFixture.GOOD_CANDIDATE,
        CommitGateFixture.BLOCKED_UNAUTHORIZED: VerificationFixture.GOOD_CANDIDATE,
        CommitGateFixture.BLOCKED_MISSING_EVIDENCE: VerificationFixture.MISSING_EVIDENCE,
        CommitGateFixture.BLOCKED_CORRELATION: VerificationFixture.GOOD_CANDIDATE,
    }[scenario]
    context = build_verification_fixture(verification_fixture)
    result = verify_candidate(context)
    risk_decision = RiskGovernor().decide(result, context.candidate, correlation_id=context.correlation_id)
    candidate = context.candidate
    if scenario not in {CommitGateFixture.BLOCKED_MISSING_VERIFICATION}:
        candidate = replace(candidate, verification_status=VerificationStatus.VERIFIED)
    known_good = KnownGoodVersion(
        pipeline_reference="test-double-pipeline-mission006",
        version_reference="aegis-known-good-test-v1",
        observation_reference="observation://TEST_DOUBLE/mission-006/known-good",
        verification_reference="verification://TEST_DOUBLE/mission-006/known-good",
        provenance=ProviderProvenance.TEST_DOUBLE,
        correlation_id=context.correlation_id,
    )
    authorization: AuthorizationContext | None = AuthorizationContext(
        actor="TEST_DOUBLE_RELEASE_ROLE",
        authorization_reference="auth://TEST_DOUBLE/mission-006/eligibility",
        scopes=("candidate_commit_eligibility",),
        correlation_id=context.correlation_id,
        provenance="TEST_DOUBLE",
    )
    if scenario is CommitGateFixture.BLOCKED_MISSING_KNOWN_GOOD:
        known_good = None
    if scenario is CommitGateFixture.BLOCKED_UNAUTHORIZED:
        authorization = AuthorizationContext(
            actor="",
            authorization_reference="",
            scopes=(),
            correlation_id=context.correlation_id,
            valid=False,
            provenance="TEST_DOUBLE",
        )
    if scenario is CommitGateFixture.BLOCKED_CORRELATION:
        authorization = replace(authorization, correlation_id="different-correlation") if authorization else None
    return candidate, context, result, risk_decision, known_good, authorization
