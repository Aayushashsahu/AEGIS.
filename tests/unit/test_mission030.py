import hashlib
import shutil
from pathlib import Path

import pytest

from aegis.adapter import (
    AdapterError,
    BrightDataCliAdapter,
    build_bright_data_heal_prompt,
    build_heal_command,
)
from aegis.mission030_evidence import ArtifactLoadError, Mission029ArtifactLoader
from scripts.mission030_validate_heal import load_mission029_repair_request, run


ROOT = Path(__file__).resolve().parents[2]


def mission029_request():
    return load_mission029_repair_request(ROOT)


def test_compact_prompt_is_within_documented_provider_limit() -> None:
    projection = build_bright_data_heal_prompt(mission029_request())
    assert projection.within_limit is True
    assert projection.prompt_length == len(projection.prompt_text)
    assert projection.prompt_length <= 1000
    assert projection.limit == 1000


def test_compact_prompt_is_byte_deterministic() -> None:
    first = build_bright_data_heal_prompt(mission029_request())
    second = build_bright_data_heal_prompt(mission029_request())
    assert first.prompt_text == second.prompt_text
    assert first.prompt_hash == second.prompt_hash
    assert first.prompt_length == second.prompt_length


def test_compact_prompt_hash_matches_exact_bytes() -> None:
    projection = build_bright_data_heal_prompt(mission029_request())
    assert projection.prompt_hash == hashlib.sha256(projection.prompt_text.encode("utf-8")).hexdigest()


def test_compact_prompt_preserves_target_objective_schema_invariants_and_unaffected_fields() -> None:
    prompt = build_bright_data_heal_prompt(mission029_request()).prompt_text
    assert "https://news.ycombinator.com" in prompt
    assert "Investigate the detected anomaly" in prompt
    assert "author, comment_count, points" in prompt
    assert "title:str:required" in prompt
    assert "valid_url" in prompt
    assert "non_negative_numeric" in prompt
    assert "title, url" in prompt


def test_compact_prompt_excludes_verbose_evidence_references_and_raw_payloads() -> None:
    prompt = build_bright_data_heal_prompt(mission029_request()).prompt_text
    assert "evidence://" not in prompt
    assert "observation://row/" not in prompt
    assert "402" not in prompt
    assert "-1" not in prompt


def test_provider_command_uses_compact_projection_not_legacy_verbose_prompt() -> None:
    request = mission029_request()
    projection = build_bright_data_heal_prompt(request)
    command = build_heal_command(request)
    assert command[7] == projection.prompt_text
    assert len(command[7]) <= 1000
    assert "Evidence references:" not in command[7]


def test_prompt_builder_redacts_credential_shaped_objective_text() -> None:
    request = mission029_request()
    modified = request.__class__(**{**request.__dict__, "repair_objective": "Repair extraction. token=never-export"})
    prompt = build_bright_data_heal_prompt(modified).prompt_text
    assert "never-export" not in prompt
    assert "token=[REDACTED]" in prompt


def test_over_limit_projection_blocks_before_runner_or_provider_call() -> None:
    calls: list[object] = []

    def runner(command):
        calls.append(command)
        raise AssertionError("provider runner must not be called")

    with BrightDataCliAdapter(runner=runner, heal_prompt_limit=80) as adapter:
        with pytest.raises(AdapterError, match="HEAL_BLOCKED_PROVIDER_PROMPT_LIMIT"):
            adapter.request_healing(mission029_request())
    assert calls == []


def test_validation_script_preflight_is_provider_free(tmp_path: Path) -> None:
    source = ROOT / "experiments/mission_029/repair_request.json"
    target = tmp_path / "experiments/mission_029/repair_request.json"
    target.parent.mkdir(parents=True)
    shutil.copy2(source, target)
    result = run(tmp_path, live=False)
    assert result["status"] == "PREFLIGHT_PASS"
    assert result["provider_called"] is False
    assert result["bright_data_heal_operations"] == 0
    assert not (tmp_path / "experiments/mission_030/provider_operations").exists()


