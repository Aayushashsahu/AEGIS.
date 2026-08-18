#!/usr/bin/env python3
"""Generate Mission 027 NVIDIA owner-review and validation-only artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from aegis.mission027_freeze import (
    build_mission027_config,
    build_records,
    json_bytes,
    validation_only,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mission 027 NVIDIA participant freeze artifacts")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config, promoted_proposal, promotion, review = build_mission027_config(root)
    dry_run = validation_only(config)
    from aegis.mission027_freeze import planned_execution_count

    planned_opportunities = planned_execution_count(config, root)
    if planned_opportunities != 180:
        raise RuntimeError(f"Mission 027 expected 180 planned opportunities, got {planned_opportunities}")
    records = build_records(config, promoted_proposal, promotion, review, dry_run, planned_opportunities)

    config_path = root / "benchmarks/configs/mission_027_nvidia_owner_freeze_config.json"
    proposal_path = root / "benchmarks/configs/mission_027_baseline_b_nvidia_ready_proposal.json"
    records_path = root / "experiments/mission_027_nvidia_freeze_records.json"
    dry_run_path = root / "experiments/mission_027_nvidia_validation_only_dry_run.json"

    for path, payload in (
        (config_path, config.to_dict()),
        (proposal_path, promoted_proposal.to_dict()),
        (records_path, records),
        (dry_run_path, dry_run.to_dict()),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_bytes(payload), encoding="utf-8")

    print(json_bytes({
        "config_path": str(config_path),
        "config_hash": config.configuration_hash,
        "promoted_participant_hash": promotion.participant_spec.configuration_hash,
        "source_proposal_hash": records["participant_proposal_hash"],
        "dry_run_status": dry_run.status.value,
        "expected_run_count": dry_run.expected_run_count,
        "planned_opportunities": planned_opportunities,
        "provider_operations_executed": dry_run.provider_operations_executed,
        "execution_authorized": dry_run.execution_authorized,
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
