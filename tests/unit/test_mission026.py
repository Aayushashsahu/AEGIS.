from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from aegis.baseline_participants import BaselineBConfiguration, apply_first_candidate
from aegis.benchmark_config import compute_configuration_hash, load_benchmark_config
from aegis.benchmark_runner import NOT_APPLICABLE, PreparedParticipantRun
from aegis.mutation_lab import MutationLab
from aegis.nvidia_provider import (
    NVIDIA_CANDIDATE_MODEL_ID,
    NVIDIA_CANDIDATE_MODEL_REVISION,
    NVIDIA_HOSTED_ENDPOINT,
    NVIDIA_PROVIDER,
    ModelDescriptor,
    NvidiaBaselineBAdapter,
    NvidiaModelCaller,
    NvidiaProviderError,
    ProviderRateLimiter,
    RateLimitConfig,
    candidate_model_descriptor,
    load_nvidia_api_key,
    normalize_nvidia_chat_response,
    official_candidate_catalog,
    prompt_sha256,
)
from aegis.participant_freeze import ParticipantFreezeProposal, compute_participant_hash, validate_participant_proposal

ROOT = Path(__file__).resolve().parents[2]
OLD_CONFIG = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
NEW_CONFIG = ROOT / "benchmarks/configs/mission_026_nvidia_nim_candidate_config.json"
PROPOSAL = ROOT / "benchmarks/configs/mission_026_baseline_b_nvidia_proposal.json"


def test_catalog_is_provider_neutral_and_contains_more_than_benchmark_concept() -> None:
    descriptor = candidate_model_descriptor()
    catalog = official_candidate_catalog()
    assert catalog.provider == NVIDIA_PROVIDER
    assert catalog.endpoint == NVIDIA_HOSTED_ENDPOINT
    assert catalog.get(NVIDIA_CANDIDATE_MODEL_ID) == descriptor
    assert descriptor.capabilities
    assert descriptor.modalities == ("text_input", "text_output")
    assert descriptor.context_length == 131072
    assert descriptor.model_revision == NVIDIA_CANDIDATE_MODEL_REVISION
    assert "limits" in descriptor.provider_metadata


def test_model_descriptor_is_immutable_enough_for_catalog_selection() -> None:
    descriptor = ModelDescriptor("x/model", "X", NVIDIA_PROVIDER, ("chat",), ("text_input",), 1024, "AVAILABLE", {"source": "test"}, "v1")
    catalog = official_candidate_catalog().from_descriptors((descriptor, candidate_model_descriptor()))
    assert catalog.get("x/model").model_id == "x/model"
    assert len(catalog.models) == 2
    with pytest.raises(KeyError):
        catalog.get("does/not-exist")


def test_env_credential_loading_uses_allowed_names_only() -> None:
    assert load_nvidia_api_key({"NVIDIA_API_KEY": "secret", "OTHER": "ignored"}) == "secret"
    assert load_nvidia_api_key({"NVIDIA_NIM_API_KEY": "nim-secret"}) == "nim-secret"
    assert load_nvidia_api_key({"OPENAI_API_KEY": "not-nvidia"}) is None


def test_prompt_hash_is_deterministic_and_ordered_by_named_fields() -> None:
    a = prompt_sha256("system", "repair")
    b = prompt_sha256("system", "repair")
    c = prompt_sha256("repair", "system")
    assert a == b
    assert a != c
    assert len(a) == 64


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_nvidia_chat_response_normalizes_candidates_without_persisting_secrets() -> None:
    caller = NvidiaModelCaller(candidate_model_descriptor(), api_key="secret", opener=lambda request, timeout: FakeResponse({"id": "resp-1", "choices": [{"message": {"content": "candidate-a"}}, {"message": {"content": "candidate-b"}}]}))
    result = caller("system", "repair")
    assert result["provider"] == NVIDIA_PROVIDER
    assert len(result["candidates"]) == 2
    assert result["candidates"][0]["candidate"] == "candidate-a"
    assert "secret" not in json.dumps(caller.redacted_metadata())
    assert "Authorization" not in json.dumps(caller.redacted_metadata())
    assert caller.request_count == 1
    assert caller.last_observation is not None
    assert caller.last_observation.failure_state == "COMPLETED"


