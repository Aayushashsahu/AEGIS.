"""Mission 002 domain contracts for collection, observations, and detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import uuid4

from .immutability import deep_freeze, freeze_mapping


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class CollectionState(str, Enum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class CollectionMode(str, Enum):
    REALTIME = "REALTIME"
    BATCH = "BATCH"
    TEST_DOUBLE = "TEST_DOUBLE"


class ProviderProvenance(str, Enum):
    BRIGHT_DATA = "BRIGHT_DATA"
    TEST_DOUBLE = "TEST_DOUBLE"


@dataclass(frozen=True)
class CollectorRequest:
    """Provider-neutral request for a collector reference."""

    target_url: str
    extraction_prompt: str
    collector_id: str | None = None
    provider: ProviderProvenance = ProviderProvenance.BRIGHT_DATA


@dataclass(frozen=True)
class CollectorHandle:
    collector_id: str
    provider: ProviderProvenance
    provider_reference: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class CollectionHandle:
    """Immutable snapshot of an asynchronous provider collection operation."""

    collection_id: str = field(default_factory=lambda: f"collection_{uuid4().hex}")
    collector_id: str = ""
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid4().hex}")
    status: CollectionState = CollectionState.SUBMITTED
    mode: CollectionMode = CollectionMode.REALTIME
    requested_version: str | None = None
    selected_version: str | None = None
    provider_revision: str | None = None
    version_evidence_source: str | None = None
    requested_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    provider_operation_ids: Mapping[str, str] = field(default_factory=dict)
    provider_status: str | None = None
    latency_ms: int | None = None
    output_schema: tuple[str, ...] = ()
    provider_provenance: ProviderProvenance = ProviderProvenance.BRIGHT_DATA
    evidence_refs: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_operation_ids", freeze_mapping(self.provider_operation_ids))
        object.__setattr__(self, "output_schema", tuple(self.output_schema))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    def transition(self, state: CollectionState, **changes: Any) -> "CollectionHandle":
        """Return a new state snapshot; the previous snapshot remains unchanged."""

        allowed = {
            CollectionState.SUBMITTED: {CollectionState.RUNNING, CollectionState.FAILED, CollectionState.TIMED_OUT},
            CollectionState.RUNNING: {CollectionState.COMPLETED, CollectionState.FAILED, CollectionState.TIMED_OUT},
            CollectionState.COMPLETED: set(),
            CollectionState.FAILED: set(),
            CollectionState.TIMED_OUT: set(),
        }
        if state not in allowed[self.status]:
            raise ValueError(f"invalid collection transition: {self.status.value} -> {state.value}")
        if state is CollectionState.RUNNING and "started_at" not in changes:
            changes["started_at"] = utc_now()
        if state in {CollectionState.COMPLETED, CollectionState.FAILED, CollectionState.TIMED_OUT} and "completed_at" not in changes:
            changes["completed_at"] = utc_now()
        return self.__class__(**{**self.__dict__, **changes, "status": state})


@dataclass(frozen=True)
class CollectionResult:
    handle: CollectionHandle
    output: Sequence[Mapping[str, Any]]
    received_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", deep_freeze(list(self.output)))


@dataclass(frozen=True)
class Observation:
    """Immutable, explicitly untrusted snapshot of a collection result."""

    observation_id: str = field(default_factory=lambda: f"observation_{uuid4().hex}")
    collection_id: str = ""
    collector_id: str = ""
    provider_operation_ids: Mapping[str, str] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=utc_now)
    input: Mapping[str, Any] = field(default_factory=dict)
    output: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    schema: tuple[str, ...] = ()
    row_count: int = 0
    latency_ms: int | None = None
    collection_mode: CollectionMode = CollectionMode.REALTIME
    provider_provenance: ProviderProvenance = ProviderProvenance.BRIGHT_DATA
    evidence_refs: tuple[str, ...] = ()
    trust_status: str = "UNTRUSTED_UNTIL_VERIFIED"

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_operation_ids", freeze_mapping(self.provider_operation_ids))
        object.__setattr__(self, "input", freeze_mapping(self.input))
        object.__setattr__(self, "output", deep_freeze(list(self.output)))
        object.__setattr__(self, "schema", tuple(self.schema))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        if self.row_count != len(self.output):
            raise ValueError("row_count must equal the immutable output length")
        if self.trust_status != "UNTRUSTED_UNTIL_VERIFIED":
            raise ValueError("Mission 002 observations must remain untrusted")

    @classmethod
    def from_result(cls, result: CollectionResult, input: Mapping[str, Any]) -> "Observation":
        if result.handle.status is not CollectionState.COMPLETED:
            raise ValueError("only completed collection results can become observations")
        schema = tuple(sorted({key for row in result.output for key in row.keys()}))
        return cls(
            collection_id=result.handle.collection_id,
            collector_id=result.handle.collector_id,
            provider_operation_ids=result.handle.provider_operation_ids,
            input=input,
            output=result.output,
            schema=schema,
            row_count=len(result.output),
            latency_ms=result.handle.latency_ms,
            collection_mode=result.handle.mode,
            provider_provenance=result.handle.provider_provenance,
            evidence_refs=result.handle.evidence_refs,
            collected_at=result.received_at,
        )


@dataclass(frozen=True)
class FieldContract:
    name: str
    required: bool = True
    expected_types: tuple[type, ...] = (str,)
    allow_null: bool = False


@dataclass(frozen=True)
class ExtractionContract:
    contract_id: str
    fields: tuple[FieldContract, ...]
    min_rows: int = 1
    max_rows: int | None = None
    expected_row_count: int | None = None
    row_count_tolerance: int = 0
    numeric_bounds: Mapping[str, tuple[float | None, float | None]] = field(default_factory=dict)
    invariants: tuple[str, ...] = ()
    expected_schema: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(self.fields))
        object.__setattr__(self, "numeric_bounds", freeze_mapping(self.numeric_bounds))
        object.__setattr__(self, "invariants", tuple(self.invariants))
        object.__setattr__(self, "expected_schema", tuple(self.expected_schema))


@dataclass(frozen=True)
class DetectionSignal:
    detector: str
    code: str
    message: str
    severity: str
    affected_fields: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetectionResult:
    detected: bool
    severity: str
    signals: tuple[DetectionSignal, ...]
    affected_fields: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    detector_provenance: tuple[str, ...]
    evaluated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", tuple(self.signals))
        object.__setattr__(self, "affected_fields", tuple(self.affected_fields))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "detector_provenance", tuple(self.detector_provenance))
