"""One-shot server-only Mission 035 read-only account-budget probe."""

from __future__ import annotations

import json
import os
import sys

from aegis.approval_boundary import BRIGHT_DATA_CLI_CREDENTIAL_ENV
from aegis.readonly_budget import DEFAULT_BUDGET_TIMEOUT_SECONDS, request_readonly_budget


def main() -> int:
    api_key = os.environ.get(BRIGHT_DATA_CLI_CREDENTIAL_ENV, "")
    if not api_key.strip():
        print(
            json.dumps(
                {
                    "operation": "budget",
                    "error_class": "CREDENTIAL_NOT_CONFIGURED",
                    "retry_count": 0,
                    "key_exposed": False,
                },
                sort_keys=True,
            )
        )
        return 2
    result = request_readonly_budget(api_key, timeout_seconds=DEFAULT_BUDGET_TIMEOUT_SECONDS)
    print(json.dumps(result.to_safe_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
