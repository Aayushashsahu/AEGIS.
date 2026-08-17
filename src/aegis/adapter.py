"""Provider adapter boundary for the verified Mission 001 Bright Data CLI path."""

from __future__ import annotations

import json
import re
import subprocess
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic, perf_counter
from typing import Callable, Mapping, Sequence

from .models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    CollectorHandle,
    CollectorRequest,
    ProviderProvenance,
    utc_now,
)


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str = ""
    returncode: int = 0
    latency_ms: int | None = None


CommandRunner = Callable[[Sequence[str]], CommandResult]


class AdapterError(RuntimeError):
    """Raised when the provider boundary cannot create a valid AEGIS record."""


def subprocess_runner(command: Sequence[str]) -> CommandResult:
    """Run one documented CLI command without embedding credentials."""

    started = perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    latency_ms = round((perf_counter() - started) * 1000)
    return CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
        latency_ms=latency_ms,
    )


def _json_values(text: str) -> list[object]:
    decoder = json.JSONDecoder()
    values: list[object] = []
    for match in re.finditer(r"[\[{]", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        values.append(value)
    return values


def _last_object(text: str) -> Mapping[str, object] | None:
    for value in reversed(_json_values(text)):
        if isinstance(value, dict):
            return value
    return None


def _last_array(text: str) -> list[Mapping[str, object]] | None:
    for value in reversed(_json_values(text)):
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value
    return None


class BrightDataCliAdapter:
    """Small async adapter around the tested Bright Data CLI command path.

    The default runner uses the locally authenticated CLI session. Tests inject a
    deterministic runner and never contact Bright Data. The adapter stores only
    redacted evidence references, never credentials or raw authorization headers.
    """

    provider = ProviderProvenance.BRIGHT_DATA

    def __init__(
        self,
        runner: CommandRunner = subprocess_runner,
        *,
        max_workers: int = 2,
        executor: ThreadPoolExecutor | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._runner = runner
        self._executor = executor or ThreadPoolExecutor(max_workers=max_workers)
        self._owns_executor = executor is None
        self._clock = clock
        self._jobs: dict[str, Future[CommandResult]] = {}
        self._handles: dict[str, CollectionHandle] = {}
        self._outputs: dict[str, CollectionResult] = {}

    def close(self) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=True, cancel_futures=True)

    def __enter__(self) -> "BrightDataCliAdapter":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def create_collector(self, request: CollectorRequest) -> CollectorHandle:
        if request.provider is not ProviderProvenance.BRIGHT_DATA:
            raise AdapterError("BrightDataCliAdapter accepts BRIGHT_DATA requests only")
        command = [
            "npx",
            "-p",
            "@brightdata/cli",
            "bdata",
            "scraper",
            "create",
            request.target_url,
            request.extraction_prompt,
        ]
        result = self._runner(command)
        if result.returncode != 0:
            raise AdapterError(f"collector creation failed: {result.stderr.strip() or 'provider error'}")
        payload = _last_object(result.stdout)
        collector_id = request.collector_id or (str(payload.get("collector_id")) if payload else "")
        if not collector_id:
            raise AdapterError("collector creation returned no collector_id")
        return CollectorHandle(
            collector_id=collector_id,
            provider=self.provider,
            provider_reference=str(payload.get("view_url")) if payload and payload.get("view_url") else None,
            created_at=utc_now(),
        )

    def run_collector(
        self,
        collector: CollectorHandle,
        *,
        target_url: str,
        timeout_seconds: float = 900.0,
        mode: CollectionMode = CollectionMode.REALTIME,
    ) -> CollectionHandle:
        """Submit a CLI run to a background worker and return immediately."""

        if collector.provider is not ProviderProvenance.BRIGHT_DATA:
            raise AdapterError("collector provenance is not BRIGHT_DATA")
        if mode not in {CollectionMode.REALTIME, CollectionMode.BATCH}:
            raise AdapterError("Bright Data runs must start in REALTIME or BATCH mode")
        requested_at = utc_now()
        handle = CollectionHandle(
            collector_id=collector.collector_id,
            requested_at=requested_at,
            mode=mode,
            provider_provenance=self.provider,
            evidence_refs=(f"evidence://bright-data/cli/run/{collector.collector_id}",),
        )
        deadline = self._clock() + timeout_seconds
        command = [
            "npx",
            "-p",
            "@brightdata/cli",
            "bdata",
            "scraper",
            "run",
            collector.collector_id,
            target_url,
            "--pretty",
        ]
        future = self._executor.submit(self._runner, command)
        self._jobs[handle.collection_id] = future
        self._handles[handle.collection_id] = handle
        setattr(future, "_aegis_deadline", deadline)
        return handle

    def poll_collection(self, handle: CollectionHandle) -> CollectionHandle:
        """Advance an operation without blocking for provider completion."""

        current = self._handles.get(handle.collection_id, handle)
        future = self._jobs.get(handle.collection_id)
        if future is None:
            raise AdapterError(f"unknown collection_id: {handle.collection_id}")
        if current.status in {CollectionState.COMPLETED, CollectionState.FAILED, CollectionState.TIMED_OUT}:
            return current
        deadline = getattr(future, "_aegis_deadline")
        if not future.done() and self._clock() >= deadline:
            future.cancel()
            current = current.transition(
                CollectionState.TIMED_OUT,
                error_code="PROVIDER_TIMEOUT",
                error_message="collection exceeded its bounded deadline",
            )
            self._handles[current.collection_id] = current
            return current
        if current.status is CollectionState.SUBMITTED:
            current = current.transition(CollectionState.RUNNING)
            self._handles[current.collection_id] = current
            if not future.done():
                return current
        if not future.done():
            return current
        result = future.result()
        if result.returncode != 0:
            current = current.transition(
                CollectionState.FAILED,
                provider_status="FAILED",
                latency_ms=result.latency_ms,
                error_code="PROVIDER_UNAVAILABLE",
                error_message=result.stderr.strip() or "provider command failed",
            )
            self._handles[current.collection_id] = current
            return current
        output = _last_array(result.stdout) or []
        provider_ids: dict[str, str] = {}
        response_match = re.search(r"response_id:\s*([^\s)]+)", result.stdout)
        batch_match = re.search(r"Batch job:\s*(j_[A-Za-z0-9]+)", result.stdout)
        if response_match:
            provider_ids["response_id"] = response_match.group(1)
        if batch_match:
            provider_ids["batch_job_id"] = batch_match.group(1)
        observed_mode = CollectionMode.BATCH if "switching to batch mode" in result.stdout.lower() else current.mode
        schema = tuple(sorted({key for row in output for key in row}))
        current = current.transition(
            CollectionState.COMPLETED,
            mode=observed_mode,
            provider_operation_ids=provider_ids,
            provider_status="COMPLETED",
            latency_ms=result.latency_ms,
            output_schema=schema,
        )
        self._handles[current.collection_id] = current
        self._outputs[current.collection_id] = CollectionResult(handle=current, output=output)
        return current

    def retrieve_output(self, handle: CollectionHandle) -> CollectionResult:
        """Return structured output only after a completed poll result exists."""

        current = self.poll_collection(handle)
        if current.status is not CollectionState.COMPLETED:
            raise AdapterError(f"collection is not complete: {current.status.value}")
        return self._outputs[current.collection_id]

    def current_handle(self, collection_id: str) -> CollectionHandle:
        try:
            return self._handles[collection_id]
        except KeyError as exc:
            raise AdapterError(f"unknown collection_id: {collection_id}") from exc
