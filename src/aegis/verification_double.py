"""Deterministic Mission 005 candidate/evidence fixtures.

These fixtures are local test data only and never claim live Bright Data
candidate correctness or mutation-laboratory ground truth.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from .healing import RepairCandidate, VerificationStatus
from .models import ExtractionContract, FieldContract, Observation, ProviderProvenance
from .verification import IndependentEvidence, VerificationContext, VerificationProvenance


class VerificationFixture(str, Enum):
    __test__ = False
    GOOD_CANDIDATE = "GOOD_CANDIDATE"
    BAD_SCHEMA = "BAD_SCHEMA"
    BAD_SEMANTIC = "BAD_SEMANTIC"
    SILENT_CORRUPTION = "SILENT_CORRUPTION"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"



def mission005_contract() -> ExtractionContract:
    return ExtractionContract(
        contract_id="mission-005-price-v1",
        fields=(
            FieldContract("product_id", expected_types=(str,)),
            FieldContract("title", expected_types=(str,)),
            FieldContract("price", expected_types=(int, float)),
            FieldContract("url", expected_types=(str,)),
        ),
        min_rows=1,
        numeric_bounds={"price": (0, None)},
        invariants=("valid_url", "price_non_negative"),
        expected_schema=("product_id", "title", "price", "url"),
    )



def _known_good_rows() -> tuple[dict[str, Any], ...]:
    return ({"product_id": "gpu-1", "title": "DGX Spark", "price": 599, "url": "https://example.test/gpu-1"},)



def _candidate(rows: tuple[dict[str, Any], ...]) -> RepairCandidate:
    return RepairCandidate(
        repair_request_id="repair_mission005_fixture",
        collector_reference="test-double-collector-mission005",
        provider_operation_reference="test-double-operation-mission005",
        provider_status="awaiting_approval",
        preview_result=rows,
        diff_summary="TEST_DOUBLE verification fixture",
        approval_command="NOT_EXECUTED_TEST_DOUBLE_APPROVAL",
        raw_evidence_ref="evidence://TEST_DOUBLE/mission-005/candidate",
        provenance=ProviderProvenance.TEST_DOUBLE,
        verification_status=VerificationStatus.UNVERIFIED,
        latency_ms=1,
    )



def _history() -> tuple[Observation, ...]:
    return (
        Observation(
            collection_id="history-collection-mission005",
            collector_id="test-double-collector-mission005",
            input={"target_url": "https://example.test/gpu-1"},
            output=_known_good_rows(),
            schema=("product_id", "price", "title", "url"),
            row_count=1,
            provider_provenance=ProviderProvenance.TEST_DOUBLE,
            evidence_refs=("evidence://TEST_DOUBLE/mission-005/history",),
        ),
    )



def build_verification_fixture(fixture: VerificationFixture) -> VerificationContext:
    good = _known_good_rows()
    contract = mission005_contract()
    if fixture is VerificationFixture.BAD_SCHEMA:
        rows = ({"product_id": "gpu-1", "title": "DGX Spark", "url": "https://example.test/gpu-1"},)
    elif fixture is VerificationFixture.BAD_SEMANTIC:
        rows = ({"product_id": "gpu-1", "title": "DGX Spark", "price": -1, "url": "https://example.test/gpu-1"},)
    elif fixture is VerificationFixture.SILENT_CORRUPTION:
        rows = ({"product_id": "gpu-1", "title": "DGX Spark", "price": 29.99, "url": "https://example.test/gpu-1"},)
    else:
        rows = good
    history = () if fixture is VerificationFixture.UNKNOWN_EVIDENCE else _history()
    independent = None
    if fixture in {VerificationFixture.GOOD_CANDIDATE, VerificationFixture.BAD_SCHEMA, VerificationFixture.BAD_SEMANTIC, VerificationFixture.SILENT_CORRUPTION}:
        independent_rows = good
        if fixture is VerificationFixture.CONTRADICTORY_EVIDENCE:
            independent_rows = ({"product_id": "gpu-1", "title": "DGX Spark", "price": 29.99, "url": "https://example.test/gpu-1"},)
        independent = IndependentEvidence(
            evidence_id="independent-mission005",
            source="controlled-alternate-path",
            rows=independent_rows,
            provenance=VerificationProvenance.TEST_DOUBLE,
            source_group="alternate-path",
            evidence_refs=("evidence://TEST_DOUBLE/mission-005/independent",),
            correlation_id="corr-mission005",
        )
    if fixture is VerificationFixture.MISSING_EVIDENCE:
        independent = None
    if fixture is VerificationFixture.CONTRADICTORY_EVIDENCE:
        independent = IndependentEvidence(
            evidence_id="independent-mission005-contradiction",
            source="controlled-alternate-path",
            rows=({"product_id": "gpu-1", "title": "DGX Spark", "price": 29.99, "url": "https://example.test/gpu-1"},),
            provenance=VerificationProvenance.TEST_DOUBLE,
            source_group="alternate-path",
            evidence_refs=("evidence://TEST_DOUBLE/mission-005/contradictory",),
            correlation_id="corr-mission005",
        )
    return VerificationContext(
        candidate=_candidate(rows),
        contract=contract,
        candidate_output=rows,
        history=history,
        independent_evidence=independent,
        correlation_id="corr-mission005",
        evidence_refs=(f"evidence://TEST_DOUBLE/mission-005/{fixture.value.lower()}",),
        semantic_expectations={"price": 599} if fixture is VerificationFixture.SILENT_CORRUPTION else {},
        history_source_group="history-path",
        model_opinion={"overall": "PASS", "rationale": "ignored auxiliary opinion"} if fixture in {VerificationFixture.BAD_SEMANTIC, VerificationFixture.SILENT_CORRUPTION} else {},
    )
