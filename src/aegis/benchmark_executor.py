"""Explicit Mission 021 benchmark execution boundary.

This module is deliberately separate from the Mission 020 validation-only
runner.  Importing it performs no execution and creates no artifacts.  The
real CLI must provide an explicit authorization gate and a model caller; tests
use an injected caller and the existing deterministic MutationLab boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .audit_store import _to_jsonable
from .baseline_participants import BaselineBUnavailable
from .benchmark_config import BenchmarkConfig, validate_config
from .benchmark_lifecycle import BASELINE_B_SMOKE_SUBROOT, BenchmarkArtifactLayout, BenchmarkLifecyclePhase, deterministic_benchmark_run_id
from .benchmark_runner import (
    PARTICIPANT_IDS,
    BenchmarkRunner,
    FreezeSnapshot,
    ParticipantExecutionInput,
    ParticipantRegistry,
    ParticipantRunEvidence,
    RunManifest,
    RunnerState,
    validate_freeze,
)
from .metric_boundary import (
    MetricBoundaryError,
    ParticipantEvidenceContext,
    adapt_completed_evidence,
    calculate_compatibility_metrics,
)
from .mutation_lab import MutationCase, MutationLab, MutationRun, baseline_fixture


EXPECTED_CONFIGURATION_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
EXPECTED_BENCHMARK_ATTEMPT_ID = "mission-020-floor-v1"
EXPECTED_SMOKE_RUN_ID = "mission_016_floor_59a11e27a71f"
EXPECTED_BENCHMARK_RUN_ID = "mission_020_floor_2a80a8cf8d989326"
EXPECTED_SEED = 12345
EXPECTED_MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")
TRIALS_PER_MUTATION = 10
EXPECTED_SOURCE_REVISIONS = {
    "BASELINE_A": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
    "BASELINE_B": "067c06d8d41b2c23a93aebdcc45ac46a2c71351e",
    "AEGIS": "b79050044be0a6d919eecd5633f72188469022df",
}
SOURCE_FILES = {
    "BASELINE_A": "src/aegis/baseline_participants.py",
    "BASELINE_B": "src/aegis/baseline_participants.py",
    "AEGIS": "src/aegis/benchmark_runner.py",
}

ModelCaller = Callable[[str, str], Mapping[str, Any]]


class GeminiDeveloperCaller:
    """Explicit Gemini Developer API caller; constructed only by --run."""

    def __init__(self, api_key: str | None, *, model_id: str = "gemini-3.6-flash", timeout_seconds: int = 300) -> None:
        self._api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    def __call__(self, system_prompt: str, repair_prompt: str) -> Mapping[str, Any]:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is required for explicit benchmark execution")
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": repair_prompt}]}],
            "generationConfig": {"maxOutputTokens": 8192},
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?{urlencode({'key': self._api_key})}",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Gemini API transport failure: {exc.reason}") from exc
        if not isinstance(parsed, Mapping):
            raise RuntimeError("Gemini API returned a non-object response")
        return parsed


def deterministic_trial_run_id(
    benchmark_run_id: str,
    participant_id: str,
    mutation_id: str,
    trial_number: int,
    seed: int,
    configuration_hash: str,
) -> str:
    """Derive a stable logical identity for one participant trial."""

    if trial_number <= 0:
        raise ValueError("trial_number must be positive")
    payload = "|".join(
        (
            benchmark_run_id,
            participant_id,
            mutation_id,
            str(trial_number),
            str(seed),
            configuration_hash,
        )
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{benchmark_run_id}__{participant_id.lower()}__{mutation_id.lower()}__trial-{trial_number}__{digest}"


def deterministic_trial_artifact_name(
    benchmark_run_id: str,
    participant_id: str,
    mutation_id: str,
    trial_number: int,
    seed: int,
    configuration_hash: str,
) -> str:
    digest = hashlib.sha256(
        "|".join(
            (
                benchmark_run_id,
                participant_id,
                mutation_id,
                str(trial_number),
                str(seed),
                configuration_hash,
            )
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"{participant_id.lower()}__{mutation_id.lower()}__trial-{trial_number}__seed-{seed}__{digest}.json"


def deterministic_ground_truth_reference(config: BenchmarkConfig, mutation_id: str, seed: int, trial_number: int) -> str:
    return f"ground-truth://{config.fixture_id}/v{config.fixture_version}/{mutation_id}/{seed}/trial-{trial_number}"


class RecordingMutationLab(MutationLab):
    """MutationLab that exposes evaluator-owned metric inputs without leakage."""

    def __init__(self) -> None:
        super().__init__()
        self.last_run: MutationRun | None = None

    def run(self, mutation_id: str, seed: int):  # type: ignore[override]
        result = super().run(mutation_id, seed)
        self.last_run = result[0]
        return result


@dataclass(frozen=True)
class TrialParticipantExecutionInput(ParticipantExecutionInput):
    trial_number: int = 1
    benchmark_run_id: str = ""

    @property
    def run_id(self) -> str:
        return deterministic_trial_run_id(
            self.benchmark_run_id,
            self.participant_id,
            self.mutation_id,
            self.trial_number,
            self.seed,
            self.configuration_hash,
        )

    @property
    def artifact_name(self) -> str:
        return deterministic_trial_artifact_name(
            self.benchmark_run_id,
            self.participant_id,
            self.mutation_id,
            self.trial_number,
            self.seed,
            self.configuration_hash,
        )


@dataclass(frozen=True)
class FixtureResetResult:
    passed: bool
    reason: str = ""


class FixtureController:
    """Small deterministic fixture boundary used before and after every trial."""

    def __init__(self, lab: MutationLab) -> None:
        self.lab = lab
        self._current = lab.fixture

    def validate_clean(self) -> FixtureResetResult:
        passed = self._current == baseline_fixture()
        return FixtureResetResult(passed, "" if passed else "fixture is not at clean baseline")

    def reset(self) -> FixtureResetResult:
        self._current = baseline_fixture()
        return self.validate_clean()

    def apply(self, mutation_id: str, seed: int) -> MutationCase:
        case = self.lab.apply_mutation(mutation_id, seed)
        self._current = case.mutated.fixture
        return case


@dataclass(frozen=True)
class ExecutionGateResult:
    passed: bool
    benchmark_run_id: str
    configuration_hash: str
    expected_run_count: int
    checks: Mapping[str, Any]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)


@dataclass(frozen=True)
class ExecutionSummary:
    status: str
    benchmark_run_id: str
    configuration_hash: str
    planned_runs: int
    completed_runs: int
    failed_runs: int
    timed_out_runs: int
    invalidated_runs: int
    benchmark_runs_executed: int
    provider_operations_executed: int
    healing_operations_executed: int
    metric_results_generated: int
    execution_authorized: bool
    gate: ExecutionGateResult
    errors: tuple[str, ...] = ()
    stopped_reason: str | None = None

    def to_dict(self) -> Mapping[str, Any]:
        return _to_jsonable(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


class BenchmarkExecutor:
    """Execute exactly the frozen 3 × 6 × 10 floor after explicit gating."""

    def __init__(
        self,
        config: BenchmarkConfig,
        *,
        repository_root: str | Path,
        output_root: str | Path,
        model_caller: ModelCaller | None = None,
        registry: ParticipantRegistry | None = None,
        lab: RecordingMutationLab | None = None,
        fixture_controller: FixtureController | None = None,
        source_revision_checker: Callable[[str, str], bool] | None = None,
        smoke_evidence_validator: Callable[[], Mapping[str, Any]] | None = None,
        expected_source_revisions: Mapping[str, str] = EXPECTED_SOURCE_REVISIONS,
    ) -> None:
        self.config = config
        self.repository_root = Path(repository_root).resolve()
        self.output_root = Path(output_root).resolve()
        self.model_caller = model_caller
        self.lab = lab or RecordingMutationLab()
        self.fixture_controller = fixture_controller or FixtureController(self.lab)
        self.expected_source_revisions = dict(expected_source_revisions)
        self.source_revision_checker = source_revision_checker or self._source_revision_matches
        self.smoke_evidence_validator = smoke_evidence_validator or self._validate_immutable_smoke_evidence
        self.benchmark_run_id = deterministic_benchmark_run_id(
            config.configuration_hash,
            EXPECTED_BENCHMARK_ATTEMPT_ID,
            self.expected_source_revisions,
        )
        smoke_root = self.repository_root / "benchmarks/runs" / EXPECTED_SMOKE_RUN_ID
        self.layout = BenchmarkArtifactLayout(
            self.benchmark_run_id,
            self.repository_root / "benchmarks/runs",
            smoke_root,
            smoke_root / BASELINE_B_SMOKE_SUBROOT,
        )
        if registry is None:
            registry = ParticipantRegistry(config, self.lab)
            baseline_b = registry.get("BASELINE_B")
            if hasattr(baseline_b, "_model_caller"):
                baseline_b._model_caller = model_caller
        self.registry = registry
        self.runner = BenchmarkRunner(
            config,
            registry=self.registry,
            lab=self.lab,
            lifecycle_phase=BenchmarkLifecyclePhase.BENCHMARK_EXECUTION,
            artifact_root=str(self.output_root),
            forbidden_artifact_roots=(str(self.layout.smoke_root),),
        )

    @property
    def expected_run_count(self) -> int:
        return len(PARTICIPANT_IDS) * len(EXPECTED_MUTATIONS) * TRIALS_PER_MUTATION

    def _source_revision_matches(self, revision: str, relative_path: str) -> bool:
        result = subprocess.run(
            ["git", "diff", "--quiet", revision, "--", relative_path],
            cwd=self.repository_root,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def _validate_immutable_smoke_evidence(self) -> Mapping[str, Any]:
        root = self.layout.smoke_evidence_root
        required = {
            "smoke": root / "smoke.json",
            "smoke_execution_log": root / "execution_log.json",
            "preflight": root.parent / "preflight.json",
            "root_execution_log": root.parent / "execution_log.json",
            "frozen_config": root.parent / "frozen_config.json",
        }
        missing = [name for name, path in required.items() if not path.is_file()]
        if missing:
            return {"pass": False, "status": "MISSING", "errors": [f"missing immutable evidence: {', '.join(missing)}"]}
        try:
            records = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in required.items()}
        except (OSError, json.JSONDecodeError) as exc:
            return {"pass": False, "status": "CORRUPT", "errors": [str(exc)]}
        smoke = records["smoke"]
        smoke_checks = smoke.get("checks", {})
        adapter = smoke.get("adapter_evidence", {})
        application = adapter.get("candidate_application", {}) if isinstance(adapter, Mapping) else {}
        root_log = records["root_execution_log"]
        smoke_log = records["smoke_execution_log"]
        preflight = records["preflight"].get("result", {})
        frozen_config = records["frozen_config"]
        checks = {
            "smoke_status": smoke.get("name") == "BASELINE_B_EXECUTION_READINESS_SMOKE" and smoke.get("status") == "PASS",
            "smoke_checks": isinstance(smoke_checks, Mapping) and all(value is True for value in smoke_checks.values() if isinstance(value, bool)),
            "candidate_accepted": adapter.get("candidate_accepted") is True if isinstance(adapter, Mapping) else False,
            "bounded_application": application.get("application_mode") == "SAFE_TEST_DOUBLE_BOUNDARY" and application.get("generated_code_executed") is False,
            "runtime_ground_truth_not_provided": smoke.get("runtime_ground_truth_payload") == "NOT_PROVIDED",
            "smoke_log_status": smoke_log.get("status") == "BASELINE_B_SMOKE_PASS_STOPPED_BEFORE_BENCHMARK",
            "preflight_passed": preflight.get("passed") is True if isinstance(preflight, Mapping) else False,
            "frozen_config_hash": frozen_config.get("configuration_hash") == EXPECTED_CONFIGURATION_HASH,
            "benchmark_runs_zero": root_log.get("benchmark_runs_executed") == 0,
            "provider_operations_zero": root_log.get("provider_operations_executed") == 0,
            "healing_zero": root_log.get("healing_operations_executed") == 0,
            "metrics_zero": root_log.get("metric_results_generated", root_log.get("metric_values_generated")) == 0,
            "execution_unauthorized": root_log.get("execution_authorized", root_log.get("benchmark_execution_authorized")) is False,
        }
        return {"pass": all(checks.values()), "status": "VALID" if all(checks.values()) else "INVALID", "checks": checks, "errors": [name for name, value in checks.items() if value is False]}

    def _trial_input(self, participant_id: str, mutation_id: str, trial_number: int, seed: int) -> TrialParticipantExecutionInput:
        return TrialParticipantExecutionInput(
            benchmark_id=self.config.benchmark_id,
            benchmark_run_id=self.benchmark_run_id,
            configuration_hash=self.config.configuration_hash,
            participant_id=participant_id,
            mutation_id=mutation_id,
            severity=self.config.mutation_severity[mutation_id],
            seed=seed,
            trial_number=trial_number,
            fixture_version=self.config.fixture_version,
            ground_truth_reference=deterministic_ground_truth_reference(self.config, mutation_id, seed, trial_number),
            code_revision=self.config.code_revision,
            environment_reference=self.config.environment_reference,
            timeout_policy=self.config.timeout_policy,
            retry_policy=self.config.retry_policy,
            artifact_root=str(self.output_root),
            trial_metadata={
                "trial_number": trial_number,
                "baseline_independent": True,
                "ground_truth_runtime_payload": "NOT_PROVIDED",
                "metric_calculation": "DOWNSTREAM_MISSION_010_ONLY",
            },
        )

    def plan_manifests(self) -> tuple[RunManifest, ...]:
        manifests: list[RunManifest] = []
        for participant_id in PARTICIPANT_IDS:
            readiness = self.registry.get(participant_id).readiness(self.config)
            for mutation_id in EXPECTED_MUTATIONS:
                for trial_number in range(1, TRIALS_PER_MUTATION + 1):
                    for seed in self.config.seeds:
                        execution_input = self._trial_input(participant_id, mutation_id, trial_number, seed)
                        manifests.append(
                            RunManifest(
                                benchmark_id=execution_input.benchmark_id,
                                configuration_hash=execution_input.configuration_hash,
                                participant_id=participant_id,
                                participant_revision=readiness.participant_revision,
                                participant_configuration_hash=readiness.participant_configuration_hash,
                                mutation_id=mutation_id,
                                severity=execution_input.severity,
                                seed=seed,
                                fixture_version=execution_input.fixture_version,
                                ground_truth_reference=execution_input.ground_truth_reference,
                                code_revision=execution_input.code_revision,
                                environment_reference=execution_input.environment_reference,
                                timeout_policy=execution_input.timeout_policy,
                                retry_policy=execution_input.retry_policy,
                                artifact_root=execution_input.artifact_root,
                                run_id=execution_input.run_id,
                                artifact_name=execution_input.artifact_name,
                            )
                        )
        return tuple(manifests)

    def execution_gate(self) -> ExecutionGateResult:
        errors: list[str] = []
        validation = validate_config(self.config)
        snapshot = FreezeSnapshot.from_config(self.config)
        freeze_validation = validate_freeze(self.config, snapshot)
        readiness = self.registry.readiness(self.config) if validation.valid else {}
        smoke = self.smoke_evidence_validator()
        source_checks = {
            participant: self.source_revision_checker(revision, SOURCE_FILES[participant])
            for participant, revision in self.expected_source_revisions.items()
        }
        spec_by_id = {spec.baseline_id: spec for spec in self.config.baselines}
        participant_revision_checks = {
            participant: readiness.get(participant) is not None and readiness[participant].participant_revision == spec_by_id[participant].implementation_revision
            for participant in PARTICIPANT_IDS
        }
        fixture_clean = self.fixture_controller.validate_clean().passed
        shared_inputs = [self._trial_input(participant, "M001", 1, EXPECTED_SEED).shared_metadata() for participant in PARTICIPANT_IDS]
        fairness = shared_inputs[0] == shared_inputs[1] == shared_inputs[2] and all(
            item["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED" for item in shared_inputs
        )
        try:
            self.layout.validate_isolation()
            isolation = True
        except ValueError:
            isolation = False
        output_matches = self.output_root == self.layout.root.resolve()
        output_absent = not self.output_root.exists()
        duplicate_free = len({manifest.run_id for manifest in self.plan_manifests()}) == self.expected_run_count if validation.valid else False
        checks: dict[str, Any] = {
            "configuration_hash": self.config.configuration_hash == EXPECTED_CONFIGURATION_HASH,
            "configuration_validation": validation.valid,
            "freeze_validation": freeze_validation.valid,
            "participant_source_revisions": all(source_checks.values()),
            "participant_revision_metadata": all(participant_revision_checks.values()),
            "participants_ready": bool(readiness) and all(report.ready for report in readiness.values()),
            "fairness": fairness,
            "fixture_clean": fixture_clean,
            "smoke_evidence": smoke.get("pass") is True,
            "artifact_root_isolated": isolation,
            "artifact_root_matches_deterministic_run": output_matches,
            "artifact_root_absent": output_absent,
            "benchmark_run_id": self.benchmark_run_id == EXPECTED_BENCHMARK_RUN_ID,
            "no_duplicate_run_ids": duplicate_free,
            "code_config_freeze": freeze_validation.valid and all(source_checks.values()),
            "metric_authority_available": callable(getattr(__import__("aegis.mutation_metrics", fromlist=["calculate_metrics"]), "calculate_metrics", None)),
            "model_caller_available": self.model_caller is not None,
            "planned_run_count": self.expected_run_count == 180,
        }
        for name, passed in checks.items():
            if isinstance(passed, bool) and not passed:
                errors.append(name)
        return ExecutionGateResult(
            passed=not errors,
            benchmark_run_id=self.benchmark_run_id,
            configuration_hash=self.config.configuration_hash,
            expected_run_count=self.expected_run_count,
            checks={**checks, "source_revision_checks": source_checks, "participant_revision_checks": participant_revision_checks, "smoke_evidence_detail": smoke},
            errors=tuple(errors),
        )

    def _write_exclusive(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            json.dump(_to_jsonable(payload), handle, sort_keys=True, indent=2, separators=(",", ": "))
            handle.write("\n")

    def _write_replaceable(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2, separators=(",", ": ")) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def _trial_number_from_manifest(manifest: RunManifest) -> int:
        return int(manifest.run_id.split("__trial-", 1)[1].split("__", 1)[0])

    def _manifest_payload(self, manifest: RunManifest) -> Mapping[str, Any]:
        return {
            **manifest.to_dict(),
            "benchmark_run_id": self.benchmark_run_id,
            "trial_number": self._trial_number_from_manifest(manifest),
        }

    def _persist_manifest(self, manifests: Sequence[RunManifest]) -> None:
        self._write_exclusive(
            self.layout.participant_manifest,
            {
                "manifest_version": "mission-021-participant-manifest-v1",
                "benchmark_run_id": self.benchmark_run_id,
                "configuration_hash": self.config.configuration_hash,
                "planned_runs": len(manifests),
                "runs": [self._manifest_payload(manifest) for manifest in manifests],
            },
        )

    def _persist_raw(self, manifest: RunManifest, state: RunnerState, evidence: ParticipantRunEvidence | None, errors: Sequence[str] = ()) -> None:
        payload = {
            "artifact_schema": "participant-run-evidence-v1",
            "benchmark_run_id": self.benchmark_run_id,
            "terminal_state": state.value,
            "manifest": self._manifest_payload(manifest),
            "evidence": None if evidence is None else evidence.to_dict(),
            "errors": tuple(errors),
        }
        self._write_exclusive(self.output_root / "raw" / manifest.artifact_name, payload)

    def _metric_run(self, manifest: RunManifest, trial_number: int, seed: int) -> tuple[MutationRun, Mapping[str, Any]] | None:
        if manifest.participant_id != "AEGIS" or self.lab.last_run is None:
            return None
        truth = self.fixture_controller.lab.apply_mutation(manifest.mutation_id, seed).ground_truth
        stable_truth_id = f"{manifest.mutation_id}-{seed}-trial-{trial_number}"
        stable_reference = f"ground-truth://{self.config.fixture_id}/v{self.config.fixture_version}/{stable_truth_id}"
        return replace(self.lab.last_run, run_id=manifest.run_id, ground_truth_reference=stable_reference), {stable_truth_id: truth}

    def execute(self) -> ExecutionSummary:
        gate = self.execution_gate()
        if not gate.passed:
            return ExecutionSummary(
                status="BLOCKED_NOT_READY",
                benchmark_run_id=self.benchmark_run_id,
                configuration_hash=self.config.configuration_hash,
                planned_runs=self.expected_run_count,
                completed_runs=0,
                failed_runs=0,
                timed_out_runs=0,
                invalidated_runs=0,
                benchmark_runs_executed=0,
                provider_operations_executed=0,
                healing_operations_executed=0,
                metric_results_generated=0,
                execution_authorized=False,
                gate=gate,
                errors=gate.errors,
            )

        manifests = self.plan_manifests()
        self.layout.create_empty_layout()
        self._write_exclusive(self.layout.frozen_config, self.config.to_dict())
        self._persist_manifest(manifests)
        self._write_replaceable(self.layout.execution_log, {"status": "RUNNING", "benchmark_run_id": self.benchmark_run_id, "planned_runs": len(manifests), "runs": []})

        completed = failed = timed_out = invalidated = attempted = provider_operations = 0
        run_records: list[Mapping[str, Any]] = []
        evidence_records: list[ParticipantRunEvidence] = []
        ground_truths_by_reference: dict[str, Any] = {}
        contexts_by_run_id: dict[str, ParticipantEvidenceContext] = {}
        errors: list[str] = []
        stopped_reason: str | None = None

        for manifest in manifests:
            trial_number = int(manifest.run_id.split("__trial-", 1)[1].split("__", 1)[0])
            clean_before = self.fixture_controller.validate_clean()
            if not clean_before.passed:
                state = RunnerState.INVALIDATED
                reason = clean_before.reason
                invalidated += 1
                self._persist_raw(manifest, state, None, (reason,))
                run_records.append({"run_id": manifest.run_id, "state": state.value, "errors": [reason]})
                errors.append(reason)
                stopped_reason = "fixture_not_clean_before_trial"
                break

            case = self.fixture_controller.apply(manifest.mutation_id, manifest.seed)
            adapter = self.registry.get(manifest.participant_id)
            execution_input = self._trial_input(manifest.participant_id, manifest.mutation_id, trial_number, manifest.seed)
            ground_truths_by_reference[execution_input.ground_truth_reference] = case.ground_truth
            contexts_by_run_id[manifest.run_id] = ParticipantEvidenceContext(
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
                trial_number=trial_number,
                artifact_root=manifest.artifact_root,
                artifact_name=manifest.artifact_name,
            )
            evidence: ParticipantRunEvidence | None = None
            state = RunnerState.COMPLETED
            trial_errors: tuple[str, ...] = ()
            attempted += 1
            if manifest.participant_id == "BASELINE_B":
                provider_operations += 1
            try:
                prepared = adapter.prepare(execution_input)
                evidence = adapter.return_run_evidence(adapter.collect_result(adapter.run_mutation(prepared)))
                if isinstance(evidence, ParticipantRunEvidence):
                    evidence = replace(evidence, participant_revision=manifest.participant_revision)
                if isinstance(evidence, ParticipantRunEvidence) and evidence.failure_state not in {"COMPLETED", "NOT_APPLICABLE"}:
                    state = RunnerState.FAILED
                    trial_errors = (evidence.failure_state,)
            except TimeoutError as exc:
                state = RunnerState.TIMED_OUT
                trial_errors = (str(exc),)
            except Exception as exc:  # explicit terminal boundary; never convert failure to success
                state = RunnerState.FAILED
                trial_errors = (str(exc),)

            reset_result = self.fixture_controller.reset()
            if not reset_result.passed:
                state = RunnerState.INVALIDATED
                trial_errors = (*trial_errors, reset_result.reason)
                stopped_reason = "fixture_reset_failure"

            if state is RunnerState.COMPLETED:
                completed += 1
            elif state is RunnerState.FAILED:
                failed += 1
            elif state is RunnerState.TIMED_OUT:
                timed_out += 1
            elif state is RunnerState.INVALIDATED:
                invalidated += 1

            if state is RunnerState.COMPLETED and evidence is not None:
                evidence_records.append(evidence)
            self._persist_raw(manifest, state, evidence, trial_errors)
            run_records.append({"run_id": manifest.run_id, "state": state.value, "errors": trial_errors, "evidence_present": evidence is not None})
            if state is RunnerState.INVALIDATED:
                errors.extend(trial_errors)
                break

        metric_results_generated = 0
        status = "COMPLETED" if completed == self.expected_run_count else "FAILED"
        if status == "COMPLETED":
            if len(evidence_records) != self.expected_run_count:
                status = "FAILED_METRIC_BOUNDARY"
                errors.append(
                    "FAILED_METRIC_BOUNDARY: completed run count does not equal completed ParticipantRunEvidence count: "
                    f"{completed} vs {len(evidence_records)}"
                )
                stopped_reason = "metric_boundary_incompatible"
            else:
                compatibility = adapt_completed_evidence(
                    evidence_records,
                    ground_truths_by_reference,
                    contexts_by_run_id,
                )
                self._write_exclusive(
                    self.layout.root / "reports" / "mission-022-metric-boundary-compatibility.json",
                    compatibility.to_dict(),
                )
                if not compatibility.passed:
                    status = "FAILED_METRIC_BOUNDARY"
                    errors.extend(compatibility.fatal_errors or ("FAILED_METRIC_BOUNDARY: no eligible metric inputs",))
                    stopped_reason = "metric_boundary_incompatible"
                else:
                    try:
                        report = calculate_compatibility_metrics(compatibility)
                        self._write_exclusive(self.layout.root / "metrics" / "mission-010-metrics.json", json.loads(report.to_json()))
                        metric_results_generated = len(report.results)
                    except MetricBoundaryError as exc:
                        status = "FAILED_METRIC_BOUNDARY"
                        errors.append(str(exc))
                        stopped_reason = "metric_boundary_incompatible"
        final_log = {
            "status": status,
            "benchmark_run_id": self.benchmark_run_id,
            "configuration_hash": self.config.configuration_hash,
            "planned_runs": self.expected_run_count,
            "completed_runs": completed,
            "failed_runs": failed,
            "timed_out_runs": timed_out,
            "invalidated_runs": invalidated,
            "benchmark_runs_executed": attempted,
            "provider_operations_executed": provider_operations,
            "healing_operations_executed": 0,
            "metric_results_generated": metric_results_generated,
            "execution_authorized": True,
            "runs": run_records,
            "errors": errors,
            "stopped_reason": stopped_reason,
        }
        self._write_replaceable(self.layout.execution_log, final_log)
        return ExecutionSummary(
            status=status,
            benchmark_run_id=self.benchmark_run_id,
            configuration_hash=self.config.configuration_hash,
            planned_runs=self.expected_run_count,
            completed_runs=completed,
            failed_runs=failed,
            timed_out_runs=timed_out,
            invalidated_runs=invalidated,
            benchmark_runs_executed=attempted,
            provider_operations_executed=provider_operations,
            healing_operations_executed=0,
            metric_results_generated=metric_results_generated,
            execution_authorized=True,
            gate=gate,
            errors=tuple(errors),
            stopped_reason=stopped_reason,
        )


__all__ = [
    "BenchmarkExecutor",
    "EXPECTED_BENCHMARK_RUN_ID",
    "EXPECTED_CONFIGURATION_HASH",
    "EXPECTED_MUTATIONS",
    "EXPECTED_SEED",
    "EXPECTED_SOURCE_REVISIONS",
    "ExecutionGateResult",
    "ExecutionSummary",
    "FixtureController",
    "TRIALS_PER_MUTATION",
    "deterministic_ground_truth_reference",
    "deterministic_trial_artifact_name",
    "deterministic_trial_run_id",
]
