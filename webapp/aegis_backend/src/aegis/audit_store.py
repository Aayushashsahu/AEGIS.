"""Mission 008 durable append-only audit/evidence boundary.

The domain records remain canonical. This module stores redacted normalized
payloads around them in SQLite, with no update/delete interface and read-only
query methods. It is intentionally local and provider-neutral.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol, Sequence
from uuid import uuid4

from .immutability import deep_freeze


SCHEMA_VERSION = 1
_SECRET_KEY = re.compile(r"(api[_-]?key|authorization|cookie|credential|password|secret|token|private[_-]?key)", re.IGNORECASE)
_SECRET_VALUE = re.compile(r"(?i)(bearer\s+|sk-[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{16})[A-Za-z0-9._:/+\-=]*")


class AuditEventType(str, Enum):
    OBSERVATION = "OBSERVATION"
    DETECTION = "DETECTION"
    DIAGNOSIS = "DIAGNOSIS"
    REPAIR_REQUEST = "REPAIR_REQUEST"
    CANDIDATE = "CANDIDATE"
    VERIFICATION = "VERIFICATION"
    RISK_DECISION = "RISK_DECISION"
    COMMIT_DECISION = "COMMIT_DECISION"
    QUARANTINE = "QUARANTINE"
    WATCH_REGISTRATION = "WATCH_REGISTRATION"
    WATCH_CYCLE = "WATCH_CYCLE"
    WATCH_RESULT = "WATCH_RESULT"
    REGRESSION = "REGRESSION"
    EVIDENCE_REFERENCE = "EVIDENCE_REFERENCE"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: AuditEventType
    aggregate_id: str
    correlation_id: str
    timestamp: str
    provenance: str
    schema_version: int
    payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", deep_freeze(dict(self.payload)))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))
        if not self.event_id or not self.aggregate_id or not self.correlation_id:
            raise ValueError("AuditEvent requires event, aggregate, and correlation identifiers")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported audit schema version")

    @classmethod
    def from_record(
        cls,
        event_type: AuditEventType,
        record: Any,
        *,
        aggregate_id: str,
        correlation_id: str,
        provenance: str,
        evidence_refs: Sequence[str] = (),
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> "AuditEvent":
        payload = _to_jsonable(record)
        payload = _redact(payload)
        return cls(
            event_id=event_id or f"audit_{uuid4().hex}",
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            timestamp=timestamp or _utc_iso(),
            provenance=provenance,
            schema_version=SCHEMA_VERSION,
            payload=payload,
            evidence_refs=tuple(evidence_refs),
        )


class AuditStore(Protocol):
    """Provider-neutral persistence/query interface."""

    def append_event(self, event: AuditEvent) -> AuditEvent: ...

    def get_event(self, event_id: str) -> AuditEvent | None: ...

    def history(self, *, aggregate_id: str | None = None, correlation_id: str | None = None, event_type: AuditEventType | None = None) -> tuple[AuditEvent, ...]: ...

    def current_status(self, aggregate_id: str) -> Mapping[str, Any]: ...


class SQLiteAuditStore:
    """Small durable SQLite implementation; append-only at the SQL boundary."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                provenance TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL
            )
            """
        )
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_aggregate ON audit_events(aggregate_id, timestamp)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id, timestamp)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type, timestamp)")
        self._connection.commit()

    def append_event(self, event: AuditEvent) -> AuditEvent:
        payload = json.dumps(_to_jsonable(event.payload), sort_keys=True, separators=(",", ":"))
        refs = json.dumps(list(event.evidence_refs), sort_keys=True, separators=(",", ":"))
        try:
            self._connection.execute(
                "INSERT INTO audit_events(event_id,event_type,aggregate_id,correlation_id,timestamp,provenance,schema_version,payload_json,evidence_refs_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.event_type.value,
                    event.aggregate_id,
                    event.correlation_id,
                    event.timestamp,
                    event.provenance,
                    event.schema_version,
                    payload,
                    refs,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("append-only audit event ID conflict; existing records cannot be replaced") from exc
        return event

    def append_observation(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.OBSERVATION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_detection(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.DETECTION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_diagnosis(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.DIAGNOSIS, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_repair_request(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.REPAIR_REQUEST, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_candidate(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.CANDIDATE, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_verification(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.VERIFICATION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_risk_decision(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.RISK_DECISION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_commit_decision(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.COMMIT_DECISION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_quarantine(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.QUARANTINE, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_watch_registration(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.WATCH_REGISTRATION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_watch_cycle(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.WATCH_CYCLE, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_watch_result(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.WATCH_RESULT, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_regression(self, record: Any, *, aggregate_id: str, correlation_id: str, provenance: str, evidence_refs: Sequence[str] = ()) -> AuditEvent:
        return self.append_event(AuditEvent.from_record(AuditEventType.REGRESSION, record, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=evidence_refs))

    def append_evidence_reference(self, reference: str, *, aggregate_id: str, correlation_id: str, provenance: str) -> AuditEvent:
        if not reference or reference.startswith("secret:"):
            raise ValueError("invalid evidence reference")
        return self.append_event(AuditEvent.from_record(AuditEventType.EVIDENCE_REFERENCE, {"evidence_ref": reference}, aggregate_id=aggregate_id, correlation_id=correlation_id, provenance=provenance, evidence_refs=(reference,)))

    def get_event(self, event_id: str) -> AuditEvent | None:
        row = self._connection.execute("SELECT * FROM audit_events WHERE event_id = ?", (event_id,)).fetchone()
        return None if row is None else _row_to_event(row)

    def history(
        self,
        *,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        event_type: AuditEventType | None = None,
    ) -> tuple[AuditEvent, ...]:
        clauses: list[str] = []
        params: list[str] = []
        if aggregate_id is not None:
            clauses.append("aggregate_id = ?")
            params.append(aggregate_id)
        if correlation_id is not None:
            clauses.append("correlation_id = ?")
            params.append(correlation_id)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type.value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._connection.execute(f"SELECT * FROM audit_events{where} ORDER BY timestamp, rowid", params).fetchall()
        return tuple(_row_to_event(row) for row in rows)

    def current_status(self, aggregate_id: str) -> Mapping[str, Any]:
        events = self.history(aggregate_id=aggregate_id)
        if not events:
            return MappingProxyType({"aggregate_id": aggregate_id, "status": "NOT_FOUND", "event_count": 0})
        latest = events[-1]
        status = _extract_status(latest.payload) or latest.event_type.value
        return MappingProxyType({
            "aggregate_id": aggregate_id,
            "status": status,
            "latest_event_id": latest.event_id,
            "latest_event_type": latest.event_type.value,
            "correlation_id": latest.correlation_id,
            "event_count": len(events),
            "evidence_refs": latest.evidence_refs,
        })

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteAuditStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _to_jsonable(value: Any) -> Any:
    value = _enum_value(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _redact(value: Any, *, key_context: str = "") -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            redacted[key_text] = "[REDACTED]" if _SECRET_KEY.search(key_text) else _redact(item, key_context=key_text)
        return redacted
    if isinstance(value, list):
        return [_redact(item, key_context=key_context) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        event_type=AuditEventType(row["event_type"]),
        aggregate_id=row["aggregate_id"],
        correlation_id=row["correlation_id"],
        timestamp=row["timestamp"],
        provenance=row["provenance"],
        schema_version=row["schema_version"],
        payload=json.loads(row["payload_json"]),
        evidence_refs=tuple(json.loads(row["evidence_refs_json"])),
    )


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "eligibility", "decision"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None
