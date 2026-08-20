"""One-shot server-only Mission 038 Self-Healing progress probe."""

from __future__ import annotations

import json
import os

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.readonly_heal_progress import DEFAULT_HEAL_PROGRESS_TIMEOUT_SECONDS, request_readonly_heal_progress


MISSION033_CANDIDATE_ID = "candidate_m033_a0d9aa5a0d056720"


def main() -> int:
    api_token = os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "")
    if not api_token.strip():
        print(json.dumps({"error_class": "CREDENTIAL_NOT_CONFIGURED", "key_exposed": False, "operation": "self_healing_progress", "retry_count": 0}, sort_keys=True))
        return 2
    result = request_readonly_heal_progress(
        api_token,
        collector_id=MISSION034_COLLECTOR_ID,
        candidate_id=MISSION033_CANDIDATE_ID,
        timeout_seconds=DEFAULT_HEAL_PROGRESS_TIMEOUT_SECONDS,
    )
    print(json.dumps(result.to_safe_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
