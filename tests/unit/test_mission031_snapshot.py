import json
import shutil
from pathlib import Path

import pytest

from scripts.mission031_build_demo_snapshot import build_snapshot, write_snapshot


ROOT = Path(__file__).resolve().parents[2]


def test_snapshot_is_provider_free_and_preserves_live_failure_boundary() -> None:
    snapshot = build_snapshot(ROOT)
    assert snapshot["provider_operations_executed_by_builder"] == 0
    assert snapshot["live_lane"]["mode"] == "LIVE_HISTORICAL_EVIDENCE"
    assert snapshot["live_lane"]["provider_heal"]["transport_prompt"]["length"] == 676
    assert snapshot["live_lane"]["provider_heal"]["candidate_created"] is False
    assert snapshot["live_lane"]["provider_heal"]["verification_invoked"] is False
    assert snapshot["live_lane"]["provider_heal"]["production_commit_performed"] is False


def test_snapshot_replay_is_explicit_test_double_and_rejects_silent_corruption() -> None:
    replay = build_snapshot(ROOT)["controlled_replay"]
    assert replay["mode"] == "TEST_DOUBLE_CONTROLLED_REPLAY"
    assert replay["candidate"]["provenance"] == "TEST_DOUBLE"
    assert replay["ai_proposal"]["overall"] == "PASS"
    assert replay["expected_value"]["value"] == 599
    assert replay["observed_value"]["value"] == 29.99
    assert replay["verification"]["overall_status"] == "FAIL"
    assert replay["risk"]["decision"] == "REJECT"
    assert replay["commit"]["output_eligible"] is False
    assert replay["commit"]["data_shipped"] is False


def test_snapshot_reports_only_controlled_aegis_benchmark_metrics() -> None:
    benchmark = build_snapshot(ROOT)["benchmark"]
    assert benchmark["run_id"] == "mission_028_recovery_floor_4812160675146552"
    assert benchmark["execution"]["planned_opportunities"] == 180
    assert benchmark["execution"]["completed_opportunities"] == 179
    assert benchmark["protocol"]["nvidia_provider_limit"] == "UNKNOWN"
    metrics = benchmark["controlled_aegis_metrics"]
    assert metrics["provenance"] == "TEST_DOUBLE_CONTROLLED_HARNESS"
    assert metrics["detection_rate"] == {"numerator": 50, "denominator": 50}
    assert metrics["l5_detection_rate"] == {"numerator": 20, "denominator": 20}
    assert metrics["l5_bad_data_shipped"] == {"numerator": 0, "denominator": 20}


def test_snapshot_is_deterministic_and_redacts_inputs(tmp_path: Path) -> None:
    first = build_snapshot(ROOT)
    second = build_snapshot(ROOT)
    assert first == second
    output = write_snapshot(ROOT, tmp_path / "snapshot.json")
    assert json.loads(output.read_text(encoding="utf-8")) == first
    assert "token" not in output.read_text(encoding="utf-8").lower()


def test_snapshot_fails_closed_on_unredacted_historical_input(tmp_path: Path) -> None:
    copied = tmp_path / "repo"
    shutil.copytree(ROOT / "experiments", copied / "experiments")
    shutil.copytree(ROOT / "benchmarks", copied / "benchmarks")
    manifest = copied / "experiments" / "mission_029" / "demo_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["authorization"] = "unsafe"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sensitive field"):
        build_snapshot(copied)
