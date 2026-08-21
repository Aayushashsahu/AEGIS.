from aegis.mission056_candidate_evidence import (
    candidate_field_states,
    candidate_is_complete,
    normalize_candidate_row,
    target_facts_from_html,
)


def test_target_facts_parse_from_each_static_variant_without_provider_output() -> None:
    baseline = b'<h1 data-aegis-field="title">AEGIS Recovery Widget</h1><p data-aegis-field="price" data-currency="USD" data-value="599.00">$599.00</p><p data-aegis-field="availability">Available</p>'
    drift = b'<span data-testid="product-title">AEGIS Recovery Widget</span><span data-testid="product-price" data-money-currency="USD" data-money-value="599.00">$599.00</span><span data-testid="product-availability">Available</span>'
    expected = {"title": "AEGIS Recovery Widget", "price": {"currency": "USD", "value": 599.0}, "availability": "Available"}

    assert target_facts_from_html(baseline, variant="baseline") == expected
    assert target_facts_from_html(drift, variant="drift") == expected


def test_candidate_completeness_and_transparent_price_normalization_are_fail_closed() -> None:
    complete = [{"title": "AEGIS Recovery Widget", "price": "$599.00", "availability": "Available", "debug": "untrusted"}]
    incomplete = [{"input": {"url": "https://example.test"}}]

    assert candidate_field_states(complete) == {"title": "PRESENT", "price": "PRESENT", "availability": "PRESENT"}
    assert candidate_is_complete(complete) is True
    assert normalize_candidate_row(complete[0]) == {"title": "AEGIS Recovery Widget", "price": {"currency": "USD", "value": 599.0}, "availability": "Available"}
    assert candidate_field_states(incomplete) == {"title": "MISSING", "price": "MISSING", "availability": "MISSING"}
    assert candidate_is_complete(incomplete) is False
