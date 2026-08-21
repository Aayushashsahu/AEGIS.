import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "experiments" / "mission_054_prod_dev_reconciliation"


def _read(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_reconciliation_remains_unknown_without_exact_parser_or_run_binding() -> None:
    reconciliation = _read("reconciliation.json")
    answers = reconciliation["answers"]
    audit = _read("version_assumption_audit.json")

    assert answers["PRODUCTION_PARSER_IDENTITY"] == "UNKNOWN"
    assert answers["DEVELOPMENT_PRODUCTION_MATCH"] == "UNKNOWN"
    assert answers["LIKELY_ROOT_CAUSE"] == "UNKNOWN; DEVELOPMENT/PRODUCTION_TEMPLATE_DIVERGENCE is a plausible hypothesis but is not supported strongly enough to assert because parser identity and Mission 041B run-to-version binding are both unproven."
    assert answers["REAL_PROVIDER_CALLS"] == 0
    assert answers["MUTATIONS"] == 0
    assert audit["mission_041b"]["explicit_version_selector"] == "ABSENT"
    assert audit["aegis_adapter"]["implicit_selection_behavior"] == "DELEGATED_TO_PROVIDER_DEFAULT"


def test_cli_capabilities_and_future_action_are_documented_but_not_executed() -> None:
    reconciliation = _read("reconciliation.json")["answers"]
    future = _read("minimum_future_action.json")

    assert reconciliation["CURRENT_CLI_VERSION"] == "0.3.5 via npx -y -p @brightdata/cli bdata --version"
    assert reconciliation["RUN_VERSION_SELECTOR_SUPPORTED"] == "YES; scraper run --help exposes --version <version> and uses dev as its documented example."
    assert reconciliation["AUTO_SAVE_SUPPORTED"].startswith("YES;")
    assert future["status"] == "PREPARED_NOT_EXECUTED"
    assert future["dashboard_action"]["execution"] == "NOT_AUTHORIZED_NOT_EXECUTED"
    assert future["pending_heal_cli_action"]["execution"] == "NOT_AUTHORIZED_NOT_EXECUTED"
