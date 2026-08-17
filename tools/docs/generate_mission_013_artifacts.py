from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from aegis.audit_store import _to_jsonable
from aegis.benchmark_config import load_benchmark_config, validate_config
from aegis.benchmark_runner import BenchmarkRunner
from aegis.participant_freeze import default_mission013_proposals, validate_participant_proposal


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks" / "configs" / "mission_011_validation_floor.json"
FREEZE_PATH = ROOT / "benchmarks" / "configs" / "mission_013_participant_freeze.json"
DRY_RUN_PATH = ROOT / "benchmarks" / "configs" / "mission_013_readiness_dry_run.json"


def main() -> None:
    config = load_benchmark_config(CONFIG_PATH)
    proposals = default_mission013_proposals(config)
    validations = {participant_id: validate_participant_proposal(proposal) for participant_id, proposal in proposals.items()}
    runner = BenchmarkRunner(config)
    first = runner.dry_run()
    second = BenchmarkRunner(config).dry_run()
    if first.to_json() != second.to_json() or first.plan != second.plan:
        raise SystemExit("Mission 013 determinism check failed")
    if first.status.value != "BLOCKED_NOT_READY":
        raise SystemExit(f"Mission 013 expected BLOCKED_NOT_READY, got {first.status.value}")
    if any(validation.ready for validation in validations.values()):
        raise SystemExit("Mission 013 must not promote unapproved default proposals")
    fairness = [runner.build_input(participant_id, "M005", 12345).shared_metadata() for participant_id in ("BASELINE_A", "BASELINE_B", "AEGIS")]
    fairness_pass = fairness[0] == fairness[1] == fairness[2] and fairness[0]["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED"
    if not fairness_pass:
        raise SystemExit("Mission 013 fairness check failed")
    changed_spec = replace(config.baselines[0], metadata={"extraction_implementation": "unreviewed-change"})
    changed_config = replace(config, baselines=(changed_spec, *config.baselines[1:]))
    participant_change_invalidates_old_hash = not validate_config(changed_config).valid

    payload = {
        "mission": "MISSION_013",
        "artifact_version": "mission-013-participant-freeze-v1",
        "validation_only": True,
        "owner_review_status": "NOT_PROVIDED",
        "promotion_status": "NOT_PERFORMED",
        "source_configuration_hash": config.configuration_hash,
        "new_configuration_hash": "NOT_GENERATED",
        "participant_proposals": proposals,
        "participant_validations": validations,
        "readiness_transitions": (),
        "fairness_check": {
            "status": "PASS" if fairness_pass else "FAIL",
            "participants": ["BASELINE_A", "BASELINE_B", "AEGIS"],
            "mutation_id": "M005",
            "seed": 12345,
            "ground_truth_runtime_payload": "NOT_PROVIDED",
        },
        "participant_change_invalidates_old_hash": participant_change_invalidates_old_hash,
        "dry_run_status": first.status.value,
        "benchmark_runs_executed": 0,
        "provider_operations_executed": 0,
        "healing_operations_executed": 0,
        "metric_results_generated": 0,
        "execution_authorized": False,
        "runner_dry_run": first,
    }
    FREEZE_PATH.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    DRY_RUN_PATH.write_text(first.to_json(), encoding="utf-8")


if __name__ == "__main__":
    main()
