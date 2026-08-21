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
    assert lineage.required_fields_missing_after_normalization == ()
    assert lineage.required_fields_null_in_any_normalized_row == REQUIRED


def test_required_field_drop_is_classified_as_aegis_normalization_loss() -> None:
    raw = ({"input": {"url": "https://example.test"}, "title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"},)
    normalized = ({"input": {"url": "https://example.test"}},)

    lineage = analyze_output_lineage(raw, normalized, REQUIRED)

    assert lineage.classification == "AEGIS_NORMALIZATION_LOSS"
    assert lineage.required_fields_missing_from_provider == ()
    assert lineage.required_fields_dropped_by_normalization == REQUIRED
    assert lineage.required_fields_missing_after_normalization == REQUIRED


def test_null_required_fields_are_explicit_and_not_misclassified_as_absent() -> None:
    rows = ({"input": {"url": "https://example.test"}, "title": None, "price": {"currency": "USD", "value": 599}, "availability": "Available"},)

    lineage = analyze_output_lineage(rows, rows, REQUIRED)

    assert lineage.classification == "DECODED_PROVIDER_OUTPUT_NULL_REQUIRED_FIELD"
    assert lineage.required_fields_missing_from_provider == ()
    assert lineage.required_fields_null_in_any_provider_row == ("title",)
    assert lineage.required_fields_missing_in_any_provider_row == ()


def test_missing_required_field_in_one_of_multiple_rows_is_explicit() -> None:
    rows = (
        {"title": "Widget A", "price": {"currency": "USD", "value": 599}, "availability": "Available"},
        {"title": "Widget B", "price": {"currency": "USD", "value": 699}},
    )

    lineage = analyze_output_lineage(rows, rows, REQUIRED)

    assert lineage.classification == "DECODED_PROVIDER_OUTPUT_PARTIALLY_INCOMPLETE"
    assert lineage.required_fields_missing_from_provider == ()
    assert lineage.required_fields_missing_in_any_provider_row == ("availability",)
    assert lineage.decoded_provider_row_count == 2


def test_empty_required_string_is_explicit_while_nested_fields_remain_nonmatching() -> None:
    empty = ({"title": "", "price": {"currency": "USD", "value": 599}, "availability": "Available", "trace": {"request": "safe"}},)
    nested = ({"product": {"title": "Widget", "price": 599, "availability": "Available"}},)

    empty_lineage = analyze_output_lineage(empty, empty, REQUIRED)
    nested_lineage = analyze_output_lineage(nested, nested, REQUIRED)

    assert empty_lineage.classification == "DECODED_PROVIDER_OUTPUT_EMPTY_REQUIRED_FIELD"
    assert empty_lineage.required_fields_empty_string_in_any_provider_row == ("title",)
    assert nested_lineage.classification == "DECODED_PROVIDER_OUTPUT_INCOMPLETE"
    assert nested_lineage.required_fields_missing_from_provider == REQUIRED


def test_extra_fields_are_visible_without_being_treated_as_required_loss() -> None:
    rows = ({"title": "Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available", "source": "provider", "timestamp": "2026-08-20T00:00:00Z"},)

    lineage = analyze_output_lineage(rows, rows, REQUIRED)

    assert lineage.classification == "REQUIRED_FIELDS_PRESERVED"
    assert lineage.decoded_provider_fields == ("availability", "price", "source", "timestamp", "title")
    assert lineage.nonrequired_fields_dropped == ()
