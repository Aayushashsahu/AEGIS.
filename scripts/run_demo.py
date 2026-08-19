#!/usr/bin/env python3
"""Build a safe AEGIS Judge Mode demo session.

The default invocation is replay-only: it validates committed evidence,
regenerates the static snapshot, and writes a DemoSession artifact. `--live`
is deliberately blocked until an explicit future live authorization module
implements every gate in Mission 031's audit. This prevents a demo command
from becoming an accidental collection/healing loop.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis.audit_store import _redact, _to_jsonable
from scripts.mission031_build_demo_snapshot import build_snapshot


ROOT = Path(__file__).resolve().parents[1]


def run_demo(root: Path, *, live: bool = False, output_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    if live:
        return {
            "status": "BLOCKED_PROVIDER_AUTHORIZATION_REQUIRED",
            "live_provider_invoked": False,
            "bright_data_create_operations": 0,
            "bright_data_run_operations": 0,
            "bright_data_heal_operations": 0,
            "approval_operations": 0,
            "production_commits": 0,
            "message": "Mission 031 live mode is fail-closed until a separately reviewed gate records G1–G5. Use the default replay mode for Judge Mode.",
        }
    snapshot = build_snapshot(root)
    session = {
        "schema_version": "mission-031-demo-session-v1",
        "session_type": "JUDGE_MODE_REPLAY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "REPLAY_READY",
        "live_provider_invoked": False,
        "bright_data_create_operations": 0,
        "bright_data_run_operations": 0,
        "bright_data_heal_operations": 0,
        "approval_operations": 0,
        "production_commits": 0,
        "benchmark_runs_executed": 0,
        "gemini_invocations": 0,
        "nvidia_invocations": 0,
        "snapshot_schema_version": snapshot["schema_version"],
        "live_lane_status": snapshot["live_lane"]["terminal_status"],
        "controlled_replay_mode": snapshot["controlled_replay"]["mode"],
        "controlled_replay_output_eligible": snapshot["controlled_replay"]["commit"]["output_eligible"],
        "judge_mode_launch": "cd webapp && pnpm dev",
        "claim": "AI proposes. Evidence decides.",
    }
    session_path = output_path or root / "experiments" / "mission_031" / "demo_session.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(_redact(_to_jsonable(session)), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return session


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the AEGIS Judge Mode replay session")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--live", action="store_true", help="request the fail-closed live-mode gate; no provider call occurs")
    args = parser.parse_args()
    result = run_demo(args.root, live=args.live)
    print(json.dumps(_redact(_to_jsonable(result)), sort_keys=True, indent=2))
    return 0 if result["status"] == "REPLAY_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
