from __future__ import annotations

import pytest

from aegis.commit_gate import QuarantineLedger
from dataclasses import replace

from aegis.watch import WatchEngine, WatchMetricHooks, WatchPolicy, WatchResultStatus, WatchState
from aegis.watch_double import WatchFixture, build_watch_fixture


def evaluate(fixture: WatchFixture):
    registration, observation, _ = build_watch_fixture(fixture)
    return WatchEngine().evaluate(
        registration,
        observation,
        observation_reference=f"observation://TEST_DOUBLE/mission-007/{fixture.value.lower()}",
        ledger=QuarantineLedger(),
    )


def test_healthy_post_commit_observation_remains_healthy() -> None:
    evaluation = evaluate(WatchFixture.HEALTHY_AFTER_COMMIT)
    assert evaluation.result.status is WatchResultStatus.HEALTHY
    assert evaluation.registration.state is WatchState.HEALTHY
    assert evaluation.cycle.status is WatchState.HEALTHY
    assert evaluation.regression_event is None
    assert evaluation.quarantine_record is None


def test_schema_regression_is_detected_and_quarantined() -> None:
    evaluation = evaluate(WatchFixture.REGRESSION_SCHEMA)
    assert evaluation.result.status is WatchResultStatus.REGRESSION
    assert evaluation.result.detection.detected is True
    assert evaluation.regression_event is not None
    assert evaluation.regression_event.severity == "L2"
    assert evaluation.registration.state is WatchState.QUARANTINED
    assert evaluation.cycle.status is WatchState.QUARANTINED
    assert evaluation.quarantine_record is not None
    assert evaluation.quarantine_record.status.value == "OPEN"
    assert evaluation.quarantine_ledger is not None


def test_semantic_regression_is_detected_and_quarantined() -> None:
    evaluation = evaluate(WatchFixture.REGRESSION_SEMANTIC)
    assert evaluation.result.status is WatchResultStatus.REGRESSION
    assert evaluation.result.severity == "L3"
    assert evaluation.regression_event is not None
    assert "NEGATIVE_NUMERIC_VALUE" in evaluation.regression_event.failed_evidence_refs or evaluation.regression_event.affected_fields
    assert evaluation.quarantine_record is not None


def test_statistical_regression_is_detected_and_quarantined() -> None:
    evaluation = evaluate(WatchFixture.REGRESSION_STATISTICAL)
    assert evaluation.result.status is WatchResultStatus.REGRESSION
    assert evaluation.result.severity == "L3"
    assert evaluation.regression_event is not None
    assert evaluation.quarantine_record is not None


def test_unknown_evidence_does_not_become_healthy_or_auto_quarantine() -> None:
    evaluation = evaluate(WatchFixture.UNKNOWN_EVIDENCE)
    assert evaluation.result.status is WatchResultStatus.UNKNOWN
    assert evaluation.registration.state is WatchState.UNKNOWN
    assert evaluation.cycle.status is WatchState.UNKNOWN
    assert evaluation.regression_event is None
    assert evaluation.quarantine_record is None
    assert evaluation.quarantine_ledger is not None
    assert len(evaluation.quarantine_ledger.records) == 0


def test_watch_registration_requires_existing_commit_eligibility() -> None:
    registration, observation, _ = build_watch_fixture(WatchFixture.HEALTHY_AFTER_COMMIT)
    with pytest.raises(ValueError):
        WatchEngine().evaluate(registration.transition(WatchState.HEALTHY), observation, observation_reference="observation://invalid")


def test_watch_state_machine_rejects_rollback_and_repair_like_transitions() -> None:
    registration, _, _ = build_watch_fixture(WatchFixture.HEALTHY_AFTER_COMMIT)
    with pytest.raises(ValueError):
        registration.transition(WatchState.REGRESSION)
    with pytest.raises(ValueError):
        registration.transition(WatchState.WATCHING).transition(WatchState.COMMITTED)
    engine = WatchEngine()
    assert not hasattr(engine, "repair")
    assert not hasattr(engine, "rollback")
    assert not hasattr(engine, "approve")


def test_regression_event_and_watch_records_are_immutable() -> None:
    evaluation = evaluate(WatchFixture.REGRESSION_SCHEMA)
    assert evaluation.regression_event is not None
    with pytest.raises((AttributeError, TypeError)):
        evaluation.regression_event.severity = "NONE"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        evaluation.result.status = WatchResultStatus.HEALTHY  # type: ignore[misc]
    assert evaluation.quarantine_record is not None
    with pytest.raises((AttributeError, TypeError)):
        evaluation.quarantine_record.status = evaluation.quarantine_record.status.RELEASED  # type: ignore[misc]


def test_watch_does_not_modify_input_observation() -> None:
    registration, observation, _ = build_watch_fixture(WatchFixture.REGRESSION_SEMANTIC)
    before = observation.output
    WatchEngine().evaluate(registration, observation, observation_reference="observation://TEST_DOUBLE/immutable")
    assert observation.output == before
    assert observation.trust_status == "UNTRUSTED_UNTIL_VERIFIED"


def test_metric_hooks_instrument_regression_unknown_and_quarantine_without_benchmark() -> None:
    hooks = WatchMetricHooks()
    healthy = evaluate(WatchFixture.HEALTHY_AFTER_COMMIT)
    regression = evaluate(WatchFixture.REGRESSION_SCHEMA)
    unknown = evaluate(WatchFixture.UNKNOWN_EVIDENCE)
    hooks.record(healthy)
    hooks.record(regression)
    hooks.record(unknown)
    assert hooks.regression_rate == 1 / 3
    assert hooks.watch_failure_rate == 1 / 3
    assert hooks.unsafe_refusal_rate == 1.0
    assert hooks.metric_status == "INSTRUMENTED_NOT_BENCHMARKED"
    assert len(hooks.events) == 1 + 3 + 2
    assert not hasattr(hooks, "repair")
    assert not hasattr(hooks, "rollback")


def test_unknown_watch_policy_can_be_disabled_but_does_not_create_health() -> None:
    registration, observation, _ = build_watch_fixture(WatchFixture.UNKNOWN_EVIDENCE)
    registration = replace(registration, watch_policy=WatchPolicy(enabled=False))
    with pytest.raises(ValueError):
        WatchEngine().evaluate(registration, observation, observation_reference="observation://disabled")