def test_normalizer_rejects_missing_choices() -> None:
    with pytest.raises(NvidiaProviderError, match="missing choices"):
        normalize_nvidia_chat_response({}, candidate_model_descriptor())


@pytest.mark.parametrize(
    "exc,expected_status,expected_failure",
    [
        (HTTPError("https://example.test", 429, "quota", {"Retry-After": "3"}, None), 429, "RATE_LIMITED"),
        (HTTPError("https://example.test", 503, "busy", {}, None), 503, "PROVIDER_5XX"),
        (URLError("timeout"), None, "TRANSPORT_FAILURE"),
    ],
)
def test_provider_failures_are_normalized_without_retries(exc, expected_status, expected_failure) -> None:
    def fail(_request, timeout):
        raise exc

    caller = NvidiaModelCaller(candidate_model_descriptor(), api_key="secret", opener=fail)
    with pytest.raises(NvidiaProviderError) as caught:
        caller("system", "repair")
    assert caught.value.status_code == expected_status
    assert caller.last_observation is not None
    assert caller.last_observation.failure_state == expected_failure
    assert caller.request_count == 1


def test_tools_are_disabled_and_no_implicit_retry_occurs() -> None:
    calls = []

    def opener(request, timeout):
        calls.append(request)
        return FakeResponse({"choices": [{"message": {"content": "candidate"}}]})

    caller = NvidiaModelCaller(candidate_model_descriptor(), api_key="secret", opener=opener)
    with pytest.raises(ValueError, match="tools"):
        caller("system", "repair", tools_enabled=True)
    assert calls == []


def test_rate_limiter_supports_concurrency_and_configured_limits() -> None:
    limiter = ProviderRateLimiter(RateLimitConfig(max_requests_per_minute=10, min_interval_seconds=0, concurrency_limit=1))
    first_wait = limiter.acquire()
    assert first_wait >= 0
    limiter.release()
    with pytest.raises(RuntimeError):
        limiter.release()


def test_rate_limiter_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        RateLimitConfig(max_requests_per_minute=0)
    with pytest.raises(ValueError):
        RateLimitConfig(concurrency_limit=0)


def test_first_candidate_policy_semantics_are_unchanged() -> None:
    config = BaselineBConfiguration(model_id=NVIDIA_CANDIDATE_MODEL_ID, model_revision=NVIDIA_CANDIDATE_MODEL_REVISION)
    result = apply_first_candidate(config, {"candidates": [{"candidate": "first"}, {"candidate": "second"}]}, MutationLab().fixture)
    assert result.candidate_received is True
    assert result.candidate_selected is True
    assert result.candidate_accepted is True
    assert result.candidate == {"candidate": "first"}
    assert result.application["generated_code_executed"] is False
    assert result.application["aegis_verification_invoked"] is False
    assert result.application["risk_governor_invoked"] is False
    assert result.application["commit_gate_invoked"] is False


def test_nvidia_baseline_adapter_preserves_naive_evidence_shape(tmp_path: Path) -> None:
    old = load_benchmark_config(OLD_CONFIG)
    old_spec = next(spec for spec in old.baselines if spec.baseline_id == "BASELINE_B")
    spec = replace(old_spec, model_id=NVIDIA_CANDIDATE_MODEL_ID, status="READY", metadata={**dict(old_spec.metadata), "provider": NVIDIA_PROVIDER, "model_revision": NVIDIA_CANDIDATE_MODEL_REVISION})

    class StubCaller:
        descriptor = candidate_model_descriptor()
        last_observation = None

        def __call__(self, system_prompt, repair_prompt):
            return {"candidates": [{"candidate": "safe"}]}

    adapter = NvidiaBaselineBAdapter(spec, MutationLab(), model_caller=StubCaller())
    from aegis.benchmark_runner import ParticipantExecutionInput

    execution_input = ParticipantExecutionInput(
        benchmark_id="test",
        configuration_hash="config",
        participant_id="BASELINE_B",
        mutation_id="M001",
        severity="L1",
        seed=12345,
        fixture_version="1",
        ground_truth_reference="ground-truth://test",
        code_revision="revision",
        environment_reference="TEST_DOUBLE",
        timeout_policy={"timeout_seconds": 300},
        retry_policy={"retry_count": 0},
        artifact_root=str(tmp_path),
    )
    evidence = adapter.run_mutation(PreparedParticipantRun("BASELINE_B", execution_input))
    assert evidence.candidate_received is True
    assert evidence.candidate_selected is True
    assert evidence.candidate_accepted is True
    assert evidence.failure_state == "COMPLETED"
    assert evidence.output_eligible is True
    assert evidence.verification_status == NOT_APPLICABLE
    assert evidence.risk_decision == NOT_APPLICABLE
    assert evidence.llm_calls == 1
    assert evidence.candidate_application["provider"] == NVIDIA_PROVIDER
    assert evidence.candidate_application["tools_enabled"] is False
    assert evidence.candidate_application["generated_code_executed"] is False


