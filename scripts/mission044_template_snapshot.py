"""Exactly-one owner-authorized Mission 044 read-only collector output-schema snapshot."""

from __future__ import annotations

import json
import os

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.readonly_template_snapshot import request_readonly_template_snapshot


COLLECTOR_NAME = "aegis-mission-033-v1"


def main() -> int:
    result = request_readonly_template_snapshot(
        os.environ[BRIGHT_DATA_DCA_TOKEN_ENV],
        collector_id=MISSION034_COLLECTOR_ID,
        collector_name=COLLECTOR_NAME,
    )
    print(json.dumps(result.to_safe_dict(), sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
