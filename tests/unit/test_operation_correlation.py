from pathlib import Path

import pytest

from aegis.operation_correlation import append_correlation_record, build_operation_correlation


COLLECTOR = "c_mt09pib13nxqz1coi"
TARGET = "https://example.test/mission-033/target"


def _record(*, operation_id: str, target: str = TARGET, provider_run_id: str | None = "vj_safe"):
    return build_operation_correlation(
        aegis_operation_id=operation_id,
        collector_id=COLLECTOR,
        target_url=target,
        started_at_utc="2026-08-20T00:00:00Z",
        provider_run_id=provider_run_id,
        template_version=None,
        operation_type="synchronous_collector_rerun",
        correlation_id="mission041b-rerun-c_mt09pib13nxqz1coi",
    )


def test_similar_runs_have_distinct_operation_records_and_url_hashes(tmp_path: Path) -> None:
    first = _record(operation_id="op-001")
    second = _record(operation_id="op-002", target="https://example.test/mission-033/other", provider_run_id="vj_other")

    first_path = append_correlation_record(tmp_path, first)
    second_path = append_correlation_record(tmp_path, second)

    assert first_path != second_path
    assert first.target_url_sha256 != second.target_url_sha256
    assert TARGET not in first_path.read_text(encoding="utf-8")
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_correlation_record_cannot_overwrite_an_existing_operation(tmp_path: Path) -> None:
    record = _record(operation_id="op-001", provider_run_id=None)

    append_correlation_record(tmp_path, record)

    with pytest.raises(FileExistsError):
        append_correlation_record(tmp_path, record)


def test_correlation_records_requested_and_selected_version_provenance_and_raw_digest() -> None:
    record = build_operation_correlation(
        aegis_operation_id="op-056",
        collector_id=COLLECTOR,
        target_url=TARGET,
        started_at_utc="2026-08-22T00:00:00Z",
        provider_run_id="r_056",
        template_version="v1",
        provider_revision="rev_17",
        requested_version="v1",
        selected_version="v1",
        version_evidence_source="PROVIDER_RESPONSE",
        raw_response_sha256="a" * 64,
        operation_type="versioned_cli_run",
        correlation_id="mission056-cli-run-c_mt09pib13nxqz1coi",
    )
    evidence = record.to_evidence_dict()
    assert evidence["schema_version"] == "operation-correlation-v2"
    assert evidence["requested_version"] == evidence["selected_version"] == "v1"
    assert evidence["provider_revision"] == "rev_17"
    assert evidence["raw_response_sha256"] == "a" * 64


@pytest.mark.parametrize("timestamp", ["2026-08-20T00:00:00+00:00", "invalid"])
def test_correlation_requires_explicit_utc_timestamp(timestamp: str) -> None:
    with pytest.raises(ValueError):
        build_operation_correlation(
            aegis_operation_id="op-001",
            collector_id=COLLECTOR,
            target_url=TARGET,
            started_at_utc=timestamp,
            provider_run_id=None,
            template_version=None,
            operation_type="synchronous_collector_rerun",
            correlation_id="mission041b-rerun-c_mt09pib13nxqz1coi",
        )


@pytest.mark.parametrize("operation_id", ["../escape", "op/child", "", "space id"])
def test_correlation_rejects_path_like_or_ambiguous_operation_ids(operation_id: str) -> None:
    with pytest.raises(ValueError, match="safe opaque"):
        build_operation_correlation(
            aegis_operation_id=operation_id,
            collector_id=COLLECTOR,
            target_url=TARGET,
            started_at_utc="2026-08-20T00:00:00Z",
            provider_run_id=None,
            template_version=None,
            operation_type="synchronous_collector_rerun",
            correlation_id="mission041b-rerun-c_mt09pib13nxqz1coi",
        )
