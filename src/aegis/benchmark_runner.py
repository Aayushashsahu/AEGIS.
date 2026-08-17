"""Mission 012 common participant and benchmark-runner contract.

The runner is deliberately validation-first.  It can describe the common
execution boundary and normalize a controlled TEST_DOUBLE result, but its dry
run never executes a participant, provider operation, healing operation, or
metric calculation.  Mission 010 remains the sole metric authority.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from .audit_store import _to_jsonable
from .baseline_participants import BaselineAStaticExtractor, BaselineBConfiguration, BaselineBUnavailable, apply_first_candidate, baseline_b_model_call
from .benchmark_config import BenchmarkConfig, BaselineSpec, ValidationResult, validate_config
from .immutability import freeze_mapping
from .mutation_lab import MutationLab, MutationRun, MutationSeverity
from .models import ProviderProvenance
from .participant_freeze import proposal_from_spec, validate_participant_proposal


PARTICIPANT_IDS = ("BASELINE_A", "BASELINE_B", "AEGIS")
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_READY = "NOT_READY"


class ParticipantId(str, Enum):
    BASELINE_A = "BASELINE_A"
    BASELINE_B = "BASELINE_B"
    AEGIS = "AEGIS"


class ParticipantReadinessStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    NOT_READY_FOR_BENCHMARK = "NOT_READY_FOR_BENCHMARK"
    INVALID = "INVALID"


class RunnerState(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    INVALIDATED = "INVALIDATED"


class RunnerDryRunStatus(str, Enum):
    VALIDATION_ONLY = "VALIDATION_ONLY"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    BLOCKED_NOT_READY = "BLOCKED_NOT_READY"
    INVALID = "INVALID"


class ParticipantNotReady(RuntimeError):
    """Raised when an adapter is asked to execute before readiness is frozen."""


@dataclass(frozen=True)
class ParticipantReadiness:
    participant_id: str
    status: ParticipantReadinessStatus
    contract_ready: bool
    benchmark_ready: bool
    participant_revision: str
    participant_configuration_hash: str
    provenance: str
    checks: Mapping[str, str]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", freeze_mapping(self.checks))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def ready(self) -> bool:
        return self.status is ParticipantReadinessStatus.READY and self.contract_ready and self.benchmark_ready

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class ParticipantExecutionInput:
    """Identical evaluator input delivered to each participant."""

    benchmark_id: str
    configuration_hash: str
    participant_id: str
    mutation_id: str
    severity: str
    seed: int
    fixture_version: str
    ground_truth_reference: str
    code_revision: str
    environment_reference: str
    timeout_policy: Mapping[str, Any]
    retry_policy: Mapping[str, Any]
    artifact_root: str
    trial_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))
        object.__setattr__(self, "trial_metadata", freeze_mapping(self.trial_metadata))

    @property
    def run_id(self) -> str:
        return deterministic_run_id(self.participant_id, self.mutation_id, self.seed, self.configuration_hash)

    @property
    def artifact_name(self) -> str:
        return deterministic_artifact_name(self.participant_id, self.mutation_id, self.seed, self.configuration_hash)

    def shared_metadata(self) -> Mapping[str, Any]:
        """Return participant-independent metadata for fairness assertions."""

        return _to_jsonable(
            {
                "benchmark_id": self.benchmark_id,
                "configuration_hash": self.configuration_hash,
                "mutation_id": self.mutation_id,
                "severity": self.severity,
                "seed": self.seed,
                "fixture_version": self.fixture_version,
                "ground_truth_reference": self.ground_truth_reference,
                "code_revision": self.code_revision,
                "environment_reference": self.environment_reference,
                "timeout_policy": self.timeout_policy,
                "retry_policy": self.retry_policy,
                "artifact_root": self.artifact_root,
                "trial_metadata": self.trial_metadata,
            }
        )


@dataclass(frozen=True)
class PreparedParticipantRun:
    participant_id: str
    input: ParticipantExecutionInput
    state: RunnerState = RunnerState.READY
    artifact_reference: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_reference:
            object.__setattr__(self, "artifact_reference", f"{self.input.artifact_root}/{self.input.artifact_name}")


@dataclass(frozen=True)
class ParticipantRunEvidence:
    """Normalized raw evidence shared by all participants.

    Baselines use ``NOT_APPLICABLE`` for AEGIS-only concepts rather than
    inventing equivalents.  This record is raw evidence; it never calculates
    benchmark metrics.
    """

    participant_id: str
    run_id: str
    mutation_id: str
    severity: str
    seed: int
    fixture_version: str
    participant_revision: str
    configuration_hash: str
    ground_truth_reference: str
    code_revision: str
    environment_reference: str
    timeout_policy: Mapping[str, Any]
    retry_policy: Mapping[str, Any]
    artifact_root: str
    observation_reference: str
    detected: bool | str
    verification_status: str
    risk_decision: str
    output_eligible: bool | str
    failure_state: str
    timing_ms: Mapping[str, int]
    cost: int | float | str
    llm_calls: int | str
    evidence_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    provenance: str
    state: RunnerState = RunnerState.COMPLETED
    candidate_received: bool | str = NOT_APPLICABLE
    candidate_selected: bool | str = NOT_APPLICABLE
    candidate_accepted: bool | str = NOT_APPLICABLE
    candidate: Any = NOT_APPLICABLE
    candidate_application: Mapping[str, Any] | str = NOT_APPLICABLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))
        object.__setattr__(self, "timing_ms", freeze_mapping(self.timing_ms))
        if isinstance(self.candidate, Mapping):
            object.__setattr__(self, "candidate", freeze_mapping(self.candidate))
        elif isinstance(self.candidate, (list, tuple)):
            object.__setattr__(self, "candidate", tuple(self.candidate))
        if isinstance(self.candidate_application, Mapping):
            object.__setattr__(self, "candidate_application", freeze_mapping(self.candidate_application))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        object.__setattr__(self, "artifact_refs", tuple(dict.fromkeys(self.artifact_refs)))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class RunManifest:
    """Immutable planned-run manifest; it has no output/result payload."""

    benchmark_id: str
    configuration_hash: str
    participant_id: str
    participant_revision: str
    participant_configuration_hash: str
    mutation_id: str
    severity: str
    seed: int
    fixture_version: str
    ground_truth_reference: str
    code_revision: str
    environment_reference: str
    timeout_policy: Mapping[str, Any]
    retry_policy: Mapping[str, Any]
    artifact_root: str
    run_id: str
    artifact_name: str
    state: RunnerState = RunnerState.PLANNED

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class FreezeSnapshot:
    configuration_hash: str
    code_revision: str
    fixture_version: str
    mutation_class_ids: tuple[str, ...]
    mutation_severity: Mapping[str, str]
    seeds: tuple[int, ...]
    baseline_configuration_hashes: Mapping[str, str]
    metric_formula_version: str
    timeout_policy: Mapping[str, Any]
    retry_policy: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mutation_class_ids", tuple(self.mutation_class_ids))
        object.__setattr__(self, "mutation_severity", freeze_mapping(self.mutation_severity))
        object.__setattr__(self, "seeds", tuple(self.seeds))
        object.__setattr__(self, "baseline_configuration_hashes", freeze_mapping(self.baseline_configuration_hashes))
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))

    @classmethod
    def from_config(cls, config: BenchmarkConfig) -> "FreezeSnapshot":
        return cls(
            configuration_hash=config.configuration_hash,
            code_revision=config.code_revision,
            fixture_version=config.fixture_version,
            mutation_class_ids=config.mutation_class_ids,
            mutation_severity=config.mutation_severity,
            seeds=config.seeds,
            baseline_configuration_hashes={baseline.baseline_id: baseline.configuration_hash for baseline in config.baselines},
            metric_formula_version=config.metric_formula_version,
            timeout_policy=config.timeout_policy,
            retry_policy=config.retry_policy,
        )


@dataclass(frozen=True)
class FreezeValidation:
    valid: bool
    errors: tuple[str, ...]
    checks: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "checks", freeze_mapping(self.checks))


@dataclass(frozen=True)
class ExecutionAttempt:
    state: RunnerState
    manifest: RunManifest
    evidence: ParticipantRunEvidence | None
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))


@dataclass(frozen=True)
class RunnerDryRunResult:
    status: RunnerDryRunStatus
    validation: ValidationResult
    freeze_validation: FreezeValidation
    participant_readiness: Mapping[str, ParticipantReadiness]
    fixture_checks: Mapping[str, str]
    seed_checks: Mapping[str, str]
    plan: tuple[RunManifest, ...]
    expected_run_count: int
    participant_count: int
    mutation_count: int
    seed_count: int
    metric_calculator_available: bool
    benchmark_runs_executed: int = 0
    provider_operations_executed: int = 0
    healing_operations_executed: int = 0
    metric_results_generated: int = 0
    execution_authorized: bool = False
    generated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "participant_readiness", freeze_mapping(self.participant_readiness))
        object.__setattr__(self, "fixture_checks", freeze_mapping(self.fixture_checks))
        object.__setattr__(self, "seed_checks", freeze_mapping(self.seed_checks))
        object.__setattr__(self, "plan", tuple(self.plan))

    @property
    def valid(self) -> bool:
        return self.status in {RunnerDryRunStatus.VALIDATION_ONLY, RunnerDryRunStatus.READY_TO_EXECUTE}

    @property
    def blocked_not_ready(self) -> bool:
        return self.status is RunnerDryRunStatus.BLOCKED_NOT_READY

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(
            {
                "runner_version": "mission-012-runner-v1",
                "status": self.status.value,
                "validation_only": True,
                "notice": "VALIDATION ONLY — NO BENCHMARK EXECUTED",
                "validation": self.validation,
                "freeze_validation": self.freeze_validation,
                "participant_readiness": self.participant_readiness,
                "fixture_checks": self.fixture_checks,
                "seed_checks": self.seed_checks,
                "plan": self.plan,
                "expected_run_count": self.expected_run_count,
                "participant_count": self.participant_count,
                "mutation_count": self.mutation_count,
                "seed_count": self.seed_count,
                "metric_calculator_available": self.metric_calculator_available,
                "benchmark_runs_executed": self.benchmark_runs_executed,
                "provider_operations_executed": self.provider_operations_executed,
                "healing_operations_executed": self.healing_operations_executed,
                "metric_results_generated": self.metric_results_generated,
                "execution_authorized": self.execution_authorized,
                "generated_at": self.generated_at,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"

    def render(self) -> str:
        return "\n".join(
            (
                "VALIDATION ONLY",
                "NO BENCHMARK EXECUTED",
                f"status={self.status.value}",
                f"expected_run_count={self.expected_run_count}",
                f"benchmark_runs_executed={self.benchmark_runs_executed}",
                f"provider_operations_executed={self.provider_operations_executed}",
                f"healing_operations_executed={self.healing_operations_executed}",
                f"metric_results_generated={self.metric_results_generated}",
                f"execution_authorized={self.execution_authorized}",
            )
        ) + "\n"


class ParticipantAdapter(Protocol):
    participant_id: str

    def readiness(self, config: BenchmarkConfig) -> ParticipantReadiness:
        ...

    def prepare(self, execution_input: ParticipantExecutionInput) -> PreparedParticipantRun:
        ...

    def run_mutation(self, prepared: PreparedParticipantRun) -> ParticipantRunEvidence:
        ...

    def collect_result(self, result: ParticipantRunEvidence) -> ParticipantRunEvidence:
        ...

    def return_run_evidence(self, result: ParticipantRunEvidence) -> ParticipantRunEvidence:
        ...


class _BaseAdapter:
    provenance = ProviderProvenance.TEST_DOUBLE.value

    def __init__(self, spec: BaselineSpec, lab: MutationLab | None = None) -> None:
        self.spec = spec
        self._lab = lab or MutationLab()
        self.participant_id = spec.baseline_id
        self._benchmark_config: BenchmarkConfig | None = None

    def prepare(self, execution_input: ParticipantExecutionInput) -> PreparedParticipantRun:
        _validate_input_against_lab(execution_input, self._lab)
        report = self.readiness_for_execution()
        if not report.contract_ready:
            raise ParticipantNotReady(f"{self.participant_id} contract is not ready: {report.errors}")
        return PreparedParticipantRun(self.participant_id, execution_input)

    def readiness_for_execution(self) -> ParticipantReadiness:
        raise NotImplementedError

    def collect_result(self, result: ParticipantRunEvidence) -> ParticipantRunEvidence:
        return result

    def return_run_evidence(self, result: ParticipantRunEvidence) -> ParticipantRunEvidence:
        return result


class BaselineAAdapter(_BaseAdapter):
    """Static extraction adapter with no AEGIS trust-evaluation controls."""

    def readiness(self, config: BenchmarkConfig) -> ParticipantReadiness:
        contract_checks = {
            "mutation_coverage": "PASS" if tuple(self._lab.mutation_ids) == tuple(config.mutation_class_ids) else "FAIL",
            "normalization": "PASS",
            "timeout_policy": "PASS" if config.timeout_policy else "FAIL",
            "retry_policy": "PASS" if config.retry_policy else "FAIL",
            "artifact_format": "PASS",
            "aegis_detection": "NOT_USED",
            "aegis_verification": "NOT_USED",
            "risk_governor": "NOT_USED",
            "commit_gate": "NOT_USED",
            "provenance": "PASS_TEST_DOUBLE",
        }
        errors = [name for name, value in contract_checks.items() if value == "FAIL"]
        slot_ready = self.spec.status == "READY"
        if not slot_ready:
            errors.append("frozen baseline slot is NOT_READY")
        else:
            reviewed = validate_participant_proposal(proposal_from_spec(self.spec))
            contract_checks["reviewed_metadata"] = "PASS" if reviewed.ready else "FAIL"
            errors.extend(reviewed.errors)
        contract_ready = not any(value == "FAIL" for value in contract_checks.values())
        return ParticipantReadiness(
            participant_id=self.participant_id,
            status=ParticipantReadinessStatus.READY if slot_ready and contract_ready and not errors else ParticipantReadinessStatus.NOT_READY,
            contract_ready=contract_ready,
            benchmark_ready=slot_ready and contract_ready and not errors,
            participant_revision=self.spec.implementation_revision,
            participant_configuration_hash=self.spec.configuration_hash,
            provenance=self.provenance,
            checks=contract_checks,
            errors=tuple(errors),
            warnings=("Baseline A has no healing, AEGIS verification, RiskGovernor, or CommitGate path.",),
        )

    def readiness_for_execution(self) -> ParticipantReadiness:
        ready = self.spec.status == "READY" and all(
            isinstance(value, str) and value.strip() and value not in {"TBD", "UNKNOWN", "NOT_READY"}
            for value in (self.spec.implementation_revision, self.spec.configuration_hash)
        )
        return ParticipantReadiness(
            participant_id=self.participant_id,
            status=ParticipantReadinessStatus.READY if ready else ParticipantReadinessStatus.NOT_READY,
            contract_ready=True,
            benchmark_ready=ready,
            participant_revision=self.spec.implementation_revision,
            participant_configuration_hash=self.spec.configuration_hash,
            provenance=self.provenance,
            checks={"static_contract": "PASS", "aegis_controls": "NOT_USED"},
            errors=() if ready else ("frozen baseline slot is NOT_READY",),
        )

    def run_mutation(self, prepared: PreparedParticipantRun) -> ParticipantRunEvidence:
        case = self._lab.apply_mutation(prepared.input.mutation_id, prepared.input.seed)
        extracted = BaselineAStaticExtractor().extract(case.mutated.fixture)
        artifact = f"{prepared.input.artifact_root}/{prepared.input.artifact_name}"
        observation_ref = f"{artifact}#observation"
        return ParticipantRunEvidence(
            participant_id=self.participant_id,
            run_id=prepared.input.run_id,
            mutation_id=prepared.input.mutation_id,
            severity=prepared.input.severity,
            seed=prepared.input.seed,
            fixture_version=prepared.input.fixture_version,
            participant_revision=prepared.input.code_revision,
            configuration_hash=prepared.input.configuration_hash,
            ground_truth_reference=prepared.input.ground_truth_reference,
            code_revision=prepared.input.code_revision,
            environment_reference=prepared.input.environment_reference,
            timeout_policy=prepared.input.timeout_policy,
            retry_policy=prepared.input.retry_policy,
            artifact_root=prepared.input.artifact_root,
            observation_reference=observation_ref,
            detected=NOT_APPLICABLE,
            verification_status=NOT_APPLICABLE,
            risk_decision=NOT_APPLICABLE,
            output_eligible=NOT_APPLICABLE,
            failure_state="COMPLETED",
            timing_ms={"collection": 0, "total": 0},
            cost=NOT_APPLICABLE,
            llm_calls=0,
            evidence_refs=(prepared.input.ground_truth_reference, f"{artifact}#output"),
            artifact_refs=(artifact,),
            provenance=self.provenance,
        )


class BaselineBAdapter(_BaseAdapter):
    """Approved naive Gemini first-candidate baseline with an injected caller seam."""

    def __init__(self, spec: BaselineSpec, lab: MutationLab | None = None, *, model_caller: Any | None = None) -> None:
        super().__init__(spec, lab)
        self.configuration = BaselineBConfiguration()
        self._model_caller = model_caller

    def readiness(self, config: BenchmarkConfig) -> ParticipantReadiness:
        fields = {
            "model_id": self.spec.model_id,
            "prompt_revision": self.spec.prompt_revision,
            "model_configuration": config.model_configuration,
            "execution_policy": self.spec.execution_policy,
            "retry_policy": self.spec.retry_policy,
            "implementation_revision": self.spec.implementation_revision,
            "configuration_hash": self.spec.configuration_hash,
        }
        checks: dict[str, str] = {}
        errors: list[str] = []
        for name, value in fields.items():
            missing = value in (None, "", "TBD", "UNKNOWN", "NOT_READY", "NOT_APPLICABLE") or value == {}
            checks[name] = "FAIL" if missing else "PASS"
            if missing:
                errors.append(f"missing {name}")
        checks["aegis_verification"] = "NOT_USED"
        checks["risk_governor"] = "NOT_USED"
        checks["commit_gate"] = "NOT_USED"
        checks["provenance"] = "PASS_TEST_DOUBLE"
        if self.spec.status == "READY":
            reviewed = validate_participant_proposal(proposal_from_spec(self.spec))
            checks["reviewed_metadata"] = "PASS" if reviewed.ready else "FAIL"
            errors.extend(reviewed.errors)
        return ParticipantReadiness(
            participant_id=self.participant_id,
            status=ParticipantReadinessStatus.READY if not errors and self.spec.status == "READY" else ParticipantReadinessStatus.NOT_READY,
            contract_ready=not errors,
            benchmark_ready=not errors and self.spec.status == "READY",
            participant_revision=self.spec.implementation_revision,
            participant_configuration_hash=self.spec.configuration_hash,
            provenance=self.provenance,
            checks=checks,
            errors=tuple(errors) if errors else ("frozen baseline slot is NOT_READY",),
            warnings=("Baseline B cannot choose a model, prompt, or first-candidate policy automatically.",),
        )

    def readiness_for_execution(self) -> ParticipantReadiness:
        if self._benchmark_config is None:
            raise ParticipantNotReady("Baseline B requires an attached frozen BenchmarkConfig")
        readiness = self.readiness(self._benchmark_config)
        if not readiness.ready:
            raise ParticipantNotReady(f"Baseline B is not executable: {readiness.errors}")
        return readiness

    def run_mutation(self, prepared: PreparedParticipantRun) -> ParticipantRunEvidence:
        case = self._lab.apply_mutation(prepared.input.mutation_id, prepared.input.seed)
        repair_prompt = self.configuration.repair_prompt_template.format(
            target="https://example.test/gpu-1",
            extraction_contract="gpu-price-schema-v1",
            observed_output=repr(case.mutated.fixture.records),
            failure_description=f"controlled mutation {prepared.input.mutation_id}",
            scraper_source="approved static selector scraper configuration",
        )
        model_result = baseline_b_model_call(
            self.configuration,
            caller=self._model_caller,
            system_prompt=self.configuration.system_prompt,
            repair_prompt=repair_prompt,
        )
        artifact = f"{prepared.input.artifact_root}/{prepared.input.artifact_name}"
        unavailable = isinstance(model_result, BaselineBUnavailable)
        if unavailable:
            candidate_execution = None
            failure_state = model_result.reason
            candidate_received = False
            candidate_selected = False
            candidate_accepted = False
            candidate = NOT_APPLICABLE
            candidate_application = NOT_APPLICABLE
            output_eligible: bool | str = NOT_APPLICABLE
        else:
            candidate_execution = apply_first_candidate(self.configuration, model_result, case.mutated.fixture)
            failure_state = candidate_execution.failure_state
            candidate_received = candidate_execution.candidate_received
            candidate_selected = candidate_execution.candidate_selected
            candidate_accepted = candidate_execution.candidate_accepted
            candidate = candidate_execution.candidate
            candidate_application = candidate_execution.application or NOT_APPLICABLE
            output_eligible = candidate_accepted
        evidence_refs = [prepared.input.ground_truth_reference, f"{artifact}#model-output"]
        if candidate_received:
            evidence_refs.append(f"{artifact}#candidate-received")
        if candidate_selected:
            evidence_refs.append(f"{artifact}#candidate-selected")
        if candidate_accepted:
            evidence_refs.append(f"{artifact}#candidate-accepted")
        return ParticipantRunEvidence(
            participant_id=self.participant_id,
            run_id=prepared.input.run_id,
            mutation_id=prepared.input.mutation_id,
            severity=prepared.input.severity,
            seed=prepared.input.seed,
            fixture_version=prepared.input.fixture_version,
            participant_revision=prepared.input.code_revision,
            configuration_hash=prepared.input.configuration_hash,
            ground_truth_reference=prepared.input.ground_truth_reference,
            code_revision=prepared.input.code_revision,
            environment_reference=prepared.input.environment_reference,
            timeout_policy=prepared.input.timeout_policy,
            retry_policy=prepared.input.retry_policy,
            artifact_root=prepared.input.artifact_root,
            observation_reference=f"{artifact}#observation",
            detected=NOT_APPLICABLE,
            verification_status=NOT_APPLICABLE,
            risk_decision=NOT_APPLICABLE,
            output_eligible=output_eligible,
            failure_state=failure_state,
            timing_ms={"collection": 0, "model": 0, "total": 0},
            cost=NOT_APPLICABLE,
            llm_calls=0 if unavailable else 1,
            evidence_refs=tuple(evidence_refs),
            artifact_refs=(artifact,),
            provenance=self.configuration.provenance,
            candidate_received=candidate_received,
            candidate_selected=candidate_selected,
            candidate_accepted=candidate_accepted,
            candidate=candidate,
            candidate_application=candidate_application,
        )


class AegisAdapter(_BaseAdapter):
    """AEGIS TEST_DOUBLE adapter using the existing Mission 009 lifecycle."""

    participant_configuration_version = "aegis-benchmark-v1"
    participant_adapter_name = "AegisAdapter"
    participant_normalization = "canonical-participant-run-v1"
    participant_artifact_schema = "participant-run-evidence-v1"
    participant_metric_formula_version = "mission-010-metrics-v1"

    def readiness(self, config: BenchmarkConfig) -> ParticipantReadiness:
        checks = {
            "mutation_coverage": "PASS" if tuple(self._lab.mutation_ids) == tuple(config.mutation_class_ids) else "FAIL",
            "normalization": "PASS",
            "test_double_provenance": "PASS",
            "detection": "PASS",
            "verification": "PASS",
            "risk": "PASS",
            "commit_gate": "PASS",
            "metric_calculator": "AVAILABLE_INTERFACE_ONLY",
        }
        errors = [name for name, value in checks.items() if value == "FAIL"]
        if self.spec.status == "READY":
            reviewed = validate_participant_proposal(proposal_from_spec(self.spec))
            checks["reviewed_metadata"] = "PASS" if reviewed.ready else "FAIL"
            errors.extend(reviewed.errors)
        slot_ready = self.spec.status == "READY" and self.spec.configuration_hash not in {"", "TBD", "UNKNOWN", "NOT_READY"}
        if not slot_ready:
            errors.append("AEGIS benchmark slot is NOT_READY_FOR_BENCHMARK")
        contract_ready = not any(value == "FAIL" for value in checks.values())
        return ParticipantReadiness(
            participant_id=self.participant_id,
            status=ParticipantReadinessStatus.READY if slot_ready and contract_ready else ParticipantReadinessStatus.NOT_READY_FOR_BENCHMARK,
            contract_ready=contract_ready,
            benchmark_ready=slot_ready and contract_ready,
            participant_revision=self.spec.implementation_revision,
            participant_configuration_hash=self.spec.configuration_hash,
            provenance=self.provenance,
            checks=checks,
            errors=tuple(errors),
            warnings=("TEST_DOUBLE lifecycle normalization is available; benchmark execution remains blocked.",),
        )

    def readiness_for_execution(self) -> ParticipantReadiness:
        return ParticipantReadiness(
            participant_id=self.participant_id,
            status=ParticipantReadinessStatus.READY,
            contract_ready=True,
            benchmark_ready=False,
            participant_revision=self.spec.implementation_revision,
            participant_configuration_hash=self.spec.configuration_hash,
            provenance=self.provenance,
            checks={"test_double_lifecycle": "PASS", "benchmark_activation": "NOT_READY_FOR_BENCHMARK"},
            warnings=("Direct TEST_DOUBLE contract validation is allowed; BenchmarkRunner execution remains blocked.",),
        )

    def run_mutation(self, prepared: PreparedParticipantRun) -> ParticipantRunEvidence:
        run, _case, _detection, _verification, _risk = self._lab.run(prepared.input.mutation_id, prepared.input.seed)
        return normalize_mutation_run(run, prepared.input, participant_revision=prepared.input.code_revision)


def normalize_mutation_run(run: MutationRun, execution_input: ParticipantExecutionInput, *, participant_revision: str | None = None) -> ParticipantRunEvidence:
    """Project an existing AEGIS TEST_DOUBLE MutationRun into common evidence."""

    artifact = f"{execution_input.artifact_root}/{execution_input.artifact_name}"
    return ParticipantRunEvidence(
        participant_id=ParticipantId.AEGIS.value,
        run_id=execution_input.run_id,
        mutation_id=execution_input.mutation_id,
        severity=execution_input.severity,
        seed=execution_input.seed,
        fixture_version=execution_input.fixture_version,
        participant_revision=participant_revision or execution_input.code_revision,
        configuration_hash=execution_input.configuration_hash,
        ground_truth_reference=execution_input.ground_truth_reference,
        code_revision=execution_input.code_revision,
        environment_reference=execution_input.environment_reference,
        timeout_policy=execution_input.timeout_policy,
        retry_policy=execution_input.retry_policy,
        artifact_root=execution_input.artifact_root,
        observation_reference=run.observation_reference,
        detected=run.detected,
        verification_status=run.verification_status,
        risk_decision=run.risk_decision,
        output_eligible=run.output_eligible,
        failure_state="COMPLETED",
        timing_ms=run.timing_ms,
        cost=NOT_APPLICABLE,
        llm_calls=0,
        evidence_refs=(execution_input.ground_truth_reference, *run.evidence_refs),
        artifact_refs=(artifact,),
        provenance=run.provenance.value if hasattr(run.provenance, "value") else str(run.provenance),
    )


class ParticipantRegistry:
    def __init__(self, config: BenchmarkConfig, lab: MutationLab | None = None) -> None:
        specs = {spec.baseline_id: spec for spec in config.baselines}
        self._adapters: Mapping[str, ParticipantAdapter] = {
            ParticipantId.BASELINE_A.value: BaselineAAdapter(specs[ParticipantId.BASELINE_A.value], lab),
            ParticipantId.BASELINE_B.value: BaselineBAdapter(specs[ParticipantId.BASELINE_B.value], lab),
            ParticipantId.AEGIS.value: AegisAdapter(specs[ParticipantId.AEGIS.value], lab),
        }
        for adapter in self._adapters.values():
            if isinstance(adapter, _BaseAdapter):
                adapter._benchmark_config = config

    def all(self) -> tuple[ParticipantAdapter, ...]:
        return tuple(self._adapters[participant_id] for participant_id in PARTICIPANT_IDS)

    def get(self, participant_id: str) -> ParticipantAdapter:
        return self._adapters[participant_id]

    def readiness(self, config: BenchmarkConfig) -> Mapping[str, ParticipantReadiness]:
        return {participant_id: self._adapters[participant_id].readiness(config) for participant_id in PARTICIPANT_IDS}


class BenchmarkRunner:
    """Common raw-evidence runner with explicit validation-only dry-run."""

    def __init__(self, config: BenchmarkConfig, *, registry: ParticipantRegistry | None = None, lab: MutationLab | None = None) -> None:
        self.config = config
        self.lab = lab or MutationLab()
        self.registry = registry or ParticipantRegistry(config, self.lab)

    def build_input(self, participant_id: str, mutation_id: str, seed: int) -> ParticipantExecutionInput:
        if participant_id not in PARTICIPANT_IDS:
            raise ValueError(f"unknown participant: {participant_id}")
        return ParticipantExecutionInput(
            benchmark_id=self.config.benchmark_id,
            configuration_hash=self.config.configuration_hash,
            participant_id=participant_id,
            mutation_id=mutation_id,
            severity=self.config.mutation_severity[mutation_id],
            seed=seed,
            fixture_version=self.config.fixture_version,
            ground_truth_reference=planned_ground_truth_reference(self.config, mutation_id, seed),
            code_revision=self.config.code_revision,
            environment_reference=self.config.environment_reference,
            timeout_policy=self.config.timeout_policy,
            retry_policy=self.config.retry_policy,
            artifact_root=self.config.artifact_root,
            trial_metadata={
                "baseline_independent": True,
                "ground_truth_runtime_payload": "NOT_PROVIDED",
                "metric_calculation": "DOWNSTREAM_MISSION_010_ONLY",
            },
        )

    def plan(self) -> tuple[RunManifest, ...]:
        manifests: list[RunManifest] = []
        for participant_id in PARTICIPANT_IDS:
            readiness = self.registry.get(participant_id).readiness(self.config)
            for mutation_id in sorted(self.config.mutation_class_ids):
                for seed in sorted(self.config.seeds):
                    execution_input = self.build_input(participant_id, mutation_id, seed)
                    manifests.append(
                        RunManifest(
                            benchmark_id=execution_input.benchmark_id,
                            configuration_hash=execution_input.configuration_hash,
                            participant_id=participant_id,
                            participant_revision=readiness.participant_revision,
                            participant_configuration_hash=readiness.participant_configuration_hash,
                            mutation_id=execution_input.mutation_id,
                            severity=execution_input.severity,
                            seed=execution_input.seed,
                            fixture_version=execution_input.fixture_version,
                            ground_truth_reference=execution_input.ground_truth_reference,
                            code_revision=execution_input.code_revision,
                            environment_reference=execution_input.environment_reference,
                            timeout_policy=execution_input.timeout_policy,
                            retry_policy=execution_input.retry_policy,
                            artifact_root=execution_input.artifact_root,
                            run_id=execution_input.run_id,
                            artifact_name=execution_input.artifact_name,
                            state=RunnerState.PLANNED,
                        )
                    )
        return tuple(manifests)

    def dry_run(self) -> RunnerDryRunResult:
        validation = validate_config(self.config)
        freeze_validation = validate_freeze(self.config, FreezeSnapshot.from_config(self.config))
        readiness = self.registry.readiness(self.config) if validation.valid else {}
        fixture_checks, seed_checks = _deterministic_fixture_checks(self.config, self.lab) if validation.valid else ({}, {})
        plan = self.plan() if validation.valid else ()
        metric_available = _metric_calculator_available()
        if not validation.valid or not freeze_validation.valid:
            status = RunnerDryRunStatus.INVALID
        elif any(not report.ready for report in readiness.values()):
            status = RunnerDryRunStatus.BLOCKED_NOT_READY
        else:
            status = RunnerDryRunStatus.READY_TO_EXECUTE
        return RunnerDryRunResult(
            status=status,
            validation=validation,
            freeze_validation=freeze_validation,
            participant_readiness=readiness,
            fixture_checks=fixture_checks,
            seed_checks=seed_checks,
            plan=plan,
            expected_run_count=len(plan),
            participant_count=len(PARTICIPANT_IDS),
            mutation_count=len(self.config.mutation_class_ids),
            seed_count=len(self.config.seeds),
            metric_calculator_available=metric_available,
        )

    def execute_one(self, participant_id: str, mutation_id: str, seed: int, snapshot: FreezeSnapshot | None = None) -> ExecutionAttempt:
        """Explicit single-run boundary; dry_run never calls this method."""

        snapshot = snapshot or FreezeSnapshot.from_config(self.config)
        freeze_validation = validate_freeze(self.config, snapshot)
        adapter = self.registry.get(participant_id)
        readiness = adapter.readiness(self.config)
        execution_input = self.build_input(participant_id, mutation_id, seed)
        manifest = next(item for item in self.plan() if item.run_id == execution_input.run_id)
        if not freeze_validation.valid:
            return ExecutionAttempt(RunnerState.INVALIDATED, manifest, None, freeze_validation.errors)
        if not readiness.ready:
            return ExecutionAttempt(RunnerState.INVALIDATED, manifest, None, readiness.errors)
        try:
            prepared = adapter.prepare(execution_input)
            evidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
        except TimeoutError as exc:
            return ExecutionAttempt(RunnerState.TIMED_OUT, manifest, None, (str(exc),))
        except Exception as exc:  # explicit terminal evidence boundary
            return ExecutionAttempt(RunnerState.FAILED, manifest, None, (str(exc),))
        return ExecutionAttempt(RunnerState.COMPLETED, manifest, evidence)


def validate_freeze(config: BenchmarkConfig, snapshot: FreezeSnapshot) -> FreezeValidation:
    errors: list[str] = []
    checks: dict[str, str] = {}
    expected = FreezeSnapshot.from_config(config)
    comparisons = {
        "configuration_hash": (snapshot.configuration_hash, expected.configuration_hash),
        "code_revision": (snapshot.code_revision, expected.code_revision),
        "fixture_version": (snapshot.fixture_version, expected.fixture_version),
        "mutation_class_ids": (snapshot.mutation_class_ids, expected.mutation_class_ids),
        "mutation_severity": (snapshot.mutation_severity, expected.mutation_severity),
        "seeds": (snapshot.seeds, expected.seeds),
        "baseline_configuration_hashes": (snapshot.baseline_configuration_hashes, expected.baseline_configuration_hashes),
        "metric_formula_version": (snapshot.metric_formula_version, expected.metric_formula_version),
        "timeout_policy": (snapshot.timeout_policy, expected.timeout_policy),
        "retry_policy": (snapshot.retry_policy, expected.retry_policy),
    }
    for name, (actual, wanted) in comparisons.items():
        checks[name] = "PASS" if actual == wanted else "FAIL"
        if actual != wanted:
            errors.append(f"freeze mismatch: {name}")
    return FreezeValidation(valid=not errors, errors=tuple(errors), checks=checks)


def planned_ground_truth_reference(config: BenchmarkConfig, mutation_id: str, seed: int) -> str:
    return f"ground-truth://{config.fixture_id}/v{config.fixture_version}/{mutation_id}/{seed}"


def deterministic_run_id(participant_id: str, mutation_id: str, seed: int, configuration_hash: str) -> str:
    digest = hashlib.sha256(f"{participant_id}|{mutation_id}|{seed}|{configuration_hash}".encode("utf-8")).hexdigest()[:16]
    return f"benchmark_run_{participant_id.lower()}_{mutation_id.lower()}_{seed}_{digest}"


def deterministic_artifact_name(participant_id: str, mutation_id: str, seed: int, configuration_hash: str) -> str:
    digest = hashlib.sha256(f"{participant_id}|{mutation_id}|{seed}|{configuration_hash}".encode("utf-8")).hexdigest()[:12]
    return f"{participant_id.lower()}__{mutation_id.lower()}__seed-{seed}__{digest}.json"


def _validate_input_against_lab(execution_input: ParticipantExecutionInput, lab: MutationLab) -> None:
    if execution_input.mutation_id not in lab.mutation_ids:
        raise ValueError(f"unknown mutation ID: {execution_input.mutation_id}")
    if execution_input.fixture_version != lab.fixture.fixture_version:
        raise ValueError("fixture version mismatch")
    if execution_input.severity != lab.definition(execution_input.mutation_id).severity.value:
        raise ValueError("mutation severity mismatch")


def _deterministic_fixture_checks(config: BenchmarkConfig, lab: MutationLab) -> tuple[Mapping[str, str], Mapping[str, str]]:
    fixture_checks: dict[str, str] = {}
    seed_checks: dict[str, str] = {}
    for mutation_id in sorted(config.mutation_class_ids):
        fixture_checks[mutation_id] = "PASS" if mutation_id in lab.mutation_ids else "FAIL"
        for seed in sorted(config.seeds):
            first = lab.apply_mutation(mutation_id, seed)
            second = lab.apply_mutation(mutation_id, seed)
            same = (
                first.mutated.fixture == second.mutated.fixture
                and first.ground_truth.expected_correct_state == second.ground_truth.expected_correct_state
                and first.ground_truth.expected_corrupted_state == second.ground_truth.expected_corrupted_state
            )
            seed_checks[f"{mutation_id}:{seed}"] = "PASS" if same else "FAIL"
    return fixture_checks, seed_checks


def _metric_calculator_available() -> bool:
    module = importlib.import_module("aegis.mutation_metrics")
    return callable(getattr(module, "calculate_metrics", None))
