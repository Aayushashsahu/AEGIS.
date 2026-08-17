from __future__ import annotations

from aegis.baseline_participants import (
    BASELINE_B_MODEL_ID,
    BASELINE_B_MODEL_REVISION,
    BASELINE_B_REPAIR_PROMPT_TEMPLATE,
    BASELINE_B_SYSTEM_PROMPT,
    BaselineBConfiguration,
    BaselineBUnavailable,
    baseline_b_model_call,
)


def test_baseline_b_configuration_is_exact_and_deterministic() -> None:
    first = BaselineBConfiguration()
    second = BaselineBConfiguration()
    assert first == second
    assert first.model_id == BASELINE_B_MODEL_ID == "gemini-3.6-flash"
    assert first.model_revision == BASELINE_B_MODEL_REVISION == "stable"
    assert first.system_prompt == BASELINE_B_SYSTEM_PROMPT
    assert first.repair_prompt_template == BASELINE_B_REPAIR_PROMPT_TEMPLATE
    assert first.max_output_tokens == 8192
    assert first.tools_enabled is False
    assert first.candidate_policy == "FIRST_CANDIDATE"
    assert first.max_candidates == 1
    assert first.auto_accept_first_candidate is True
    assert first.timeout_seconds == 300
    assert first.retry_count == 0
    assert first.backoff_seconds == 0


def test_baseline_b_without_injected_caller_is_honestly_unavailable() -> None:
    configuration = BaselineBConfiguration()
    result = baseline_b_model_call(
        configuration,
        caller=None,
        system_prompt=configuration.system_prompt,
        repair_prompt=configuration.repair_prompt_template,
    )
    assert isinstance(result, BaselineBUnavailable)
    assert result.model_id == "gemini-3.6-flash"
    assert result.reason == "MODEL_CALL_NOT_EXECUTED_IN_VALIDATION_ONLY_MISSION"


def test_baseline_b_injected_caller_receives_exact_approved_prompts() -> None:
    configuration = BaselineBConfiguration()
    calls: list[tuple[str, str]] = []

    def caller(system_prompt: str, repair_prompt: str):
        calls.append((system_prompt, repair_prompt))
        return {"candidate": "approved-test-double-response"}

    result = baseline_b_model_call(
        configuration,
        caller=caller,
        system_prompt=configuration.system_prompt,
        repair_prompt=configuration.repair_prompt_template,
    )
    assert result == {"candidate": "approved-test-double-response"}
    assert calls == [(configuration.system_prompt, configuration.repair_prompt_template)]
