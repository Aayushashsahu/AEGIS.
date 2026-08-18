"""Provider-neutral NVIDIA NIM catalog and Baseline B adapter seam.

The module contains no default network behavior. A real request occurs only when
``NvidiaModelCaller`` is explicitly constructed with an environment-provided key
and invoked by the dedicated Mission 026 smoke script or an authorized runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .baseline_participants import (
    BaselineBConfiguration,
    BaselineBUnavailable,
    apply_first_candidate,
    baseline_b_model_call,
)
from .benchmark_config import BaselineSpec, BenchmarkConfig
from .benchmark_runner import (
    BaselineAAdapter,
    BaselineBAdapter,
    AegisAdapter,
    NOT_APPLICABLE,
    ParticipantAdapter,
    ParticipantReadiness,
    ParticipantRunEvidence,
    ParticipantRegistry,
    PreparedParticipantRun,
    _BaseAdapter,
)
from .mutation_lab import MutationLab


NVIDIA_PROVIDER = "NVIDIA_NIM"
NVIDIA_HOSTED_ENDPOINT = "https://integrate.api.nvidia.com/v1"
NVIDIA_CHAT_COMPLETIONS_PATH = "/chat/completions"
NVIDIA_API_KEY_ENV_NAMES = ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY", "NGC_API_KEY")
NVIDIA_CANDIDATE_MODEL_ID = "openai/gpt-oss-20b"
NVIDIA_CANDIDATE_MODEL_REVISION = "gpt-oss-20b-v1.0-2025-08-05"
NVIDIA_MODEL_DESCRIPTOR_REVISION = "mission-026-catalog-v1"


@dataclass(frozen=True)
class ModelDescriptor:
    model_id: str
    display_name: str
    provider: str
    capabilities: tuple[str, ...]
    modalities: tuple[str, ...]
    context_length: int | None
    availability: str
    provider_metadata: Mapping[str, Any]
    model_revision: str = "UNKNOWN"

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(self, "modalities", tuple(self.modalities))
        object.__setattr__(self, "provider_metadata", dict(self.provider_metadata))


@dataclass(frozen=True)
class NvidiaModelCatalog:
    catalog_revision: str
    provider: str
    endpoint: str
    models: tuple[ModelDescriptor, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "models", tuple(self.models))

    def get(self, model_id: str) -> ModelDescriptor:
        for model in self.models:
            if model.model_id == model_id:
                return model
        raise KeyError(model_id)

    def to_dict(self) -> Mapping[str, Any]:
        return {
            "catalog_revision": self.catalog_revision,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "models": [
                {
                    "model_id": model.model_id,
                    "display_name": model.display_name,
                    "provider": model.provider,
                    "capabilities": model.capabilities,
                    "modalities": model.modalities,
                    "context_length": model.context_length,
                    "availability": model.availability,
                    "provider_metadata": model.provider_metadata,
                    "model_revision": model.model_revision,
                }
                for model in self.models
            ],
        }

    @classmethod
    def from_descriptors(cls, descriptors: Sequence[ModelDescriptor], *, catalog_revision: str = NVIDIA_MODEL_DESCRIPTOR_REVISION) -> "NvidiaModelCatalog":
        return cls(catalog_revision, NVIDIA_PROVIDER, NVIDIA_HOSTED_ENDPOINT, tuple(descriptors))


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests_per_minute: int | None = None
    min_interval_seconds: float = 0.0
    concurrency_limit: int = 1

    def __post_init__(self) -> None:
        if self.max_requests_per_minute is not None and self.max_requests_per_minute <= 0:
            raise ValueError("max_requests_per_minute must be positive or None")
        if self.min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative")
        if self.concurrency_limit <= 0:
            raise ValueError("concurrency_limit must be positive")


class ProviderRateLimiter:
    """Provider-neutral limiter; limits are configuration, never guessed."""

    def __init__(self, config: RateLimitConfig, *, clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self._clock = clock
        self._sleeper = sleeper
        self._condition = threading.Condition()
        self._timestamps: deque[float] = deque()
        self._active = 0
        self._last_start: float | None = None

    def acquire(self) -> float:
        started_waiting = self._clock()
        with self._condition:
            while True:
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= 60.0:
                    self._timestamps.popleft()
                interval_wait = 0.0 if self._last_start is None else max(0.0, self.config.min_interval_seconds - (now - self._last_start))
                rpm_wait = 0.0
                if self.config.max_requests_per_minute is not None and len(self._timestamps) >= self.config.max_requests_per_minute:
                    rpm_wait = max(0.0, 60.0 - (now - self._timestamps[0]))
                if self._active < self.config.concurrency_limit and interval_wait <= 0 and rpm_wait <= 0:
                    self._active += 1
                    self._last_start = now
                    self._timestamps.append(now)
                    return max(0.0, now - started_waiting)
                wait_for = max(interval_wait, rpm_wait, 0.001)
                self._condition.wait(timeout=wait_for)

    def release(self) -> None:
        with self._condition:
            if self._active <= 0:
                raise RuntimeError("rate limiter release without acquire")
            self._active -= 1
            self._condition.notify_all()


class NvidiaProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, retry_after_seconds: float | None = None, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.response_body = response_body


@dataclass(frozen=True)
class NvidiaCallObservation:
    provider: str
    model_id: str
    endpoint: str
    request_count: int
    wait_ms: int
    latency_ms: int
    status_code: int | None
    rate_limit_retry_after_seconds: float | None
    failure_state: str
    provider_error: str | None


def prompt_sha256(system_prompt: str, repair_prompt: str) -> str:
    payload = json.dumps({"system_prompt": system_prompt, "repair_prompt": repair_prompt}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def candidate_model_descriptor() -> ModelDescriptor:
    return ModelDescriptor(
        model_id=NVIDIA_CANDIDATE_MODEL_ID,
        display_name="OpenAI gpt-oss-20b via NVIDIA hosted NIM",
        provider=NVIDIA_PROVIDER,
        capabilities=("chat", "instruction_following", "structured_output", "function_calling", "reasoning"),
        modalities=("text_input", "text_output"),
        context_length=131072,
        availability="CANDIDATE_OFFICIAL_CATALOG_NOT_SMOKE_VERIFIED",
        provider_metadata={
            "hosted_endpoint": NVIDIA_HOSTED_ENDPOINT,
            "model_revision": NVIDIA_CANDIDATE_MODEL_REVISION,
            "catalog_source": "https://docs.api.nvidia.com/nim/reference/llm-apis",
            "model_source": "https://build.nvidia.com/openai/gpt-oss-20b",
            "tools": "DISABLED_FOR_BENCHMARK",
            "limits": "UNKNOWN_UNTIL_ACCOUNT_RESPONSE",
        },
        model_revision=NVIDIA_CANDIDATE_MODEL_REVISION,
    )


def official_candidate_catalog() -> NvidiaModelCatalog:
    return NvidiaModelCatalog.from_descriptors((candidate_model_descriptor(),))


def load_nvidia_api_key(env: Mapping[str, str] | None = None) -> str | None:
    values = env if env is not None else os.environ
    for name in NVIDIA_API_KEY_ENV_NAMES:
        value = values.get(name)
        if value:
            return value
    return None


class NvidiaModelCaller:
    """OpenAI-compatible NVIDIA hosted caller with no secret persistence."""

    def __init__(self, descriptor: ModelDescriptor, *, api_key: str | None = None, endpoint: str = NVIDIA_HOSTED_ENDPOINT, rate_limit: RateLimitConfig | None = None, timeout_seconds: int = 300, opener: Callable[..., Any] = urlopen) -> None:
        self.descriptor = descriptor
        self.api_key = api_key if api_key is not None else load_nvidia_api_key()
        self.endpoint = endpoint.rstrip("/")
        self.rate_limiter = ProviderRateLimiter(rate_limit or RateLimitConfig(concurrency_limit=1))
        self.timeout_seconds = timeout_seconds
        self._opener = opener
        self.request_count = 0
        self.last_observation: NvidiaCallObservation | None = None

    @property
    def ready(self) -> bool:
        return bool(self.api_key)

    def redacted_metadata(self) -> Mapping[str, Any]:
        return {
            "provider": NVIDIA_PROVIDER,
            "model_id": self.descriptor.model_id,
            "model_revision": self.descriptor.model_revision,
            "endpoint": self.endpoint,
            "request_count": self.request_count,
            "last_observation": None if self.last_observation is None else self.last_observation.__dict__,
        }

    def __call__(self, system_prompt: str, repair_prompt: str, *, sampling: Mapping[str, Any] | None = None, max_output_tokens: int = 8192, tools_enabled: bool = False) -> Mapping[str, Any]:
        if not self.api_key:
            raise NvidiaProviderError("NVIDIA API key is not configured")
        if tools_enabled:
            raise ValueError("Mission 026 benchmark tools must remain disabled")
        sampling = dict(sampling or {})
        payload: dict[str, Any] = {
            "model": self.descriptor.model_id,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": repair_prompt}],
            "max_tokens": max_output_tokens,
            "stream": False,
        }
        for name in ("temperature", "top_p"):
            value = sampling.get(name)
            if value is not None and value != "NOT_APPLICABLE":
                payload[name] = value
        url = f"{self.endpoint}{NVIDIA_CHAT_COMPLETIONS_PATH}"
        request = Request(url, data=json.dumps(payload, separators=(",", ":")).encode("utf-8"), method="POST", headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json", "Content-Type": "application/json"})
        wait_ms = int(self.rate_limiter.acquire() * 1000)
        started = time.monotonic()
        status_code: int | None = None
        retry_after: float | None = None
        try:
            self.request_count += 1
            with self._opener(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", None)
                body = response.read().decode("utf-8")
            parsed = json.loads(body)
            if not isinstance(parsed, Mapping):
                raise NvidiaProviderError("NVIDIA returned a non-object response", status_code=status_code)
            normalized = normalize_nvidia_chat_response(parsed, self.descriptor)
            self.last_observation = NvidiaCallObservation(NVIDIA_PROVIDER, self.descriptor.model_id, url, self.request_count, wait_ms, int((time.monotonic() - started) * 1000), status_code, None, "COMPLETED", None)
            return normalized
        except HTTPError as exc:
            status_code = exc.code
            retry_after = _retry_after(exc.headers)
            body = exc.read().decode("utf-8", errors="replace")[:2000]
            failure = "RATE_LIMITED" if status_code == 429 else "PROVIDER_5XX" if 500 <= status_code < 600 else "PROVIDER_HTTP_ERROR"
            self.last_observation = NvidiaCallObservation(NVIDIA_PROVIDER, self.descriptor.model_id, url, self.request_count, wait_ms, int((time.monotonic() - started) * 1000), status_code, retry_after, failure, body)
            raise NvidiaProviderError(f"NVIDIA HTTP {status_code}: {body}", status_code=status_code, retry_after_seconds=retry_after, response_body=body) from exc
        except (URLError, TimeoutError) as exc:
            self.last_observation = NvidiaCallObservation(NVIDIA_PROVIDER, self.descriptor.model_id, url, self.request_count, wait_ms, int((time.monotonic() - started) * 1000), status_code, retry_after, "TRANSPORT_FAILURE", str(exc))
            raise NvidiaProviderError(f"NVIDIA transport failure: {exc}", status_code=status_code, response_body=str(exc)) from exc
        except json.JSONDecodeError as exc:
            self.last_observation = NvidiaCallObservation(NVIDIA_PROVIDER, self.descriptor.model_id, url, self.request_count, wait_ms, int((time.monotonic() - started) * 1000), status_code, retry_after, "INVALID_PROVIDER_RESPONSE", str(exc))
            raise NvidiaProviderError(f"NVIDIA returned invalid JSON: {exc}", status_code=status_code) from exc
        finally:
            self.rate_limiter.release()


def normalize_nvidia_chat_response(payload: Mapping[str, Any], descriptor: ModelDescriptor) -> Mapping[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        raise NvidiaProviderError("NVIDIA response is missing choices")
    candidates = []
    for choice in choices:
        if not isinstance(choice, Mapping):
            continue
        message = choice.get("message")
        content: Any = message.get("content") if isinstance(message, Mapping) else choice.get("text")
        if content is not None:
            candidates.append({"candidate": content})
    return {
        "candidates": candidates,
        "provider": NVIDIA_PROVIDER,
        "model_id": descriptor.model_id,
        "model_revision": descriptor.model_revision,
        "provider_response_id": payload.get("id", NOT_APPLICABLE),
        "usage": payload.get("usage", {}),
    }


def _retry_after(headers: Any) -> float | None:
    raw = headers.get("Retry-After") if headers is not None else None
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class NvidiaBaselineBAdapter(BaselineBAdapter):
    """Naive first-candidate adapter with provider-specific metadata only."""

    def __init__(self, spec: BaselineSpec, lab: MutationLab | None = None, *, model_caller: NvidiaModelCaller | None = None) -> None:
        super().__init__(spec, lab, model_caller=model_caller)
        self.configuration = replace(
            self.configuration,
            model_id=spec.model_id,
            model_revision=str(spec.metadata.get("model_revision", NVIDIA_CANDIDATE_MODEL_REVISION)),
            provenance="MODEL_ASSISTED",
        )
        self._nvidia_model_caller = model_caller

    def run_mutation(self, prepared: PreparedParticipantRun) -> ParticipantRunEvidence:
        case = self._lab.apply_mutation(prepared.input.mutation_id, prepared.input.seed)
        repair_prompt = self.configuration.repair_prompt_template.format(
            target="https://example.test/gpu-1",
            extraction_contract="gpu-price-schema-v1",
            observed_output=repr(case.mutated.fixture.records),
            failure_description=f"controlled mutation {prepared.input.mutation_id}",
            scraper_source="approved static selector scraper configuration",
        )
        model_result = baseline_b_model_call(self.configuration, caller=self._model_caller, system_prompt=self.configuration.system_prompt, repair_prompt=repair_prompt)
        artifact = f"{prepared.input.artifact_root}/{prepared.input.artifact_name}"
        unavailable = isinstance(model_result, BaselineBUnavailable)
        if unavailable:
            candidate_execution = None
            failure_state = model_result.reason
            candidate_received = candidate_selected = candidate_accepted = False
            candidate = NOT_APPLICABLE
            candidate_application: Mapping[str, Any] | str = NOT_APPLICABLE
            output_eligible: bool | str = NOT_APPLICABLE
        else:
            candidate_execution = apply_first_candidate(self.configuration, model_result, case.mutated.fixture)
            failure_state = candidate_execution.failure_state
            candidate_received = candidate_execution.candidate_received
            candidate_selected = candidate_execution.candidate_selected
            candidate_accepted = candidate_execution.candidate_accepted
            candidate = candidate_execution.candidate
            application = dict(candidate_execution.application or {})
            if self._nvidia_model_caller is not None:
                application.update({"provider": NVIDIA_PROVIDER, "model_id": self._nvidia_model_caller.descriptor.model_id, "model_revision": self._nvidia_model_caller.descriptor.model_revision, "tools_enabled": False})
                if self._nvidia_model_caller.last_observation is not None:
                    application["provider_observation"] = self._nvidia_model_caller.last_observation.__dict__
            candidate_application = application or NOT_APPLICABLE
            output_eligible = candidate_accepted
        evidence_refs = [prepared.input.ground_truth_reference, f"{artifact}#model-output"]
        for marker, present in (("candidate-received", candidate_received), ("candidate-selected", candidate_selected), ("candidate-accepted", candidate_accepted)):
            if present:
                evidence_refs.append(f"{artifact}#{marker}")
        return ParticipantRunEvidence(
            participant_id=self.participant_id,
            run_id=prepared.input.run_id,
            mutation_id=prepared.input.mutation_id,
            severity=prepared.input.severity,
            seed=prepared.input.seed,
            fixture_version=prepared.input.fixture_version,
            participant_revision=prepared.input.code_revision,
            configuration_hash=prepared.input.configuration_hash,
            ground_truth_reference=prepared.input.ground_truth_reference,
            code_revision=prepared.input.code_revision,
            environment_reference=prepared.input.environment_reference,
            timeout_policy=prepared.input.timeout_policy,
            retry_policy=prepared.input.retry_policy,
            artifact_root=prepared.input.artifact_root,
            observation_reference=f"{artifact}#observation",
            detected=NOT_APPLICABLE,
            verification_status=NOT_APPLICABLE,
            risk_decision=NOT_APPLICABLE,
            output_eligible=output_eligible,
            failure_state=failure_state,
            timing_ms={"collection": 0, "model": 0, "total": 0},
            cost=NOT_APPLICABLE,
            llm_calls=0 if unavailable else 1,
            evidence_refs=tuple(evidence_refs),
            artifact_refs=(artifact,),
            provenance=self.configuration.provenance,
            candidate_received=candidate_received,
            candidate_selected=candidate_selected,
            candidate_accepted=candidate_accepted,
            candidate=candidate,
            candidate_application=candidate_application,
        )


class NvidiaParticipantRegistry(ParticipantRegistry):
    """Registry that swaps only Baseline B when config metadata selects NVIDIA NIM."""

    def __init__(self, config: BenchmarkConfig, lab: MutationLab | None = None, *, model_caller: NvidiaModelCaller | None = None) -> None:
        lab = lab or MutationLab()
        specs = {spec.baseline_id: spec for spec in config.baselines}
        self._adapters: Mapping[str, ParticipantAdapter] = {
            "BASELINE_A": BaselineAAdapter(specs["BASELINE_A"], lab),
            "BASELINE_B": NvidiaBaselineBAdapter(specs["BASELINE_B"], lab, model_caller=model_caller),
            "AEGIS": AegisAdapter(specs["AEGIS"], lab),
        }
        for adapter in self._adapters.values():
            if isinstance(adapter, _BaseAdapter):
                adapter._benchmark_config = config


__all__ = [
    "NVIDIA_API_KEY_ENV_NAMES",
    "NVIDIA_CANDIDATE_MODEL_ID",
    "NVIDIA_CANDIDATE_MODEL_REVISION",
    "NVIDIA_HOSTED_ENDPOINT",
    "NVIDIA_PROVIDER",
    "ModelDescriptor",
    "NvidiaBaselineBAdapter",
    "NvidiaCallObservation",
    "NvidiaModelCaller",
    "NvidiaModelCatalog",
    "NvidiaParticipantRegistry",
    "NvidiaProviderError",
    "ProviderRateLimiter",
    "RateLimitConfig",
    "candidate_model_descriptor",
    "load_nvidia_api_key",
    "normalize_nvidia_chat_response",
    "official_candidate_catalog",
    "prompt_sha256",
]
