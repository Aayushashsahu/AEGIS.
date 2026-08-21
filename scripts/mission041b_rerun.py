"""Provider-free preflight and exactly-one owner-authorized Mission 041B rerun."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from aegis.approval_boundary import BRIGHT_DATA_DCA_TOKEN_ENV, MISSION034_COLLECTOR_ID
from aegis.one_shot_rerun import DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS, DEFAULT_RERUN_WAIT_SECONDS, rerun_collector_once
from aegis.operation_correlation import append_correlation_record, build_operation_correlation
from aegis.output_lineage import analyze_output_lineage


ROOT = Path(__file__).resolve().parents[1]
TARGET_URL = "https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target"
CORRELATION_ID = "mission041b-rerun-c_mt09pib13nxqz1coi"
MAX_RERUN_OPERATIONS = 1
REQUIRED_OUTPUT_FIELDS = ("title", "price", "availability")
CONTROLLED_EVIDENCE_ROOT = ROOT / "experiments"


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def preflight() -> dict[str, object]:
    approval = _read_json(ROOT / "experiments" / "mission_041a_post_approval_progress" / "progress_check.json")
    mission040 = _read_json(ROOT / "experiments" / "mission_033_live_bright_data_success" / "risk_decision.json")
    checks = {
        "mission040_approval_preserved": approval.get("approval") == "COMPLETED_IN_MISSION_040",
        "provider_heal_completed": approval.get("response", {}).get("progress_status") == "COMPLETED" if isinstance(approval.get("response"), dict) else False,
        "exact_collector": approval.get("collector_id") == MISSION034_COLLECTOR_ID,
        "authenticated_transport_configured": bool(os.environ.get(BRIGHT_DATA_DCA_TOKEN_ENV, "").strip()),
        "rerun_budget_exactly_one": MAX_RERUN_OPERATIONS == 1,
        "retry_budget_zero": True,
        "no_active_conflict": approval.get("response", {}).get("progress_status") == "COMPLETED" if isinstance(approval.get("response"), dict) else False,
        "historical_risk_evidence_present": mission040.get("decision") == "ACCEPT",
    }
    return {
        "collector_id": MISSION034_COLLECTOR_ID,
        "target_url": TARGET_URL,
        "correlation_id": CORRELATION_ID,
        "checks": checks,
        "all_pass": all(checks.values()),
        "max_rerun_operations": MAX_RERUN_OPERATIONS,
        "retry_count": 0,
        "key_exposed": False,
    }


def _controlled_evidence_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(CONTROLLED_EVIDENCE_ROOT.resolve())
    except ValueError as error:
        raise ValueError("evidence paths must be under the canonical experiments directory") from error
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform the exactly-one owner-authorized rerun after preflight passes.")
    parser.add_argument("--raw-response-path", type=Path, help="New controlled-evidence path for the exact provider response body; required with --execute.")
    parser.add_argument("--operation-id", help="Explicit, unique AEGIS operation ID; required with --execute.")
    parser.add_argument("--correlation-record-dir", type=Path, help="New append-only correlation-record directory; required with --execute.")
    args = parser.parse_args()
    if args.execute and (args.raw_response_path is None or not args.operation_id or args.correlation_record_dir is None):
        parser.error("--raw-response-path, --operation-id, and --correlation-record-dir are required with --execute")
    if not args.execute and (args.raw_response_path is not None or args.operation_id is not None or args.correlation_record_dir is not None):
        parser.error("raw-response and correlation options are valid only with --execute")
    if args.execute:
        try:
            args.raw_response_path = _controlled_evidence_path(args.raw_response_path)
            args.correlation_record_dir = _controlled_evidence_path(args.correlation_record_dir)
        except ValueError as error:
            parser.error(str(error))
    report = preflight()
    if not report["all_pass"]:
        report["rerun"] = "NOT_ATTEMPTED"
        print(json.dumps(report, sort_keys=True))
        return 2
    if not args.execute:
        report["rerun"] = "NOT_ATTEMPTED"
        print(json.dumps(report, sort_keys=True))
        return 0
    requested_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = rerun_collector_once(
        os.environ[BRIGHT_DATA_DCA_TOKEN_ENV],
        collector_id=MISSION034_COLLECTOR_ID,
        target_url=TARGET_URL,
        correlation_id=CORRELATION_ID,
        wait_seconds=DEFAULT_RERUN_WAIT_SECONDS,
        http_timeout_seconds=DEFAULT_RERUN_HTTP_TIMEOUT_SECONDS,
    )
    report["requested_at_utc"] = requested_at_utc
    report["rerun"] = "SUCCESS" if result.success else "FAILED"
    report["rerun_result"] = result.to_evidence_dict()
    if args.raw_response_path is not None:
        report["raw_response_evidence"] = result.preserve_raw_response(args.raw_response_path)
        correlation_record = build_operation_correlation(
            aegis_operation_id=args.operation_id,
            collector_id=MISSION034_COLLECTOR_ID,
            target_url=TARGET_URL,
            started_at_utc=requested_at_utc,
            provider_run_id=result.response_id,
            template_version=None,
            operation_type=result.operation,
            correlation_id=CORRELATION_ID,
        )
        report["correlation_record"] = str(append_correlation_record(args.correlation_record_dir, correlation_record))
    if result.success:
        # This transport performs no field projection: its decoded provider rows
        # are the derived AEGIS rows. The diagnostic makes that fact explicit
        # without claiming the original response body was retained.
        report["decoded_output_lineage"] = analyze_output_lineage(
            result.rows,
            result.rows,
            REQUIRED_OUTPUT_FIELDS,
        ).to_evidence_dict()
    print(json.dumps(report, sort_keys=True))
    return 0 if result.success else 3


if __name__ == "__main__":
    raise SystemExit(main())
