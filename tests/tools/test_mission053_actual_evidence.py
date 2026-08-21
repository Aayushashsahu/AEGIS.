import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "experiments" / "mission_053_candidate_only"


def _read(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_single_authorized_heal_failed_before_candidate_without_additional_provider_actions() -> None:
    preflight = _read("preflight.json")
    request = _read("heal_request.json")
    result = _read("heal_result.json")
    summary = _read("summary.json")

    assert preflight["all_pass"] is True
    assert preflight["provider_requests_attempted"] == 0
    assert preflight["provider_mutations_attempted"] == 0
    assert request["collector_id"] == "c_mt09pib13nxqz1coi"
    assert request["prompt_length"] == 368
    assert request["retry_budget"] == 0
    assert request["approval_authorized"] is False
    assert request["rerun_authorized"] is False
    assert result["provider_mutations"] == 1
    assert result["retries"] == 0
    assert result["provider_status"] == "error"
    assert result["raw_provider_response"]["preserved"] is True
    assert (EVIDENCE / result["raw_provider_response"]["path"]).is_file()
    assert not (EVIDENCE / "candidate_preview.json").exists()
    assert summary["heal"] == "FAILED"
    assert summary["candidate"] == "ABSENT"
    assert summary["approval"] == "NOT_AUTHORIZED"
    assert summary["rerun"] == "NOT_AUTHORIZED"
    assert summary["data_shipped"] == "NO"
