from scripts.mission048c_evidence_preserving_rerun import _field_state


def test_field_state_classifies_nested_input_url_without_changing_required_field_semantics() -> None:
    row = {"input": {"url": "https://example.test"}, "title": None, "price": "", "availability": "Available"}

    assert _field_state(row, "input.url") == "PRESENT"
    assert _field_state(row, "title") == "NULL"
    assert _field_state(row, "price") == "EMPTY"
    assert _field_state(row, "availability") == "PRESENT"
    assert _field_state(row, "input.missing") == "MISSING"
