from __future__ import annotations

from dataclasses import fields, replace
from threading import Event
from time import sleep

import pytest

from aegis import CollectorRequest
from aegis.adapter import AdapterError, BrightDataCliAdapter, CommandResult, build_heal_command, build_heal_prompt
from aegis.contracts import default_extraction_contract
from aegis.detection import evaluate_detection
from aegis.diagnosis import DiagnosisContext, build_repair_request, diagnose_deterministically
from aegis.healing import HealState, VerificationStatus
from aegis.models import ProviderProvenance
from aegis.test_double import (
    DeterministicBrightDataHealingTestDouble,
    DeterministicBrightDataTestDouble,
    HealTestDoubleScenario,
    TestDoubleScenario,
)


def repair_request_for(scenario: TestDoubleScenario = TestDoubleScenario.MISSING_FIELD):
    source = DeterministicBrightDataTestDouble(scenario)
    collector = source.create_collector(
        CollectorRequest("https://example.test", "extract stories", provider=ProviderProvenance.TEST_DOUBLE)
    )
    handle = source.run_collector(collector, target_url="https://example.test")
    handle = source.poll_collection(handle)
    handle = source.poll_collection(handle)
    observation = __import__("aegis").Observation.from_result(
        source.retrieve_output(handle),
        {"target_url": "https://example.test"},
    )
    contract = default_extraction_contract()
    detection = evaluate_detection(observation, contract)
    diagnosis = diagnose_deterministically(DiagnosisContext(
        observation=observation,
        detection=detection,
        contract=contract,
        detection_id="detection-mission004",
        correlation_id="corr-mission004",
    ))
    assert diagnosis is not None
    return build_repair_request(diagnosis, observation=observation, contract=contract)


def test_repair_request_translates_to_documented_heal_command() -> None:
    request = repair_request_for()
    command = build_heal_command(request)
    assert command[:7] == ["npx", "-p", "@brightdata/cli", "bdata", "scraper", "heal", request.collector_reference]
    assert command[-2:] == ["--url", "https://example.test"]
    assert request.repair_objective in command[7]
    assert "author" in command[7]
    assert "points" in command[7]
    assert "output schema" in command[7]
    assert "bdata scraper approve" not in command
    assert "--auto-approve" not in command


def test_heal_prompt_contains_contract_and_untrusted_content_boundary() -> None:
    request = repair_request_for()
    prompt = build_heal_prompt(request)
    assert "Known invariants" in prompt
    assert "Evidence references" in prompt
    assert "Target input" in prompt
    assert "untrusted data" in prompt


def test_invalid_target_input_fails_before_submission() -> None:
    request = repair_request_for()
    bad_input = dict(request.target_input)
    bad_input["target_url"] = "file:///secret"
    bad_request = __import__("dataclasses").replace(request, target_input=bad_input)
    with pytest.raises(AdapterError, match=r"HTTP\(S\)"):
        build_heal_command(bad_request)


def test_cli_heal_submission_returns_immediately_and_reaches_awaiting_approval() -> None:
    calls: list[list[str]] = []

    runner_started = Event()
    release_runner = Event()

    def runner(command):
        runner_started.set()
        release_runner.wait(timeout=1)
        calls.append(list(command))
        return CommandResult(
            """Heal finished\n{\"status\":\"awaiting_approval\",\"response_id\":\"r_heal_test\",\"preview_result\":[{\"author\":\"aegis\"}],\"diff_summary\":\"proposed template has 2 step(s)\",\"next_step_command\":\"bdata scraper approve c_test --url https://example.test\"}""",
            latency_ms=70_001,
        )

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        started = adapter.request_healing(request, timeout_seconds=1)
        assert started.status is HealState.SUBMITTED
        assert runner_started.wait(timeout=0.2)
        release_runner.set()
        state = adapter.poll_healing(started)
        assert state.status in {HealState.RUNNING, HealState.AWAITING_APPROVAL}
        for _ in range(20):
            state = adapter.poll_healing(state)
            if state.status is HealState.AWAITING_APPROVAL:
                break
            sleep(0.001)
        assert state.status is HealState.AWAITING_APPROVAL
        result = adapter.retrieve_heal_result(state)
        assert result.handle.status is HealState.CANDIDATE_READY
        assert result.envelope is not None
        assert result.envelope.collector_reference == request.collector_reference
        assert result.envelope.provider_operation_reference == "r_heal_test"
        assert result.envelope.preview_result[0]["author"] == "aegis"
        assert result.envelope.diff_summary == "proposed template has 2 step(s)"
        assert result.envelope.approval_command.startswith("bdata scraper approve")
        assert result.candidate is not None
        assert result.candidate.verification_status is VerificationStatus.UNVERIFIED
        assert result.candidate.provenance is ProviderProvenance.BRIGHT_DATA
        assert result.candidate.latency_ms == 70_001
        joined = " ".join(item for call in calls for item in call)
        assert "bdata scraper approve" not in joined
        assert "--auto-approve" not in joined


