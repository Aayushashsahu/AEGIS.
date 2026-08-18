"""Mission 028 execution boundary for the authorized NVIDIA benchmark.

The module keeps the Mission 027 configuration immutable, derives a new
Mission 028 run identity, verifies the pre-execution gate, and constructs the
NVIDIA caller only for the explicit execution path. Preflight never calls a
provider and never creates the run root.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .benchmark_config import BenchmarkConfig, load_benchmark_config
from .benchmark_executor import BenchmarkExecutor, ExecutionGateResult, ExecutionSummary
from .benchmark_lifecycle import deterministic_benchmark_run_id
from .nvidia_provider import (
    NVIDIA_CANDIDATE_MODEL_ID,
    NVIDIA_CANDIDATE_MODEL_REVISION,
    NVIDIA_PROVIDER,
    NvidiaModelCaller,
    NvidiaParticipantRegistry,
    RateLimitConfig,
    candidate_model_descriptor,
)

MISSION_027_COMMIT = "fc563b3e9837834612d84db7afd331d1a18f80e6"
MISSION_028_ATTEMPT_ID = "mission-028-nvidia-comparative-benchmark-v1"
MISSION_028_RUN_ID_PREFIX = "mission_028_floor"
MISSION_028_RECOVERY_ATTEMPT_ID = "mission-028-nvidia-comparative-benchmark-recovery-v1"
MISSION_028_RECOVERY_RUN_ID_PREFIX = "mission_028_recovery_floor"
MISSION_028_INVALIDATED_RUN_ID = "mission_028_floor_00c77f2abd976a10"
MISSION_028_CONFIGURATION_HASH = "8f926adfe2f50a1b404e5f28a9e6b0bf5ad62edfba13f3e0bbf29c16cf204bd4"
MISSION_028_PARTICIPANT_HASH = "9b630269de415be0f69b92e7abd62dcaf4a3a535c3e8f3df982017a50ba25c14"
MISSION_026_NVIDIA_IMPLEMENTATION_REVISION = "mission-026-nvidia-adapter-74817617100cc17d"
MISSION_028_SOURCE_REVISIONS: Mapping[str, str] = {
    "BASELINE_A": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
    "BASELINE_B": MISSION_026_NVIDIA_IMPLEMENTATION_REVISION,
    "AEGIS": "b79050044be0a6d919eecd5633f72188469022df",
}
MISSION_028_SOURCE_FILES: Mapping[str, str] = {
    "BASELINE_A": "src/aegis/baseline_participants.py",
    "BASELINE_B": "src/aegis/nvidia_provider.py",
    "AEGIS": "src/aegis/benchmark_runner.py",
}


def load_mission028_config(root: str | Path) -> BenchmarkConfig:
    config = load_benchmark_config(Path(root) / "benchmarks/configs/mission_027_nvidia_owner_freeze_config.json")
    if config.configuration_hash != MISSION_028_CONFIGURATION_HASH:
        raise ValueError("Mission 027 frozen configuration hash does not match Mission 028 input")
    return config


def benchmark_rate_limit(config: BenchmarkConfig) -> RateLimitConfig:
    raw = dict(config.model_configuration.get("rate_limit", {}))
    return RateLimitConfig(
        max_requests_per_minute=int(raw["benchmark_requests_per_minute"]),
        min_interval_seconds=float(raw["benchmark_min_interval_seconds"]),
        concurrency_limit=int(raw["concurrency_limit"]),
    )


def validate_benchmark_rate_policy(config: BenchmarkConfig) -> Mapping[str, Any]:
    raw = dict(config.model_configuration.get("rate_limit", {}))
    policy = {
        "benchmark_requests_per_minute": raw.get("benchmark_requests_per_minute"),
        "benchmark_min_interval_seconds": raw.get("benchmark_min_interval_seconds"),
        "concurrency_limit": raw.get("concurrency_limit"),
        "provider_limit": raw.get("provider_limit"),
        "provider_limit_status": raw.get("provider_limit_status"),
    }
    passed = (
        policy["benchmark_requests_per_minute"] == 6
        and policy["benchmark_min_interval_seconds"] == 10
        and policy["concurrency_limit"] == 1
        and policy["provider_limit"] == "UNKNOWN"
        and policy["provider_limit_status"] == "UNKNOWN_UNTIL_ACCOUNT_RESPONSE"
    )
    return {"pass": passed, **policy}


def mission028_source_revision_checker(root: str | Path) -> Callable[[str, str], bool]:
    repository_root = Path(root).resolve()

    def check(revision: str, relative_path: str) -> bool:
        if revision == MISSION_026_NVIDIA_IMPLEMENTATION_REVISION:
            reference = MISSION_027_COMMIT
            path = MISSION_028_SOURCE_FILES["BASELINE_B"]
        else:
            reference = revision
            path = relative_path
        result = subprocess.run(
            ["git", "diff", "--quiet", reference, "--", path],
            cwd=repository_root,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    return check


def mission028_run_id(config: BenchmarkConfig) -> str:
    return deterministic_benchmark_run_id(
        config.configuration_hash,
        MISSION_028_ATTEMPT_ID,
        MISSION_028_SOURCE_REVISIONS,
        run_id_prefix=MISSION_028_RUN_ID_PREFIX,
    )


def build_mission028_executor(
    root: str | Path,
    *,
    output_root: str | Path,
    model_caller: NvidiaModelCaller | object | None,
    runs_root: str | Path | None = None,
    attempt_id: str = MISSION_028_ATTEMPT_ID,
    run_id_prefix: str = MISSION_028_RUN_ID_PREFIX,
) -> BenchmarkExecutor:
    repository_root = Path(root).resolve()
    config = load_mission028_config(repository_root)
    if isinstance(model_caller, NvidiaModelCaller):
        registry = NvidiaParticipantRegistry(config, model_caller=model_caller)
    else:
        registry = NvidiaParticipantRegistry(config)
    rate_policy = validate_benchmark_rate_policy(config)
    participant_hash_pass = next(
        spec.configuration_hash == MISSION_028_PARTICIPANT_HASH
        for spec in config.baselines
        if spec.baseline_id == "BASELINE_B"
    )
    return BenchmarkExecutor(
        config,
        repository_root=repository_root,
        output_root=Path(output_root),
        model_caller=model_caller,
        registry=registry,
        expected_source_revisions=MISSION_028_SOURCE_REVISIONS,
        source_revision_checker=mission028_source_revision_checker(repository_root),
        expected_configuration_hash=MISSION_028_CONFIGURATION_HASH,
        attempt_id=attempt_id,
        run_id_prefix=run_id_prefix,
        expected_benchmark_run_id=deterministic_benchmark_run_id(config.configuration_hash, attempt_id, MISSION_028_SOURCE_REVISIONS, run_id_prefix=run_id_prefix),
        additional_gate_checks={
            "participant_hash": participant_hash_pass,
            "rate_limit_policy_valid": bool(rate_policy["pass"]),
        },
        runs_root=runs_root,
    )


def recovery_run_id(config: BenchmarkConfig) -> str:
    return deterministic_benchmark_run_id(
        config.configuration_hash,
        MISSION_028_RECOVERY_ATTEMPT_ID,
        MISSION_028_SOURCE_REVISIONS,
        run_id_prefix=MISSION_028_RECOVERY_RUN_ID_PREFIX,
    )


def recovery_preflight(root: str | Path) -> tuple[ExecutionGateResult, BenchmarkConfig, str]:
    repository_root = Path(root).resolve()
    config = load_mission028_config(repository_root)
    rate_policy = validate_benchmark_rate_policy(config)
    if not rate_policy["pass"]:
        raise ValueError(f"Mission 028 recovery benchmark-side rate policy invalid: {rate_policy}")
    run_id = recovery_run_id(config)
    output_root = repository_root / "benchmarks/runs" / run_id
    executor = build_mission028_executor(
        repository_root,
        output_root=output_root,
        model_caller=object(),
        attempt_id=MISSION_028_RECOVERY_ATTEMPT_ID,
        run_id_prefix=MISSION_028_RECOVERY_RUN_ID_PREFIX,
    )
    gate = executor.execution_gate()
    return gate, config, run_id


def preflight(root: str | Path) -> tuple[ExecutionGateResult, BenchmarkConfig, str]:
    repository_root = Path(root).resolve()
    config = load_mission028_config(repository_root)
    rate_policy = validate_benchmark_rate_policy(config)
    if not rate_policy["pass"]:
        raise ValueError(f"Mission 028 benchmark-side rate policy invalid: {rate_policy}")
    run_id = mission028_run_id(config)
    output_root = repository_root / "benchmarks/runs" / run_id
    executor = build_mission028_executor(repository_root, output_root=output_root, model_caller=object())
    gate = executor.execution_gate()
    return gate, config, run_id


def build_nvidia_caller(config: BenchmarkConfig, api_key: str | None = None) -> NvidiaModelCaller:
    model_configuration = dict(config.model_configuration)
    if model_configuration.get("provider") != NVIDIA_PROVIDER:
        raise ValueError("Mission 028 configuration does not select NVIDIA_NIM")
    if model_configuration.get("model_id") != NVIDIA_CANDIDATE_MODEL_ID:
        raise ValueError("Mission 028 model identifier drifted")
    if model_configuration.get("model_revision") != NVIDIA_CANDIDATE_MODEL_REVISION:
        raise ValueError("Mission 028 model revision drifted")
    return NvidiaModelCaller(
        candidate_model_descriptor(),
        api_key=api_key,
        endpoint=str(model_configuration["endpoint"]),
        rate_limit=benchmark_rate_limit(config),
        timeout_seconds=int(config.timeout_policy["total_ms"] / 1000),
    )


__all__ = [
    "MISSION_026_NVIDIA_IMPLEMENTATION_REVISION",
    "MISSION_027_COMMIT",
    "MISSION_028_ATTEMPT_ID",
    "MISSION_028_CONFIGURATION_HASH",
    "MISSION_028_INVALIDATED_RUN_ID",
    "MISSION_028_RECOVERY_ATTEMPT_ID",
    "MISSION_028_RECOVERY_RUN_ID_PREFIX",
    "MISSION_028_PARTICIPANT_HASH",
    "MISSION_028_RUN_ID_PREFIX",
    "MISSION_028_SOURCE_FILES",
    "MISSION_028_SOURCE_REVISIONS",
    "benchmark_rate_limit",
    "build_mission028_executor",
    "build_nvidia_caller",
    "load_mission028_config",
    "mission028_run_id",
    "recovery_preflight",
    "recovery_run_id",
    "mission028_source_revision_checker",
    "preflight",
    "validate_benchmark_rate_policy",
]
