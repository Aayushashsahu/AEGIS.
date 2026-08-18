"""Fail-closed resume state for the frozen AEGIS benchmark attempt."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .benchmark_runner import ParticipantRunEvidence, RunManifest, RunnerState


TERMINAL_STATES = frozenset({
    RunnerState.COMPLETED.value,
    RunnerState.FAILED.value,
    RunnerState.TIMED_OUT.value,
    RunnerState.INVALIDATED.value,
})


class ResumeValidationError(ValueError):
    """Raised when an existing benchmark root cannot be safely resumed."""


@dataclass(frozen=True)
class PersistedTerminalArtifact:
    manifest: RunManifest
    state: str
    payload: Mapping[str, Any]
    path: Path


@dataclass(frozen=True)
class ResumeInspection:
    benchmark_run_id: str
    artifacts_by_run_id: Mapping[str, PersistedTerminalArtifact]
    missing_manifests: tuple[RunManifest, ...]
    terminal_counts: Mapping[str, int]
    reconstructed_runs: tuple[Mapping[str, Any], ...]
    existing_artifact_digests: Mapping[str, str]

    @property
    def persisted_terminal_count(self) -> int:
        return len(self.artifacts_by_run_id)

    @property
    def missing_count(self) -> int:
        return len(self.missing_manifests)


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResumeValidationError(f"cannot read valid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ResumeValidationError(f"artifact is not a JSON object: {path}")
    return value


def _manifest_from_payload(payload: Mapping[str, Any]) -> RunManifest:
    raw = payload.get("manifest")
    if not isinstance(raw, Mapping):
        raise ResumeValidationError("raw artifact is missing manifest object")
    try:
        return RunManifest(
            benchmark_id=str(raw["benchmark_id"]),
            configuration_hash=str(raw["configuration_hash"]),
            participant_id=str(raw["participant_id"]),
            participant_revision=str(raw["participant_revision"]),
            participant_configuration_hash=str(raw["participant_configuration_hash"]),
            mutation_id=str(raw["mutation_id"]),
            severity=str(raw["severity"]),
            seed=int(raw["seed"]),
            fixture_version=str(raw["fixture_version"]),
            ground_truth_reference=str(raw["ground_truth_reference"]),
            code_revision=str(raw["code_revision"]),
            environment_reference=str(raw["environment_reference"]),
            timeout_policy=raw["timeout_policy"],
            retry_policy=raw["retry_policy"],
            artifact_root=str(raw["artifact_root"]),
            run_id=str(raw["run_id"]),
            artifact_name=str(raw["artifact_name"]),
            state=RunnerState.PLANNED,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ResumeValidationError(f"raw artifact manifest is malformed: {exc}") from exc


def _validate_manifest_identity(
    manifest: RunManifest,
    expected: RunManifest,
    *,
    expected_benchmark_run_id: str,
    expected_configuration_hash: str,
) -> None:
    fields = (
        "benchmark_id",
        "configuration_hash",
        "participant_id",
        "participant_revision",
        "participant_configuration_hash",
        "mutation_id",
        "severity",
        "seed",
        "fixture_version",
        "ground_truth_reference",
        "code_revision",
        "environment_reference",
        "timeout_policy",
        "retry_policy",
        "artifact_root",
        "run_id",
        "artifact_name",
    )
    for field in fields:
        if getattr(manifest, field) != getattr(expected, field):
            if field == "configuration_hash":
                raise ResumeValidationError(f"wrong configuration hash: {getattr(manifest, field)!r}")
            if field == "participant_revision":
                raise ResumeValidationError(f"wrong participant revision: {getattr(manifest, field)!r}")
            if field == "run_id":
                raise ResumeValidationError(f"wrong deterministic run ID: {getattr(manifest, field)!r}")
            raise ResumeValidationError(f"manifest identity mismatch for {field}: {getattr(manifest, field)!r}")
    if manifest.run_id != expected.run_id or manifest.run_id.split("__", 1)[0] != expected_benchmark_run_id:
        raise ResumeValidationError(f"wrong deterministic run ID: {manifest.run_id}")
    if manifest.configuration_hash != expected_configuration_hash:
        raise ResumeValidationError(f"wrong configuration hash: {manifest.configuration_hash}")


def deserialize_participant_evidence(payload: Mapping[str, Any]) -> ParticipantRunEvidence:
    raw = payload.get("evidence")
    if not isinstance(raw, Mapping):
        raise ResumeValidationError("completed raw artifact is missing ParticipantRunEvidence")
    try:
        values = dict(raw)
        values["state"] = RunnerState(str(values.get("state", RunnerState.COMPLETED.value)))
        values["evidence_refs"] = tuple(values.get("evidence_refs", ()))
        values["artifact_refs"] = tuple(values.get("artifact_refs", ()))
        return ParticipantRunEvidence(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ResumeValidationError(f"persisted ParticipantRunEvidence is malformed: {exc}") from exc


def inspect_existing_run(
    root: str | Path,
    manifests: Sequence[RunManifest],
    *,
    expected_benchmark_run_id: str,
    expected_configuration_hash: str,
    expected_participant_revisions: Mapping[str, str] | None = None,
) -> ResumeInspection:
    """Consume only valid terminal raw artifacts and derive missing manifests."""

    run_root = Path(root).resolve()
    manifest_by_run_id = {manifest.run_id: manifest for manifest in manifests}
    if len(manifest_by_run_id) != len(tuple(manifests)):
        raise ResumeValidationError("planned manifest contains duplicate run IDs")
    if not run_root.is_dir():
        raise ResumeValidationError(f"existing benchmark root is not a directory: {run_root}")
    for required_name in ("frozen_config.json", "participant_manifest.json", "execution_log.json"):
        if not (run_root / required_name).is_file():
            raise ResumeValidationError(f"existing benchmark root is missing {required_name}")
    frozen_config = _read_json(run_root / "frozen_config.json")
    if frozen_config.get("configuration_hash") != expected_configuration_hash:
        raise ResumeValidationError("existing frozen_config.json has the wrong configuration hash")
    persisted_manifest = _read_json(run_root / "participant_manifest.json")
    if persisted_manifest.get("benchmark_run_id") != expected_benchmark_run_id:
        raise ResumeValidationError("existing participant_manifest.json has the wrong benchmark run ID")
    if persisted_manifest.get("configuration_hash") != expected_configuration_hash:
        raise ResumeValidationError("existing participant_manifest.json has the wrong configuration hash")
    persisted_runs = persisted_manifest.get("runs")
    if not isinstance(persisted_runs, list) or len(persisted_runs) != len(manifests):
        raise ResumeValidationError("existing participant_manifest.json does not contain the frozen planned run set")
    persisted_run_ids = [item.get("run_id") for item in persisted_runs if isinstance(item, Mapping)]
    if len(persisted_run_ids) != len(manifests) or set(persisted_run_ids) != set(manifest_by_run_id):
        raise ResumeValidationError("existing participant_manifest.json run IDs do not match the deterministic plan")
    execution_log = _read_json(run_root / "execution_log.json")
    if execution_log.get("benchmark_run_id") != expected_benchmark_run_id or execution_log.get("planned_runs") != len(manifests):
        raise ResumeValidationError("existing execution_log.json identity does not match the deterministic plan")

    raw_root = run_root / "raw"
    artifacts_by_run_id: dict[str, PersistedTerminalArtifact] = {}
    digests: dict[str, str] = {}
    for path in sorted(raw_root.glob("*.json")) if raw_root.is_dir() else ():
        payload = _read_json(path)
        state = payload.get("terminal_state")
        if state not in TERMINAL_STATES:
            raise ResumeValidationError(f"non-terminal or missing terminal_state in {path}: {state!r}")
        manifest = _manifest_from_payload(payload)
        expected = manifest_by_run_id.get(manifest.run_id)
        if expected is None:
            raise ResumeValidationError(f"artifact run ID is not in deterministic manifest: {manifest.run_id}")
        _validate_manifest_identity(
            manifest,
            expected,
            expected_benchmark_run_id=expected_benchmark_run_id,
            expected_configuration_hash=expected_configuration_hash,
        )
        if expected_participant_revisions is not None and manifest.participant_revision != expected_participant_revisions.get(manifest.participant_id):
            raise ResumeValidationError(f"wrong participant revision for {manifest.participant_id}: {manifest.participant_revision}")
        if path.name != manifest.artifact_name:
            raise ResumeValidationError(f"artifact filename does not match manifest: {path.name}")
        if state == RunnerState.COMPLETED.value:
            deserialize_participant_evidence(payload)
        if manifest.run_id in artifacts_by_run_id:
            raise ResumeValidationError(f"duplicate terminal run ID: {manifest.run_id}")
        artifacts_by_run_id[manifest.run_id] = PersistedTerminalArtifact(manifest, str(state), payload, path)
        digests[str(path)] = _sha256(path)

    missing = tuple(manifest for manifest in manifests if manifest.run_id not in artifacts_by_run_id)
    counts = {state: 0 for state in sorted(TERMINAL_STATES)}
    for artifact in artifacts_by_run_id.values():
        counts[artifact.state] += 1
    reconstructed = tuple(
        {
            "run_id": manifest.run_id,
            "state": artifacts_by_run_id[manifest.run_id].state,
            "errors": tuple(artifacts_by_run_id[manifest.run_id].payload.get("errors", ())),
            "evidence_present": artifacts_by_run_id[manifest.run_id].payload.get("evidence") is not None,
        }
        for manifest in manifests
        if manifest.run_id in artifacts_by_run_id
    )
    return ResumeInspection(expected_benchmark_run_id, artifacts_by_run_id, missing, counts, reconstructed, digests)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct_execution_log(
    inspection: ResumeInspection,
    *,
    configuration_hash: str,
    status: str,
    planned_runs: int,
) -> Mapping[str, Any]:
    """Build a deterministic log projection without rewriting raw evidence."""

    counts = inspection.terminal_counts
    return {
        "status": status,
        "benchmark_run_id": inspection.benchmark_run_id,
        "configuration_hash": configuration_hash,
        "planned_runs": planned_runs,
        "completed_runs": counts.get(RunnerState.COMPLETED.value, 0),
        "failed_runs": counts.get(RunnerState.FAILED.value, 0),
        "timed_out_runs": counts.get(RunnerState.TIMED_OUT.value, 0),
        "invalidated_runs": counts.get(RunnerState.INVALIDATED.value, 0),
        "benchmark_runs_executed": inspection.persisted_terminal_count,
        "provider_operations_executed": sum(
            1
            for artifact in inspection.artifacts_by_run_id.values()
            if artifact.manifest.participant_id == "BASELINE_B"
        ),
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
        "execution_authorized": False,
        "runs": inspection.reconstructed_runs,
        "errors": [],
        "stopped_reason": "resume_pending" if inspection.missing_count else None,
    }


__all__ = [
    "PersistedTerminalArtifact",
    "ResumeInspection",
    "ResumeValidationError",
    "TERMINAL_STATES",
    "deserialize_participant_evidence",
    "inspect_existing_run",
    "reconstruct_execution_log",
]
