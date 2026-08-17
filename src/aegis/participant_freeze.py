"""Mission 013 human-reviewed participant metadata freeze and promotion.

This module never chooses a model, prompt, provider, or policy.  Missing or
unapproved values remain explicit and keep a participant NOT_READY.  Promotion
returns new immutable records and evidence; it never mutates prior history or
launches a benchmark.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .audit_store import _to_jsonable
from .benchmark_config import BenchmarkConfig, BaselineSpec, freeze_config
from .immutability import freeze_mapping

PARTICIPANT_IDS = ("BASELINE_A", "BASELINE_B", "AEGIS")
PLACEHOLDER_VALUES = {"", "TBD", "UNKNOWN", "NOT_READY", "NOT_APPLICABLE", "NOT_PROVIDED"}


class PromotionStatus(str, Enum):
    NOT_READY = "NOT_READY"
    READY = "READY"
    INVALID = "INVALID"


class PromotionError(ValueError):
    """Raised when a participant promotion would violate the freeze contract."""


@dataclass(frozen=True)
class ParticipantFreezeProposal:
    participant_id: str
    prior_status: str
    implementation_revision: str
    configuration: Mapping[str, Any]
    timeout_policy: Mapping[str, Any]
    retry_policy: Mapping[str, Any]
    output_normalization_policy: str
    provenance: str
    artifact_schema: str
    execution_policy: str
    verification_policy: str
    commit_policy: str
    configuration_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "configuration", freeze_mapping(self.configuration))
        object.__setattr__(self, "timeout_policy", freeze_mapping(self.timeout_policy))
        object.__setattr__(self, "retry_policy", freeze_mapping(self.retry_policy))
        if not self.configuration_hash:
            object.__setattr__(self, "configuration_hash", compute_participant_hash(self))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class OwnerReviewDecision:
    participant_id: str
    approved: bool
    owner: str
    reviewer: str
    rationale: str
    reviewed_at: str
    correlation_id: str

    def __post_init__(self) -> None:
        for field_name in ("owner", "reviewer", "rationale", "reviewed_at", "correlation_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required for an owner review decision")

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class ParticipantFreezeValidation:
    participant_id: str
    status: PromotionStatus
    participant_configuration_hash: str
    computed_configuration_hash: str
    checks: Mapping[str, str]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", freeze_mapping(self.checks))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def ready(self) -> bool:
        return self.status is PromotionStatus.READY

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class ReadinessPromotion:
    participant_id: str
    prior_status: str
    new_status: str
    implementation_revision: str
    configuration_hash: str
    rationale: str
    reviewer: str
    owner: str
    timestamp: str
    correlation_id: str
    evidence_type: str = "READINESS_PROMOTION"

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class PromotionResult:
    participant_id: str
    participant_spec: BaselineSpec
    validation: ParticipantFreezeValidation
    promotion: ReadinessPromotion

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


def compute_participant_hash(proposal: ParticipantFreezeProposal) -> str:
    payload = {
        "participant_id": proposal.participant_id,
        "implementation_revision": proposal.implementation_revision,
        "configuration": proposal.configuration,
        "timeout_policy": proposal.timeout_policy,
        "retry_policy": proposal.retry_policy,
        "output_normalization_policy": proposal.output_normalization_policy,
        "provenance": proposal.provenance,
        "artifact_schema": proposal.artifact_schema,
        "execution_policy": proposal.execution_policy,
        "verification_policy": proposal.verification_policy,
        "commit_policy": proposal.commit_policy,
    }
    encoded = json.dumps(_to_jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def proposal_from_spec(spec: BaselineSpec) -> ParticipantFreezeProposal:
    metadata = dict(spec.metadata) or _default_metadata(spec)
    return ParticipantFreezeProposal(
        participant_id=spec.baseline_id,
        prior_status=spec.status,
        implementation_revision=spec.implementation_revision,
        configuration=metadata,
        timeout_policy=metadata.get("timeout_policy", {}),
        retry_policy=dict(spec.retry_policy),
        output_normalization_policy=str(metadata.get("output_normalization_policy", "NOT_READY")),
        provenance=str(metadata.get("provenance", "TEST_DOUBLE")),
        artifact_schema=str(metadata.get("artifact_schema", "NOT_READY")),
        execution_policy=spec.execution_policy,
        verification_policy=spec.verification_policy,
        commit_policy=spec.commit_policy,
        configuration_hash=spec.configuration_hash,
    )


def validate_participant_proposal(proposal: ParticipantFreezeProposal, *, require_owner_approval: bool = False) -> ParticipantFreezeValidation:
    checks: dict[str, str] = {}
    errors: list[str] = []
    required = _required_fields(proposal.participant_id)
    for field_name in required:
        value = proposal.configuration.get(field_name)
        present = _present(value)
        checks[field_name] = "PASS" if present else "FAIL"
        if not present:
            errors.append(f"missing {field_name}")
    checks["implementation_revision"] = "PASS" if _present(proposal.implementation_revision) else "FAIL"
    if not _present(proposal.implementation_revision):
        errors.append("missing implementation_revision")
    for field_name, value in (
        ("output_normalization_policy", proposal.output_normalization_policy),
        ("provenance", proposal.provenance),
        ("artifact_schema", proposal.artifact_schema),
        ("execution_policy", proposal.execution_policy),
        ("verification_policy", proposal.verification_policy),
        ("commit_policy", proposal.commit_policy),
    ):
        checks[field_name] = "PASS" if _present(value) else "FAIL"
        if not _present(value):
            errors.append(f"missing {field_name}")
    checks["timeout_policy"] = "PASS" if bool(proposal.timeout_policy) else "FAIL"
    checks["retry_policy"] = "PASS" if bool(proposal.retry_policy) else "FAIL"
    if not proposal.timeout_policy:
        errors.append("missing timeout_policy")
    if not proposal.retry_policy:
        errors.append("missing retry_policy")
    computed = compute_participant_hash(proposal)
    checks["participant_hash"] = "PASS" if proposal.configuration_hash == computed else "FAIL"
    if proposal.configuration_hash != computed:
        errors.append("participant configuration hash does not match frozen metadata")
    if require_owner_approval and proposal.prior_status != "READY":
        errors.append("owner review is required before readiness promotion")
    ready = not errors
    return ParticipantFreezeValidation(
        participant_id=proposal.participant_id,
        status=PromotionStatus.READY if ready else PromotionStatus.NOT_READY,
        participant_configuration_hash=proposal.configuration_hash,
        computed_configuration_hash=computed,
        checks=checks,
        errors=tuple(sorted(set(errors))),
        warnings=() if ready else ("missing or unapproved participant metadata remains explicit; no substitution is permitted",),
    )


def promote_participant(proposal: ParticipantFreezeProposal, review: OwnerReviewDecision) -> PromotionResult:
    if review.participant_id != proposal.participant_id:
        raise PromotionError("owner review participant does not match proposal")
    if not review.approved:
        raise PromotionError("participant cannot be promoted without explicit owner approval")
    validation = validate_participant_proposal(proposal)
    if not validation.ready:
        raise PromotionError(f"participant metadata is not complete: {validation.errors}")
    if proposal.prior_status == "READY":
        raise PromotionError("promotion must record a NOT_READY to READY transition")
    spec = _spec_from_proposal(proposal)
    promotion = ReadinessPromotion(
        participant_id=proposal.participant_id,
        prior_status=proposal.prior_status,
        new_status="READY",
        implementation_revision=proposal.implementation_revision,
        configuration_hash=proposal.configuration_hash,
        rationale=review.rationale,
        reviewer=review.reviewer,
        owner=review.owner,
        timestamp=review.reviewed_at,
        correlation_id=review.correlation_id,
    )
    return PromotionResult(proposal.participant_id, spec, validation, promotion)


def apply_promotions(config: BenchmarkConfig, promotions: tuple[PromotionResult, ...]) -> BenchmarkConfig:
    replacements = {result.participant_id: result.participant_spec for result in promotions}
    if len(replacements) != len(promotions):
        raise PromotionError("duplicate participant promotion")
    existing = {spec.baseline_id: spec for spec in config.baselines}
    if not set(replacements).issubset(existing):
        raise PromotionError("promotion contains unknown participant")
    updated = tuple(replacements.get(participant_id, existing[participant_id]) for participant_id in existing)
    return freeze_config(replace(config, baselines=updated))


def default_mission013_proposals(config: BenchmarkConfig) -> Mapping[str, ParticipantFreezeProposal]:
    """Return explicit proposals; no values are guessed or owner-approved."""

    specs = {spec.baseline_id: spec for spec in config.baselines}
    return {participant_id: proposal_from_spec(specs[participant_id]) for participant_id in PARTICIPANT_IDS}


def _default_metadata(spec: BaselineSpec) -> dict[str, Any]:
    common = {
        "description": spec.description,
        "configuration": {"status": "NOT_READY"},
        "timeout_policy": {},
        "retry_policy": dict(spec.retry_policy),
        "output_normalization_policy": "NOT_READY",
        "provenance": "TEST_DOUBLE",
        "artifact_schema": "NOT_READY",
    }
    if spec.baseline_id == "BASELINE_A":
        return {
            **common,
            "extraction_implementation": "NOT_READY",
            "healing": "NOT_USED",
            "aegis_verification": "NOT_USED",
            "risk_governor": "NOT_USED",
            "commit_gate": "NOT_USED",
            "quarantine": "NOT_USED",
            "watch": "NOT_USED",
            "rollback": "NOT_USED",
        }
    if spec.baseline_id == "BASELINE_B":
        return {
            **common,
            "model_identifier": spec.model_id,
            "provider": "TBD",
            "system_prompt": "TBD",
            "repair_prompt_template": "TBD",
            "sampling_configuration": "TBD",
            "max_output": "TBD",
            "tools_permitted": "TBD",
            "first_candidate_policy": spec.commit_policy,
        }
    if spec.baseline_id == "AEGIS":
        return {
            **common,
            "code_revision": spec.implementation_revision,
            "fixture_version": "1",
            "mutation_class_ids": ["M001", "M002", "M003", "M004", "M005", "M006"],
            "seeds": [12345],
            "benchmark_configuration_hash": "NOT_READY",
            "participant_adapter": "aegis.benchmark_runner.AegisAdapter",
            "deterministic_test_double": True,
            "metric_formula_version": "mission-010-metrics-v1",
            "safety_policy": "UNCHANGED; VERIFICATION_RISK_COMMIT_GATE_REQUIRED",
        }
    raise ValueError(f"unknown participant: {spec.baseline_id}")


def _spec_from_proposal(proposal: ParticipantFreezeProposal) -> BaselineSpec:
    model_id = str(proposal.configuration.get("model_identifier", "NOT_APPLICABLE"))
    nested_configuration = proposal.configuration.get("configuration", {})
    prompt_revision = str(proposal.configuration.get("prompt_revision", nested_configuration.get("prompt_revision", "NOT_APPLICABLE")))
    return BaselineSpec(
        baseline_id=proposal.participant_id,
        description=str(proposal.configuration.get("description", proposal.participant_id)),
        implementation_revision=proposal.implementation_revision,
        model_id=model_id,
        prompt_revision=prompt_revision,
        configuration_hash=proposal.configuration_hash,
        execution_policy=proposal.execution_policy,
        retry_policy=proposal.retry_policy,
        verification_policy=proposal.verification_policy,
        commit_policy=proposal.commit_policy,
        status="READY",
        metadata=proposal.configuration,
    )


def _required_fields(participant_id: str) -> tuple[str, ...]:
    if participant_id == "BASELINE_A":
        return (
            "extraction_implementation",
            "configuration",
            "timeout_policy",
            "retry_policy",
            "output_normalization_policy",
            "provenance",
            "artifact_schema",
            "healing",
            "aegis_verification",
            "risk_governor",
            "commit_gate",
            "quarantine",
            "watch",
            "rollback",
        )
    if participant_id == "BASELINE_B":
        return (
            "model_identifier",
            "provider",
            "system_prompt",
            "repair_prompt_template",
            "sampling_configuration",
            "max_output",
            "tools_permitted",
            "timeout_policy",
            "retry_policy",
            "first_candidate_policy",
            "configuration",
        )
    if participant_id == "AEGIS":
        return (
            "code_revision",
            "fixture_version",
            "mutation_class_ids",
            "seeds",
            "benchmark_configuration_hash",
            "participant_adapter",
            "artifact_schema",
            "deterministic_test_double",
            "timeout_policy",
            "retry_policy",
            "provenance",
            "metric_formula_version",
            "safety_policy",
        )
    raise ValueError(f"unknown participant: {participant_id}")


def _present(value: Any) -> bool:
    if isinstance(value, str) and value in PLACEHOLDER_VALUES:
        return False
    if isinstance(value, Mapping):
        return bool(value) and all(_present(item) for item in value.values())
    if isinstance(value, (tuple, list, set)):
        return bool(value) and all(_present(item) for item in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return True
    return value is not None and bool(value)