def test_completed_live_heal_replays_without_a_second_provider_operation() -> None:
    operation = ROOT / "experiments/mission_030/provider_operations/operation_001.json"
    before = operation.read_bytes()
    result = run(ROOT, live=True)
    assert result["replay_only"] is True
    assert result["bright_data_heal_operations"] == 1
    assert operation.read_bytes() == before


def test_loader_reads_the_committed_mission029_artifact_shapes() -> None:
    evidence = Mission029ArtifactLoader(ROOT / "experiments/mission_029").load()
    assert evidence.collector_id == "c_msyo46bp1slx64351"
    assert evidence.target_url == "https://news.ycombinator.com"
    assert evidence.row_count == 150
    assert evidence.collection_mode == "BATCH"


def test_loader_preserves_actual_lifecycle_states_without_fabrication() -> None:
    evidence = Mission029ArtifactLoader(ROOT / "experiments/mission_029").load()
    status_by_stage = {stage.stage_id: stage.status for stage in evidence.stages}
    assert status_by_stage == {
        "collector": "SUCCESS",
        "observation": "RECORDED",
        "mutation": "DEMO_MUTATION / L3",
        "detection": "DETECTED",
        "diagnosis": "AMBIGUOUS",
        "repair_request": "CREATED",
        "bright_data_heal": "FAILED / PROMPT_LIMIT",
        "candidate": "NOT_CREATED",
        "verification": "NOT_RUN",
        "risk": "NOT_RUN",
        "commit": "NOT_PERFORMED",
    }
    assert evidence.candidate_id is None
    assert evidence.verification_id is None
    assert evidence.risk_decision_id is None
    assert evidence.commit_decision_id is None


def test_loader_preserves_live_ids_latency_error_and_provenance() -> None:
    evidence = Mission029ArtifactLoader(ROOT / "experiments/mission_029").load()
    assert evidence.provider_operation_ids["response_id"] == "d2t1787058048204rt325p1dbgjg"
    assert evidence.collection_latency_ms == 108112
    assert evidence.error_code == "PROVIDER_COMMAND_FAILED"
    assert "1187 chars" in (evidence.error_message or "")
    assert evidence.provenance["heal"] == "REAL_PROVIDER_EVIDENCE"
    assert evidence.provenance["mutation_detection"] == "DEMO_CONTROLLED"


def test_loader_is_read_only(tmp_path: Path) -> None:
    copied = tmp_path / "mission_029"
    shutil.copytree(ROOT / "experiments/mission_029", copied)
    before = {path.relative_to(copied): path.read_bytes() for path in copied.rglob("*.json")}
    Mission029ArtifactLoader(copied).load()
    after = {path.relative_to(copied): path.read_bytes() for path in copied.rglob("*.json")}
    assert before == after


def test_loader_rejects_missing_required_artifacts(tmp_path: Path) -> None:
    with pytest.raises(ArtifactLoadError, match="missing Mission 029 artifact"):
        Mission029ArtifactLoader(tmp_path).load()


def test_loader_rejects_malformed_artifacts(tmp_path: Path) -> None:
    copied = tmp_path / "mission_029"
    shutil.copytree(ROOT / "experiments/mission_029", copied)
    (copied / "diagnosis.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ArtifactLoadError, match="malformed Mission 029 artifact"):
        Mission029ArtifactLoader(copied).load()


def test_loader_rejects_unredacted_sensitive_fields(tmp_path: Path) -> None:
    copied = tmp_path / "mission_029"
    shutil.copytree(ROOT / "experiments/mission_029", copied)
    manifest = copied / "demo_manifest.json"
    manifest.write_text('{"collector_id":"c_msyo46bp1slx64351","target_url":"https://news.ycombinator.com","row_count":150,"authorization":"nope"}', encoding="utf-8")
    with pytest.raises(ArtifactLoadError, match="sensitive field"):
        Mission029ArtifactLoader(copied).load()
