"""Evidence-based policy for a separately authorized bounded collector rerun."""

from __future__ import annotations

from dataclasses import asdict, dataclass


EXPECTED_COLLECTOR_ID = "c_mt09pib13nxqz1coi"
OPERATION_STATES = frozenset({"KNOWN_CLEAR", "KNOWN_CONFLICT", "UNKNOWN"})


@dataclass(frozen=True)
class BoundedRerunPreflightEvidence:
    collector_id: str
    current_operation_state: str
    known_conflict: bool
    rerun_budget: int
    retry_budget: int
    approval_budget: int
    heal_budget: int
    commit_budget: int
    rollback_budget: int
    historical_evidence_intact: bool
    response_capture_armed: bool
    correlation_id_generated: bool


@dataclass(frozen=True)
class BoundedRerunPreflightDecision:
    current_operation_state: str
    known_conflict: str
    conflict_absence_proven: bool
    preflight_decision: str
    preflight_reason: str
    checks: dict[str, bool]

    @property
    def allows_single_bounded_rerun(self) -> bool:
        return self.preflight_decision == "ALLOW_SINGLE_BOUNDED_RERUN"

    def to_evidence_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_bounded_rerun_preflight(evidence: BoundedRerunPreflightEvidence) -> BoundedRerunPreflightDecision:
    """Evaluate documented known-conflict evidence without treating UNKNOWN as CLEAR."""

    state_valid = evidence.current_operation_state in OPERATION_STATES
    conflict_absence_proven = evidence.current_operation_state == "KNOWN_CLEAR" and not evidence.known_conflict
    checks = {
        "exact_collector": evidence.collector_id == EXPECTED_COLLECTOR_ID,
        "current_operation_state_valid": state_valid,
        "no_known_conflict": not evidence.known_conflict,
        "one_rerun_budget": evidence.rerun_budget == 1,
        "zero_retry_budget": evidence.retry_budget == 0,
        "zero_approval_budget": evidence.approval_budget == 0,
        "zero_heal_budget": evidence.heal_budget == 0,
        "zero_commit_budget": evidence.commit_budget == 0,
        "zero_rollback_budget": evidence.rollback_budget == 0,
        "historical_evidence_intact": evidence.historical_evidence_intact,
        "response_capture_armed": evidence.response_capture_armed,
        "correlation_id_generated": evidence.correlation_id_generated,
    }
    if all(checks.values()):
        if evidence.current_operation_state == "UNKNOWN":
            reason = (
                "Provider does not expose documented collector-scoped current-operation listing; "
                "no known conflicting operation exists in available documented evidence."
            )
        else:
            reason = "Available documented evidence is known clear and contains no known conflicting operation."
        decision = "ALLOW_SINGLE_BOUNDED_RERUN"
    else:
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        reason = f"Bounded rerun blocked by failed preflight checks: {failed}."
        decision = "BLOCK"
    return BoundedRerunPreflightDecision(
        current_operation_state=evidence.current_operation_state if state_valid else "UNKNOWN",
        known_conflict="YES" if evidence.known_conflict else "NO",
        conflict_absence_proven=conflict_absence_proven,
        preflight_decision=decision,
        preflight_reason=reason,
        checks=checks,
    )
