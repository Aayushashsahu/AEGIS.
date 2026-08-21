from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.mission029_live_demo import (
    DEMO_MUTATION_ID,
    DESCRIPTION,
    SELECTED_FIELDS,
    TARGET_URL,
    RecordingRunner,
    apply_demo_mutation,
    run_demo,
    validate_demo_target,
)
from aegis.adapter import BrightDataCliAdapter, CommandResult
from aegis.commit_gate import CommitEligibility, CommitGate
from aegis.contracts import default_extraction_contract
from aegis.diagnosis import DiagnosisContext, DeterministicDiagnostician, build_repair_request
from aegis.healing import RepairCandidate, VerificationStatus
from aegis.models import CollectorRequest, CollectionMode, Observation, ProviderProvenance
from aegis.risk import RiskDecisionType, RiskGovernor
from aegis.verification import VerificationContext, VerificationOverallStatus, verify_candidate


LIVE_ROWS = (
    {"title": "Story one", "url": "https://example.test/one", "points": 42, "author": "alice", "comment_count": 3},
    {"title": "Story two", "url": "https://example.test/two", "points": 7, "author": "bob", "comment_count": 1},
)


class FakeProvider:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str] | tuple[str, ...]) -> CommandResult:
        self.commands.append(list(command))
        if "create" in command:
            return CommandResult(stdout=json.dumps({"collector_id": "c_demo029", "view_url": "https://brightdata.test/c_demo029"}), latency_ms=12)
        if "run" in command:
            return CommandResult(stdout=json.dumps(list(LIVE_ROWS)), stderr="Realtime page limit exceeded — switching to batch mode...\nresponse_id: d_demo029\nBatch job: j_demo029", latency_ms=34)
        if "heal" in command:
            preview = [{**row} for row in LIVE_ROWS]
            return CommandResult(stdout=json.dumps({"status": "awaiting_approval", "operation_id": "h_demo029", "preview_result": preview, "diff_summary": "proposed template has 1 step(s)", "next_step": "bdata scraper approve c_demo029"}), latency_ms=56)
        raise AssertionError(command)


def make_observation(rows=LIVE_ROWS) -> Observation:
    return Observation(
        collection_id="collection_demo029",
        collector_id="c_demo029",
        provider_operation_ids={"response_id": "d_demo029"},
        input={"target_url": TARGET_URL},
        output=rows,
        schema=SELECTED_FIELDS,
        row_count=len(rows),
        latency_ms=34,
        collection_mode=CollectionMode.BATCH,
        provider_provenance=ProviderProvenance.BRIGHT_DATA,
        evidence_refs=("evidence://mission-029/live",),
    )


def make_candidate(output=LIVE_ROWS) -> RepairCandidate:
    return RepairCandidate(
        repair_request_id="repair_request_demo029",
        collector_reference="c_demo029",
        provider_operation_reference="h_demo029",
        provider_status="awaiting_approval",
        preview_result=list(output),
        diff_summary="preview",
        approval_command="bdata scraper approve c_demo029",
        raw_evidence_ref="evidence://bright-data/cli/heal/repair_request_demo029",
        provenance=ProviderProvenance.BRIGHT_DATA,
    )


def test_demo_target_validation_accepts_public_target() -> None:
    validate_demo_target(TARGET_URL, SELECTED_FIELDS)


def test_demo_target_validation_rejects_non_public_target() -> None:
    with pytest.raises(ValueError):
        validate_demo_target("https://private.example.test", SELECTED_FIELDS)


def test_demo_target_schema_is_frozen() -> None:
    with pytest.raises(ValueError):
        validate_demo_target(TARGET_URL, ("title", "url"))
    assert DESCRIPTION.startswith("Extract top stories")


def test_recording_runner_redacts_secret_like_provider_output(tmp_path: Path) -> None:
    runner = RecordingRunner(tmp_path, runner=lambda command: CommandResult(stdout="Authorization: Bearer secret-value", latency_ms=1))
    runner(["bdata", "scraper", "run", "c_demo029"])
    saved = next(tmp_path.glob("operation_*.json")).read_text()
    assert "secret-value" not in saved
    assert "[REDACTED]" in saved


def test_collector_create_uses_documented_fresh_cli_path() -> None:
    fake = FakeProvider()
    with BrightDataCliAdapter(runner=fake) as adapter:
        handle = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
    assert handle.collector_id == "c_demo029"
    assert fake.commands[0][:5] == ["npx", "-p", "@brightdata/cli", "bdata", "scraper"]
    assert fake.commands[0][5] == "create"


def test_collector_evidence_has_real_c_prefix() -> None:
    fake = FakeProvider()
    with BrightDataCliAdapter(runner=fake) as adapter:
        handle = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
    assert handle.collector_id.startswith("c_")


