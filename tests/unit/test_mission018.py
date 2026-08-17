from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_PREFLIGHT_SPEC = importlib.util.spec_from_file_location("mission016_preflight_smoke", ROOT / "scripts/mission016_preflight_smoke.py")
assert _PREFLIGHT_SPEC is not None and _PREFLIGHT_SPEC.loader is not None
preflight = importlib.util.module_from_spec(_PREFLIGHT_SPEC)
sys.modules[_PREFLIGHT_SPEC.name] = preflight
_PREFLIGHT_SPEC.loader.exec_module(preflight)

HISTORICAL_ROOT = ROOT / "benchmarks/runs/mission_016_floor_f48ec5c5792b"
CORRECTED_ROOT = ROOT / "benchmarks/runs/mission_016_floor_59a11e27a71f"
CORRECTED_CONFIG = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
OLD_CONFIG = ROOT / "benchmarks/configs/mission_015_frozen_config.json"
OLD_HASH = "f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96"
CORRECTED_HASH = "59a11e27a71f241dbf58d1d41bc37a53ba52b2652cbe23f7e2d46891c63e0f0b"
ACTUAL_BASELINE_REVISION = "067c06d8d41b2c23a93aebdcc45ac46a2c71351e"
ACTUAL_AEGIS_REVISION = "067c06d8d41b2c23a93aebdcc45ac46a2c71351e"


def _directory_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_mission016_uses_corrected_mission017_config_and_run_id() -> None:
    assert preflight.CONFIG_PATH == CORRECTED_CONFIG
    assert preflight.EXPECTED_CONFIG_HASH == CORRECTED_HASH
    assert preflight.FLOOR_RUN_ID == "mission_016_floor_59a11e27a71f"
    assert preflight.FLOOR_RUN_ROOT == CORRECTED_ROOT
    assert preflight.FLOOR_RUN_ID != "mission_016_floor_f48ec5c5792b"
    assert preflight.HISTORICAL_FLOOR_RUN_ROOT == HISTORICAL_ROOT


def test_superseded_mission015_hash_is_not_active() -> None:
    assert preflight.EXPECTED_CONFIG_HASH != OLD_HASH
    assert preflight.CONFIG_PATH != OLD_CONFIG
    assert OLD_HASH not in preflight.EXPECTED_CONFIG_HASH


def test_corrected_participant_revisions_resolve() -> None:
    assert preflight.EXPECTED_REVISIONS == {
        "BASELINE_A": ACTUAL_BASELINE_REVISION,
        "BASELINE_B": ACTUAL_BASELINE_REVISION,
        "AEGIS": ACTUAL_AEGIS_REVISION,
    }
    for participant, revision in preflight.EXPECTED_REVISIONS.items():
        assert preflight._revision_matches(revision, preflight.SOURCE_FILES[participant])


def test_historical_mission016_directory_is_present_and_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = _directory_digest(HISTORICAL_ROOT)
    assert before
    isolated_root = tmp_path / "corrected-floor"
    monkeypatch.setattr(preflight, "FLOOR_RUN_ROOT", isolated_root)
    monkeypatch.setattr(preflight, "SMOKE_ROOT", isolated_root / "baseline_b_execution_readiness_smoke")
    result, _ = preflight.run_preflight()
    assert result.checks["artifact_paths"]["historical_floor_run_preserved"] is True
    assert result.checks["artifact_paths"]["floor_run_absent"] is True
    assert _directory_digest(HISTORICAL_ROOT) == before
    assert not isolated_root.exists()


def test_run_preflight_uses_normal_validation_boundary_and_stops_before_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def smoke_must_not_run(_config):
        raise AssertionError("Mission 018 must not execute the Baseline B smoke test")

    isolated_root = tmp_path / "corrected-floor"
    monkeypatch.setattr(preflight, "FLOOR_RUN_ROOT", isolated_root)
    monkeypatch.setattr(preflight, "SMOKE_ROOT", isolated_root / "baseline_b_execution_readiness_smoke")
    monkeypatch.setattr(preflight, "run_baseline_b_smoke", smoke_must_not_run)
    result, config = preflight.run_preflight()
    assert result.passed is True
    assert config.configuration_hash == CORRECTED_HASH
    assert result.checks["configuration_validation"]["pass"] is True
    assert result.checks["participants_ready"]["pass"] is True
    assert result.checks["fairness"]["pass"] is True
    assert result.checks["dry_run"]["status"] == "READY_TO_EXECUTE"
    assert result.checks["dry_run"]["pass"] is True


def test_old_config_is_fail_closed_when_substituted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    isolated_root = tmp_path / "old-config-floor"
    monkeypatch.setattr(preflight, "FLOOR_RUN_ROOT", isolated_root)
    monkeypatch.setattr(preflight, "SMOKE_ROOT", isolated_root / "baseline_b_execution_readiness_smoke")
    monkeypatch.setattr(preflight, "CONFIG_PATH", OLD_CONFIG)
    result, config = preflight.run_preflight()
    assert config.configuration_hash == OLD_HASH
    assert result.passed is False
    assert any("configuration_hash" in error for error in result.errors)
    assert [spec.implementation_revision for spec in config.baselines if spec.baseline_id in ("BASELINE_A", "BASELINE_B")] == ["0e8bcc4a2c2184cae9a50b291054ec47d83fc895"] * 2
    assert not isolated_root.exists()


def test_mission019_smoke_artifact_isolated_from_results_and_reports() -> None:
    assert CORRECTED_ROOT.exists()
    assert (CORRECTED_ROOT / "baseline_b_execution_readiness_smoke/smoke.json").exists()
    assert not (ROOT / "benchmarks/results/mission_016_floor_59a11e27a71f").exists()
    assert not (ROOT / "benchmarks/reports/mission_016_floor_59a11e27a71f").exists()
