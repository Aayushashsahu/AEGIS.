from __future__ import annotations

import json
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.benchmark_config import load_benchmark_config
from aegis.owner_approved_validation import load_owner_payload, validate_owner_configuration


ROOT = Path(__file__).resolve().parents[2]
OWNER_PATH = ROOT / "benchmarks" / "configs" / "mission_014_owner_approved_participants.json"
FROZEN_CONFIG_PATH = ROOT / "benchmarks" / "configs" / "mission_011_validation_floor.json"
OUTPUT_PATH = ROOT / "benchmarks" / "configs" / "mission_014_owner_validation.json"


def main() -> None:
    owner_payload = load_owner_payload(OWNER_PATH)
    frozen_config = load_benchmark_config(FROZEN_CONFIG_PATH)
    validation = validate_owner_configuration(owner_payload, source_configuration_hash=frozen_config.configuration_hash)
    if validation.status.value != "VALID":
        payload = {
            "mission": "MISSION_014_OWNER_APPROVED_READINESS",
            "artifact_version": "mission-014-owner-validation-v1",
            "source_owner_artifact": OWNER_PATH.relative_to(ROOT).as_posix(),
            "source_configuration_hash": frozen_config.configuration_hash,
            "validation": validation,
            "promotions_created": 0,
            "new_benchmark_config": "NOT_GENERATED",
            "dry_run_status": "NOT_RUN_DUE_TO_BLOCKED_VALIDATION",
            "benchmark_runs_executed": 0,
            "provider_operations_executed": 0,
            "healing_operations_executed": 0,
            "metric_results_generated": 0,
            "execution_authorized": False,
            "stop_reason": "Owner-approved input contains missing/unresolved fields or fairness conflicts.",
        }
        OUTPUT_PATH.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return
    raise SystemExit("Owner input unexpectedly validated; no promotion implementation is enabled in this blocked-validation boundary")


if __name__ == "__main__":
    main()
