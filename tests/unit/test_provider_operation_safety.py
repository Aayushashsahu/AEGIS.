from __future__ import annotations

from aegis.mission059_evidence import extraction_contract_status
from aegis.provider_operation_safety import (
    FutureProviderAuthorization,
    FutureVersionBoundRun,
    OperationAccess,
    ProviderIdentifierState,
    build_raw_first_envelope,
    preserve_provider_identifier_provenance,
)


def _authorization() -> FutureProviderAuthorization:
    return FutureProviderAuthorization(
        mission="MISSION_TEST",
        collector_id="c_mt09pib13nxqz1coi",
        candidate_id="candidate_safe",
        operator="owner",
        authorized_at_utc="2026-08-21T00:00:00Z",
        expires_at_utc="2026-08-22T00:00:00Z",
        scope="one_candidate_approval",
        max_operations=1,
        max_retries=0,
        timeout_seconds=30,
        allowed_operation="approve",
        prohibited_operations=("heal", "rerun", "commit", "rollback"),
    )


def test_authorization_fails_closed_for_wrong_scope_candidate_collector_expiry_and_retry() -> None:
    authorization = _authorization()

    assert authorization.validates(
        operation="approve", collector_id="c_mt09pib13nxqz1coi", candidate_id="candidate_safe",
        now_utc="2026-08-21T01:00:00Z", attempted_operations=0, retry_count=0,
    )
    assert not authorization.validates(
        operation="rerun", collector_id="c_mt09pib13nxqz1coi", candidate_id="candidate_safe",
        now_utc="2026-08-21T01:00:00Z", attempted_operations=0, retry_count=0,
    )
    assert not authorization.validates(
        operation="approve", collector_id="c_other", candidate_id="candidate_safe",
        now_utc="2026-08-21T01:00:00Z", attempted_operations=0, retry_count=0,
    )
    assert not authorization.validates(
        operation="approve", collector_id="c_mt09pib13nxqz1coi", candidate_id="candidate_wrong",
        now_utc="2026-08-21T01:00:00Z", attempted_operations=0, retry_count=0,
    )
    assert not authorization.validates(
        operation="approve", collector_id="c_mt09pib13nxqz1coi", candidate_id="candidate_safe",
        now_utc="2026-08-23T01:00:00Z", attempted_operations=0, retry_count=0,
    )
    assert not authorization.validates(
        operation="approve", collector_id="c_mt09pib13nxqz1coi", candidate_id="candidate_safe",
        now_utc="2026-08-21T01:00:00Z", attempted_operations=0, retry_count=1,
    )


def test_raw_first_envelope_never_substitutes_aeGIS_identifier_for_provider_id() -> None:
    envelope = build_raw_first_envelope(
        mission="MISSION_TEST", operation="heal", access=OperationAccess.MUTATION,
        correlation_id="aegis-local-correlation", collector_id="c_mt09pib13nxqz1coi",
        target_url="https://example.test", timeout_seconds=10, authorization_reference="auth-1",
        artifact_destination="experiments/mission/raw.bin", raw_response_bytes=b'{"status":"error"}',
        provider_identifiers=None, failure_class="PROVIDER_ERROR",
    )

    assert envelope.provider_identifier_state is ProviderIdentifierState.NOT_RETURNED_BY_PROVIDER
    assert envelope.provider_identifiers == {}
    assert envelope.raw_response_sha256 is not None


def test_http_200_with_input_only_is_transport_success_and_contract_failure() -> None:
    status = extraction_contract_status([{"input": {"url": "https://example.test"}}], http_status=200)

    assert status["provider_transport"] == "SUCCESS"
    assert status["extraction_contract"] == "FAIL"
    assert status["required_field_states"] == {"title": "MISSING", "price": "MISSING", "availability": "MISSING"}


def _version_bound_run(**overrides: object) -> FutureVersionBoundRun:
    values: dict[str, object] = {
        "mission": "MISSION_064",
        "collector_id": "c_mt09pib13nxqz1coi",
        "target_url": "https://example.test/product/1",
        "explicit_version": "v1",
        "correlation_id": "aegis-m064-version-bound-run-001",
        "prompt_sha256": "a" * 64,
        "authorization_reference": "evidence://mission-064/future-authorization",
        "max_operations": 1,
        "retry_budget": 0,
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return FutureVersionBoundRun(**values)  # type: ignore[arg-type]


def test_version_bound_run_requires_exact_identity_correlation_prompt_and_budget() -> None:
    run = _version_bound_run()

    assert run.prepared_cli_arguments() == (
        "bdata", "scraper", "run", "c_mt09pib13nxqz1coi", "https://example.test/product/1", "--version", "v1", "--json",
    )
    assert run.required_evidence()["AEGIS_CORRELATION_ID"] == "aegis-m064-version-bound-run-001"
    assert run.required_evidence()["explicit_version"] == "v1"


def test_version_bound_run_fails_closed_for_missing_or_wrong_required_fields() -> None:
    invalid = (
        {"collector_id": ""},
        {"target_url": "not-a-url"},
        {"explicit_version": ""},
        {"correlation_id": ""},
        {"prompt_sha256": "not-a-digest"},
        {"max_operations": 0},
        {"retry_budget": 1},
    )

    for override in invalid:
        try:
            _version_bound_run(**override)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected fail-closed validation for {override}")


def test_version_bound_provider_ids_cannot_use_local_fallback_identifiers() -> None:
    try:
        preserve_provider_identifier_provenance(
            {"provider_run_id": "aegis-local-run-001"},
            local_identifiers=("aegis-local-run-001", "candidate_local"),
        )
    except ValueError as exc:
        assert "local identifiers" in str(exc)
    else:
        raise AssertionError("local fallback identifier must not be accepted as provider evidence")


def test_version_bound_provider_id_absence_and_present_provider_ids_remain_distinct() -> None:
    absent_state, absent_ids = preserve_provider_identifier_provenance(None, local_identifiers=("local-1",))
    present_state, present_ids = preserve_provider_identifier_provenance(
        {"provider_operation_id": "op_123", "provider_run_id": "run_456", "local_id": "ignored"},
        local_identifiers=("local-1",),
    )

    assert absent_state is ProviderIdentifierState.NOT_RETURNED_BY_PROVIDER
    assert absent_ids == {}
    assert present_state is ProviderIdentifierState.PRESENT
    assert present_ids == {"provider_operation_id": "op_123", "provider_run_id": "run_456"}
