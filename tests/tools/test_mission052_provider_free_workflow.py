from scripts.mission052_provider_free_workflow import EXPECTED_ROW, INPUT_URL_ONLY_ROW, evaluate_post_approval_output


def test_simulated_persisted_template_returns_all_required_fields_and_passes_without_shipping() -> None:
    result = evaluate_post_approval_output(EXPECTED_ROW)

    assert result["provenance"] == "TEST_DOUBLE"
    assert result["candidate_preview_fields"] == ("availability", "price.currency", "price.value", "title")
    assert result["approval"] == "ACCEPTED_SIMULATED"
    assert result["template_persistence"] == "YES_SIMULATED"
    assert {"title", "price.value", "price.currency", "availability"}.issubset(result["post_approval_output_fields"])
    assert result["verification"] == "PASS"
    assert result["risk"] == "ACCEPT"
    assert result["commit"] == "BLOCKED"
    assert result["data_shipped"] == "NO"
    assert result["provider_operations"] == 0
    assert result["retries"] == 0


def test_simulated_input_url_only_post_approval_output_fails_closed() -> None:
    result = evaluate_post_approval_output(INPUT_URL_ONLY_ROW)

    assert result["provenance"] == "TEST_DOUBLE"
    assert result["post_approval_output_fields"] == ("input.url",)
    assert result["verification"] == "FAIL"
    assert result["risk"] == "REJECT"
    assert result["commit"] == "BLOCKED"
    assert result["data_shipped"] == "NO"
    assert result["provider_operations"] == 0
    assert result["retries"] == 0
