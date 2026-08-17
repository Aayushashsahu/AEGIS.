from __future__ import annotations

from dataclasses import replace
from time import sleep

import pytest

from aegis.adapter import BrightDataCliAdapter, CommandResult
from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    CollectorRequest,
    Observation,
    ProviderProvenance,
)
from aegis.test_double import DeterministicBrightDataTestDouble, TestDoubleScenario


def complete_test_double(scenario: TestDoubleScenario = TestDoubleScenario.HEALTHY) -> Observation:
    adapter = DeterministicBrightDataTestDouble(scenario)
    collector = adapter.create_collector(
        CollectorRequest("https://example.test", "extract stories", provider=ProviderProvenance.TEST_DOUBLE)
    )
    handle = adapter.run_collector(collector, target_url="https://example.test")
    running = adapter.poll_collection(handle)
    assert running.status is CollectionState.RUNNING
    completed = adapter.poll_collection(running)
    assert completed.status is CollectionState.COMPLETED
    result = adapter.retrieve_output(completed)
    return Observation.from_result(result, {"target_url": "https://example.test"})


def detection_codes(observation: Observation, contract=None) -> set[str]:
    result = evaluate_detection(observation, contract or default_extraction_contract())
    return {signal.code for signal in result.signals}


def observation_with_output(output, *, mode=CollectionMode.TEST_DOUBLE) -> Observation:
    handle = CollectionHandle(
        collector_id="test-double-collector",
        status=CollectionState.COMPLETED,
        mode=mode,
        provider_provenance=ProviderProvenance.TEST_DOUBLE,
        provider_operation_ids={"test_run_id": "test-run-manual"},
        latency_ms=1,
    )
    return Observation.from_result(
        CollectionResult(handle=handle, output=output),
        {"target_url": "https://example.test"},
    )


def test_healthy_observation_passes_without_false_alarm() -> None:
    result = evaluate_detection(complete_test_double(), default_extraction_contract())
    assert result.detected is False
    assert result.severity == "NONE"
    assert result.signals == ()
    assert set(result.detector_provenance) == {"schema", "statistical", "semantic"}


def test_missing_field_is_detected() -> None:
    result = evaluate_detection(complete_test_double(TestDoubleScenario.MISSING_FIELD), default_extraction_contract())
    assert result.detected is True
    assert "MISSING_FIELD" in {signal.code for signal in result.signals}
    assert "author" in result.affected_fields


def test_invalid_type_is_detected() -> None:
    result = evaluate_detection(complete_test_double(TestDoubleScenario.TYPE_CORRUPTION), default_extraction_contract())
    assert "INVALID_TYPE" in {signal.code for signal in result.signals}


def test_unexpected_null_is_detected() -> None:
    output = [dict(row) for row in complete_test_double().output]
    output[0]["author"] = None
    assert "NULL_FIELD" in detection_codes(observation_with_output(output))


def test_invalid_url_is_detected() -> None:
    result = evaluate_detection(complete_test_double(TestDoubleScenario.SEMANTIC_CORRUPTION), default_extraction_contract())
    assert "INVALID_URL" in {signal.code for signal in result.signals}


def test_impossible_numeric_value_is_detected() -> None:
    output = [dict(row) for row in complete_test_double().output]
    output[0]["points"] = -1
    codes = detection_codes(observation_with_output(output))
    assert {"NUMERIC_OUT_OF_BOUNDS", "NEGATIVE_NUMERIC_VALUE"}.issubset(codes)


def test_statistical_row_count_drift_is_detected() -> None:
    contract = replace(default_extraction_contract(), expected_row_count=2)
    result = evaluate_detection(complete_test_double(TestDoubleScenario.STATISTICAL_DRIFT), contract)
    assert "ROW_COUNT_ANOMALY" in {signal.code for signal in result.signals}


def test_timeout_does_not_produce_a_healthy_result() -> None:
    adapter = DeterministicBrightDataTestDouble(TestDoubleScenario.TIMEOUT)
    collector = adapter.create_collector(CollectorRequest("https://example.test", "extract", provider=ProviderProvenance.TEST_DOUBLE))
    submitted = adapter.run_collector(collector, target_url="https://example.test")
    running = adapter.poll_collection(submitted)
    timed_out = adapter.poll_collection(running)
    assert timed_out.status is CollectionState.TIMED_OUT
    with pytest.raises(ValueError, match="not complete"):
        adapter.retrieve_output(timed_out)
    with pytest.raises(ValueError, match="completed collection"):
        Observation.from_result(CollectionResult(handle=timed_out, output=[]), {"target_url": "https://example.test"})


def test_test_double_provenance_and_mode_are_preserved() -> None:
    observation = complete_test_double()
    assert observation.provider_provenance is ProviderProvenance.TEST_DOUBLE
    assert observation.collection_mode is CollectionMode.TEST_DOUBLE


def test_observation_is_immutable() -> None:
    observation = complete_test_double()
    with pytest.raises(TypeError):
        observation.output[0]["title"] = "mutated"  # type: ignore[index]
    with pytest.raises((AttributeError, TypeError)):
        observation.row_count = 999  # type: ignore[misc]


def test_cli_adapter_preserves_observed_batch_fallback_and_provider_ids() -> None:
    def runner(command):
        if "create" in command:
            return CommandResult('{"collector_id":"c_test","status":"done"}')
        return CommandResult(
            """Triggering scrape...\nTriggered (response_id: r_test)\nRealtime page limit exceeded — switching to batch mode...\nBatch job: j_test\n[{\"title\":\"Story\",\"url\":\"https://example.test/story\",\"points\":1,\"author\":\"aegis\",\"comment_count\":0}]"""
        )

    with BrightDataCliAdapter(runner=runner) as adapter:
        collector = adapter.create_collector(CollectorRequest("https://example.test", "extract stories"))
        handle = adapter.run_collector(collector, target_url="https://example.test", timeout_seconds=1)
        for _ in range(20):
            handle = adapter.poll_collection(handle)
            if handle.status is CollectionState.COMPLETED:
                break
            sleep(0.001)
        assert handle.status is CollectionState.COMPLETED
        assert handle.mode is CollectionMode.BATCH
        assert handle.provider_operation_ids == {"response_id": "r_test", "batch_job_id": "j_test"}
        result = adapter.retrieve_output(handle)
        observation = Observation.from_result(result, {"target_url": "https://example.test"})
        assert observation.provider_provenance is ProviderProvenance.BRIGHT_DATA
        assert observation.row_count == 1
