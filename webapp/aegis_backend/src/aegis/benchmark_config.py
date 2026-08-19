"""Mission 011 benchmark configuration freeze and validation-only dry run.

This module defines the experiment contract without executing a benchmark. It
reuses Mission 009's MutationLab as the fixture/truth authority and Mission
010's metric formula version/calculator boundary. No provider, healing, repair,
commit, rollback, or metric calculation is invoked by a dry run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .audit_store import _to_jsonable
from .immutability import freeze_mapping
from .mutation_lab import MutationLab, MutationSeverity
from .mutation_metrics import FORMULA_VERSION


BENCHMARK_CONFIG_VERSION = "mission-011-benchmark-config-v1"
DRY_RUN_VERSION = "mission-011-dry-run-v1"
DEFAULT_CREATED_AT = "2026-08-17T00:00:00+00:00"
REQUIRED_MUTATION_IDS = ("M001", "M002", "M003", "M004", "M005", "M006")
REQUIRED_BASELINE_IDS = ("BASELINE_A", "BASELINE_B", "AEGIS")
VALID_BASELINE_STATUSES = ("READY", "NOT_READY", "UNKNOWN", "UNAVAILABLE")
VALID_SEVERITIES = tuple(level.value for level in MutationSeverity)


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class DryRunStatus(str, Enum):
    VALIDATION_ONLY = "VALIDATION_ONLY"
    INVALID = "INVALID"


@dataclass(frozen=True)
class BaselineSpec:
    """An immutable benchmark baseline slot; it contains no run result."""

    baseline_id: str
    description: str
    implementation_revision: str
    model_id: str
    prompt_revision: str
    configuration_hash: str
    execution_policy: str
    retry_policy: Mapping[str, Any]
    verification_policy: str
    commit_policy: str
    status: str = "NOT_READY"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


@dataclass(frozen=True)
class BenchmarkConfig:
    """Immutable benchmark definition and freeze metadata."""

    benchmark_id: str
    benchmark_version: str
    fixture_id: str
    fixture_version: str
    mutation_class_ids: tuple[str, ...]
    mutation_severity: Mapping[str, str]
    seeds: tuple[int, ...]
    trial_count: int
    baselines: tuple[BaselineSpec, ...]
    code_revision: str
    repository_revision: str
    repository_state: str
    environment_reference: str
    runtime_reference: str
    model_identifier: str
    model_configuration: Mapping[str, Any]
    prompt_version: str
    retry_policy: Mapping[str, Any]
    timeout_policy: Mapping[str, Any]
    collection_policy: Mapping[str, Any]
    evidence_policy: Mapping[str, Any]
    artifact_contract: Mapping[str, str]
    artifact_root: str
    metric_formula_version: str
    created_at: str
    configuration_hash: str = ""
    config_version: str = BENCHMARK_CONFIG_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "mutation_class_ids", tuple(self.mutation_class_ids))
        object.__setattr__(self, "mutation_severity", freeze_mapping(self.mutation_severity))
        object.__setattr__(self, "seeds", tuple(self.seeds))
        object.__setattr__(self, "baselines", tuple(self.baselines))
        object.__setattr__(self, "model_configuration", freeze_mapping(self.model_configuration))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "collection_policy", freeze_mapping(self.collection_policy))
        object.__setattr__(self, "evidence_policy", freeze_mapping(self.evidence_policy))
        object.__setattr__(self, "artifact_contract", freeze_mapping(self.artifact_contract))
        if not self.configuration_hash:
            object.__setattr__(self, "configuration_hash", compute_configuration_hash(self))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BenchmarkConfig":
        data = dict(payload)
        raw_baselines = data.pop("baselines", data.pop("baseline_specs", ()))
        data["baselines"] = tuple(
            BaselineSpec(
                baseline_id=item["baseline_id"],
                description=item["description"],
                implementation_revision=item["implementation_revision"],
                model_id=item["model_id"],
                prompt_revision=item["prompt_revision"],
                configuration_hash=item["configuration_hash"],
                execution_policy=item["execution_policy"],
                retry_policy=item["retry_policy"],
                verification_policy=item["verification_policy"],
                commit_policy=item["commit_policy"],
                status=item.get("status", "NOT_READY"),
                metadata=item.get("metadata", {}),
            )
            for item in raw_baselines
        )
        data["mutation_class_ids"] = tuple(data.get("mutation_class_ids", ()))
        data["seeds"] = tuple(data.get("seeds", ()))
        return cls(**data)


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: Mapping[str, str]
    configuration_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "checks", freeze_mapping(self.checks))

    @property
    def valid(self) -> bool:
        return self.status is ValidationStatus.VALID


@dataclass(frozen=True)
class DryRunResult:
    status: DryRunStatus
    validation: ValidationResult
    benchmark_id: str
    configuration_hash: str
    fixture_checks: Mapping[str, str]
    seed_checks: Mapping[str, str]
    baseline_checks: Mapping[str, str]
    metric_calculator_available: bool
    artifact_path_check: str
    execution_plan: tuple[Mapping[str, Any], ...]
    expected_run_count: int
    mutation_count: int
    seed_count: int
    baseline_count: int
    benchmark_runs_executed: int = 0
    provider_operations_executed: int = 0
    healing_operations_executed: int = 0
    metric_values_generated: int = 0
    benchmark_execution_authorized: bool = False
    generated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixture_checks", freeze_mapping(self.fixture_checks))
        object.__setattr__(self, "seed_checks", freeze_mapping(self.seed_checks))
        object.__setattr__(self, "baseline_checks", freeze_mapping(self.baseline_checks))
        object.__setattr__(self, "execution_plan", tuple(freeze_mapping(step) for step in self.execution_plan))

    @property
    def valid(self) -> bool:
        return self.status is DryRunStatus.VALIDATION_ONLY and self.validation.valid

    def to_dict(self) -> Mapping[str, Any]:
        payload = {
            "dry_run_version": DRY_RUN_VERSION,
            "status": self.status.value,
            "validation_only": True,
            "notice": "VALIDATION ONLY — NO BENCHMARK EXECUTED",
            "benchmark_id": self.benchmark_id,
            "configuration_hash": self.configuration_hash,
            "validation": self.validation,
            "fixture_checks": self.fixture_checks,
            "seed_checks": self.seed_checks,
            "baseline_checks": self.baseline_checks,
            "metric_calculator_available": self.metric_calculator_available,
            "metric_values_generated": self.metric_values_generated,
            "benchmark_execution_authorized": self.benchmark_execution_authorized,
            "artifact_path_check": self.artifact_path_check,
            "execution_plan": self.execution_plan,
            "expected_run_count": self.expected_run_count,
            "mutation_count": self.mutation_count,
            "seed_count": self.seed_count,
            "baseline_count": self.baseline_count,
            "benchmark_runs_executed": self.benchmark_runs_executed,
            "provider_operations_executed": self.provider_operations_executed,
            "healing_operations_executed": self.healing_operations_executed,
            "generated_at": self.generated_at,
        }
        return _to_jsonable(payload)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"

    def render(self) -> str:
        return "\n".join(
            (
                "VALIDATION ONLY",
                "NO BENCHMARK EXECUTED",
                f"status={self.status.value}",
                f"benchmark_id={self.benchmark_id}",
                f"configuration_hash={self.configuration_hash}",
                f"expected_run_count={self.expected_run_count}",
                f"benchmark_runs_executed={self.benchmark_runs_executed}",
                f"provider_operations_executed={self.provider_operations_executed}",
                f"healing_operations_executed={self.healing_operations_executed}",
                f"metric_values_generated={self.metric_values_generated}",
                f"benchmark_execution_authorized={self.benchmark_execution_authorized}",
            )
        ) + "\n"


def compute_configuration_hash(config: BenchmarkConfig) -> str:
    canonical = _canonical_config_payload(config)
    encoded = json.dumps(_to_jsonable(canonical), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_config(config: BenchmarkConfig) -> BenchmarkConfig:
    """Return a new immutable config with the canonical configuration hash."""

    return replace(config, configuration_hash=compute_configuration_hash(config))


def validate_config(config: BenchmarkConfig) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}
    lab = MutationLab()

    _require_text(config.benchmark_id, "benchmark_id", errors)
    _require_text(config.benchmark_version, "benchmark_version", errors)
    _require_text(config.fixture_id, "fixture_id", errors)
    _require_text(config.fixture_version, "fixture_version", errors)
    _require_text(config.code_revision, "code_revision", errors)
    _require_text(config.repository_revision, "repository_revision", errors)
    _require_text(config.environment_reference, "environment_reference", errors)
    _require_text(config.runtime_reference, "runtime_reference", errors)
    _require_text(config.artifact_root, "artifact_root", errors)
    _require_text(config.metric_formula_version, "metric_formula_version", errors)
    _require_text(config.created_at, "created_at", errors)

    mutation_ids = tuple(config.mutation_class_ids)
    if len(mutation_ids) != len(set(mutation_ids)):
        errors.append("duplicate mutation IDs")
    missing = sorted(set(REQUIRED_MUTATION_IDS) - set(mutation_ids))
    extra = sorted(set(mutation_ids) - set(REQUIRED_MUTATION_IDS))
    if missing:
        errors.append(f"missing mutation classes: {','.join(missing)}")
    if extra:
        errors.append(f"unexpected mutation classes: {','.join(extra)}")
    checks["mutation_set"] = "PASS" if not missing and not extra and len(mutation_ids) == len(set(mutation_ids)) else "FAIL"

    if set(config.mutation_severity) != set(mutation_ids):
        errors.append("mutation severity mapping keys do not match mutation_class_ids")
    severity_ok = True
    for mutation_id in mutation_ids:
        severity = config.mutation_severity.get(mutation_id)
        if severity not in VALID_SEVERITIES:
            errors.append(f"invalid severity mapping for {mutation_id}: {severity}")
            severity_ok = False
        elif mutation_id in lab.mutation_ids and severity != lab.definition(mutation_id).severity.value:
            errors.append(f"severity mapping conflicts with MutationLab for {mutation_id}")
            severity_ok = False
    checks["mutation_severity"] = "PASS" if severity_ok and set(config.mutation_severity) == set(mutation_ids) else "FAIL"

    seeds = tuple(config.seeds)
    if not seeds:
        errors.append("missing seed list")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        errors.append("seed list contains a non-integer seed")
    if len(seeds) != len(set(seeds)):
        errors.append("duplicate seeds")
    if config.trial_count <= 0:
        errors.append("trial_count must be positive")
    if seeds and config.trial_count != len(seeds):
        errors.append("trial_count must equal seed count for the deterministic execution plan")
    checks["seed_policy"] = "PASS" if seeds and len(seeds) == len(set(seeds)) and config.trial_count == len(seeds) else "FAIL"

    baseline_ids = tuple(baseline.baseline_id for baseline in config.baselines)
    if len(baseline_ids) != len(set(baseline_ids)):
        errors.append("duplicate baseline IDs")
    missing_baselines = sorted(set(REQUIRED_BASELINE_IDS) - set(baseline_ids))
    extra_baselines = sorted(set(baseline_ids) - set(REQUIRED_BASELINE_IDS))
    if missing_baselines:
        errors.append(f"missing baselines: {','.join(missing_baselines)}")
    if extra_baselines:
        errors.append(f"unexpected baselines: {','.join(extra_baselines)}")
    baseline_ok = True
    for baseline in config.baselines:
        fields = {
            "description": baseline.description,
            "implementation_revision": baseline.implementation_revision,
            "model_id": baseline.model_id,
            "prompt_revision": baseline.prompt_revision,
            "configuration_hash": baseline.configuration_hash,
            "execution_policy": baseline.execution_policy,
            "verification_policy": baseline.verification_policy,
            "commit_policy": baseline.commit_policy,
        }
        for name, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f"baseline {baseline.baseline_id} missing {name}")
                baseline_ok = False
        if baseline.status not in VALID_BASELINE_STATUSES:
            errors.append(f"baseline {baseline.baseline_id} has invalid status {baseline.status}")
            baseline_ok = False
        if not isinstance(baseline.retry_policy, Mapping):
            errors.append(f"baseline {baseline.baseline_id} retry_policy is not a mapping")
            baseline_ok = False
        else:
            before = len(errors)
            _validate_retry_policy(baseline.retry_policy, f"baseline {baseline.baseline_id} retry_policy", errors)
            if len(errors) != before:
                baseline_ok = False
        if baseline.status == "READY" and baseline.configuration_hash in {"TBD", "UNKNOWN", "NOT_READY", ""}:
            errors.append(f"ready baseline {baseline.baseline_id} lacks a real configuration hash")
            baseline_ok = False
    checks["baseline_slots"] = "PASS" if baseline_ok and not missing_baselines and not extra_baselines and len(baseline_ids) == len(set(baseline_ids)) else "FAIL"
    if any(baseline.status != "READY" for baseline in config.baselines):
        warnings.append("one or more baseline slots are NOT_READY/UNKNOWN; dry-run is not benchmark execution readiness")

    _validate_retry_policy(config.retry_policy, "retry_policy", errors)
    _validate_timeout_policy(config.timeout_policy, errors)
    checks["retry_policy"] = "PASS" if not any(error.startswith("retry_policy") for error in errors) else "FAIL"
    checks["timeout_policy"] = "PASS" if not any(error.startswith("timeout_policy") for error in errors) else "FAIL"

    if config.fixture_version != lab.fixture.fixture_version:
        errors.append(f"fixture_version does not match MutationLab fixture: {config.fixture_version}")
    if config.fixture_id != lab.fixture.fixture_id:
        errors.append(f"fixture_id does not match MutationLab fixture: {config.fixture_id}")
    checks["fixture"] = "PASS" if config.fixture_id == lab.fixture.fixture_id and config.fixture_version == lab.fixture.fixture_version else "FAIL"

    if config.metric_formula_version != FORMULA_VERSION:
        errors.append(f"metric_formula_version must equal {FORMULA_VERSION}")
    checks["metric_formula_version"] = "PASS" if config.metric_formula_version == FORMULA_VERSION else "FAIL"

    if config.code_revision != config.repository_revision:
        errors.append("code_revision and repository_revision conflict")
    checks["code_revision"] = "PASS" if config.code_revision and config.code_revision == config.repository_revision else "FAIL"

    if config.repository_state not in {"CLEAN", "DIRTY", "DIRTY_USER_FILES_PRESERVED", "UNKNOWN"}:
        errors.append(f"invalid repository_state: {config.repository_state}")
    elif config.repository_state == "UNKNOWN":
        errors.append("repository_state must be recorded as CLEAN or DIRTY, not UNKNOWN")
    checks["repository_state"] = "PASS" if config.repository_state in {"CLEAN", "DIRTY", "DIRTY_USER_FILES_PRESERVED"} else "FAIL"
    if config.repository_state != "CLEAN":
        warnings.append("repository is not clean; no benchmark execution is authorized by this dry-run")

    if not isinstance(config.model_configuration, Mapping):
        errors.append("model_configuration must be a mapping")
    if config.model_identifier == "NOT_APPLICABLE" and config.prompt_version not in {"NOT_APPLICABLE", "UNKNOWN", "TBD"}:
        errors.append("prompt_version conflicts with model_identifier=NOT_APPLICABLE")
    checks["model_metadata"] = "PASS" if not any(error.startswith("model_configuration") or error.startswith("prompt_version") for error in errors) else "FAIL"

    if not isinstance(config.collection_policy, Mapping) or not config.collection_policy:
        errors.append("collection_policy is missing")
    if not isinstance(config.evidence_policy, Mapping) or not config.evidence_policy:
        errors.append("evidence_policy is missing")
    checks["policies"] = "PASS" if isinstance(config.collection_policy, Mapping) and bool(config.collection_policy) and isinstance(config.evidence_policy, Mapping) and bool(config.evidence_policy) else "FAIL"

    required_artifacts = {"configs", "manifests", "runs", "results", "reports"}
    artifact_contract_ok = isinstance(config.artifact_contract, Mapping) and set(config.artifact_contract) == required_artifacts
    if not artifact_contract_ok:
        errors.append("artifact_contract must define configs, manifests, runs, results, and reports")
    else:
        for artifact_name, artifact_path in config.artifact_contract.items():
            if not isinstance(artifact_path, str) or not artifact_path.startswith("benchmarks/") or Path(artifact_path).is_absolute():
                errors.append(f"artifact_contract.{artifact_name} must be a relative benchmarks path")
                artifact_contract_ok = False
    checks["artifact_contract"] = "PASS" if artifact_contract_ok else "FAIL"

    if not config.artifact_root.strip() or Path(config.artifact_root).is_file():
        errors.append("artifact_root is missing or points to a file")
    checks["artifact_root"] = "PASS" if bool(config.artifact_root.strip()) and not Path(config.artifact_root).is_file() else "FAIL"

    expected_hash = compute_configuration_hash(config)
    if config.configuration_hash != expected_hash:
        errors.append("configuration_hash does not match canonical frozen configuration")
    checks["configuration_hash"] = "PASS" if config.configuration_hash == expected_hash else "FAIL"

    return ValidationResult(
        status=ValidationStatus.VALID if not errors else ValidationStatus.INVALID,
        errors=tuple(sorted(set(errors))),
        warnings=tuple(sorted(set(warnings))),
        checks=checks,
        configuration_hash=config.configuration_hash,
    )


def run_dry_run(config: BenchmarkConfig, *, repository_root: str | Path | None = None) -> DryRunResult:
    validation = validate_config(config)
    if not validation.valid:
        return DryRunResult(
            status=DryRunStatus.INVALID,
            validation=validation,
            benchmark_id=config.benchmark_id,
            configuration_hash=config.configuration_hash,
            fixture_checks={},
            seed_checks={},
            baseline_checks={},
            metric_calculator_available=False,
            artifact_path_check="BLOCKED_INVALID_CONFIG",
            execution_plan=(),
            expected_run_count=0,
            mutation_count=0,
            seed_count=0,
            baseline_count=0,
        )

    lab = MutationLab()
    fixture_checks: dict[str, str] = {}
    seed_checks: dict[str, str] = {}
    baseline_checks: dict[str, str] = {}
    for mutation_id in sorted(config.mutation_class_ids):
        fixture_checks[mutation_id] = "PASS" if mutation_id in lab.mutation_ids else "FAIL"
        for seed in sorted(config.seeds):
            first = lab.apply_mutation(mutation_id, seed)
            second = lab.apply_mutation(mutation_id, seed)
            reproducible = (
                first.mutated.fixture == second.mutated.fixture
                and first.ground_truth.expected_correct_state == second.ground_truth.expected_correct_state
                and first.ground_truth.expected_corrupted_state == second.ground_truth.expected_corrupted_state
                and first.ground_truth.deterministic_metadata == second.ground_truth.deterministic_metadata
            )
            seed_checks[f"{mutation_id}:{seed}"] = "PASS" if reproducible else "FAIL"

    for baseline in sorted(config.baselines, key=lambda item: item.baseline_id):
        baseline_checks[baseline.baseline_id] = f"{baseline.status}:RESOLVABLE_METADATA"

    metric_calculator_available = _metric_calculator_available()
    artifact_path_check = _artifact_path_check(config.artifact_root, repository_root)
    execution_plan: list[Mapping[str, Any]] = []
    for baseline in sorted(config.baselines, key=lambda item: item.baseline_id):
        for mutation_id in sorted(config.mutation_class_ids):
            for seed in sorted(config.seeds):
                execution_plan.append(
                    {
                        "baseline_id": baseline.baseline_id,
                        "mutation_id": mutation_id,
                        "severity": config.mutation_severity[mutation_id],
                        "seed": seed,
                        "fixture_id": config.fixture_id,
                        "fixture_version": config.fixture_version,
                        "code_revision": config.code_revision,
                        "configuration_hash": config.configuration_hash,
                        "execution": "NOT_EXECUTED",
                    }
                )
    expected_run_count = len(execution_plan)
    return DryRunResult(
        status=DryRunStatus.VALIDATION_ONLY,
        validation=validation,
        benchmark_id=config.benchmark_id,
        configuration_hash=config.configuration_hash,
        fixture_checks=fixture_checks,
        seed_checks=seed_checks,
        baseline_checks=baseline_checks,
        metric_calculator_available=metric_calculator_available,
        artifact_path_check=artifact_path_check,
        execution_plan=tuple(execution_plan),
        expected_run_count=expected_run_count,
        mutation_count=len(config.mutation_class_ids),
        seed_count=len(config.seeds),
        baseline_count=len(config.baselines),
    )


def dry_run(config: BenchmarkConfig, *, repository_root: str | Path | None = None) -> DryRunResult:
    """Alias with the concise public name used by validation scripts."""

    return run_dry_run(config, repository_root=repository_root)


def load_benchmark_config(path: str | Path) -> BenchmarkConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return BenchmarkConfig.from_mapping(payload)


def default_validation_config(*, code_revision: str, repository_state: str = "DIRTY_USER_FILES_PRESERVED") -> BenchmarkConfig:
    baseline_retry = {"mode": "BOUNDED", "max_attempts": 1, "backoff_ms": 0}
    baselines = (
        BaselineSpec(
            baseline_id="BASELINE_A",
            description="Static selector extraction without healing or AEGIS verification.",
            implementation_revision="NOT_READY",
            model_id="NOT_APPLICABLE",
            prompt_revision="NOT_APPLICABLE",
            configuration_hash="NOT_READY",
            execution_policy="SINGLE_PASS_NO_HEALING",
            retry_policy={"mode": "NONE", "max_attempts": 1, "backoff_ms": 0},
            verification_policy="NOT_APPLICABLE_BASELINE_NO_VERIFICATION",
            commit_policy="NOT_APPLICABLE_BASELINE_NO_COMMIT",
            status="NOT_READY",
        ),
        BaselineSpec(
            baseline_id="BASELINE_B",
            description="Naive LLM repair baseline; configuration slot only, no model or prompt is frozen in Mission 011.",
            implementation_revision="NOT_READY",
            model_id="TBD",
            prompt_revision="TBD",
            configuration_hash="NOT_READY",
            execution_policy="SINGLE_CANDIDATE_POLICY_DEFINED_BUT_NOT_EXECUTED",
            retry_policy=baseline_retry,
            verification_policy="NO_AEGIS_VERIFICATION",
            commit_policy="FIRST_CANDIDATE_POLICY_DEFINED_BUT_NOT_EXECUTED",
            status="NOT_READY",
        ),
        BaselineSpec(
            baseline_id="AEGIS",
            description="AEGIS lifecycle with deterministic verification, risk governor, commit gate, quarantine, and watch boundaries.",
            implementation_revision=code_revision,
            model_id="NOT_APPLICABLE",
            prompt_revision="NOT_APPLICABLE",
            configuration_hash="NOT_READY",
            execution_policy="FULL_LIFECYCLE_DEFINED_BUT_NOT_EXECUTED",
            retry_policy=baseline_retry,
            verification_policy="MISSION_010_DETERMINISTIC_CALCULATOR_AND_EXISTING_GATES",
            commit_policy="COMMIT_GATE_REQUIRED; NO_DRY_RUN_COMMIT",
            status="NOT_READY",
        ),
    )
    return BenchmarkConfig(
        benchmark_id="aegis-benchmark-floor",
        benchmark_version="mission-011-validation-floor-v1",
        fixture_id="gpu-price-staging",
        fixture_version="1",
        mutation_class_ids=REQUIRED_MUTATION_IDS,
        mutation_severity={"M001": "L1", "M002": "L2", "M003": "L3", "M004": "L4", "M005": "L5", "M006": "L5"},
        seeds=(12345,),
        trial_count=1,
        baselines=baselines,
        code_revision=code_revision,
        repository_revision=code_revision,
        repository_state=repository_state,
        environment_reference="AEGIS_LOCAL_VALIDATION_ONLY; TEST_DOUBLE_FIXTURE; NO_PROVIDER_EXECUTION",
        runtime_reference="Python 3.12; standard-library application modules; pytest test environment",
        model_identifier="NOT_APPLICABLE",
        model_configuration={"status": "NOT_APPLICABLE_FOR_VALIDATION_ONLY"},
        prompt_version="NOT_APPLICABLE",
        retry_policy={"mode": "BOUNDED", "max_attempts": 1, "backoff_ms": 0},
        timeout_policy={"collection_ms": 300000, "healing_ms": 900000, "polling_ms": 300000, "verification_ms": 30000, "total_ms": 1800000},
        collection_policy={"mode": "VALIDATION_ONLY", "provider_execution": "NOT_EXECUTED", "provenance": "TEST_DOUBLE_FIXTURE_ONLY"},
        evidence_policy={"ground_truth": "MutationGroundTruth_ONLY", "raw_runs": "MutationRun_ONLY", "metrics": "Mission010_calculator_only", "redaction": "Mission008_audit_store", "manual_result_editing": False},
        artifact_contract={"configs": "benchmarks/configs", "manifests": "benchmarks/manifests", "runs": "benchmarks/runs", "results": "benchmarks/results", "reports": "benchmarks/reports"},
        artifact_root="benchmarks/results/mission_011_validation_floor",
        metric_formula_version=FORMULA_VERSION,
        created_at=DEFAULT_CREATED_AT,
    )


def _canonical_config_payload(config: BenchmarkConfig) -> Mapping[str, Any]:
    return {
        "config_version": config.config_version,
        "benchmark_id": config.benchmark_id,
        "benchmark_version": config.benchmark_version,
        "fixture_id": config.fixture_id,
        "fixture_version": config.fixture_version,
        "mutation_class_ids": tuple(sorted(config.mutation_class_ids)),
        "mutation_severity": dict(sorted(config.mutation_severity.items())),
        "seeds": tuple(sorted(config.seeds)),
        "trial_count": config.trial_count,
        "baselines": [
            {
                "baseline_id": baseline.baseline_id,
                "description": baseline.description,
                "implementation_revision": baseline.implementation_revision,
                "model_id": baseline.model_id,
                "prompt_revision": baseline.prompt_revision,
                "configuration_hash": baseline.configuration_hash,
                "execution_policy": baseline.execution_policy,
                "retry_policy": dict(sorted(baseline.retry_policy.items())),
                "verification_policy": baseline.verification_policy,
                "commit_policy": baseline.commit_policy,
                "status": baseline.status,
                **({"participant_metadata": baseline.metadata} if baseline.metadata else {}),
            }
            for baseline in sorted(config.baselines, key=lambda item: item.baseline_id)
        ],
        "code_revision": config.code_revision,
        "repository_revision": config.repository_revision,
        "repository_state": config.repository_state,
        "environment_reference": config.environment_reference,
        "runtime_reference": config.runtime_reference,
        "model_identifier": config.model_identifier,
        "model_configuration": config.model_configuration,
        "prompt_version": config.prompt_version,
        "retry_policy": config.retry_policy,
        "timeout_policy": config.timeout_policy,
        "collection_policy": config.collection_policy,
        "evidence_policy": config.evidence_policy,
        "artifact_contract": config.artifact_contract,
        "artifact_root": config.artifact_root,
        "metric_formula_version": config.metric_formula_version,
        "created_at": config.created_at,
    }


def _require_text(value: Any, field_name: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing {field_name}")


def _validate_retry_policy(policy: Mapping[str, Any], prefix: str, errors: list[str]) -> None:
    if not isinstance(policy, Mapping):
        errors.append(f"{prefix} must be a mapping")
        return
    mode = policy.get("mode")
    max_attempts = policy.get("max_attempts")
    backoff_ms = policy.get("backoff_ms")
    if mode not in {"NONE", "BOUNDED"}:
        errors.append(f"{prefix}.mode invalid")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        errors.append(f"{prefix}.max_attempts invalid")
    if isinstance(backoff_ms, bool) or not isinstance(backoff_ms, int) or backoff_ms < 0:
        errors.append(f"{prefix}.backoff_ms invalid")
    if mode == "NONE" and max_attempts != 1:
        errors.append(f"{prefix}.NONE must have max_attempts=1")


def _validate_timeout_policy(policy: Mapping[str, Any], errors: list[str]) -> None:
    if not isinstance(policy, Mapping):
        errors.append("timeout_policy must be a mapping")
        return
    required = ("collection_ms", "healing_ms", "polling_ms", "verification_ms", "total_ms")
    values: dict[str, int] = {}
    for name in required:
        value = policy.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"timeout_policy.{name} invalid")
        else:
            values[name] = value
    if values and values.get("total_ms", 0) < max(values.get(name, 0) for name in required[:-1]):
        errors.append("timeout_policy.total_ms must cover every component timeout")


def _metric_calculator_available() -> bool:
    from .mutation_metrics import calculate_metrics

    return callable(calculate_metrics)


def _artifact_path_check(artifact_root: str, repository_root: str | Path | None) -> str:
    if not artifact_root.strip():
        return "FAIL_MISSING_ARTIFACT_ROOT"
    path = Path(artifact_root)
    if path.is_absolute() or path.parts[0] != "benchmarks":
        return "FAIL_ARTIFACT_ROOT_OUTSIDE_BENCHMARKS"
    if path.exists() and path.is_file():
        return "FAIL_ARTIFACT_ROOT_IS_FILE"
    if repository_root is not None:
        resolved = Path(repository_root) / path
        if resolved.exists() and resolved.is_file():
            return "FAIL_ARTIFACT_ROOT_IS_FILE"
        if resolved.parent.exists():
            return "PASS_FUTURE_ROOT_PARENT_EXISTS_NOT_CREATED"
    return "PASS_FUTURE_ROOT_NOT_CREATED"
