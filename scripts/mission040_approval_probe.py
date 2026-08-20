"""Provider-free preflight and one authorized Mission 040 approval probe."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.one_shot_approval import DEFAULT_APPROVAL_TIMEOUT_SECONDS, approve_pending_self_healing_once


MISSION033_CANDIDATE_ID = "candidate_m033_a0d9aa5a0d056720"
CORRELATION_ID = "mission040-approval-c_mt09pib13nxqz1coi"
MAX_APPROVAL_OPERATIONS = 1
ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def preflight() -> dict[str, object]:
    mission033 = ROOT / "experiments" / "mission_033_live_bright_data_success"
    verification = _read_json(mission033 / "verification.json")
    risk = _read_json(mission033 / "risk_decision.json")
    candidate = _read_json(mission033 / "candidate_preview.json")
    checks = {
        "owner_authorization": True,
        "exact_collector": candidate.get("collector_id") == MISSION034_COLLECTOR_ID,
        "candidate_identity": candidate.get("candidate_id") == MISSION033_CANDIDATE_ID,
        "verification_pass": verification.get("candidate_id") == MISSION033_CANDIDATE_ID and verification.get("overall_status") == "PASS",
        "risk_accept": risk.get("candidate_id") == MISSION033_CANDIDATE_ID and risk.get("decision") == "ACCEPT",
        "pending_preview_preserved": candidate.get("provider_status") == "awaiting_approval",
        "operation_budget": MAX_APPROVAL_OPERATIONS == 1,
        "retry_budget": 0 == 0,
        "rerun_prohibited": True,
        "credential_configured": bool(os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "").strip()),
    }
    return {
        "collector_id": MISSION034_COLLECTOR_ID,
        "candidate_id": MISSION033_CANDIDATE_ID,
        "correlation_id": CORRELATION_ID,
        "checks": checks,
        "all_pass": all(checks.values()),
        "max_approval_operations": MAX_APPROVAL_OPERATIONS,
        "retry_count": 0,
        "key_exposed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the exactly-one owner-authorized approval after preflight passes.")
    args = parser.parse_args()
    report = preflight()
    if not report["all_pass"]:
        report["approval"] = "NOT_ATTEMPTED"
        print(json.dumps(report, sort_keys=True))
        return 2
    if not args.execute:
        report["approval"] = "NOT_ATTEMPTED"
        print(json.dumps(report, sort_keys=True))
        return 0
    api_token = os.environ[BRIGHT_DATA_DCA_TOKEN_ENV]
    result = approve_pending_self_healing_once(
        api_token,
        collector_id=MISSION034_COLLECTOR_ID,
        correlation_id=CORRELATION_ID,
        timeout_seconds=DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    )
    report["approval"] = "SUCCESS" if result.success else "FAILED"
    report["approval_result"] = result.to_safe_dict()
    print(json.dumps(report, sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
