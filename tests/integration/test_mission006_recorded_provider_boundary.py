from __future__ import annotations

import json
from pathlib import Path

from aegis.commit_gate import AuthorizationContext, CommitEligibility, CommitGate, KnownGoodVersion, QuarantineLedger
from aegis.healing import RepairCandidate, VerificationStatus
from aegis.models import ProviderProvenance
from aegis.risk import RiskGovernor
from aegis.verification import VerificationContext, verify_candidate
from aegis.verification_double import mission005_contract


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_bright_data_proposal_cannot_cross_mission006_gate() -> None:
    output = json.loads((REPO_ROOT / "experiments/mission_001_collection_output.json").read_text())
    metadata = json.loads((REPO_ROOT / "experiments/mission_001_collection_metadata.json").read_text())
    candidate = RepairCandidate(
        repair_request_id="recorded-mission001-repair-request",
        collector_reference=metadata["collector_id"],
        provider_operation_reference="recorded-mission001-heal-response",
        provider_status="awaiting_approval",
        preview_result=output,
        diff_summary="recorded provider preview; not approved or verified",
        approval_command="recorded but not executed",
        raw_evidence_ref="evidence://mission-001/heal-preview",
        provenance=ProviderProvenance.BRIGHT_DATA,
        verification_status=VerificationStatus.UNVERIFIED,
        latency_ms=metadata["run_latency_ms"],
    )
    context = VerificationContext(
        candidate=candidate,
        contract=mission005_contract(),
        candidate_output=output,
        correlation_id="corr-mission006-recorded-provider",
        evidence_refs=("evidence://mission-001/heal-preview",),
    )
    verification = verify_candidate(context)
    risk_decision = RiskGovernor().decide(verification, candidate, correlation_id=context.correlation_id)
    known_good = KnownGoodVersion(
        pipeline_reference="aegis-recorded-pipeline",
        version_reference="aegis-known-good-recorded-v1",
        observation_reference="observation://mission-001/known-good",
        verification_reference="verification://mission-001/known-good",
        provenance=ProviderProvenance.BRIGHT_DATA,
        correlation_id=context.correlation_id,
    )
    authorization = AuthorizationContext(
        actor="TEST_DOUBLE_RELEASE_ROLE",
        authorization_reference="auth://TEST_DOUBLE/mission-006",
        scopes=("candidate_commit_eligibility",),
        correlation_id=context.correlation_id,
    )
    decision = CommitGate().evaluate(
        candidate,
        verification,
        risk_decision,
        context.contract,
        known_good,
        authorization,
        correlation_id=context.correlation_id,
    )
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert any(reason.value == "CANDIDATE_NOT_VERIFIED" for reason in decision.block_reasons)
    ledger = QuarantineLedger().record_for_decision(candidate, verification, risk_decision, decision)
    record = ledger.latest_for_candidate(candidate.candidate_id)
    assert record is not None
    assert record.candidate_provenance is ProviderProvenance.BRIGHT_DATA
    assert record.status.value == "OPEN"
    assert decision.production_commit_performed is False
