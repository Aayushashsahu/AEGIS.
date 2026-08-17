from __future__ import annotations

import pytest

from aegis.baseline_participants import BaselineAStaticExtractor
from aegis.mutation_lab import MutationLab


@pytest.mark.parametrize("mutation_id", ["M001", "M002", "M003", "M004", "M005", "M006"])
def test_baseline_a_extracts_each_exact_mutation_fixture_without_ground_truth(mutation_id: str) -> None:
    lab = MutationLab()
    case = lab.apply_mutation(mutation_id, 12345)
    extractor = BaselineAStaticExtractor()
    first = extractor.extract(case.mutated.fixture)
    second = extractor.extract(case.mutated.fixture)
    assert first == second
    assert first == case.mutated.fixture.records
    assert "expected_correct_state" not in first[0] if first else True


def test_baseline_a_configuration_is_fixed_selector_only() -> None:
    extractor = BaselineAStaticExtractor()
    assert extractor.config.selector_version == "baseline-a-v1"
    assert extractor.config.schema_version == "gpu-price-schema-v1"
    assert extractor.config.selectors == {
        "title": "CSS_SELECTOR",
        "price": "CSS_SELECTOR",
        "availability": "CSS_SELECTOR",
        "rating": "CSS_SELECTOR",
        "url": "CSS_SELECTOR",
    }
