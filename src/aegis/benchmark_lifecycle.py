"""Mission 020 lifecycle and artifact-isolation contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence


class BenchmarkLifecyclePhase(str, Enum):
    PREFLIGHT = "PREFLIGHT"
    SMOKE = "SMOKE"
    BENCHMARK_EXECUTION = "BENCHMARK_EXECUTION"


def deterministic_benchmark_run_id(
    configuration_hash: str,
    attempt_id: str,
    participant_revisions: Mapping[str, str],
) -> str:
    """Derive a stable benchmark-run identity from frozen execution inputs."""

    if not configuration_hash or not attempt_id or not participant_revisions:
        raise ValueError("configuration hash, attempt ID, and participant revisions are required")
    payload = {
        "attempt_id": attempt_id,
        "configuration_hash": configuration_hash,
        "participant_revisions": dict(sorted(participant_revisions.items())),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return f"mission_020_floor_{digest}"


@dataclass(frozen=True)
class BenchmarkArtifactLayout:
    """Provider-neutral layout for a future benchmark attempt."""

    run_id: str
    runs_root: Path
    smoke_root: Path

    @property
    def root(self) -> Path:
        return self.runs_root / self.run_id

    @property
    def frozen_config(self) -> Path:
        return self.root / "frozen_config.json"

    @property
    def participant_manifest(self) -> Path:
        return self.root / "participant_manifest.json"

    @property
    def execution_log(self) -> Path:
        return self.root / "execution_log.json"

    @property
    def phase_directories(self) -> tuple[Path, ...]:
        return tuple(self.root / name for name in ("raw", "observations", "decisions", "metrics", "reports"))

    def validate_isolation(self) -> None:
        benchmark_root = self.root.resolve()
        smoke_root = self.smoke_root.resolve()
        try:
            benchmark_root.relative_to(smoke_root)
            raise ValueError(f"benchmark artifact root {benchmark_root} overlaps immutable smoke root {smoke_root}")
        except ValueError as exc:
            if str(exc).startswith("benchmark artifact root"):
                raise
        try:
            smoke_root.relative_to(benchmark_root)
        except ValueError:
            return
        raise ValueError(f"benchmark artifact root {benchmark_root} contains immutable smoke root {smoke_root}")

    def validate_absent(self) -> None:
        self.validate_isolation()
        if self.root.exists():
            raise FileExistsError(f"benchmark run directory already exists: {self.root}")

    def planned_paths(self) -> tuple[Path, ...]:
        return (self.frozen_config, self.participant_manifest, *self.phase_directories, self.execution_log)

    def create_empty_layout(self) -> None:
        """Create only a future benchmark directory; never touch smoke evidence."""

        self.validate_absent()
        for directory in self.phase_directories:
            directory.mkdir(parents=True, exist_ok=False)
        self.root.mkdir(parents=True, exist_ok=True)


__all__ = [
    "BenchmarkArtifactLayout",
    "BenchmarkLifecyclePhase",
    "deterministic_benchmark_run_id",
]
