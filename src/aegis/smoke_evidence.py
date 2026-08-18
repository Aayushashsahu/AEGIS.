"""Canonical immutable Mission 019 smoke-evidence paths and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


CANONICAL_SMOKE_RUN_ID = "mission_016_floor_59a11e27a71f"
BASELINE_B_SMOKE_SUBROOT = "baseline_b_execution_readiness_smoke"
EXPECTED_CONFIGURATION_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"


@dataclass(frozen=True)
class SmokeEvidencePaths:
    """All immutable smoke-evidence paths resolved from one repository root."""

    repository_root: Path
    smoke_root: Path
    baseline_b_smoke_root: Path
    smoke: Path
    smoke_log: Path
    preflight: Path
    root_execution_log: Path
    frozen_config: Path

    def to_dict(self) -> Mapping[str, str]:
        return {
            "repository_root": str(self.repository_root),
            "smoke_root": str(self.smoke_root),
            "baseline_b_smoke_root": str(self.baseline_b_smoke_root),
            "smoke": str(self.smoke),
            "smoke_log": str(self.smoke_log),
            "preflight": str(self.preflight),
            "root_execution_log": str(self.root_execution_log),
            "frozen_config": str(self.frozen_config),
        }


@dataclass(frozen=True)
class SmokeEvidenceValidation:
    """Mission 019/020 smoke validation result with no execution side effects."""

    passed: bool
    status: str
    checks: Mapping[str, bool]
    errors: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    provider_operation_count: int | None = None

    def to_dict(self) -> Mapping[str, Any]:
        return {
            "pass": self.passed,
            "status": self.status,
            "checks": dict(self.checks),
            "errors": list(self.errors),
            "missing": list(self.missing),
            "provider_operation_count": self.provider_operation_count,
        }


def resolve_immutable_smoke_evidence(repository_root: str | Path) -> SmokeEvidencePaths:
    """Resolve every immutable evidence file from the supplied repository root."""

    root = Path(repository_root).resolve()
    smoke_root = root / "benchmarks" / "runs" / CANONICAL_SMOKE_RUN_ID
    baseline_b_smoke_root = smoke_root / BASELINE_B_SMOKE_SUBROOT
    return SmokeEvidencePaths(
        repository_root=root,
        smoke_root=smoke_root,
        baseline_b_smoke_root=baseline_b_smoke_root,
        smoke=baseline_b_smoke_root / "smoke.json",
        smoke_log=baseline_b_smoke_root / "execution_log.json",
        preflight=smoke_root / "preflight.json",
        root_execution_log=smoke_root / "execution_log.json",
        frozen_config=smoke_root / "frozen_config.json",
    )


def validate_immutable_smoke_evidence(repository_root: str | Path) -> SmokeEvidenceValidation:
    """Validate the exact immutable Mission 019 evidence contract read-only."""

    paths = resolve_immutable_smoke_evidence(repository_root)
    required = {
        "smoke": paths.smoke,
        "smoke_execution_log": paths.smoke_log,
        "preflight": paths.preflight,
        "root_execution_log": paths.root_execution_log,
        "frozen_config": paths.frozen_config,
    }
    missing = tuple(name for name, path in required.items() if not path.is_file())
    if missing:
        return SmokeEvidenceValidation(
            passed=False,
            status="MISSING",
            checks={},
            errors=(f"missing immutable evidence: {', '.join(missing)}",),
            missing=missing,
        )
    try:
        records = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in required.items()}
    except (OSError, json.JSONDecodeError) as exc:
        return SmokeEvidenceValidation(False, "CORRUPT", {}, (str(exc),))
    if not all(isinstance(record, Mapping) for record in records.values()):
        return SmokeEvidenceValidation(False, "INVALID", {}, ("immutable smoke evidence has an invalid JSON object shape",))

    smoke = records["smoke"]
    smoke_checks_value = smoke.get("checks", {})
    smoke_checks = smoke_checks_value if isinstance(smoke_checks_value, Mapping) else {}
    adapter_value = smoke.get("adapter_evidence", {})
    adapter = adapter_value if isinstance(adapter_value, Mapping) else {}
    application_value = adapter.get("candidate_application", {})
    application = application_value if isinstance(application_value, Mapping) else {}
    configured_model_value = smoke_checks.get("configured_model", {})
    configured_model = configured_model_value if isinstance(configured_model_value, Mapping) else {}
    root_log = records["root_execution_log"]
    smoke_log = records["smoke_execution_log"]
    preflight_value = records["preflight"].get("result", {})
    preflight = preflight_value if isinstance(preflight_value, Mapping) else {}
    frozen_config = records["frozen_config"]
    checks = {
        "smoke_status": smoke.get("name") == "BASELINE_B_EXECUTION_READINESS_SMOKE" and smoke.get("status") == "PASS",
        "smoke_checks": all(value is True for value in smoke_checks.values() if isinstance(value, bool)) and configured_model.get("pass") is True,
        "candidate_accepted": adapter.get("candidate_accepted") is True,
        "bounded_application": application.get("application_mode") == "SAFE_TEST_DOUBLE_BOUNDARY" and application.get("generated_code_executed") is False,
        "runtime_ground_truth_not_provided": smoke.get("runtime_ground_truth_payload") == "NOT_PROVIDED",
        "smoke_log_status": smoke_log.get("status") == "BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK",
        "preflight_passed": preflight.get("passed") is True,
        "frozen_config_hash": frozen_config.get("configuration_hash") == EXPECTED_CONFIGURATION_HASH,
        "benchmark_runs_zero": root_log.get("benchmark_runs_executed") == 0,
        "provider_operations_zero": root_log.get("provider_operations_executed") == 0,
        "healing_zero": root_log.get("healing_operations_executed") == 0,
        "metrics_zero": root_log.get("metric_results_generated", root_log.get("metric_values_generated")) == 0,
        "execution_unauthorized": root_log.get("execution_authorized", root_log.get("benchmark_execution_authorized")) is False,
    }
    errors = tuple(name for name, value in checks.items() if value is False)
    return SmokeEvidenceValidation(
        passed=not errors,
        status="VALID" if not errors else "INVALID",
        checks=checks,
        errors=errors,
        provider_operation_count=smoke.get("provider_operation_count") if isinstance(smoke.get("provider_operation_count"), int) else None,
    )


__all__ = [
    "BASELINE_B_SMOKE_SUBROOT",
    "CANONICAL_SMOKE_RUN_ID",
    "EXPECTED_CONFIGURATION_HASH",
    "SmokeEvidencePaths",
    "SmokeEvidenceValidation",
    "resolve_immutable_smoke_evidence",
    "validate_immutable_smoke_evidence",
]
