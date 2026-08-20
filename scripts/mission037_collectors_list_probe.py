"""One-shot server-only Mission 037 read-only collector-list probe."""

from __future__ import annotations

import json
import os
import sys

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.readonly_collectors import DEFAULT_COLLECTORS_LIST_TIMEOUT_SECONDS, request_readonly_collectors_list


def main() -> int:
    api_token = os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "")
    if not api_token.strip():
        print(
            json.dumps(
                {
                    "operation": "collectors_list",
                    "error_class": "CREDENTIAL_NOT_CONFIGURED",
                    "retry_count": 0,
                    "key_exposed": False,
                },
                sort_keys=True,
            )
        )
        return 2
    result = request_readonly_collectors_list(
        api_token,
        canonical_collector_id=MISSION034_COLLECTOR_ID,
        timeout_seconds=DEFAULT_COLLECTORS_LIST_TIMEOUT_SECONDS,
    )
    print(json.dumps(result.to_safe_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
