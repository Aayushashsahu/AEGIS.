"""Provider-free model of the documented approval, persistence, and re-run loop.

This module contains only TEST_DOUBLE fixture behavior. It never invokes Bright
Data, does not claim a live template was persisted, and keeps release blocked
without a separately supplied commit authorization.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.healing import RepairCandidate, VerificationStatus
from aegis.models import ExtractionContract, FieldContract, Observation, ProviderProvenance
from aegis.risk import RiskGovernor
from aegis.verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate


COLLECTOR_ID = "c_mt09pib13nxqz1coi"
TARGET_URL = "https://example.test/mission-033/target"
FIELDS = ("title", "price", "availability")
EXPECTED_ROW: dict[str, Any] = {
    "title": "AEGIS Verification Widget",
    "price": {"value": 599, "currency": "USD"},
    "availability": "Available",
}
INPUT_URL_ONLY_ROW: dict[str, Any] = {"input": {"url": TARGET_URL}}


def _contract() -> ExtractionContract:
    return ExtractionContract(
        contract_id="mission-052-provider-free-product-v1",
        fields=(
            FieldContract("title", expected_types=(str,)),
            FieldContract("price", expected_types=(dict, MappingProxyType)),
            FieldContract("availability", expected_types=(str,)),
        ),
        min_rows=1,
        expected_schema=FIELDS,
    )


def _candidate() -> RepairCandidate:
    return RepairCandidate(
        candidate_id="candidate_m052_test_double",
        repair_request_id="repair_m052_test_double",
        collector_reference=COLLECTOR_ID,
        provider_operation_reference="test-double-approval-persistence",
        provider_status="APPROVED_SIMULATED",
        preview_result=(EXPECTED_ROW,),
        diff_summary="TEST_DOUBLE: preview includes every contract-required field.",
        approval_command="NOT_EXECUTED_TEST_DOUBLE_APPROVAL",
        raw_evidence_ref="evidence://TEST_DOUBLE/mission-052/candidate-preview",
        provenance=ProviderProvenance.TEST_DOUBLE,
        verification_status=VerificationStatus.UNVERIFIED,
    )


def _observation(*, identifier: str, output: Mapping[str, Any], evidence_ref: str) -> Observation:
    return Observation(
        observation_id=f"observation_m052_test_double_{identifier}",
        collection_id=f"collection_m052_test_double_{identifier}",
        collector_id=COLLECTOR_ID,
        input={"url": TARGET_URL},
        output=(dict(output),),
        schema=tuple(sorted(output.keys())),
        row_count=1,
        provider_provenance=ProviderProvenance.TEST_DOUBLE,
        evidence_refs=(evidence_ref,),
    )


def _field_paths(row: Mapping[str, Any]) -> tuple[str, ...]:
    fields: list[str] = []
    for key, value in row.items():
        if isinstance(value, Mapping):
            fields.extend(f"{key}.{nested}" for nested in value)
        else:
            fields.append(key)
    return tuple(sorted(fields))


def evaluate_post_approval_output(output: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a simulated post-approval row through canonical safety gates."""

    candidate = _candidate()
    history = _observation(
        identifier="history",
        output=EXPECTED_ROW,
        evidence_ref="evidence://TEST_DOUBLE/mission-052/history",
    )
    post_approval = _observation(
        identifier="post_approval",
        output=output,
        evidence_ref="evidence://TEST_DOUBLE/mission-052/post-approval-output",
    )
    expected = _observation(
        identifier="independent",
        output=EXPECTED_ROW,
        evidence_ref="evidence://TEST_DOUBLE/mission-052/independent",
    )
    correlation_id = "mission052-test-double-post-approval"
    verification = verify_candidate(
        VerificationContext(
            candidate=candidate,
            contract=_contract(),
            candidate_output=post_approval.output,
            history=(history,),
            independent_evidence=IndependentEvidence(
                evidence_id="independent_m052_test_double",
                source="controlled expected structured result",
                rows=expected.output,
                provenance=VerificationProvenance.TEST_DOUBLE,
                source_group="TEST_DOUBLE_INDEPENDENT",
                evidence_refs=expected.evidence_refs,
                correlation_id=correlation_id,
            ),
            correlation_id=correlation_id,
            evidence_refs=post_approval.evidence_refs,
            semantic_expectations=expected.output[0],
            history_source_group="TEST_DOUBLE_HISTORY",
        )
    )
    risk = RiskGovernor().decide(verification, candidate, correlation_id=correlation_id)
    commit = CommitGate().evaluate(
        candidate,
        verification,
        risk,
        _contract(),
        known_good_version=None,
        authorization=None,
        correlation_id=correlation_id,
    )
    output_eligibility = OutputEligibilityBoundary.evaluate(commit)
    return {
        "provenance": "TEST_DOUBLE",
        "candidate_preview_fields": _field_paths(EXPECTED_ROW),
        "approval": "ACCEPTED_SIMULATED",
        "template_persistence": "YES_SIMULATED",
        "post_approval_output_fields": _field_paths(output),
        "verification": verification.overall_status.value,
        "risk": risk.decision.value,
        "commit": commit.eligibility.value,
        "data_shipped": "YES" if output_eligibility.eligible else "NO",
        "provider_operations": 0,
        "retries": 0,
        "note": "Provider-free TEST_DOUBLE model; no provider approval, persistence, rerun, or commit was executed.",
    }