def test_collector_run_retrieves_structured_rows_and_batch_fallback() -> None:
    fake = FakeProvider()
    with BrightDataCliAdapter(runner=fake) as adapter:
        collector = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
        pending = adapter.run_collector(collector, target_url=TARGET_URL)
        while pending.status.value not in {"COMPLETED", "FAILED", "TIMED_OUT"}:
            pending = adapter.poll_collection(pending)
        result = adapter.retrieve_output(pending)
    assert result.handle.mode is CollectionMode.BATCH
    assert len(result.output) == 2
    assert result.handle.provider_operation_ids["response_id"] == "d_demo029"


def test_collector_run_records_and_passes_an_explicit_documented_version_selector() -> None:
    fake = FakeProvider()
    with BrightDataCliAdapter(runner=fake) as adapter:
        collector = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
        pending = adapter.run_collector(collector, target_url=TARGET_URL, version="v1")
    assert pending.requested_version == "v1"
    assert pending.selected_version is None
    assert pending.version_evidence_source == "DOCUMENTED_CLI_SELECTOR"
    assert fake.commands[1][-3:] == ["--version", "v1", "--pretty"]


def test_observation_conversion_preserves_bright_data_and_untrusted_state() -> None:
    observation = make_observation()
    assert observation.provider_provenance is ProviderProvenance.BRIGHT_DATA
    assert observation.trust_status == "UNTRUSTED_UNTIL_VERIFIED"
    assert observation.row_count == 2


def test_demo_mutation_is_reversible_and_boundary_only() -> None:
    mutated, record = apply_demo_mutation(LIVE_ROWS)
    assert record["mutation_id"] == DEMO_MUTATION_ID
    assert record["external_website_modified"] is False
    assert record["collector_modified"] is False
    assert mutated[0]["points"] == -1
    assert LIVE_ROWS[0]["points"] == 42


def test_detection_catches_demo_semantic_corruption() -> None:
    mutated, _ = apply_demo_mutation(LIVE_ROWS)
    observation = make_observation(mutated)
    from aegis.detection import evaluate_detection
    result = evaluate_detection(observation, default_extraction_contract())
    assert result.detected is True
    assert "points" in result.affected_fields
    assert result.severity == "L3"


def test_diagnosis_uses_existing_deterministic_boundary() -> None:
    mutated, _ = apply_demo_mutation(LIVE_ROWS)
    observation = make_observation(mutated)
    from aegis.detection import evaluate_detection
    detection = evaluate_detection(observation, default_extraction_contract())
    diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(observation, detection, default_extraction_contract(), "detection_demo029"))
    assert diagnosis is not None
    assert diagnosis.failure_class.value == "UNKNOWN"
    assert {item.value for item in diagnosis.candidate_classes} == {"SEMANTIC_INVARIANT", "STATISTICAL_DRIFT"}
    assert diagnosis.certainty.value == "AMBIGUOUS"
    assert diagnosis.diagnosis_provenance.value == "DETERMINISTIC"


def test_repair_request_is_provider_neutral_and_bounded() -> None:
    mutated, mutation = apply_demo_mutation(LIVE_ROWS)
    observation = make_observation(mutated)
    from aegis.detection import evaluate_detection
    detection = evaluate_detection(observation, default_extraction_contract())
    diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(observation, detection, default_extraction_contract(), "detection_demo029"))
    request = build_repair_request(diagnosis, observation=observation, contract=default_extraction_contract(), mutation_context=mutation)
    assert request.collector_reference == "c_demo029"
    assert "approve" not in request.repair_objective.lower()
    assert "commit" not in request.repair_objective.lower()


def test_heal_returns_provider_candidate_without_auto_approval() -> None:
    fake = FakeProvider()
    observation = make_observation()
    from aegis.detection import evaluate_detection
    detection = evaluate_detection(observation, default_extraction_contract())
    diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(observation, detection, default_extraction_contract(), "detection_demo029"))
    # Build a request from a real detected mutation so the adapter path is exercised.
    mutated, mutation = apply_demo_mutation(LIVE_ROWS)
    mutated_observation = make_observation(mutated)
    mutated_detection = evaluate_detection(mutated_observation, default_extraction_contract())
    mutated_diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(mutated_observation, mutated_detection, default_extraction_contract(), "detection_demo029"))
    request = build_repair_request(mutated_diagnosis, observation=mutated_observation, contract=default_extraction_contract(), mutation_context=mutation)
    with BrightDataCliAdapter(runner=fake) as adapter:
        collector = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
        heal = adapter.request_healing(request)
        while heal.status.value not in {"AWAITING_APPROVAL", "CANDIDATE_READY", "FAILED", "TIMED_OUT"}:
            heal = adapter.poll_healing(heal)
        result = adapter.retrieve_heal_result(heal)
    assert result.candidate is not None
    assert result.candidate.verification_status is VerificationStatus.UNVERIFIED
    assert result.candidate.collector_reference == collector.collector_id
    assert not any("approve" == command for command in fake.commands[-1])


