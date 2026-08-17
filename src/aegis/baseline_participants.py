"""Mission 015 Baseline A deterministic participant implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

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
