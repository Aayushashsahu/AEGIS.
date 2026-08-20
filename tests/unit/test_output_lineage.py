from aegis.output_lineage import analyze_output_lineage


REQUIRED = ("title", "price", "availability")


def test_complete_provider_row_survives_canonical_normalization() -> None:
    raw = ({"input": {"url": "https://example.test"}, "title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"},)
    normalized = ({"title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"},)

    lineage = analyze_output_lineage(raw, normalized, REQUIRED)

    assert lineage.classification == "REQUIRED_FIELDS_PRESERVED"
    assert lineage.required_fields_missing_from_provider == ()
    assert lineage.required_fields_dropped_by_normalization == ()
    assert lineage.required_fields_missing_after_normalization == ()
    assert lineage.nonrequired_fields_dropped == ("input",)


def test_mission_041b_observed_shape_is_incomplete_before_normalization() -> None:
    raw = ({"input": {"url": "https://example.test/mission-033/target"}},)
    normalized = ({"title": None, "price": None, "availability": None},)

    lineage = analyze_output_lineage(raw, normalized, REQUIRED)

    assert lineage.classification == "DECODED_PROVIDER_OUTPUT_INCOMPLETE"
    assert lineage.decoded_provider_fields == ("input",)
    assert lineage.required_fields_missing_from_provider == REQUIRED
    assert lineage.required_fields_dropped_by_normalization == ()
    assert lineage.required_fields_missing_after_normalization == REQUIRED


def test_required_field_drop_is_classified_as_aegis_normalization_loss() -> None:
    raw = ({"input": {"url": "https://example.test"}, "title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"},)
    normalized = ({"input": {"url": "https://example.test"}},)

    lineage = analyze_output_lineage(raw, normalized, REQUIRED)

    assert lineage.classification == "AEGIS_NORMALIZATION_LOSS"
    assert lineage.required_fields_missing_from_provider == ()
    assert lineage.required_fields_dropped_by_normalization == REQUIRED
    assert lineage.required_fields_missing_after_normalization == REQUIRED
