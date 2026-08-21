import pytest

from aegis.bounded_rerun_preflight import BoundedRerunPreflightEvidence, evaluate_bounded_rerun_preflight


def _evidence(**changes: object) -> BoundedRerunPreflightEvidence:
    values: dict[str, object] = {
        "collector_id": "c_mt09pib13nxqz1coi",
        "current_operation_state": "UNKNOWN",
        "known_conflict": False,
        "rerun_budget": 1,
        "retry_budget": 0,
        "approval_budget": 0,
        "heal_budget": 0,
        "commit_budget": 0,
        "rollback_budget": 0,
        "historical_evidence_intact": True,
        "response_capture_armed": True,
        "correlation_id_generated": True,
    }
    values.update(changes)
    return BoundedRerunPreflightEvidence(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "allowed"),
    [
        ({"current_operation_state": "KNOWN_CONFLICT", "known_conflict": True}, False),
        ({"current_operation_state": "KNOWN_CLEAR"}, True),
        ({"current_operation_state": "UNKNOWN", "known_conflict": False}, True),
        ({"current_operation_state": "UNKNOWN", "known_conflict": True}, False),
        ({"collector_id": ""}, False),
        ({"collector_id": "c_wrong"}, False),
        ({"rerun_budget": 0}, False),
        ({"retry_budget": 1}, False),
        ({"response_capture_armed": False}, False),
        ({"historical_evidence_intact": False}, False),
    ],
    ids=[
        "known-conflict-blocks",
        "known-clear-allows",
        "unknown-without-known-conflict-allows",
        "unknown-with-known-conflict-blocks",
        "missing-collector-blocks",
        "wrong-collector-blocks",
        "consumed-budget-blocks",
        "retry-budget-blocks",
        "capture-unavailable-blocks",
        "integrity-failure-blocks",
    ],
)
def test_owner_specified_bounded_policy_cases(changes: dict[str, object], allowed: bool) -> None:
    decision = evaluate_bounded_rerun_preflight(_evidence(**changes))
    assert decision.allows_single_bounded_rerun is allowed


def test_unknown_is_not_proven_clear_even_when_bounded_policy_allows() -> None:
    decision = evaluate_bounded_rerun_preflight(_evidence(current_operation_state="UNKNOWN"))
    assert decision.allows_single_bounded_rerun is True
    assert decision.known_conflict == "NO"
    assert decision.conflict_absence_proven is False
    assert "does not expose documented collector-scoped" in decision.preflight_reason
