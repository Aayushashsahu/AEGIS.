from __future__ import annotations

from aegis.mission059_evidence import extraction_contract_status
from aegis.provider_operation_safety import (
    FutureProviderAuthorization,
    OperationAccess,
    ProviderIdentifierState,
    build_raw_first_envelope,
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
