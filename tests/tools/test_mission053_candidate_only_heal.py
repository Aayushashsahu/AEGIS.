import json

from scripts.mission053_candidate_only_heal import (
    COLLECTOR_ID,
    REQUIRED_FIELDS,
    _field_state,
    _parse_json,
    _preview,
    _prompt,
    _target_url,
    build_command,
    preflight,
)


def test_exact_heal_command_has_zero_retries_and_no_approval_or_rerun() -> None:
    command = build_command(collector_id=COLLECTOR_ID, target_url=_target_url(), prompt=_prompt())

    assert command[:7] == ["npx", "-p", "@brightdata/cli", "bdata", "--timing", "scraper", "heal"]
    assert command[7] == COLLECTOR_ID
    assert command[command.index("--max-retries") + 1] == "0"
    assert "--auto-approve" not in command
    assert "approve" not in command
    assert "run" not in command


def test_candidate_preview_is_complete_only_when_all_required_fields_are_present() -> None:
    complete = {"title": "Widget", "price": {"value": 599, "currency": "USD"}, "availability": "Available"}
    incomplete = {"input": {"url": _target_url()}}

    assert all(_field_state(complete, field) == "PRESENT" for field in REQUIRED_FIELDS)
    assert _field_state(incomplete, "title") == "MISSING"
    assert _field_state(incomplete, "price") == "MISSING"
    assert _field_state(incomplete, "availability") == "MISSING"


def test_json_parser_and_preview_extraction_are_provider_free() -> None:
    payload = {"status": "awaiting_approval", "preview_result": [{"title": "Widget", "price": {"value": 599}, "availability": "Available"}]}

    assert _parse_json(b"progress line\n" + json.dumps(payload).encode("utf-8")) == payload
    assert _preview(payload) == payload["preview_result"]
    assert _preview({"status": "awaiting_approval", "preview_result": {}}) is None


def test_post_execution_preflight_fails_closed_on_consumed_evidence_paths_without_contacting_provider(monkeypatch) -> None:
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "test-key-present-only-in-memory")
    report = preflight()

    assert report["checks"]["fresh_controlled_paths"] is False
    assert all(value for key, value in report["checks"].items() if key != "fresh_controlled_paths"), report["checks"]
    assert report["all_pass"] is False
    assert report["provider_requests_attempted"] == 0
    assert report["provider_mutations_attempted"] == 0
    assert report["retries"] == 0
