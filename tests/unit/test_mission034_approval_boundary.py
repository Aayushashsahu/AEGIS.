"""Mission 034 future approval boundary tests; all provider behavior is TEST_DOUBLE."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
import ast
import hashlib
import json

import pytest

from aegis.approval_boundary import (
    BRIGHT_DATA_CLI_CREDENTIAL_ENV,
    BRIGHT_DATA_DCA_TOKEN_ENV,
    MISSION034_CANDIDATE_ID,
    MISSION034_COLLECTOR_ID,
    ApprovalBoundaryError,
    ApprovalResult,
    CollectorAccessStatus,
    FixtureApprovalAuthorization,
    FixtureOnlyApprovalGate,
    ReadOnlyCollectorAccessBoundary,
    validate_cli_credential_environment,
)
from aegis.models import ProviderProvenance


NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)


def authorization(**changes: object) -> FixtureApprovalAuthorization:
    values: dict[str, object] = {
        "candidate_id": MISSION034_CANDIDATE_ID,
        "collector_id": MISSION034_COLLECTOR_ID,
        "operator": "Aayush Sahu",
        "authorization_reference": "fixture://mission034/approval-authority",
        "correlation_id": "corr-mission034-approval-fixture",
        "authorized_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
    }
    values.update(changes)
    return FixtureApprovalAuthorization(**values)


def test_documented_cli_credential_name_is_the_only_canonical_interface() -> None:
    loaded = validate_cli_credential_environment({BRIGHT_DATA_CLI_CREDENTIAL_ENV: "fixture-secret"})
    assert loaded.source_name == BRIGHT_DATA_CLI_CREDENTIAL_ENV
    assert loaded.configured is True
    assert "fixture-secret" not in repr(loaded)


@pytest.mark.parametrize(
    "environment",
    [{}, {BRIGHT_DATA_DCA_TOKEN_ENV: "fixture-dca-token"}],
)
def test_missing_or_dca_only_credential_configuration_fails_closed(environment: dict[str, str]) -> None:
    with pytest.raises(ApprovalBoundaryError):
        validate_cli_credential_environment(environment)


def test_read_only_collector_access_preserves_unknown_and_makes_zero_provider_calls() -> None:
    result = ReadOnlyCollectorAccessBoundary().inspect(MISSION034_COLLECTOR_ID)

    assert result.collector_id == MISSION034_COLLECTOR_ID
    assert result.status is CollectorAccessStatus.UNKNOWN
    assert result.provider_called is False
    assert "No documented harmless" in result.reason
    with pytest.raises(ApprovalBoundaryError, match="canonical Mission 034 collector"):
        ReadOnlyCollectorAccessBoundary().inspect("c_mt09pib13nxqz1co")


def test_exact_scope_creates_only_a_test_double_approval_record() -> None:
    gate = FixtureOnlyApprovalGate(now=NOW)
    record = gate.approve_candidate(MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, authorization())

    assert record.result is ApprovalResult.FIXTURE_APPROVED
    assert record.provenance is ProviderProvenance.TEST_DOUBLE
    assert record.real_provider_mutation_performed is False
    assert record.automatic_commit_performed is False
    assert record.automatic_rollback_performed is False
    assert record.provider_response_metadata["provider_called"] == "false"
    assert record.evidence_hash
    assert len(gate.records) == 1


@pytest.mark.parametrize(
    "candidate_id,collector_id,context",
    [
        ("candidate_wrong", MISSION034_COLLECTOR_ID, authorization()),
        (MISSION034_CANDIDATE_ID, "c_wrong", authorization()),
        (MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, authorization(candidate_id="candidate_wrong")),
        (MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, authorization(collector_id="c_wrong")),
    ],
)
def test_candidate_and_collector_mismatch_are_rejected(
    candidate_id: str,
    collector_id: str,
    context: FixtureApprovalAuthorization,
) -> None:
    with pytest.raises(ApprovalBoundaryError, match="match"):
        FixtureOnlyApprovalGate(now=NOW).approve_candidate(candidate_id, collector_id, context)


@pytest.mark.parametrize(
    "context",
    [
        authorization(operator=""),
        authorization(authorization_reference=""),
        authorization(correlation_id=""),
        authorization(expires_at=NOW),
        authorization(authorized_at=NOW + timedelta(minutes=1)),
        authorization(operation_count=1),
        authorization(retry_count=1),
        authorization(automatic_commit_enabled=True),
        authorization(automatic_rollback_enabled=True),
        authorization(provenance=ProviderProvenance.BRIGHT_DATA),
    ],
)
def test_incomplete_expired_or_unsafe_authorization_fails_closed(context: FixtureApprovalAuthorization) -> None:
    with pytest.raises(ApprovalBoundaryError):
        FixtureOnlyApprovalGate(now=NOW).approve_candidate(MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, context)


def test_single_operation_budget_and_test_double_provenance_cannot_escalate() -> None:
    gate = FixtureOnlyApprovalGate(now=NOW)
    record = gate.approve_candidate(MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, authorization())
    with pytest.raises(ApprovalBoundaryError, match="budget"):
        gate.approve_candidate(MISSION034_CANDIDATE_ID, MISSION034_COLLECTOR_ID, authorization())
    assert record.provenance is ProviderProvenance.TEST_DOUBLE
    assert "real_provider_mutation_performed" in {item.name for item in fields(record)}
    assert record.real_provider_mutation_performed is False


def test_fixture_boundary_contains_no_provider_execution_primitive_or_real_approval_command() -> None:
    source_path = Path(__file__).resolve().parents[2] / "src" / "aegis" / "approval_boundary.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert {"subprocess", "requests", "httpx", "urllib"}.isdisjoint(imported_modules)
    assert "bdata scraper approve" not in source_path.read_text(encoding="utf-8")


def test_historical_mission033_and_guarded_evidence_hashes_remain_unchanged() -> None:
    root = Path(__file__).resolve().parents[2]
    artifacts = root / "experiments" / "mission_033_live_bright_data_success"
    manifest = json.loads((artifacts / "artifact_hashes.json").read_text(encoding="utf-8"))

    for relative_path, expected_hash in manifest["historical_guard"].items():
        assert hashlib.sha256((root / relative_path).read_bytes()).hexdigest() == expected_hash
    for relative_path, expected_hash in manifest["mission_033_artifacts"].items():
        assert hashlib.sha256((artifacts / relative_path).read_bytes()).hexdigest() == expected_hash
    assert manifest["terminal_boundary"] == {
        "provider_candidate_status": "awaiting_approval",
        "provider_approval_executed": False,
        "production_commit_executed": False,
        "post_heal_run_executed": False,
        "corrected_live_output_claimed": False,
    }