def test_cli_missing_operation_id_fails_closed() -> None:
    def runner(command):
        return CommandResult('{"status":"awaiting_approval","preview_result":{},"diff_summary":"x"}', latency_ms=1)

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request)
        state = adapter.poll_healing(handle)
        for _ in range(10):
            state = adapter.poll_healing(state)
            if state.status is HealState.FAILED:
                break
            sleep(0.001)
        assert state.status is HealState.FAILED
        assert state.error_code == "MISSING_PROVIDER_OPERATION_ID"
        with pytest.raises(AdapterError, match="not ready"):
            adapter.retrieve_heal_result(state)


def test_cli_missing_preview_fails_closed() -> None:
    def runner(command):
        return CommandResult('{"status":"awaiting_approval","response_id":"r_missing_preview"}', latency_ms=1)

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request)
        state = adapter.poll_healing(handle)
        for _ in range(10):
            state = adapter.poll_healing(state)
            if state.status is HealState.FAILED:
                break
            sleep(0.001)
        assert state.status is HealState.FAILED
        assert state.error_code == "MISSING_PREVIEW_RESULT"


def test_cli_malformed_response_fails_closed() -> None:
    def runner(command):
        return CommandResult("not-json", latency_ms=1)

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request)
        state = adapter.poll_healing(handle)
        for _ in range(10):
            state = adapter.poll_healing(state)
            if state.status is HealState.FAILED:
                break
            sleep(0.001)
        assert state.status is HealState.FAILED
        assert state.error_code == "MALFORMED_PROVIDER_RESPONSE"


def test_cli_provider_failure_fails_closed() -> None:
    def runner(command):
        return CommandResult("", stderr="authentication failed", returncode=1, latency_ms=2)

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request)
        state = adapter.poll_healing(handle)
        for _ in range(10):
            state = adapter.poll_healing(state)
            if state.status is HealState.FAILED:
                break
            sleep(0.001)
        assert state.status is HealState.FAILED
        assert state.error_code == "PROVIDER_COMMAND_FAILED"


def test_cli_timeout_fails_closed() -> None:
    def runner(command):
        sleep(0.05)
        return CommandResult('{"status":"awaiting_approval","response_id":"r_late","preview_result":{}}', latency_ms=50)

    request = repair_request_for()
    with BrightDataCliAdapter(runner=runner) as adapter:
        handle = adapter.request_healing(request, timeout_seconds=0.001)
        state = adapter.poll_healing(handle)
        for _ in range(20):
            state = adapter.poll_healing(state)
            if state.status is HealState.TIMED_OUT:
                break
            sleep(0.005)
        assert state.status is HealState.TIMED_OUT
        with pytest.raises(AdapterError, match="not ready"):
            adapter.retrieve_heal_result(state)


def test_test_double_healing_scenarios_are_explicit_and_unverified() -> None:
    request = repair_request_for()
    double = DeterministicBrightDataHealingTestDouble(HealTestDoubleScenario.HEAL_AWAITING_APPROVAL)
    handle = double.request_healing(request)
    assert handle.provider_provenance is ProviderProvenance.TEST_DOUBLE
    assert handle.status is HealState.SUBMITTED
    handle = double.poll_healing(handle)
    assert handle.status is HealState.RUNNING
    handle = double.poll_healing(handle)
    assert handle.status is HealState.AWAITING_APPROVAL
    result = double.retrieve_heal_result(handle)
    assert result.candidate is not None
    assert result.candidate.provenance is ProviderProvenance.TEST_DOUBLE
    assert result.candidate.verification_status is VerificationStatus.UNVERIFIED
    assert result.candidate.provider_operation_reference == "test-heal-operation-1"


def test_test_double_failure_scenarios_fail_closed() -> None:
    request = repair_request_for()
    for scenario, expected in (
        (HealTestDoubleScenario.HEAL_MALFORMED_RESPONSE, HealState.FAILED),
        (HealTestDoubleScenario.HEAL_PROVIDER_FAILURE, HealState.FAILED),
        (HealTestDoubleScenario.HEAL_TIMEOUT, HealState.TIMED_OUT),
    ):
        double = DeterministicBrightDataHealingTestDouble(scenario)
        handle = double.request_healing(request)
        handle = double.poll_healing(handle)
        handle = double.poll_healing(handle)
        assert handle.status is expected
        with pytest.raises(ValueError, match="not ready"):
            double.retrieve_heal_result(handle)


def test_candidate_cannot_enter_later_states() -> None:
    request = repair_request_for()
    double = DeterministicBrightDataHealingTestDouble()
    handle = double.request_healing(request)
    handle = double.poll_healing(handle)
    handle = double.poll_healing(handle)
    candidate = double.retrieve_heal_result(handle).candidate
    assert candidate is not None
    with pytest.raises(ValueError, match="later mission"):
        candidate.mark_verified()
    with pytest.raises(ValueError, match="later mission"):
        candidate.mark_accepted()
    with pytest.raises(ValueError, match="later mission"):
        candidate.mark_committed()


def test_candidate_domain_fields_are_provider_neutral() -> None:
    request = repair_request_for()
    double = DeterministicBrightDataHealingTestDouble()
    handle = double.request_healing(request)
    handle = double.poll_healing(handle)
    handle = double.poll_healing(handle)
    candidate = double.retrieve_heal_result(handle).candidate
    assert candidate is not None
    field_names = {field.name for field in fields(candidate)}
    assert {"api_endpoint", "cli_command", "api_key", "auto_approve"}.isdisjoint(field_names)
