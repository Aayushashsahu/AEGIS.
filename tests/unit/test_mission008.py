from __future__ import annotations

import json
from dataclasses import replace

import pytest

from aegis.audit_store import AuditEvent, AuditEventType, SCHEMA_VERSION, SQLiteAuditStore
from aegis.commit_gate import CommitGate
from aegis.commit_gate_double import CommitGateFixture, build_commit_gate_fixture
from aegis.watch import WatchEngine
from aegis.watch_double import WatchFixture, build_watch_fixture


def test_sqlite_store_is_durable_and_queryable(tmp_path) -> None:
    path = tmp_path / "aegis-audit.sqlite3"
    with SQLiteAuditStore(path) as store:
        event = store.append_event(AuditEvent.from_record(
            AuditEventType.EVIDENCE_REFERENCE,
            {"status": "RECORDED", "evidence_ref": "evidence://TEST_DOUBLE/durable"},
            aggregate_id="aggregate-1",
            correlation_id="corr-1",
            provenance="TEST_DOUBLE",
            evidence_refs=("evidence://TEST_DOUBLE/durable",),
        ))
        assert store.get_event(event.event_id) is not None
        assert store.current_status("aggregate-1")["status"] == "RECORDED"
    with SQLiteAuditStore(path) as reopened:
        events = reopened.history(aggregate_id="aggregate-1", correlation_id="corr-1")
        assert len(events) == 1
        assert events[0].event_id == event.event_id
        assert events[0].schema_version == SCHEMA_VERSION


def test_append_only_duplicate_event_id_is_rejected(tmp_path) -> None:
    with SQLiteAuditStore(tmp_path / "audit.sqlite3") as store:
        event = AuditEvent.from_record(
            AuditEventType.DETECTION,
            {"status": "ANOMALOUS"},
            aggregate_id="aggregate-duplicate",
            correlation_id="corr-duplicate",
            provenance="TEST_DOUBLE",
        )
        store.append_event(event)
        with pytest.raises(ValueError, match="append-only"):
            store.append_event(event)
        assert len(store.history(aggregate_id="aggregate-duplicate")) == 1
        assert not hasattr(store, "update")
        assert not hasattr(store, "delete")


def test_payload_and_record_envelope_are_immutable() -> None:
    store = SQLiteAuditStore()
    event = store.append_event(AuditEvent.from_record(
        AuditEventType.RISK_DECISION,
        {"status": "ACCEPT", "nested": {"decision": "ACCEPT"}},
        aggregate_id="aggregate-immutable",
        correlation_id="corr-immutable",
        provenance="TEST_DOUBLE",
    ))
    with pytest.raises(TypeError):
        event.payload["status"] = "REJECT"  # type: ignore[index]
    retrieved = store.get_event(event.event_id)
    assert retrieved is not None
    with pytest.raises(TypeError):
        retrieved.payload["nested"]["decision"] = "REJECT"  # type: ignore[index]
    store.close()


def test_secret_values_are_redacted_before_sqlite_persistence(tmp_path) -> None:
    path = tmp_path / "redaction.sqlite3"
    with SQLiteAuditStore(path) as store:
        event = store.append_event(AuditEvent.from_record(
            AuditEventType.CANDIDATE,
            {
                "status": "UNVERIFIED",
                "api_key": "sk-this-must-not-persist",
                "headers": {"Authorization": "Bearer super-secret-token"},
                "page_text": "ordinary untrusted content",
            },
            aggregate_id="aggregate-redaction",
            correlation_id="corr-redaction",
            provenance="TEST_DOUBLE",
        ))
        payload = str(event.payload)
        assert "sk-this-must-not-persist" not in payload
        assert "super-secret-token" not in payload
        assert "ordinary untrusted content" in payload
        raw = store._connection.execute("SELECT payload_json FROM audit_events WHERE event_id = ?", (event.event_id,)).fetchone()[0]
        assert "sk-this-must-not-persist" not in raw
        assert "super-secret-token" not in raw


