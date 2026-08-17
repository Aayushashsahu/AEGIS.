from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aegis.benchmark_config import load_benchmark_config, validate_config
from aegis.participant_freeze import compute_participant_hash, proposal_from_spec

ROOT = Path(__file__).resolve().parents[2]
CORRECTED_CONFIG_PATH = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
CORRECTED_DRY_RUN_PATH = ROOT / "benchmarks/configs/mission_017_corrected_dry_run.json"
RECORDS_PATH = ROOT / "experiments/mission_017_corrected_freeze_records.json"
OLD_CONFIG_PATH = ROOT / "benchmarks/configs/mission_015_frozen_config.json"

ACTUAL_REVISIONS = {
    "BASELINE_A": "0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47",
    "BASELINE_B": "0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47",
    "AEGIS": "7de2bc65ed9eeb9f4abd24017543f3f366990738",
}
OLD_CONFIG_HASH = "f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96"


def _config():
    return load_benchmark_config(CORRECTED_CONFIG_PATH)


def _records():
    return json.loads(RECORDS_PATH.read_text(encoding="utf-8"))


def test_actual_revisions_resolve_exactly() -> None:
    for revision in ACTUAL_REVISIONS.values():
        result = subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT)
        assert result.returncode == 0


def test_corrected_config_is_valid_and_supersedes_mission015() -> None:
    corrected = _config()
    old = load_benchmark_config(OLD_CONFIG_PATH)
    assert validate_config(corrected).valid
    assert corrected.configuration_hash != OLD_CONFIG_HASH
    assert corrected.configuration_hash != old.configuration_hash
    assert corrected.collection_policy["supersedes_configuration_hash"] == OLD_CONFIG_HASH
    assert corrected.evidence_policy["supersedes_configuration_hash"] == OLD_CONFIG_HASH
    assert corrected.benchmark_id == "aegis-benchmark-mission-017-corrected"


def test_corrected_participant_hashes_are_deterministic_and_revisions_are_actual() -> None:
    corrected = _config()
    records = _records()
    for spec in corrected.baselines:
        assert spec.implementation_revision == ACTUAL_REVISIONS[spec.baseline_id]
        proposal = proposal_from_spec(spec)
        assert compute_participant_hash(proposal) == spec.configuration_hash
        assert records["participant_validations"][spec.baseline_id]["computed_configuration_hash"] == spec.configuration_hash
        assert records["owner_review_decisions"][spec.baseline_id]["corrected_participant_hash"] == spec.configuration_hash


def test_baseline_a_and_b_are_distinct_strategies_without_execution() -> None:
    records = _records()
    strategy = records["strategy_separation"]
    assert strategy["strategies_distinct"] is True
    assert all(strategy["baseline_a"]["checks"].values())
    assert all(strategy["baseline_b"]["checks"].values())
    assert records["revision_checks"]["BASELINE_A"]["resolves"] is True
    assert records["revision_checks"]["BASELINE_B"]["resolves"] is True
    assert strategy["note"].endswith("no participant execution was performed.")


def test_corrected_config_preserves_mission015_benchmark_values() -> None:
    corrected = _config()
    old = load_benchmark_config(OLD_CONFIG_PATH)
    assert corrected.mutation_class_ids == old.mutation_class_ids == ("M001", "M002", "M003", "M004", "M005", "M006")
    assert corrected.mutation_severity == old.mutation_severity
    assert corrected.seeds == old.seeds == (12345,)
    assert corrected.fixture_id == old.fixture_id == "gpu-price-staging"
    assert corrected.fixture_version == old.fixture_version == "1"
    assert corrected.metric_formula_version == old.metric_formula_version == "mission-010-metrics-v1"
    assert corrected.timeout_policy == old.timeout_policy
    assert corrected.retry_policy == old.retry_policy
    assert all(spec.status == "READY" for spec in corrected.baselines)


def test_owner_approvals_and_readiness_promotions_are_recorded() -> None:
    records = _records()
    assert set(records["owner_review_decisions"]) == {"BASELINE_A", "BASELINE_B", "AEGIS"}
    assert all(item["approved"] is True for item in records["owner_review_decisions"].values())
    assert all(item["owner"] == "PROJECT_OWNER" and item["reviewer"] == "PROJECT_OWNER" for item in records["owner_review_decisions"].values())
    assert all(item["correlation_id"] for item in records["owner_review_decisions"].values())
    assert [(item["prior_status"], item["new_status"]) for item in records["readiness_promotions"]] == [("NOT_READY", "READY")] * 3


def test_corrected_dry_run_is_ready_fair_and_zero_execution() -> None:
    dry_run = json.loads(CORRECTED_DRY_RUN_PATH.read_text(encoding="utf-8"))
    assert dry_run["status"] == "READY_TO_EXECUTE"
    assert dry_run["validation_only"] is True
    assert dry_run["fairness"]["status"] == "PASS"
    assert dry_run["expected_run_count"] == 18
    assert dry_run["participant_count"] == 3
    assert dry_run["mutation_count"] == 6
    assert dry_run["seed_count"] == 1
    assert dry_run["execution_authorized"] is False
    assert dry_run["benchmark_runs_executed"] == 0
    assert dry_run["provider_operations_executed"] == 0
    assert dry_run["healing_operations_executed"] == 0
    assert dry_run["metric_results_generated"] == 0