def test_candidate_state_is_unverified_by_default() -> None:
    assert make_candidate().verification_status is VerificationStatus.UNVERIFIED


def test_verification_fails_when_candidate_contains_demo_corruption() -> None:
    mutated, _ = apply_demo_mutation(LIVE_ROWS)
    candidate = make_candidate(mutated)
    result = verify_candidate(VerificationContext(candidate, default_extraction_contract(), mutated, history=(make_observation(),), correlation_id="corr_demo029"))
    assert result.overall_status is VerificationOverallStatus.FAIL
    assert result.failed_checks


def test_risk_governor_rejects_critical_verification_failure() -> None:
    mutated, _ = apply_demo_mutation(LIVE_ROWS)
    candidate = make_candidate(mutated)
    verification = verify_candidate(VerificationContext(candidate, default_extraction_contract(), mutated, history=(make_observation(),), correlation_id="corr_demo029"))
    decision = RiskGovernor().decide(verification, candidate, correlation_id="corr_demo029")
    assert decision.decision is RiskDecisionType.REJECT


def test_commit_gate_blocks_unverified_candidate_and_missing_authority() -> None:
    candidate = make_candidate()
    verification = verify_candidate(VerificationContext(candidate, default_extraction_contract(), LIVE_ROWS, history=(make_observation(),), correlation_id="corr_demo029"))
    risk = RiskGovernor().decide(verification, candidate, correlation_id="corr_demo029")
    decision = CommitGate().evaluate(candidate, verification, risk, default_extraction_contract(), None, None, correlation_id="corr_demo029")
    assert decision.eligibility is CommitEligibility.BLOCKED
    assert decision.production_commit_performed is False


def test_no_auto_approval_command_is_executed() -> None:
    fake = FakeProvider()
    with BrightDataCliAdapter(runner=fake) as adapter:
        collector = adapter.create_collector(CollectorRequest(TARGET_URL, DESCRIPTION, provider=ProviderProvenance.BRIGHT_DATA))
    assert all("approve" not in command for command in fake.commands)
    assert collector.collector_id.startswith("c_")


def test_no_production_commit_is_represented() -> None:
    candidate = make_candidate()
    verification = verify_candidate(VerificationContext(candidate, default_extraction_contract(), LIVE_ROWS, history=(make_observation(),), correlation_id="corr_demo029"))
    risk = RiskGovernor().decide(verification, candidate, correlation_id="corr_demo029")
    decision = CommitGate().evaluate(candidate, verification, risk, default_extraction_contract(), None, None, correlation_id="corr_demo029")
    assert decision.production_commit_performed is False


def test_demo_manifest_is_credential_free_and_preserved_in_fallback_mode(tmp_path: Path) -> None:
    result = run_demo(tmp_path, live=False)
    assert result["status"] == "BLOCKED_NOT_READY"
    assert result["production_commit_performed"] is False
    assert not list((tmp_path / "experiments" / "mission_029" / "provider_operations").glob("*"))


def test_repeated_fallback_demo_is_safe(tmp_path: Path) -> None:
    first = run_demo(tmp_path, live=False)
    second = run_demo(tmp_path, live=False)
    assert first["provider_operations_executed"] == 0
    assert second["provider_operations_executed"] == 0


def test_test_double_healing_boundary_never_executes() -> None:
    from aegis.diagnosis import NoExecutionRepairBoundary
    mutated, mutation = apply_demo_mutation(LIVE_ROWS)
    observation = make_observation(mutated)
    from aegis.detection import evaluate_detection
    detection = evaluate_detection(observation, default_extraction_contract())
    diagnosis = DeterministicDiagnostician().diagnose(DiagnosisContext(observation, detection, default_extraction_contract(), "detection_demo029"))
    request = build_repair_request(diagnosis, observation=observation, contract=default_extraction_contract(), mutation_context=mutation)
    handle = NoExecutionRepairBoundary().request_healing(request)
    assert handle.execution_started is False
    assert handle.provider_operation_reference is None


def test_evidence_chain_identifiers_are_linked() -> None:
    observation = make_observation()
    assert observation.collector_id == "c_demo029"
    candidate = make_candidate()
    assert candidate.repair_request_id
    assert candidate.collector_reference == observation.collector_id