def test_read_queries_filter_by_event_type_and_correlation(tmp_path) -> None:
    with SQLiteAuditStore(tmp_path / "query.sqlite3") as store:
        store.append_event(AuditEvent.from_record(AuditEventType.WATCH_CYCLE, {"status": "HEALTHY"}, aggregate_id="pipeline", correlation_id="corr-a", provenance="TEST_DOUBLE"))
        store.append_event(AuditEvent.from_record(AuditEventType.REGRESSION, {"status": "REGRESSION"}, aggregate_id="pipeline", correlation_id="corr-a", provenance="TEST_DOUBLE"))
        store.append_event(AuditEvent.from_record(AuditEventType.WATCH_CYCLE, {"status": "UNKNOWN"}, aggregate_id="pipeline", correlation_id="corr-b", provenance="TEST_DOUBLE"))
        assert len(store.history(correlation_id="corr-a")) == 2
        assert len(store.history(event_type=AuditEventType.WATCH_CYCLE)) == 2
        assert store.current_status("pipeline")["status"] == "UNKNOWN"


def test_convenience_appenders_persist_mission_006_and_007_records(tmp_path) -> None:
    candidate, context, verification, risk_decision, known_good, authorization = build_commit_gate_fixture(CommitGateFixture.COMMIT_ELIGIBLE)
    commit_decision = CommitGate().evaluate(candidate, verification, risk_decision, context.contract, known_good, authorization, correlation_id=context.correlation_id)
    registration, observation, _ = build_watch_fixture(WatchFixture.REGRESSION_SCHEMA)
    evaluation = WatchEngine().evaluate(registration, observation, observation_reference="observation://TEST_DOUBLE/mission-008", ledger=None)
    with SQLiteAuditStore(tmp_path / "domain.sqlite3") as store:
        store.append_verification(verification, aggregate_id=candidate.candidate_id, correlation_id=context.correlation_id, provenance=candidate.provenance.value, evidence_refs=verification.evidence_refs)
        store.append_risk_decision(risk_decision, aggregate_id=candidate.candidate_id, correlation_id=context.correlation_id, provenance=candidate.provenance.value, evidence_refs=risk_decision.evidence_refs)
        store.append_commit_decision(commit_decision, aggregate_id=candidate.candidate_id, correlation_id=context.correlation_id, provenance=candidate.provenance.value, evidence_refs=commit_decision.evidence_refs)
        store.append_watch_registration(registration, aggregate_id=registration.registration_id, correlation_id=registration.correlation_id, provenance=registration.candidate_provenance.value)
        store.append_watch_cycle(evaluation.cycle, aggregate_id=evaluation.cycle.cycle_id, correlation_id=evaluation.cycle.correlation_id, provenance=evaluation.cycle.provenance.value, evidence_refs=evaluation.cycle.evidence_refs)
        store.append_watch_result(evaluation.result, aggregate_id=evaluation.cycle.cycle_id, correlation_id=evaluation.result.correlation_id, provenance=evaluation.result.provenance.value, evidence_refs=evaluation.result.evidence_refs)
        assert evaluation.regression_event is not None
        store.append_regression(evaluation.regression_event, aggregate_id=evaluation.regression_event.regression_id, correlation_id=evaluation.regression_event.correlation_id, provenance=evaluation.regression_event.provenance.value, evidence_refs=evaluation.regression_event.failed_evidence_refs)
        assert len(store.history(correlation_id=context.correlation_id)) >= 6
        assert store.history(event_type=AuditEventType.REGRESSION)


def test_correction_is_new_event_not_update() -> None:
    store = SQLiteAuditStore()
    original = store.append_event(AuditEvent.from_record(
        AuditEventType.VERIFICATION,
        {"status": "INCONCLUSIVE"},
        aggregate_id="candidate-correction",
        correlation_id="corr-correction",
        provenance="TEST_DOUBLE",
    ))
    correction = store.append_event(AuditEvent.from_record(
        AuditEventType.VERIFICATION,
        {"status": "PASS", "corrects_event_id": original.event_id},
        aggregate_id="candidate-correction",
        correlation_id="corr-correction",
        provenance="TEST_DOUBLE",
    ))
    assert correction.event_id != original.event_id
    assert len(store.history(aggregate_id="candidate-correction")) == 2
    assert store.current_status("candidate-correction")["status"] == "PASS"
    store.close()
