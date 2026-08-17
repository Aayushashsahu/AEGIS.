"""Deterministic provider test double for Mission 002.

This module never claims Bright Data behavior. Every handle is labeled TEST_DOUBLE.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from .models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    CollectorHandle,
    CollectorRequest,
    ProviderProvenance,
)


class TestDoubleScenario(str, Enum):
    __test__ = False

    HEALTHY = "HEALTHY"
    MISSING_FIELD = "MISSING_FIELD"
    TYPE_CORRUPTION = "TYPE_CORRUPTION"
    STATISTICAL_DRIFT = "STATISTICAL_DRIFT"
    SEMANTIC_CORRUPTION = "SEMANTIC_CORRUPTION"
    TIMEOUT = "TIMEOUT"


_BASE_ROWS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "Mission 002 test story",
        "url": "https://example.test/story/1",
        "points": 42,
        "author": "aegis",
        "comment_count": 7,
    },
    {
        "title": "Second mission story",
        "url": "https://example.test/story/2",
        "points": 12,
        "author": "evidence",
        "comment_count": 3,
    },
)


class DeterministicBrightDataTestDouble:
    """A credit-free, deterministic adapter-shaped provider substitute."""

    provider = ProviderProvenance.TEST_DOUBLE

    def __init__(self, scenario: TestDoubleScenario = TestDoubleScenario.HEALTHY) -> None:
        self.scenario = scenario
        self._outputs: dict[str, CollectionResult] = {}
        self._handles: dict[str, CollectionHandle] = {}
        self._polls: dict[str, int] = {}

    def create_collector(self, request: CollectorRequest) -> CollectorHandle:
        return CollectorHandle(
            collector_id=request.collector_id or "test-double-collector",
            provider=self.provider,
            provider_reference="TEST_DOUBLE",
        )

    def run_collector(self, collector: CollectorHandle, *, target_url: str, timeout_seconds: float = 1.0, mode: CollectionMode = CollectionMode.TEST_DOUBLE) -> CollectionHandle:
        if collector.provider is not self.provider:
            raise ValueError("test double accepts TEST_DOUBLE collectors only")
        handle = CollectionHandle(
            collector_id=collector.collector_id,
            mode=CollectionMode.TEST_DOUBLE,
            provider_provenance=self.provider,
            provider_operation_ids={"test_run_id": f"test-run-{len(self._handles) + 1}"},
            evidence_refs=("evidence://TEST_DOUBLE/mission-002",),
        )
        self._handles[handle.collection_id] = handle
        self._polls[handle.collection_id] = 0
        self._outputs[handle.collection_id] = CollectionResult(
            handle=handle,
            output=self._scenario_output(),
        )
        return handle

    def poll_collection(self, handle: CollectionHandle) -> CollectionHandle:
        current = self._handles[handle.collection_id]
        polls = self._polls[handle.collection_id]
        self._polls[handle.collection_id] = polls + 1
        if self.scenario is TestDoubleScenario.TIMEOUT:
            if current.status is CollectionState.SUBMITTED:
                current = current.transition(CollectionState.RUNNING)
            else:
                current = current.transition(CollectionState.TIMED_OUT, error_code="PROVIDER_TIMEOUT")
        elif current.status is CollectionState.SUBMITTED:
            current = current.transition(CollectionState.RUNNING)
        elif current.status is CollectionState.RUNNING:
            output = self._outputs[current.collection_id].output
            current = current.transition(
                CollectionState.COMPLETED,
                provider_status="TEST_DOUBLE_COMPLETED",
                latency_ms=1,
                output_schema=tuple(sorted({key for row in output for key in row})),
            )
            self._outputs[current.collection_id] = CollectionResult(handle=current, output=output)
        self._handles[current.collection_id] = current
        return current

    def retrieve_output(self, handle: CollectionHandle) -> CollectionResult:
        current = self._handles[handle.collection_id]
        if current.status is not CollectionState.COMPLETED:
            raise ValueError(f"test-double collection is not complete: {current.status.value}")
        return self._outputs[handle.collection_id]

    def _scenario_output(self) -> tuple[Mapping[str, Any], ...]:
        rows = [dict(row) for row in _BASE_ROWS]
        if self.scenario is TestDoubleScenario.MISSING_FIELD:
            rows[0].pop("author")
        elif self.scenario is TestDoubleScenario.TYPE_CORRUPTION:
            rows[0]["points"] = "forty-two"
        elif self.scenario is TestDoubleScenario.STATISTICAL_DRIFT:
            rows = rows[:1]
        elif self.scenario is TestDoubleScenario.SEMANTIC_CORRUPTION:
            rows[0]["url"] = "not-a-url"
        return tuple(rows)
