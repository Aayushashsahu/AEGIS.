from __future__ import annotations

import json
from pathlib import Path

from aegis.healing import RepairCandidate, VerificationStatus
from aegis.models import ProviderProvenance
from aegis.risk import RiskDecisionType, RiskGovernor
from aegis.verification import VerificationContext, VerificationOverallStatus, verify_candidate
from aegis.verification_double import mission005_contract


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_bright_data_candidate_remains_unaccepted_without_ground_truth() -> None:
    output = json.loads((REPO_ROOT / "experiments/mission_001_collection_output.json").read_text())
    metadata = json.loads((REPO_ROOT / "experiments/mission_001_collection_metadata.json").read_text())
    candidate = RepairCandidate(
        repair_request_id="recorded-mission001-repair-request",
        collector_reference=metadata["collector_id"],
        provider_operation_reference="recorded-mission001-heal-response",
        provider_status="awaiting_approval",
        preview_result=output,
        diff_summary="recorded provider preview; correctness unknown",
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
        correlation_id="corr-mission005-recorded-provider",
        evidence_refs=("evidence://mission-001/heal-preview",),
    )
    result = verify_candidate(context)
    decision = RiskGovernor().decide(result, candidate, correlation_id=context.correlation_id)
    assert candidate.provenance is ProviderProvenance.BRIGHT_DATA
    assert result.overall_status in {VerificationOverallStatus.FAIL, VerificationOverallStatus.INCONCLUSIVE}
    assert decision.decision is not RiskDecisionType.ACCEPT
    assert decision.production_commit_performed is False
