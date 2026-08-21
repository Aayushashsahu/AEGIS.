import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "mission048_evidence_preserving_rerun.py"
    spec = importlib.util.spec_from_file_location("mission048_evidence_preserving_rerun", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_fails_closed_when_current_conflict_is_not_independently_verified(tmp_path, monkeypatch) -> None:
    module = _load_module()
    root = tmp_path / "canonical"
    mission_dir = root / "experiments" / "mission_048_evidence_preserving_rerun"
    authorization_path = mission_dir / "authorization.json"
    raw_path = mission_dir / "raw_response.bin"
    correlation_dir = mission_dir / "correlation_records"
    mission_dir.mkdir(parents=True)
    monkeypatch.setattr(module, "ROOT", root)
    authorization_path.write_text(json.dumps({
        "collector_id": "c_mt09pib13nxqz1coi",
        "operation_budget": {"documented_collector_rerun": 1, "retries": 0},
        "execution_contract": {
            "raw_response_path": str(raw_path.relative_to(root)),
            "correlation_record_dir": str(correlation_dir.relative_to(root)),
            "aegis_operation_id": module.OPERATION_ID,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(module, "MISSION_DIR", mission_dir)
    monkeypatch.setattr(module, "AUTHORIZATION_PATH", authorization_path)
    monkeypatch.setattr(module, "RAW_RESPONSE_PATH", raw_path)
    monkeypatch.setattr(module, "CORRELATION_DIR", correlation_dir)
    monkeypatch.setattr(module, "_historical_evidence_intact", lambda: True)
    monkeypatch.setenv(module.BRIGHT_DATA_DCA_TOKEN_ENV, "test-token-not-retained")

    report = module.preflight()

    assert report["all_pass"] is False
    assert report["checks"]["no_conflicting_operation_currently_verified"] is False
    assert report["checks"]["response_capture_capable"] is True
    assert report["provider_operations_attempted"] == 0