def test_proposal_is_not_ready_without_owner_review() -> None:
    payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    proposal = ParticipantFreezeProposal(
        participant_id=payload["participant_id"],
        prior_status=payload["prior_status"],
        implementation_revision=payload["implementation_revision"],
        configuration=payload["configuration"],
        timeout_policy=payload["timeout_policy"],
        retry_policy=payload["retry_policy"],
        output_normalization_policy=payload["output_normalization_policy"],
        provenance=payload["provenance"],
        artifact_schema=payload["artifact_schema"],
        execution_policy=payload["execution_policy"],
        verification_policy=payload["verification_policy"],
        commit_policy=payload["commit_policy"],
        configuration_hash=payload["configuration_hash"],
    )
    validation = validate_participant_proposal(proposal, require_owner_approval=True)
    assert validation.ready is False
    assert "owner review is required before readiness promotion" in validation.errors
    assert proposal.prior_status == "NOT_READY"
    assert payload["configuration"]["owner_review_status"] == "REQUIRED"


def test_participant_hash_is_reproducible() -> None:
    payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    proposal = ParticipantFreezeProposal(
        participant_id=payload["participant_id"],
        prior_status=payload["prior_status"],
        implementation_revision=payload["implementation_revision"],
        configuration=payload["configuration"],
        timeout_policy=payload["timeout_policy"],
        retry_policy=payload["retry_policy"],
        output_normalization_policy=payload["output_normalization_policy"],
        provenance=payload["provenance"],
        artifact_schema=payload["artifact_schema"],
        execution_policy=payload["execution_policy"],
        verification_policy=payload["verification_policy"],
        commit_policy=payload["commit_policy"],
        configuration_hash=payload["configuration_hash"],
    )
    assert compute_participant_hash(proposal) == payload["configuration_hash"]


def test_new_config_changes_only_provider_participant_and_hash_is_reproducible() -> None:
    old = load_benchmark_config(OLD_CONFIG)
    new = load_benchmark_config(NEW_CONFIG)
    old_a = next(spec for spec in old.baselines if spec.baseline_id == "BASELINE_A")
    old_a_new = next(spec for spec in new.baselines if spec.baseline_id == "BASELINE_A")
    old_aegis = next(spec for spec in old.baselines if spec.baseline_id == "AEGIS")
    new_aegis = next(spec for spec in new.baselines if spec.baseline_id == "AEGIS")
    new_b = next(spec for spec in new.baselines if spec.baseline_id == "BASELINE_B")
    assert old_a.configuration_hash == old_a_new.configuration_hash
    assert old_aegis.configuration_hash == new_aegis.configuration_hash
    assert new_b.metadata["provider"] == NVIDIA_PROVIDER
    assert new_b.status == "NOT_READY"
    assert new.configuration_hash == compute_configuration_hash(new)
    assert new.configuration_hash != old.configuration_hash
    assert new.model_identifier == NVIDIA_CANDIDATE_MODEL_ID
    assert new.collection_policy["provider_execution"] == "ONE_NVIDIA_SMOKE_COMPLETED; NO_BENCHMARK_EXECUTION"


def test_old_gemini_configuration_remains_historical_and_unchanged() -> None:
    old = json.loads(OLD_CONFIG.read_text(encoding="utf-8"))
    old_b = next(spec for spec in old["baselines"] if spec["baseline_id"] == "BASELINE_B")
    assert old_b["metadata"]["provider"] == "GOOGLE_GEMINI_API"
    assert old_b["model_id"] == "gemini-3.6-flash"
    assert old["configuration_hash"] == "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
