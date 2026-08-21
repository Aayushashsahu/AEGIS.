"""Execute the single documented Mission 049 jobs-list diagnostic only when explicitly invoked."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aegis.readonly_job_diagnostics import request_readonly_jobs_list


MISSION_DIR = Path("experiments/mission_049_readonly_provider_diagnostics")
COLLECTOR_ID = "c_mt09pib13nxqz1coi"
MISSION_048C_RAW_SHA256 = "17e53a8b320b57db29f9c7538663e786b3b741a08f2ef7033c39d31d58d12364"


def _write_once(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the single authorized documented GET /dca/collector/jobs.")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing provider contact without --execute")
    token = os.environ.get("BRIGHT_DATA_API_TOKEN", "")
    if not token:
        raise SystemExit("BRIGHT_DATA_API_TOKEN is not available to the server-side diagnostic process")
    request_path = MISSION_DIR / "diagnostic_request_metadata.json"
    response_path = MISSION_DIR / "diagnostic_response.json"
    correlation_path = MISSION_DIR / "correlation.json"
    for path in (request_path, response_path, correlation_path):
        if path.exists():
            raise SystemExit(f"Refusing to overwrite evidence: {path}")
    result = request_readonly_jobs_list(token, collector_id=COLLECTOR_ID, from_date=args.from_date, to_date=args.to_date)
    safe = result.to_safe_dict()
    _write_once(request_path, {"operation": safe["operation"], "endpoint": safe["endpoint"], "collector_id": COLLECTOR_ID, "from_date": args.from_date, "to_date": args.to_date, "retry_count": 0, "key_exposed": False})
    _write_once(response_path, safe)
    _write_once(correlation_path, {"mission_048c_raw_response_sha256": MISSION_048C_RAW_SHA256, "mission_048c_correlation_id": "mission048c-rerun-c_mt09pib13nxqz1coi-20260821T042811Z", "exact_sync_response_id": None, "correlation_rule": "A returned job is not attributed to Mission 048C without an explicit provider identifier; timestamp proximity alone is insufficient.", "correlation_status": "UNRESOLVED_PENDING_READONLY_RESPONSE"})
    print(json.dumps({"http_status": safe["http_status"], "success": safe["success"], "job_count": len(result.jobs), "retry_count": 0, "key_exposed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
