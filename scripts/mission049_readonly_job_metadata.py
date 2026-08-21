"""Execute Mission 049’s one documented read-only job-metadata lookup only when explicitly invoked."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aegis.readonly_job_metadata import request_readonly_job_metadata


MISSION_DIR = Path("experiments/mission_049_readonly_provider_diagnostics")
COLLECTOR_ID = "c_mt09pib13nxqz1coi"


def _write_once(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the single documented GET /dca/log/{job_id} lookup.")
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing provider contact without --execute")
    token = os.environ.get("BRIGHT_DATA_API_TOKEN", "")
    if not token:
        raise SystemExit("BRIGHT_DATA_API_TOKEN is not available to the server-side diagnostic process")
    request_path = MISSION_DIR / "job_metadata_request_metadata.json"
    response_path = MISSION_DIR / "job_metadata_response.json"
    for path in (request_path, response_path):
        if path.exists():
            raise SystemExit(f"Refusing to overwrite evidence: {path}")
    result = request_readonly_job_metadata(token, job_id=args.job_id)
    safe = result.to_safe_dict()
    _write_once(request_path, {"operation": safe["operation"], "endpoint": safe["endpoint"], "job_id": args.job_id, "retry_count": 0, "key_exposed": False, "listed_collector_context": COLLECTOR_ID})
    _write_once(response_path, safe)
    print(json.dumps({"http_status": safe["http_status"], "success": safe["success"], "collector_id": safe["collector_id"], "template_reference": safe["template_reference"], "retry_count": 0, "key_exposed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
