"""Mission 015 Baseline A deterministic participant implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .mutation_lab import StagingFixture

BASELINE_A_CONFIG_VERSION = "baseline-a-v1"
BASELINE_A_SCHEMA_VERSION = "gpu-price-schema-v1"
PARTICIPANT_OUTPUT_SCHEMA = "participant-run-evidence-v1"
PARTICIPANT_NORMALIZATION = "canonical-participant-run-v1"


@dataclass(frozen=True)
class BaselineAStaticSelectorConfig:
    selector_version: str = "baseline-a-v1"
    schema_version: str = BASELINE_A_SCHEMA_VERSION
    selectors: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.selectors is None:
            object.__setattr__(
                self,
                "selectors",
                {
                    "title": "CSS_SELECTOR",
                    "price": "CSS_SELECTOR",
                    "availability": "CSS_SELECTOR",
                    "rating": "CSS_SELECTOR",
                    "url": "CSS_SELECTOR",
                },
            )


class BaselineAStaticExtractor:
    """Deterministic fixed-selector projection; it never reads ground truth."""

    def __init__(self, config: BaselineAStaticSelectorConfig | None = None) -> None:
        self.config = config or BaselineAStaticSelectorConfig()

    def extract(self, fixture: StagingFixture) -> tuple[Mapping[str, Any], ...]:
        output: list[Mapping[str, Any]] = []
        for row in fixture.records:
            projected = {
                field: row[field_name]
                for field, field_name in (
                    ("product_id", "product_id"),
                    ("title", "title"),
                    ("price", "price"),
                    ("availability", "availability"),
                    ("rating", "rating"),
                    ("url", "url"),
                )
                if field_name in row
            }
            output.append(projected)
        return tuple(output)


BASELINE_B_CONFIG_VERSION = "baseline-b-v1"
BASELINE_B_SYSTEM_PROMPT_VERSION = "baseline-b-system-v1"
BASELINE_B_REPAIR_PROMPT_VERSION = "baseline-b-repair-v1"
BASELINE_B_MODEL_ID = "gemini-3.6-flash"
BASELINE_B_MODEL_REVISION = "stable"
BASELINE_B_SYSTEM_PROMPT = """You repair a web scraper whose extracted output has changed.

Your job is to modify the scraper so that it restores the expected
extraction behavior while preserving the requested output schema.

Return ONLY the repaired scraper code/configuration and a concise
explanation of what changed.

Do not discuss verification.
Do not ask for human approval.
Do not perform additional validation beyond what is necessary to
produce the repaired scraper.
"""
BASELINE_B_REPAIR_PROMPT_TEMPLATE = """Repair the scraper for the following extraction failure.

TARGET:
{target}

EXPECTED OUTPUT SCHEMA:
{extraction_contract}

OBSERVED OUTPUT:
{observed_output}

FAILURE DESCRIPTION:
{failure_description}

SCRAPER:
{scraper_source}

Produce the repaired scraper.
"""


@dataclass(frozen=True)
class BaselineBConfiguration:
    model_id: str = BASELINE_B_MODEL_ID
    model_revision: str = BASELINE_B_MODEL_REVISION
    system_prompt_version: str = BASELINE_B_SYSTEM_PROMPT_VERSION
    system_prompt: str = BASELINE_B_SYSTEM_PROMPT
    repair_prompt_template_version: str = BASELINE_B_REPAIR_PROMPT_VERSION
    repair_prompt_template: str = BASELINE_B_REPAIR_PROMPT_TEMPLATE
    temperature: str = "NOT_APPLICABLE"
    top_p: str = "NOT_APPLICABLE"
    top_k: str = "NOT_APPLICABLE"
    max_output_tokens: int = 8192
    tools_enabled: bool = False
    candidate_policy: str = "FIRST_CANDIDATE"
    max_candidates: int = 1
    auto_accept_first_candidate: bool = True
    timeout_seconds: int = 300
    retry_count: int = 0
    backoff_seconds: int = 0
    provenance: str = "MODEL_ASSISTED"


@dataclass(frozen=True)
class BaselineBUnavailable:
    model_id: str
    model_revision: str
    reason: str = "MODEL_CALL_NOT_EXECUTED_IN_VALIDATION_ONLY_MISSION"


ModelCaller = Callable[[str, str], Mapping[str, Any]]


def baseline_b_model_call(
    configuration: BaselineBConfiguration,
    *,
    caller: ModelCaller | None,
    system_prompt: str,
    repair_prompt: str,
) -> Mapping[str, Any] | BaselineBUnavailable:
    """Call only an explicitly injected model client; no default network path."""

    if caller is None:
        return BaselineBUnavailable(configuration.model_id, configuration.model_revision)
    return caller(system_prompt, repair_prompt)
