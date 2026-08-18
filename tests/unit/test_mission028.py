from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from urllib.error import HTTPError

import pytest

from aegis.benchmark_executor import FixtureController, RunnerState
from aegis.benchmark_resume import inspect_existing_run
from aegis.benchmark_config import load_benchmark_config
from aegis.metric_boundary import ParticipantEvidenceContext, adapt_completed_evidence, calculate_compatibility_metrics
from aegis.mutation_lab import MutationLab
from aegis.nvidia_provider import NvidiaModelCaller, NvidiaProviderError
from aegis.mission028_execution import (
    MISSION_028_CONFIGURATION_HASH,
    MISSION_028_PARTICIPANT_HASH,
    benchmark_rate_limit,
    build_mission028_executor,
    build_nvidia_caller,
    load_mission028_config,
    mission028_run_id,
    preflight,
    recovery_preflight,
    recovery_run_id,
    validate_benchmark_rate_policy,
    MISSION_028_INVALIDATED_RUN_ID,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "mission_028_floor_00c77f2abd976a10"


@pytest.fixture(autouse=True)
def clean_mission028_test_root(tmp_path: Path):
    yield
    shutil.rmtree(tmp_path / RUN_ID, ignore_errors=True)


def config():
    return load_mission028_config(ROOT)


def executor(tmp_path: Path, *, model_caller: object | None = object()):
    return build_mission028_executor(ROOT, output_root=tmp_path / RUN_ID, runs_root=tmp_path, model_caller=model_caller)


def test_new_deterministic_run_id() -> None:
    assert mission028_run_id(config()) == RUN_ID
    assert mission028_run_id(config()).startswith("mission_028_floor_")


def test_recovery_identity_is_distinct_and_deterministic() -> None:
    recovery_id = recovery_run_id(config())
    assert recovery_id == "mission_028_recovery_floor_4812160675146552"
    assert recovery_id != RUN_ID
    assert recovery_id != MISSION_028_INVALIDATED_RUN_ID


def test_recovery_preflight_is_provider_free_and_root_absent() -> None:
    gate, frozen, recovery_id = recovery_preflight(ROOT)
    assert gate.passed
    assert recovery_id != MISSION_028_INVALIDATED_RUN_ID
    assert frozen.configuration_hash == MISSION_028_CONFIGURATION_HASH
    assert gate.execution_authorized is False
    recovery_root = ROOT / "benchmarks/runs" / recovery_id
    if recovery_root.exists():
        assert gate.checks["artifact_root_resumable"] is True
        assert gate.checks["existing_terminal_artifacts_valid"] is True
    else:
        assert not recovery_root.exists()


def test_new_artifact_root_isolated_and_absent() -> None:
    e = executor(ROOT / "tmp-mission028-test-do-not-use")
    assert e.layout.root.name == RUN_ID
    assert e.layout.root.parent == (ROOT / "tmp-mission028-test-do-not-use")
    e.layout.validate_isolation()
    assert not e.layout.root.exists()
    assert not (ROOT / "benchmarks/runs" / RUN_ID).exists()


def test_nvidia_participant_readiness() -> None:
    e = executor(ROOT / "tmp-mission028-readiness-do-not-use")
    readiness = e.registry.readiness(e.config)
    assert all(item.ready for item in readiness.values())
    assert readiness["BASELINE_B"].participant_configuration_hash == MISSION_028_PARTICIPANT_HASH


def test_rate_limiter_at_six_rpm_and_ten_seconds() -> None:
    limit = benchmark_rate_limit(config())
    assert limit.max_requests_per_minute == 6
    assert limit.min_interval_seconds == 10
    assert limit.concurrency_limit == 1
    assert validate_benchmark_rate_policy(config())["provider_limit"] == "UNKNOWN"
    caller = build_nvidia_caller(config())
    assert caller.rate_limiter.config == limit


def test_concurrency_is_one() -> None:
    assert benchmark_rate_limit(config()).concurrency_limit == 1


def test_180_opportunity_plan() -> None:
    e = executor(ROOT / "tmp-mission028-plan-do-not-use")
    manifests = e.plan_manifests()
    assert len(manifests) == 180
    assert len({manifest.run_id for manifest in manifests}) == 180


def test_participant_ordering() -> None:
    e = executor(ROOT / "tmp-mission028-order-do-not-use")
    manifests = e.plan_manifests()
    assert [manifest.participant_id for manifest in manifests[0:60]] == ["BASELINE_A"] * 60
    assert [manifest.participant_id for manifest in manifests[60:120]] == ["BASELINE_B"] * 60
    assert [manifest.participant_id for manifest in manifests[120:180]] == ["AEGIS"] * 60


def test_trial_ordering() -> None:
    e = executor(ROOT / "tmp-mission028-trial-do-not-use")
    manifests = e.plan_manifests()
    first_ten = [int(item.run_id.split("__trial-", 1)[1].split("__", 1)[0]) for item in manifests[:10]]
    second_mutation_trials = [int(item.run_id.split("__trial-", 1)[1].split("__", 1)[0]) for item in manifests[10:20]]
    assert first_ten == list(range(1, 11))
    assert second_mutation_trials == list(range(1, 11))
    assert manifests[0].mutation_id == "M001"
    assert manifests[10].mutation_id == "M002"


def test_no_gemini_invocation_boundary() -> None:
    e = executor(ROOT / "tmp-mission028-no-gemini-do-not-use")
    assert e.registry.get("BASELINE_B").spec.metadata["provider"] == "NVIDIA_NIM"
    assert e.model_caller is not None


def test_provider_failures_are_preserved() -> None:
    def fail(_request, **_kwargs):
        raise HTTPError("https://integrate.api.nvidia.com/v1/chat/completions", 429, "rate limited", {"Retry-After": "10"}, None)

    caller = NvidiaModelCaller(build_nvidia_caller(config()).descriptor, api_key="test-only", rate_limit=benchmark_rate_limit(config()), opener=fail)
    with pytest.raises(NvidiaProviderError) as error:
        caller("system", "repair")
    assert error.value.status_code == 429
    assert caller.last_observation is not None
    assert caller.last_observation.failure_state == "RATE_LIMITED"
    assert caller.last_observation.provider == "NVIDIA_NIM"


def test_retry_policy_is_zero() -> None:
    policy = config().baselines[1].metadata["retry_policy"]
    assert policy["max_attempts"] == 1
    assert config().baselines[1].metadata["timeout_policy"]["retry_count"] == 0
    assert config().baselines[1].metadata["timeout_policy"]["backoff_seconds"] == 0


def test_no_duplicate_run_ids() -> None:
    e = executor(ROOT / "tmp-mission028-duplicates-do-not-use")
    ids = [manifest.run_id for manifest in e.plan_manifests()]
    assert len(ids) == len(set(ids)) == 180


def test_interrupted_run_is_resumable_without_rerunning_terminal_artifact(tmp_path: Path) -> None:
    e = executor(tmp_path)
    e.layout.create_empty_layout()
    manifests = e.plan_manifests()
    e._write_exclusive(e.layout.frozen_config, e.config.to_dict())
    e._persist_manifest(manifests)
    e._write_replaceable(e.layout.execution_log, {"benchmark_run_id": e.benchmark_run_id, "configuration_hash": e.config.configuration_hash, "planned_runs": 180, "status": "RUNNING"})
    e._persist_raw(manifests[0], RunnerState.FAILED, None, ("TEST_DOUBLE_INTERRUPTION",))
    inspection = inspect_existing_run(e.output_root, manifests, expected_benchmark_run_id=e.benchmark_run_id, expected_configuration_hash=e.config.configuration_hash, expected_participant_revisions={spec.baseline_id: spec.implementation_revision for spec in e.config.baselines})
    assert inspection.persisted_terminal_count == 1
    assert inspection.missing_count == 179
    assert manifests[0].run_id not in {item.run_id for item in inspection.missing_manifests}


def test_raw_artifact_persistence(tmp_path: Path) -> None:
    e = executor(tmp_path)
    e.layout.create_empty_layout()
    manifest = e.plan_manifests()[0]
    e._persist_raw(manifest, RunnerState.FAILED, None, ("PROVIDER_FAILURE",))
    raw_path = e.output_root / "raw" / manifest.artifact_name
    payload = json.loads(raw_path.read_text())
    assert payload["terminal_state"] == "FAILED"
    assert payload["manifest"]["run_id"] == manifest.run_id
    assert payload["errors"] == ["PROVIDER_FAILURE"]


def test_fixture_reset() -> None:
    controller = FixtureController(MutationLab())
    assert controller.validate_clean().passed
    controller.apply("M001", 12345)
    assert controller.validate_clean().passed is False
    assert controller.reset().passed
    assert controller.validate_clean().passed


def test_final_all_terminal_check_is_required_before_metrics(tmp_path: Path) -> None:
    e = executor(tmp_path)
    e.layout.create_empty_layout()
    manifests = e.plan_manifests()
    e._write_exclusive(e.layout.frozen_config, e.config.to_dict())
    e._persist_manifest(manifests)
    e._write_replaceable(e.layout.execution_log, {"benchmark_run_id": e.benchmark_run_id, "configuration_hash": e.config.configuration_hash, "planned_runs": 180, "status": "RUNNING", "metric_results_generated": 0})
    e._persist_raw(manifests[0], RunnerState.FAILED, None, ("WAITING_FOR_REMAINING_TRIALS",))
    inspection = inspect_existing_run(e.output_root, manifests, expected_benchmark_run_id=e.benchmark_run_id, expected_configuration_hash=e.config.configuration_hash)
    assert inspection.missing_count == 179
    assert not (e.output_root / "metrics" / "mission-010-metrics.json").exists()


def _aegis_metric_fixture(tmp_path: Path):
    e = executor(tmp_path)
    manifests = [item for item in e.plan_manifests() if item.participant_id == "AEGIS"]
    manifest = manifests[0]
    execution_input = e._trial_input("AEGIS", manifest.mutation_id, 1, manifest.seed)
    adapter = e.registry.get("AEGIS")
    prepared = adapter.prepare(execution_input)
    evidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
    case = e.lab.apply_mutation(manifest.mutation_id, manifest.seed)
    context = ParticipantEvidenceContext(
        run_id=manifest.run_id,
        benchmark_id=manifest.benchmark_id,
        configuration_hash=manifest.configuration_hash,
        participant_configuration_hash=manifest.participant_configuration_hash,
        participant_revision=manifest.participant_revision,
        mutation_id=manifest.mutation_id,
        severity=manifest.severity,
        seed=manifest.seed,
        fixture_version=manifest.fixture_version,
        ground_truth_reference=manifest.ground_truth_reference,
        trial_number=1,
        artifact_root=manifest.artifact_root,
        artifact_name=manifest.artifact_name,
    )
    return evidence, context, case.ground_truth


def test_mission022_adaptation(tmp_path: Path) -> None:
    evidence, context, truth = _aegis_metric_fixture(tmp_path)
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    assert report.passed
    assert report.metric_calculation_ready
    assert report.metric_inputs[0].participant_id == "AEGIS"


def test_mission010_is_the_only_metric_calculator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, context, truth = _aegis_metric_fixture(tmp_path)
    report = adapt_completed_evidence([evidence], {evidence.ground_truth_reference: truth}, {evidence.run_id: context})
    calls = []
    import aegis.metric_boundary as boundary

    original = boundary.mutation_metrics.calculate_metrics
    monkeypatch.setattr(boundary.mutation_metrics, "calculate_metrics", lambda *args, **kwargs: (calls.append(True) or original(*args, **kwargs)))
    result = calculate_compatibility_metrics(report)
    assert calls == [True]
    assert result.formula_version == "mission-010-metrics-v1"


def test_old_gemini_benchmark_untouched() -> None:
    old_config = load_benchmark_config(ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json")
    assert old_config.configuration_hash == "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
    assert old_config.baselines[1].metadata["provider"] == "GOOGLE_GEMINI_API"
    assert subprocess.run(["git", "diff", "--quiet", "main", "--", "benchmarks/configs/mission_017_corrected_frozen_config.json"], cwd=ROOT).returncode == 0
    assert subprocess.run(["git", "diff", "--quiet", "main", "--", "benchmarks/runs/mission_016_floor_59a11e27a71f"], cwd=ROOT).returncode == 0


def test_preflight_is_zero_execution_and_root_absent() -> None:
    gate, frozen, run_id = preflight(ROOT)
    assert gate.passed
    assert run_id == RUN_ID
    assert frozen.configuration_hash == MISSION_028_CONFIGURATION_HASH
    assert gate.execution_authorized is False
    assert not (ROOT / "benchmarks/runs" / run_id).exists()
