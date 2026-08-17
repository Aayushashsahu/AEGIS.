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


from datetime import datetime, timedelta, timezone

from .diagnosis import RepairRequest
from .healing import (
    HealHandle,
    HealOperationResult,
    HealProviderEnvelope,
    HealState,
    RepairCandidate,
    VerificationStatus,
)


class HealTestDoubleScenario(str, Enum):
    __test__ = False
    HEAL_AWAITING_APPROVAL = "HEAL_AWAITING_APPROVAL"
    HEAL_MALFORMED_RESPONSE = "HEAL_MALFORMED_RESPONSE"
    HEAL_TIMEOUT = "HEAL_TIMEOUT"
    HEAL_PROVIDER_FAILURE = "HEAL_PROVIDER_FAILURE"


class DeterministicBrightDataHealingTestDouble:
    """Local healing substitute; every result is explicitly TEST_DOUBLE and UNVERIFIED."""

    provider = ProviderProvenance.TEST_DOUBLE

    def __init__(self, scenario: HealTestDoubleScenario = HealTestDoubleScenario.HEAL_AWAITING_APPROVAL) -> None:
        self.scenario = scenario
        self._handles: dict[str, HealHandle] = {}
        self._envelopes: dict[str, HealProviderEnvelope] = {}
        self._candidates: dict[str, RepairCandidate] = {}

    def request_healing(self, repair_request: RepairRequest, *, timeout_seconds: float = 30.0) -> HealHandle:
        handle = HealHandle(
            repair_request_id=repair_request.repair_request_id,
            collector_reference=repair_request.collector_reference,
            correlation_id=repair_request.correlation_id,
            provider_provenance=self.provider,
            deadline=datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds),
            evidence_refs=(f"evidence://TEST_DOUBLE/heal/{repair_request.repair_request_id}",),
        )
        self._handles[handle.heal_id] = handle
        return handle

    def poll_healing(self, handle: HealHandle) -> HealHandle:
        current = self._handles[handle.heal_id]
        if current.status in {HealState.CANDIDATE_READY, HealState.FAILED, HealState.TIMED_OUT}:
            return current
        if current.status is HealState.SUBMITTED:
            current = current.transition(HealState.RUNNING)
        elif self.scenario is HealTestDoubleScenario.HEAL_TIMEOUT:
            current = current.transition(HealState.TIMED_OUT, error_code="PROVIDER_TIMEOUT", error_message="test-double timeout")
        elif self.scenario is HealTestDoubleScenario.HEAL_PROVIDER_FAILURE:
            current = current.transition(HealState.FAILED, error_code="PROVIDER_COMMAND_FAILED", error_message="test-double provider failure")
        elif self.scenario is HealTestDoubleScenario.HEAL_MALFORMED_RESPONSE:
            current = current.transition(HealState.FAILED, error_code="MALFORMED_PROVIDER_RESPONSE", error_message="test-double malformed response")
        elif current.status is HealState.RUNNING:
            envelope = HealProviderEnvelope(
                collector_reference=current.collector_reference,
                provider_status="awaiting_approval",
                provider_operation_reference="test-heal-operation-1",
                preview_result={"status": "preview", "provenance": "TEST_DOUBLE"},
                diff_summary="test-double proposed repair",
                approval_command="NOT_EXECUTED_TEST_DOUBLE_APPROVAL",
                evidence_ref=current.evidence_refs[0],
            )
            self._envelopes[current.heal_id] = envelope
            self._candidates[current.heal_id] = RepairCandidate(
                repair_request_id=current.repair_request_id,
                collector_reference=current.collector_reference,
                provider_operation_reference=envelope.provider_operation_reference,
                provider_status=envelope.provider_status,
                preview_result=envelope.preview_result,
                diff_summary=envelope.diff_summary,
                approval_command=envelope.approval_command,
                raw_evidence_ref=envelope.evidence_ref,
                provenance=self.provider,
                verification_status=VerificationStatus.UNVERIFIED,
                latency_ms=1,
            )
            current = current.transition(
                HealState.AWAITING_APPROVAL,
                provider_operation_reference=envelope.provider_operation_reference,
                provider_status=envelope.provider_status,
                latency_ms=1,
            )
        self._handles[current.heal_id] = current
        return current

    def retrieve_heal_result(self, handle: HealHandle) -> HealOperationResult:
        current = self.poll_healing(handle)
        if current.status not in {HealState.AWAITING_APPROVAL, HealState.CANDIDATE_READY}:
            raise ValueError(f"test-double heal is not ready: {current.status.value}")
        return HealOperationResult(
            handle=current,
            envelope=self._envelopes.get(current.heal_id),
            candidate=self._candidates.get(current.heal_id),
        )
