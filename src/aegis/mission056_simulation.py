"""Controlled, provider-free Mission 056 recovery simulations.

These scenarios validate AEGIS decisions around the managed target contract.
They do not fetch the target, call Bright Data, or stand in for provider output.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from .audit_store import _to_jsonable
from .commit_gate import CommitGate, OutputEligibilityBoundary
from .detection import evaluate_detection
from .healing import RepairCandidate
from .models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    ExtractionContract,
    FieldContract,
    Observation,
    ProviderProvenance,
)
from .output_lineage import analyze_output_lineage
from .risk import RiskGovernor
from .verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate


MISSION056_TARGET_URL = "https://managed-aegis.example/mission-056/target"
MISSION056_REQUIRED_FIELDS = ("title", "price", "availability")
MISSION056_EXPECTED_ROW: Mapping[str, Any] = {
    "title": "AEGIS Recovery Widget",
    "price": {"currency": "USD", "value": 599.0},
    "availability": "Available",
}


def mission056_contract() -> ExtractionContract:
    return ExtractionContract(
        contract_id="mission-056-controlled-product-v1",
        fields=(
            FieldContract("title", expected_types=(str,)),
            FieldContract("price", expected_types=(dict, MappingProxyType)),
            FieldContract("availability", expected_types=(str,)),
        ),
        min_rows=1,
        expected_schema=MISSION056_REQUIRED_FIELDS,
    )


def _observation(rows: tuple[Mapping[str, Any], ...], *, label: str) -> Observation:
    handle = CollectionHandle(
        collection_id=f"mission056-{label}-collection",
        collector_id="c_test_double_m056",
        correlation_id=f"mission056-{label}",
        status=CollectionState.COMPLETED,
        mode=CollectionMode.TEST_DOUBLE,
        provider_operation_ids={"simulation_id": label},
        provider_status="TEST_DOUBLE_COMPLETED",
        output_schema=tuple(sorted({key for row in rows for key in row})),
        provider_provenance=ProviderProvenance.TEST_DOUBLE,
        evidence_refs=(f"evidence://mission-056/simulation/{label}",),
    )
    return Observation.from_result(
        CollectionResult(handle=handle, output=rows),
        {"target_url": MISSION056_TARGET_URL, "target_variant": label, "provenance": "TEST_DOUBLE"},
    )


def _candidate(rows: tuple[Mapping[str, Any], ...], *, label: str) -> RepairCandidate:
    return RepairCandidate(
        candidate_id=f"candidate_m056_{label}",
        repair_request_id=f"repair_m056_{label}",
        collector_reference="c_test_double_m056",
        provider_operation_reference=f"simulation_{label}",
        provider_status="TEST_DOUBLE",
        preview_result=list(rows),
        diff_summary="Provider-free Mission 056 scenario",
        approval_command=None,
        raw_evidence_ref=f"evidence://mission-056/simulation/{label}/raw",
        provenance=ProviderProvenance.TEST_DOUBLE,
    )


def run_mission056_simulation() -> dict[str, object]:
    """Return deterministic safety outcomes for baseline, drift, and candidates."""

    baseline_rows = (MISSION056_EXPECTED_ROW,)
    drift_rows = ({"input": {"url": MISSION056_TARGET_URL}},)
    baseline = _observation(baseline_rows, label="baseline")
    drift = _observation(drift_rows, label="drift")
    contract = mission056_contract()
    baseline_detection = evaluate_detection(baseline, contract)
    drift_detection = evaluate_detection(drift, contract)
    independent = IndependentEvidence(
        evidence_id="independent_m056_owned_target_contract",
        source="controlled local target contract",
        rows=baseline_rows,
        provenance=VerificationProvenance.TEST_DOUBLE,
        source_group="M056_OWNED_TARGET_DIRECT_FIXTURE",
        evidence_refs=("evidence://mission-056/simulation/target-contract",),
        correlation_id="mission056-simulation",
    )

    complete_candidate = _candidate(baseline_rows, label="complete")
    complete_verification = verify_candidate(VerificationContext(
        candidate=complete_candidate,
        contract=contract,
        candidate_output=baseline_rows,
        history=(baseline,),
        independent_evidence=independent,
        correlation_id="mission056-simulation-complete",
        evidence_refs=("evidence://mission-056/simulation/complete/raw",),
        semantic_expectations=MISSION056_EXPECTED_ROW,
        history_source_group="M056_TEST_DOUBLE_COLLECTION",
    ))
    complete_risk = RiskGovernor().decide(complete_verification, complete_candidate, correlation_id="mission056-simulation-complete")
    complete_commit = CommitGate().evaluate(
        complete_candidate,
        complete_verification,
        complete_risk,
        contract,
        known_good_version=None,
        authorization=None,
        correlation_id="mission056-simulation-complete",
    )
    complete_eligibility = OutputEligibilityBoundary.evaluate(complete_commit)

    incomplete_candidate = _candidate(drift_rows, label="incomplete")
    incomplete_verification = verify_candidate(VerificationContext(
        candidate=incomplete_candidate,
        contract=contract,
        candidate_output=drift_rows,
        history=(baseline,),
        independent_evidence=independent,
        correlation_id="mission056-simulation-incomplete",
        evidence_refs=("evidence://mission-056/simulation/incomplete/raw",),
        semantic_expectations=MISSION056_EXPECTED_ROW,
        history_source_group="M056_TEST_DOUBLE_COLLECTION",
    ))
    incomplete_risk = RiskGovernor().decide(incomplete_verification, incomplete_candidate, correlation_id="mission056-simulation-incomplete")
    incomplete_commit = CommitGate().evaluate(
        incomplete_candidate,
        incomplete_verification,
        incomplete_risk,
        contract,
        known_good_version=None,
        authorization=None,
        correlation_id="mission056-simulation-incomplete",
    )
    incomplete_eligibility = OutputEligibilityBoundary.evaluate(incomplete_commit)
    incomplete_lineage = analyze_output_lineage(drift_rows, drift_rows, MISSION056_REQUIRED_FIELDS)

    return {
        "schema_version": "mission-056-provider-free-simulation-v1",
        "provenance": "TEST_DOUBLE",
        "provider_operations": 0,
        "baseline": {"detection": _to_jsonable(baseline_detection)},
        "controlled_drift": {"detection": _to_jsonable(drift_detection), "lineage": incomplete_lineage.to_evidence_dict()},
        "complete_candidate": {
            "verification": _to_jsonable(complete_verification),
            "risk": _to_jsonable(complete_risk),
            "commit": _to_jsonable(complete_commit),
            "downstream": _to_jsonable(complete_eligibility),
        },
        "incomplete_candidate": {
            "verification": _to_jsonable(incomplete_verification),
            "risk": _to_jsonable(incomplete_risk),
            "commit": _to_jsonable(incomplete_commit),
            "downstream": _to_jsonable(incomplete_eligibility),
        },
    }
