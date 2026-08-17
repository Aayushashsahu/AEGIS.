"""Mission 009 deterministic mutation laboratory V1.

The lab is the source of ground truth for controlled fixtures. Mutations are
provider-neutral and deterministic; collection provenance is TEST_DOUBLE. The
harness drives existing detection, verification, risk, CommitGate, and
QuarantineLedger boundaries and never calls Bright Data or claims benchmark
results.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Mapping, Sequence
from uuid import uuid4

from .commit_gate import (
    AuthorizationContext,
    CommitGate,
    CommitEligibility,
    KnownGoodVersion,
    QuarantineLedger,
)
from .detection import evaluate_detection
from .healing import RepairCandidate
from .models import (
    CollectionMode,
    DetectionResult,
    ExtractionContract,
    FieldContract,
    Observation,
    ProviderProvenance,
    utc_now,
)
from .risk import RiskDecision, RiskDecisionType, RiskGovernor
from .verification import (
    IndependentEvidence,
    VerificationContext,
    VerificationOverallStatus,
    VerificationProvenance,
    VerificationResult,
    verify_candidate,
)


class MutationSeverity(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


class MutationOutcome(str, Enum):
    HEALTHY = "HEALTHY"
    DETECTED_REJECTED = "DETECTED_REJECTED"
    DETECTED_QUARANTINED = "DETECTED_QUARANTINED"
    UNKNOWN = "UNKNOWN"
    UNSAFE_BLOCKED = "UNSAFE_BLOCKED"


@dataclass(frozen=True)
class StagingFixture:
    fixture_id: str = "gpu-price-staging"
    fixture_version: str = "1"
    page_markup: str = "<article class='product-card'><h1>DGX Spark</h1><span data-field='price'>$599</span></article>"
    records: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(_freeze_row(row) for row in self.records))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        if not self.fixture_id or not self.fixture_version or (not self.records and not self.metadata.get("allow_empty", False)):
            raise ValueError("staging fixture requires an ID, version, and records unless explicitly marked allow_empty")


@dataclass(frozen=True)
class MutatedFixture:
    mutation_id: str
    seed: int
    baseline: StagingFixture
    fixture: StagingFixture
    mutation_metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mutation_metadata", _freeze_mapping(self.mutation_metadata))

    def revert(self) -> StagingFixture:
        return self.baseline


@dataclass(frozen=True)
class MutationGroundTruth:
    mutation_id: str
    severity: MutationSeverity
    seed: int
    baseline_fixture_reference: str
    mutated_fixture_reference: str
    expected_correct_state: Mapping[str, Any]
    expected_corrupted_state: Mapping[str, Any]
    affected_fields: tuple[str, ...]
    expected_detector_behavior: str
    expected_safety_behavior: str
    deterministic_metadata: Mapping[str, Any]
    created_at: datetime = field(default_factory=utc_now)
    ground_truth_id: str = field(default_factory=lambda: f"ground_truth_{uuid4().hex}")

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_correct_state", _freeze_mapping(self.expected_correct_state))
        object.__setattr__(self, "expected_corrupted_state", _freeze_mapping(self.expected_corrupted_state))
        object.__setattr__(self, "affected_fields", tuple(self.affected_fields))
        object.__setattr__(self, "deterministic_metadata", _freeze_mapping(self.deterministic_metadata))
        if not self.ground_truth_id or not self.mutation_id or not self.baseline_fixture_reference or not self.mutated_fixture_reference:
            raise ValueError("MutationGroundTruth requires stable references")


@dataclass(frozen=True)
class MutationCase:
    mutation_id: str
    severity: MutationSeverity
    seed: int
    baseline: StagingFixture
    mutated: MutatedFixture
    ground_truth: MutationGroundTruth


@dataclass(frozen=True)
class MutationRun:
    run_id: str = field(default_factory=lambda: f"mutation_run_{uuid4().hex}")
    mutation_id: str = ""
    seed: int = 0
    collector_reference: str = "mutation-lab-test-double"
    observation_reference: str = ""
    detection_reference: str = ""
    verification_reference: str | None = None
    risk_decision_reference: str | None = None
    ground_truth_reference: str = ""
    detected: bool = False
    detected_by_existing_detection: bool = False
    outcome: MutationOutcome = MutationOutcome.UNKNOWN
    provenance: ProviderProvenance = ProviderProvenance.TEST_DOUBLE
    timing_ms: Mapping[str, int] = field(default_factory=dict)
    verification_status: str = "ABSENT"
    risk_decision: str = "ABSENT"
    commit_eligibility: str = "ABSENT"
    output_eligible: bool = False
    quarantine_reference: str | None = None
    evidence_refs: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timing_ms", _freeze_mapping(self.timing_ms))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        if not self.mutation_id or not self.observation_reference or not self.detection_reference or not self.ground_truth_reference:
            raise ValueError("MutationRun requires mutation, observation, detection, and ground-truth references")
        if self.output_eligible:
            raise ValueError("Mission 009 runs cannot be output eligible")


@dataclass(frozen=True)
class MutationDefinition:
    mutation_id: str
    severity: MutationSeverity
    description: str
    expected_detector_behavior: str
    expected_safety_behavior: str
    affected_fields: tuple[str, ...]
    apply_fn: Callable[[StagingFixture, int], MutatedFixture]

    def apply(self, baseline: StagingFixture, seed: int) -> MutatedFixture:
        result = self.apply_fn(baseline, seed)
        if result.mutation_id != self.mutation_id or result.seed != seed:
            raise ValueError("mutation function returned mismatched identity")
        return result


class MutationLab:
    """Deterministic V1 harness; not a full benchmark runner."""

    def __init__(self, *, fixture: StagingFixture | None = None) -> None:
        self._fixture = fixture or baseline_fixture()
        self._definitions = _definitions()

    @property
    def fixture(self) -> StagingFixture:
        return self._fixture

    @property
    def mutation_ids(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def definition(self, mutation_id: str) -> MutationDefinition:
        try:
            return self._definitions[mutation_id]
        except KeyError as exc:
            raise ValueError(f"unknown mutation ID: {mutation_id}") from exc

    def apply_mutation(self, mutation_id: str, seed: int) -> MutationCase:
        definition = self.definition(mutation_id)
        mutated = definition.apply(self._fixture, seed)
        ground_truth = MutationGroundTruth(
            mutation_id=definition.mutation_id,
            severity=definition.severity,
            seed=seed,
            baseline_fixture_reference=f"fixture://{self._fixture.fixture_id}/v{self._fixture.fixture_version}/baseline",
            mutated_fixture_reference=f"fixture://{self._fixture.fixture_id}/v{self._fixture.fixture_version}/{mutation_id}/{seed}",
            expected_correct_state={"records": self._fixture.records, "markup": self._fixture.page_markup},
            expected_corrupted_state={"records": mutated.fixture.records, "markup": mutated.fixture.page_markup},
            affected_fields=definition.affected_fields,
            expected_detector_behavior=definition.expected_detector_behavior,
            expected_safety_behavior=definition.expected_safety_behavior,
            deterministic_metadata={
                "fixture_id": self._fixture.fixture_id,
                "fixture_version": self._fixture.fixture_version,
                "mutation_metadata": mutated.mutation_metadata,
                "seed": seed,
            },
        )
        return MutationCase(definition.mutation_id, definition.severity, seed, self._fixture, mutated, ground_truth)

    def run(self, mutation_id: str, seed: int) -> tuple[MutationRun, MutationCase, DetectionResult, VerificationResult, RiskDecision]:
        case = self.apply_mutation(mutation_id, seed)
        started = utc_now()
        observation = _observation_from_fixture(case.mutated.fixture, mutation_id, seed)
        detected_started = utc_now()
        detection = evaluate_detection(observation, extraction_contract())
        detected_ms = _elapsed_ms(detected_started, utc_now())
        candidate = _candidate_from_observation(observation, mutation_id, seed)
        baseline_observation = _observation_from_fixture(case.baseline, "BASELINE", seed)
        independent = IndependentEvidence(
            evidence_id=f"mutation-ground-truth-{mutation_id}-{seed}",
            source="mutation-lab-ground-truth",
            rows=case.baseline.records,
            provenance=VerificationProvenance.TEST_DOUBLE,
            source_group="mutation-ground-truth",
            evidence_refs=(f"ground-truth://{case.ground_truth.ground_truth_id}",),
            correlation_id=f"corr-mutation-{mutation_id}-{seed}",
        )
        verification_context = VerificationContext(
            candidate=candidate,
            contract=extraction_contract(),
            candidate_output=observation.output,
            history=(baseline_observation,),
            independent_evidence=independent,
            correlation_id=f"corr-mutation-{mutation_id}-{seed}",
            evidence_refs=(f"observation://{observation.observation_id}", f"ground-truth://{case.ground_truth.ground_truth_id}"),
            semantic_expectations={"price": 599},
            history_source_group="mutation-history",
        )
        verification_started = utc_now()
        verification = verify_candidate(verification_context)
        verification_ms = _elapsed_ms(verification_started, utc_now())
        risk_started = utc_now()
        risk_decision = RiskGovernor().decide(verification, candidate, correlation_id=verification_context.correlation_id)
        risk_ms = _elapsed_ms(risk_started, utc_now())
        known_good = KnownGoodVersion(
            pipeline_reference="mutation-lab-pipeline",
            version_reference="fixture-known-good-v1",
            observation_reference=f"observation://{baseline_observation.observation_id}",
            verification_reference=f"verification://ground-truth/{case.ground_truth.ground_truth_id}",
            provenance=ProviderProvenance.TEST_DOUBLE,
            correlation_id=verification_context.correlation_id,
        )
        authorization = AuthorizationContext(
            actor="MUTATION_LAB_TEST_DOUBLE",
            authorization_reference="auth://mutation-lab/test-double",
            scopes=("candidate_commit_eligibility",),
            correlation_id=verification_context.correlation_id,
            provenance="TEST_DOUBLE",
        )
        commit_decision = CommitGate().evaluate(
            candidate,
            verification,
            risk_decision,
            extraction_contract(),
            known_good,
            authorization,
            correlation_id=verification_context.correlation_id,
        )
        quarantine_reference = None
        ledger = QuarantineLedger()
        if risk_decision.decision is RiskDecisionType.QUARANTINE or (risk_decision.decision is RiskDecisionType.REJECT and verification.overall_status is not VerificationOverallStatus.PASS):
            ledger = ledger.record_for_decision(candidate, verification, risk_decision, commit_decision)
            latest = ledger.latest_for_candidate(candidate.candidate_id)
            quarantine_reference = latest.quarantine_id if latest else None
        outcome = _outcome(detection, verification, risk_decision, quarantine_reference)
        run = MutationRun(
            mutation_id=mutation_id,
            seed=seed,
            observation_reference=f"observation://{observation.observation_id}",
            detection_reference=f"detection://{observation.observation_id}",
            verification_reference=f"verification://{verification.verification_id}",
            risk_decision_reference=f"risk://{risk_decision.decision_id}",
            ground_truth_reference=f"ground-truth://{case.ground_truth.ground_truth_id}",
            detected=detection.detected or verification.overall_status is not VerificationOverallStatus.PASS,
            detected_by_existing_detection=detection.detected,
            outcome=outcome,
            timing_ms={"detection": detected_ms, "verification": verification_ms, "risk": risk_ms, "total": _elapsed_ms(started, utc_now())},
            verification_status=verification.overall_status.value,
            risk_decision=risk_decision.decision.value,
            commit_eligibility=commit_decision.eligibility.value,
            output_eligible=False,
            quarantine_reference=quarantine_reference,
            evidence_refs=(f"ground-truth://{case.ground_truth.ground_truth_id}", *detection.evidence_refs, *verification.evidence_refs),
        )
        return run, case, detection, verification, risk_decision


def baseline_fixture() -> StagingFixture:
    return StagingFixture(
        records=(
            {"product_id": "gpu-1", "title": "DGX Spark", "price": 599, "availability": "in_stock", "rating": 4.8, "url": "https://example.test/gpu-1"},
        ),
        metadata={"expected_price": 599, "expected_row_count": 1, "public": True},
    )


def extraction_contract() -> ExtractionContract:
    return ExtractionContract(
        contract_id="mutation-lab-gpu-price-v1",
        fields=(
            FieldContract("product_id", expected_types=(str,)),
            FieldContract("title", expected_types=(str,)),
            FieldContract("price", expected_types=(int, float)),
            FieldContract("availability", expected_types=(str,)),
            FieldContract("rating", expected_types=(int, float)),
            FieldContract("url", expected_types=(str,)),
        ),
        min_rows=1,
        max_rows=1,
        expected_row_count=1,
        numeric_bounds={"price": (0, None), "rating": (0, 5)},
        invariants=("valid_url", "price_non_negative"),
        expected_schema=("availability", "price", "product_id", "rating", "title", "url"),
    )


def _definitions() -> dict[str, MutationDefinition]:
    return {
        "M001": MutationDefinition("M001", MutationSeverity.L1, "Rename irrelevant CSS class", "NO_ALARM_EXPECTED", "baseline extraction remains correct", (), _m001),
        "M002": MutationDefinition("M002", MutationSeverity.L2, "Move availability node outside extraction target", "SCHEMA_ALARM_EXPECTED", "reject before output eligibility", ("availability",), _m002),
        "M003": MutationDefinition("M003", MutationSeverity.L3, "Change semantic price presentation to a negative value", "SEMANTIC_ALARM_EXPECTED", "reject before output eligibility", ("price",), _m003),
        "M004": MutationDefinition("M004", MutationSeverity.L4, "Drop deterministic second-page record", "STATISTICAL_ALARM_EXPECTED", "quarantine or reject incomplete behavior", ("row_count",), _m004),
        "M005": MutationDefinition("M005", MutationSeverity.L5, "Silent-corruption value swap", "VERIFICATION_ALARM_EXPECTED", "reject or quarantine; never ship bad price", ("price",), _m005),
        "M006": MutationDefinition("M006", MutationSeverity.L5, "Silent-corruption plausible decoy", "VERIFICATION_ALARM_EXPECTED", "reject or quarantine; never ship decoy", ("price",), _m006),
    }


def _m001(baseline: StagingFixture, seed: int) -> MutatedFixture:
    token = f"cosmetic-{random.Random(seed).randint(1000, 9999)}"
    return MutatedFixture("M001", seed, baseline, replace(baseline, page_markup=baseline.page_markup.replace("product-card", token)), {"mechanism": "rename_irrelevant_css_class", "class_token": token})


def _m002(baseline: StagingFixture, seed: int) -> MutatedFixture:
    rows = tuple(dict(row) for row in baseline.records)
    rows[0].pop("availability", None)
    return MutatedFixture("M002", seed, baseline, replace(baseline, records=tuple(rows)), {"mechanism": "move_field_node_outside_extraction_target", "field": "availability"})


def _m003(baseline: StagingFixture, seed: int) -> MutatedFixture:
    rows = tuple(dict(row) for row in baseline.records)
    rows[0]["price"] = -599
    return MutatedFixture("M003", seed, baseline, replace(baseline, records=tuple(rows)), {"mechanism": "semantic_presentation_change", "field": "price", "mutated_value": -599})


def _m004(baseline: StagingFixture, seed: int) -> MutatedFixture:
    return MutatedFixture("M004", seed, baseline, replace(baseline, records=baseline.records[:0], metadata={**baseline.metadata, "allow_empty": True}), {"mechanism": "deterministic_pagination_drop", "dropped_record": "gpu-1"})


def _m005(baseline: StagingFixture, seed: int) -> MutatedFixture:
    rows = tuple(dict(row) for row in baseline.records)
    rows[0]["price"] = 29.99
    return MutatedFixture("M005", seed, baseline, replace(baseline, records=tuple(rows)), {"mechanism": "value_swap", "expected_price": 599, "corrupted_price": 29.99})


def _m006(baseline: StagingFixture, seed: int) -> MutatedFixture:
    decoy = 549.99 + random.Random(seed).randint(0, 10)
    rows = tuple(dict(row) for row in baseline.records)
    rows[0]["price"] = round(decoy, 2)
    return MutatedFixture("M006", seed, baseline, replace(baseline, records=tuple(rows)), {"mechanism": "plausible_decoy", "expected_price": 599, "corrupted_price": round(decoy, 2)})


def _observation_from_fixture(fixture: StagingFixture, mutation_id: str, seed: int) -> Observation:
    return Observation(
        collection_id=f"mutation-collection-{mutation_id}-{seed}",
        collector_id="mutation-lab-test-double",
        provider_operation_ids={"mutation": f"TEST_DOUBLE-{mutation_id}-{seed}"},
        input={"target_url": "https://example.test/gpu-1", "fixture_id": fixture.fixture_id, "mutation_id": mutation_id, "seed": seed},
        output=fixture.records,
        schema=tuple(sorted({key for row in fixture.records for key in row})),
        row_count=len(fixture.records),
        latency_ms=1,
        collection_mode=CollectionMode.TEST_DOUBLE,
        provider_provenance=ProviderProvenance.TEST_DOUBLE,
        evidence_refs=(f"evidence://TEST_DOUBLE/mutation/{mutation_id}/{seed}",),
    )


def _candidate_from_observation(observation: Observation, mutation_id: str, seed: int) -> RepairCandidate:
    return RepairCandidate(
        repair_request_id=f"mutation-repair-request-{mutation_id}-{seed}",
        collector_reference=observation.collector_id,
        provider_operation_reference=f"mutation-operation-{mutation_id}-{seed}",
        provider_status="TEST_DOUBLE_COMPLETED",
        preview_result=observation.output,
        diff_summary=f"TEST_DOUBLE mutation {mutation_id}",
        approval_command="NOT_EXECUTED_TEST_DOUBLE_APPROVAL",
        raw_evidence_ref=f"evidence://TEST_DOUBLE/mutation/{mutation_id}/{seed}",
        provenance=ProviderProvenance.TEST_DOUBLE,
        latency_ms=1,
    )


def _outcome(detection: DetectionResult, verification: VerificationResult, risk: RiskDecision, quarantine_reference: str | None) -> MutationOutcome:
    if quarantine_reference or risk.decision is RiskDecisionType.QUARANTINE:
        return MutationOutcome.DETECTED_QUARANTINED
    if verification.overall_status is not VerificationOverallStatus.PASS or risk.decision is RiskDecisionType.REJECT:
        return MutationOutcome.DETECTED_REJECTED
    if detection.detected:
        return MutationOutcome.DETECTED_REJECTED
    return MutationOutcome.HEALTHY


def _elapsed_ms(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() * 1000))


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    from .immutability import freeze_mapping

    return freeze_mapping(value)


def _freeze_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return _freeze_mapping(row)
