"""Fail-closed validation for owner-supplied Mission 014 participant metadata.

The validator is deliberately declarative. It preserves the supplied values and
never fills implementation revisions, hashes, timestamps, rationales, or
correlation IDs. A single missing or inconsistent field blocks promotion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .audit_store import _to_jsonable


class OwnerValidationStatus(str, Enum):
    VALID = "VALID"
    BLOCKED_NOT_READY = "BLOCKED_NOT_READY"


@dataclass(frozen=True)
class ParticipantApprovalValidation:
    participant_id: str
    status: OwnerValidationStatus
    participant_hash: str
    missing_fields: tuple[str, ...]
    placeholder_fields: tuple[str, ...]
    checks: Mapping[str, str]
    errors: tuple[str, ...]

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class OwnerReviewValidation:
    status: OwnerValidationStatus
    approved: bool
    reviewer: str
    missing_fields: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class FairnessValidation:
    status: OwnerValidationStatus
    checks: Mapping[str, str]
    conflicts: tuple[str, ...]

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class OwnerApprovedValidationReport:
    status: OwnerValidationStatus
    source_configuration_hash: str
    new_configuration_hash: str
    participants: Mapping[str, ParticipantApprovalValidation]
    owner_review: OwnerReviewValidation
    fairness: FairnessValidation
    promotions_created: int
    benchmark_runs_executed: int = 0
    provider_operations_executed: int = 0
    healing_operations_executed: int = 0
    metric_results_generated: int = 0
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "participants", dict(self.participants))

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def validate_owner_configuration(payload: Mapping[str, Any], *, source_configuration_hash: str) -> OwnerApprovedValidationReport:
    raw_participants = payload.get("participants", {})
    participants = {
        participant_id: _validate_participant(participant_id, raw_participants.get(participant_id, {}))
        for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS")
    }
    owner_review = _validate_owner_review(payload.get("owner_review", {}))
    fairness = _validate_fairness(raw_participants)
    blocked = any(result.status is OwnerValidationStatus.BLOCKED_NOT_READY for result in participants.values()) or owner_review.status is OwnerValidationStatus.BLOCKED_NOT_READY or fairness.status is OwnerValidationStatus.BLOCKED_NOT_READY
    return OwnerApprovedValidationReport(
        status=OwnerValidationStatus.BLOCKED_NOT_READY if blocked else OwnerValidationStatus.VALID,
        source_configuration_hash=source_configuration_hash,
        new_configuration_hash="NOT_GENERATED" if blocked else "MUST_BE_GENERATED",
        participants=participants,
        owner_review=owner_review,
        fairness=fairness,
        promotions_created=0,
    )


def _validate_participant(participant_id: str, data: Mapping[str, Any]) -> ParticipantApprovalValidation:
    required = _required_paths(participant_id)
    missing: list[str] = []
    placeholders: list[str] = []
    checks: dict[str, str] = {}
    errors: list[str] = []
    for path in required:
        found, value = _lookup(data, path)
        if not found:
            missing.append(path)
            checks[path] = "FAIL_MISSING"
            continue
        if _is_placeholder(value):
            placeholders.append(path)
            checks[path] = "FAIL_PLACEHOLDER"
        else:
            checks[path] = "PASS"
    if participant_id == "BASELINE_A":
        _check_exact(data, "provider.type", "TEST_DOUBLE", checks, errors)
        _check_exact(data, "provider.name", "local-mutation-fixture", checks, errors)
        _check_exact(data, "output.provenance", "TEST_DOUBLE", checks, errors)
        _check_exact(data, "benchmark.fixture_id", "gpu-price-staging", checks, errors)
        _check_exact(data, "benchmark.fixture_version", 1, checks, errors)
        _check_exact(data, "benchmark.mutation_set", ["M001", "M002", "M003", "M004", "M005", "M006"], checks, errors)
        _check_exact(data, "benchmark.seed", 12345, checks, errors)
        _check_exact(data, "controls.healing", "NOT_USED", checks, errors)
        _check_exact(data, "controls.aegis_detection", "NOT_USED", checks, errors)
        _check_exact(data, "controls.aegis_verification", "NOT_USED", checks, errors)
        _check_exact(data, "controls.risk_governor", "NOT_USED", checks, errors)
        _check_exact(data, "controls.commit_gate", "NOT_USED", checks, errors)
        _check_exact(data, "controls.quarantine", "NOT_USED", checks, errors)
        _check_exact(data, "controls.watch", "NOT_USED", checks, errors)
        _check_exact(data, "controls.rollback", "NOT_USED", checks, errors)
    elif participant_id == "BASELINE_B":
        _check_exact(data, "provider.type", "GOOGLE_GEMINI_API", checks, errors)
        _check_exact(data, "model.id", "gemini-3.6-flash", checks, errors)
        _check_exact(data, "model.revision", "stable", checks, errors)
        _check_exact(data, "repair_policy.candidate_policy", "FIRST_CANDIDATE", checks, errors)
        _check_exact(data, "repair_policy.max_candidates", 1, checks, errors)
        _check_exact(data, "repair_policy.auto_accept_first_candidate", True, checks, errors)
        _check_exact(data, "aegis_controls.detection", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.verification", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.risk_governor", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.commit_gate", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.quarantine", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.watch", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.rollback", "NOT_USED", checks, errors)
        _check_exact(data, "aegis_controls.mutation_ground_truth_runtime_payload", "NOT_USED", checks, errors)
    elif participant_id == "AEGIS":
        _check_exact(data, "implementation.benchmark_adapter", "AegisAdapter", checks, errors)
        _check_exact(data, "provider.collection_mode", "TEST_DOUBLE", checks, errors)
        _check_exact(data, "provider.provenance", "TEST_DOUBLE", checks, errors)
        _check_exact(data, "provider.live_bright_data_execution", "NOT_USED_FOR_INITIAL_BENCHMARK", checks, errors)
        _check_exact(data, "mutation_lab.mutations", ["M001", "M002", "M003", "M004", "M005", "M006"], checks, errors)
        _check_exact(data, "mutation_lab.seed", 12345, checks, errors)
        _check_exact(data, "mutation_lab.fixture_id", "gpu-price-staging", checks, errors)
        _check_exact(data, "mutation_lab.fixture_version", 1, checks, errors)
        _check_exact(data, "mutation_lab.ground_truth_runtime_payload", "NOT_PROVIDED", checks, errors)
        _check_exact(data, "safety.blind_commit_allowed", False, checks, errors)
        _check_exact(data, "safety.auto_approve_allowed", False, checks, errors)
        _check_exact(data, "safety.verification_bypass_allowed", False, checks, errors)
        _check_exact(data, "safety.ground_truth_runtime_access", False, checks, errors)
        _check_exact(data, "safety.unsafe_candidate_shipping", False, checks, errors)
        _check_exact(data, "metrics.calculator", "mission-010-metrics-v1", checks, errors)
    for path in missing:
        errors.append(f"{participant_id}: missing field {path}")
    for path in placeholders:
        errors.append(f"{participant_id}: unresolved placeholder {path}={_lookup(data, path)[1]!r}")
    supplied_hash = str(data.get("participant_hash", ""))
    if supplied_hash.startswith("MUST_"):
        checks["participant_hash"] = "FAIL_PLACEHOLDER"
        errors.append(f"{participant_id}: participant_hash is not computed")
    else:
        checks["participant_hash"] = "PASS"
    status = OwnerValidationStatus.BLOCKED_NOT_READY if errors else OwnerValidationStatus.VALID
    return ParticipantApprovalValidation(
        participant_id=participant_id,
        status=status,
        participant_hash=supplied_hash,
        missing_fields=tuple(sorted(set(missing))),
        placeholder_fields=tuple(sorted(set(placeholders))),
        checks=checks,
        errors=tuple(sorted(set(errors))),
    )


def _validate_owner_review(data: Mapping[str, Any]) -> OwnerReviewValidation:
    required = ("approved", "reviewer", "approval_timestamp", "rationale", "correlation_id", "approved_configuration_hash")
    missing: list[str] = []
    errors: list[str] = []
    for field_name in required:
        value = data.get(field_name)
        if value is None or value == "" or value == "NOT_SUPPLIED" or (isinstance(value, str) and value.startswith("MUST_")):
            missing.append(field_name)
    if data.get("approved") is not True:
        errors.append("owner_review.approved must be true")
    if data.get("reviewer") != "PROJECT_OWNER":
        errors.append("owner_review.reviewer must equal PROJECT_OWNER")
    errors.extend(f"owner_review: missing field {field_name}" for field_name in missing)
    status = OwnerValidationStatus.BLOCKED_NOT_READY if errors else OwnerValidationStatus.VALID
    return OwnerReviewValidation(status, data.get("approved") is True, str(data.get("reviewer", "")), tuple(sorted(set(missing))), tuple(sorted(set(errors))))


def _validate_fairness(participants: Mapping[str, Any]) -> FairnessValidation:
    checks: dict[str, str] = {}
    conflicts: list[str] = []
    timeout_values = {participant_id: _lookup(data, "execution.timeout_seconds")[1] for participant_id, data in participants.items()}
    retry_values = {participant_id: _lookup(data, "execution.retry_count")[1] for participant_id, data in participants.items()}
    backoff_values = {participant_id: _lookup(data, "execution.backoff_seconds")[1] for participant_id, data in participants.items()}
    ground_truth_values = {
        participant_id: _lookup(data, "mutation_lab.ground_truth_runtime_payload" if participant_id == "AEGIS" else "ground_truth.runtime_payload")[1]
        for participant_id, data in participants.items()
    }
    def participant_value(participant_id: str, data: Mapping[str, Any], baseline_path: str, aegis_path: str) -> Any:
        return _lookup(data, aegis_path if participant_id == "AEGIS" else baseline_path)[1]

    expected_mutations = ["M001", "M002", "M003", "M004", "M005", "M006"]
    checks["mutation_id"] = "PASS" if all(participant_value(participant_id, data, "benchmark.mutation_set", "mutation_lab.mutations") == expected_mutations for participant_id, data in participants.items()) else "FAIL"
    checks["seed"] = "PASS" if all(participant_value(participant_id, data, "benchmark.seed", "mutation_lab.seed") == 12345 for participant_id, data in participants.items()) else "FAIL"
    fixture_values = {
        participant_id: (
            participant_value(participant_id, data, "benchmark.fixture_id", "mutation_lab.fixture_id"),
            participant_value(participant_id, data, "benchmark.fixture_version", "mutation_lab.fixture_version"),
        )
        for participant_id, data in participants.items()
    }
    checks["fixture_version"] = "PASS" if len(set(fixture_values.values())) == 1 and next(iter(fixture_values.values()), None) == ("gpu-price-staging", 1) else "FAIL"
    for label, values in (("timeout_policy", timeout_values), ("retry_policy", retry_values), ("backoff_policy", backoff_values)):
        if len(set(values.values())) != 1:
            checks[label] = "FAIL"
            conflicts.append(f"{label} differs across participants: {values}")
        else:
            checks[label] = "PASS"
    if len(set(ground_truth_values.values())) != 1 or next(iter(ground_truth_values.values()), None) != "NOT_PROVIDED":
        checks["ground_truth_runtime_payload"] = "FAIL"
        conflicts.append(f"ground_truth_runtime_payload is not uniformly NOT_PROVIDED: {ground_truth_values}")
    else:
        checks["ground_truth_runtime_payload"] = "PASS"
    status = OwnerValidationStatus.BLOCKED_NOT_READY if conflicts or "FAIL" in checks.values() else OwnerValidationStatus.VALID
    return FairnessValidation(status, checks, tuple(conflicts))


def _required_paths(participant_id: str) -> tuple[str, ...]:
    common = ("participant_id", "purpose", "implementation.name", "implementation.revision", "participant_config_version", "participant_hash", "execution.timeout_seconds", "execution.retry_count", "execution.backoff_seconds", "output.normalization", "output.artifact_schema", "output.provenance", "benchmark.mutation_set", "benchmark.seed", "benchmark.fixture_id", "benchmark.fixture_version", "ground_truth.runtime_payload")
    if participant_id == "BASELINE_A":
        return common + ("provider.type", "provider.name", "implementation.language", "implementation.entrypoint", "extraction.strategy", "extraction.selector_version", "extraction.schema_version", "extraction.fields", "controls.healing", "controls.llm", "controls.aegis_detection", "controls.aegis_verification", "controls.risk_governor", "controls.commit_gate", "controls.quarantine", "controls.watch", "controls.rollback", "cost.llm_calls", "cost.provider_cost")
    if participant_id == "BASELINE_B":
        return common + ("provider.type", "model.id", "model.revision", "prompts.system_prompt_version", "prompts.system_prompt", "prompts.repair_prompt_template_version", "prompts.repair_prompt_template", "sampling.temperature", "sampling.top_p", "sampling.top_k", "sampling.max_output_tokens", "tools.enabled", "repair_policy.candidate_policy", "repair_policy.max_candidates", "repair_policy.auto_accept_first_candidate", "aegis_controls.detection", "aegis_controls.verification", "aegis_controls.risk_governor", "aegis_controls.commit_gate", "aegis_controls.quarantine", "aegis_controls.watch", "aegis_controls.rollback", "aegis_controls.mutation_ground_truth_runtime_payload", "cost.llm_calls_per_attempt", "implementation.revision")
    if participant_id == "AEGIS":
        return ("participant_id", "purpose", "implementation.name", "implementation.revision", "implementation.benchmark_adapter", "participant_config_version", "participant_hash", "provider.collection_mode", "provider.provenance", "provider.live_bright_data_execution", "mutation_lab.fixture_id", "mutation_lab.fixture_version", "mutation_lab.mutations", "mutation_lab.seed", "mutation_lab.ground_truth_runtime_payload", "lifecycle.collection", "lifecycle.observation", "lifecycle.detection", "lifecycle.diagnosis", "lifecycle.repair_request", "lifecycle.healing_adapter", "lifecycle.candidate", "lifecycle.verification", "lifecycle.risk_governor", "lifecycle.commit_gate", "lifecycle.quarantine", "lifecycle.watch", "lifecycle.rollback", "safety.blind_commit_allowed", "safety.auto_approve_allowed", "safety.verification_bypass_allowed", "safety.ground_truth_runtime_access", "safety.unsafe_candidate_shipping", "execution.timeout_seconds", "execution.retry_count", "execution.backoff_seconds", "output.normalization", "output.artifact_schema", "output.provenance", "metrics.calculator", "benchmark.configuration_version", "benchmark.mutation_set", "benchmark.seed", "benchmark.fixture_id", "benchmark.fixture_version")
    return ()


def _lookup(data: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = data
    for segment in path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and (value.startswith("MUST_") or value in {"", "NOT_SUPPLIED", "TBD", "UNKNOWN", "NOT_READY"})


def _check_exact(data: Mapping[str, Any], path: str, expected: Any, checks: dict[str, str], errors: list[str]) -> None:
    found, value = _lookup(data, path)
    if found and value == expected:
        checks[f"exact:{path}"] = "PASS"
    else:
        checks[f"exact:{path}"] = "FAIL"
        errors.append(f"inconsistent {path}: expected {expected!r}, got {value!r}")


def load_owner_payload(path: str | Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
