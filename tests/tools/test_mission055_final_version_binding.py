import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "experiments" / "mission_055_final_version_binding"


def _read(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_unbound_v1_context_never_becomes_a_claimed_mission041b_version() -> None:
    result = _read("reconciliation.json")
    inventory = result["historical_inventory"]

    assert result["MISSION_041B_VERSION"] == "UNKNOWN"
    assert result["PRODUCTION_PARSER_IDENTITY"] == "UNKNOWN"
    assert result["DEVELOPMENT_PRODUCTION_MATCH"] == "UNKNOWN"
    assert result["ROOT_CAUSE"] == "UNKNOWN"
    assert inventory["version_selector"] == "ABSENT"
    assert inventory["provider_run_id"] is None
    assert inventory["provider_response_id"] is None
    assert inventory["binding_result"] == "NO_EXACT_DASHBOARD_RUN_BINDING"
    assert result["PROVIDER_OPERATIONS"] == 0


def test_missing_evidence_requires_read_only_exact_run_metadata_before_parser_comparison() -> None:
    missing = _read("missing_evidence.json")

    assert missing["provider_operations_required_by_this_mission"] == 0
    assert missing["state_changes_required_by_this_mission"] == 0
    assert any("provider run ID" in item for item in missing["required_to_resolve_version_identity"])
    assert any("one input and one record" in item for item in missing["not_sufficient"])
