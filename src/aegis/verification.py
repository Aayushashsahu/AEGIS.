"""Mission 005 deterministic candidate verification.

Verification is evidence evaluation only. This module never approves a provider
operation, activates a collector, commits a candidate, or calls an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse
from uuid import uuid4

from .healing import RepairCandidate
from .immutability import deep_freeze, freeze_mapping
from .models import ExtractionContract, Observation, utc_now


class EvidenceChannel(str, Enum):
    CONTRACT = "CONTRACT"
    HISTORY = "HISTORY"
    SEMANTIC_INVARIANT = "SEMANTIC_INVARIANT"
    INDEPENDENT_EVIDENCE = "INDEPENDENT_EVIDENCE"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class VerificationOverallStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationProvenance(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    TEST_DOUBLE = "TEST_DOUBLE"


@dataclass(frozen=True)
class IndependentEvidence:
    """A distinct, controlled evidence path; never inferred from provider output."""

    evidence_id: str
    source: str
    rows: Sequence[Mapping[str, Any]]
    provenance: VerificationProvenance = VerificationProvenance.TEST_DOUBLE
    source_group: str = ""
    evidence_refs: tuple[str, ...] = ()
    correlation_id: str = ""
    available: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", deep_freeze(list(self.rows)))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class VerificationCheck:
    check_id: str = field(default_factory=lambda: f"check_{uuid4().hex}")
    candidate_id: str = ""
    channel: EvidenceChannel = EvidenceChannel.CONTRACT
    category: str = ""
    status: CheckStatus = CheckStatus.UNKNOWN
    message: str = ""
    evidence_refs: tuple[str, ...] = ()
    provenance: VerificationProvenance = VerificationProvenance.DETERMINISTIC
    correlation_id: str = ""
    affected_fields: tuple[str, ...] = ()
    critical: bool = False
    created_at: datetime = field(default_factory=utc_now)
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "affected_fields", tuple(self.affected_fields))
        object.__setattr__(self, "details", freeze_mapping(self.details))


@dataclass(frozen=True)
class VerificationContext:
    candidate: RepairCandidate
    contract: ExtractionContract
    candidate_output: Sequence[Mapping[str, Any]]
    history: tuple[Observation, ...] = ()
    independent_evidence: IndependentEvidence | None = None
    correlation_id: str = ""
    evidence_refs: tuple[str, ...] = ()
    unaffected_fields: tuple[str, ...] = ()
    semantic_expectations: Mapping[str, Any] = field(default_factory=dict)
    history_source_group: str = ""
    model_opinion: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_output", deep_freeze(list(self.candidate_output)))
        object.__setattr__(self, "history", tuple(self.history))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "unaffected_fields", tuple(self.unaffected_fields))
        object.__setattr__(self, "semantic_expectations", freeze_mapping(self.semantic_expectations))
        object.__setattr__(self, "model_opinion", freeze_mapping(self.model_opinion or {}))


@dataclass(frozen=True)
class VerificationResult:
    candidate_id: str
    checks: tuple[VerificationCheck, ...]
    overall_status: VerificationOverallStatus
    failed_checks: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    verification_provenance: tuple[VerificationProvenance, ...]
    correlation_id: str
    started_at: datetime
    completed_at: datetime
    verification_id: str = field(default_factory=lambda: f"verification_{uuid4().hex}")
    eligible_for_future_commit: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "failed_checks", tuple(self.failed_checks))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "verification_provenance", tuple(self.verification_provenance))
        if self.eligible_for_future_commit and self.overall_status is not VerificationOverallStatus.PASS:
            raise ValueError("only a passing verification result can be eligible for a future commit")

    @property
    def unknown_checks(self) -> tuple[str, ...]:
        return tuple(check.check_id for check in self.checks if check.status is CheckStatus.UNKNOWN)

    @property
    def passing_channels(self) -> tuple[EvidenceChannel, ...]:
        return tuple(check.channel for check in self.checks if check.status is CheckStatus.PASS)



def _as_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        for key in ("rows", "items", "results", "data", "output"):
            nested = value.get(key)
            if isinstance(nested, (list, tuple)) and all(isinstance(row, Mapping) for row in nested):
                return tuple(nested)
        if all(isinstance(key, str) for key in value) and value:
            return (value,)
        return ()
    if isinstance(value, (list, tuple)) and all(isinstance(row, Mapping) for row in value):
        return tuple(value)
    return ()


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _field_name_set(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    return {key for row in rows for key in row.keys()}


def _entity_key(row: Mapping[str, Any]) -> str | None:
    for key in ("url", "id", "sku", "product_id", "title", "name"):
        value = row.get(key)
        if value is not None and str(value):
            return f"{key}:{value}"
    return None


def _rows_by_entity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {key: row for row in rows if (key := _entity_key(row)) is not None}


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        return isfinite(float(left)) and isfinite(float(right)) and abs(float(left) - float(right)) <= 1e-9
    return left == right


def _check(
    *,
    context: VerificationContext,
    channel: EvidenceChannel,
    category: str,
    status: CheckStatus,
    message: str,
    evidence: Sequence[str] = (),
    fields: Sequence[str] = (),
    critical: bool = False,
    details: Mapping[str, Any] | None = None,
) -> VerificationCheck:
    refs = tuple(sorted(set(context.evidence_refs) | set(evidence)))
    provenance = VerificationProvenance.TEST_DOUBLE if context.candidate.provenance.value == "TEST_DOUBLE" else VerificationProvenance.DETERMINISTIC
    return VerificationCheck(
        candidate_id=context.candidate.candidate_id,
        channel=channel,
        category=category,
        status=status,
        message=message,
        evidence_refs=refs,
        provenance=provenance,
        correlation_id=context.correlation_id,
        affected_fields=tuple(sorted(set(fields))),
        critical=critical,
        details=details or {},
    )


def verify_contract(context: VerificationContext) -> VerificationCheck:
    rows = _as_rows(context.candidate_output)
    if not rows:
        return _check(context=context, channel=EvidenceChannel.CONTRACT, category="OUTPUT_SHAPE", status=CheckStatus.FAIL, message="candidate output is not a non-empty sequence of row mappings", critical=True)
    expected_schema = set(context.contract.expected_schema or tuple(field.name for field in context.contract.fields))
    actual_schema = _field_name_set(rows)
    if actual_schema != expected_schema:
        return _check(context=context, channel=EvidenceChannel.CONTRACT, category="SCHEMA_COMPATIBILITY", status=CheckStatus.FAIL, message=f"candidate schema {sorted(actual_schema)} does not match expected schema {sorted(expected_schema)}", fields=sorted(actual_schema ^ expected_schema), critical=True, details={"expected_schema": sorted(expected_schema), "actual_schema": sorted(actual_schema)})
    for index, row in enumerate(rows):
        for field_contract in context.contract.fields:
            if field_contract.required and field_contract.name not in row:
                return _check(context=context, channel=EvidenceChannel.CONTRACT, category="REQUIRED_FIELD", status=CheckStatus.FAIL, message=f"row {index} is missing required field {field_contract.name}", evidence=(f"candidate://row/{index}/field/{field_contract.name}",), fields=(field_contract.name,), critical=True)
            value = row.get(field_contract.name)
            if value is None and not field_contract.allow_null:
                return _check(context=context, channel=EvidenceChannel.CONTRACT, category="NULLABILITY", status=CheckStatus.FAIL, message=f"row {index} contains null in non-nullable field {field_contract.name}", fields=(field_contract.name,), critical=True)
            if value is not None and type(value) not in field_contract.expected_types:
                return _check(context=context, channel=EvidenceChannel.CONTRACT, category="TYPE", status=CheckStatus.FAIL, message=f"row {index} field {field_contract.name} has type {type(value).__name__}", fields=(field_contract.name,), critical=True)
    history_rows = tuple(row for observation in context.history for row in observation.output)
    if context.unaffected_fields and history_rows:
        baseline = _rows_by_entity(history_rows)
        for row in rows:
            key = _entity_key(row)
            if key in baseline:
                for field_name in context.unaffected_fields:
                    if field_name in row and field_name in baseline[key] and not _values_equal(row[field_name], baseline[key][field_name]):
                        return _check(context=context, channel=EvidenceChannel.CONTRACT, category="UNAFFECTED_FIELD_PRESERVATION", status=CheckStatus.FAIL, message=f"unaffected field {field_name} changed for {key}", fields=(field_name,), critical=True)
    return _check(context=context, channel=EvidenceChannel.CONTRACT, category="CONTRACT_COMPATIBILITY", status=CheckStatus.PASS, message="required fields, types, nullability, schema, and configured unaffected fields pass", evidence=(f"contract://{context.contract.contract_id}",))


def verify_history(context: VerificationContext) -> VerificationCheck:
    if not context.history:
        return _check(context=context, channel=EvidenceChannel.HISTORY, category="HISTORY_AVAILABILITY", status=CheckStatus.UNKNOWN, message="no known-good observation history was supplied")
    baseline_rows = tuple(row for observation in context.history for row in observation.output)
    candidate_rows = _as_rows(context.candidate_output)
    baseline = _rows_by_entity(baseline_rows)
    candidate = _rows_by_entity(candidate_rows)
    if not baseline or not candidate:
        return _check(context=context, channel=EvidenceChannel.HISTORY, category="ENTITY_MATCH", status=CheckStatus.UNKNOWN, message="history or candidate rows have no deterministic entity key")
    mismatches: list[str] = []
    missing = sorted(set(baseline) - set(candidate))
    for key in sorted(set(baseline) & set(candidate)):
        for field_name, expected in baseline[key].items():
            if field_name in candidate[key] and not _values_equal(candidate[key][field_name], expected):
                mismatches.append(f"{key}.{field_name}")
    if missing or mismatches:
        return _check(context=context, channel=EvidenceChannel.HISTORY, category="HISTORICAL_CONTINUITY", status=CheckStatus.FAIL, message="candidate conflicts with known-good observation history", evidence=tuple(f"history://{item}" for item in mismatches + missing), fields=tuple(item.split(".")[-1] for item in mismatches), critical=False, details={"missing_entities": missing, "mismatches": mismatches})
    return _check(context=context, channel=EvidenceChannel.HISTORY, category="HISTORICAL_CONTINUITY", status=CheckStatus.PASS, message="candidate agrees with supplied known-good observation history", evidence=tuple(observation.evidence_refs[0] for observation in context.history if observation.evidence_refs))


def verify_semantics(context: VerificationContext) -> VerificationCheck:
    rows = _as_rows(context.candidate_output)
    fields: list[str] = []
    failures: list[str] = []
    for index, row in enumerate(rows):
        if "url" in row and not _valid_url(row["url"]):
            failures.append(f"row {index} url is not a valid HTTP(S) URL")
            fields.append("url")
        for field_name, (lower, upper) in context.contract.numeric_bounds.items():
            value = row.get(field_name)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(float(value))):
                failures.append(f"row {index} {field_name} is not a finite number")
                fields.append(field_name)
            elif isinstance(value, (int, float)) and not isinstance(value, bool) and ((lower is not None and value < lower) or (upper is not None and value > upper)):
                failures.append(f"row {index} {field_name} violates numeric bounds")
                fields.append(field_name)
        title = row.get("title")
        author = row.get("author")
        if isinstance(title, str) and isinstance(author, str) and not title.strip() and author.strip():
            failures.append(f"row {index} has author without title")
            fields.extend(("title", "author"))
        for field_name, expected in context.semantic_expectations.items():
            actual = row.get(field_name)
            if not _values_equal(actual, expected):
                failures.append(f"row {index} {field_name} does not match deterministic semantic expectation")
                fields.append(field_name)
    if failures:
        return _check(context=context, channel=EvidenceChannel.SEMANTIC_INVARIANT, category="SEMANTIC_INVARIANTS", status=CheckStatus.FAIL, message="; ".join(failures), evidence=("semantic://deterministic-invariants",), fields=fields, critical=True)
    return _check(context=context, channel=EvidenceChannel.SEMANTIC_INVARIANT, category="SEMANTIC_INVARIANTS", status=CheckStatus.PASS, message="known URL, numeric, relation, and supplied semantic invariants pass", evidence=("semantic://deterministic-invariants",))


def verify_independent_evidence(context: VerificationContext) -> VerificationCheck:
    evidence = context.independent_evidence
    if evidence is None or not evidence.available or not evidence.rows:
        return _check(context=context, channel=EvidenceChannel.INDEPENDENT_EVIDENCE, category="EVIDENCE_AVAILABILITY", status=CheckStatus.UNKNOWN, message="no independent evidence artifact was supplied")
    if context.history_source_group and evidence.source_group and context.history_source_group == evidence.source_group:
        return _check(context=context, channel=EvidenceChannel.INDEPENDENT_EVIDENCE, category="INDEPENDENCE", status=CheckStatus.UNKNOWN, message="independent evidence is correlated with the supplied history source and cannot be counted separately", evidence=evidence.evidence_refs)
    candidate_rows = _as_rows(context.candidate_output)
    expected_rows = _as_rows(evidence.rows)
    candidate = _rows_by_entity(candidate_rows)
    expected = _rows_by_entity(expected_rows)
    if not candidate or not expected or set(candidate) != set(expected):
        return _check(context=context, channel=EvidenceChannel.INDEPENDENT_EVIDENCE, category="ENTITY_CONSISTENCY", status=CheckStatus.FAIL, message="candidate entities do not match the independent evidence entities", evidence=evidence.evidence_refs, critical=True)
    mismatches: list[str] = []
    for key in sorted(expected):
        for field_name, expected_value in expected[key].items():
            if field_name in candidate[key] and not _values_equal(candidate[key][field_name], expected_value):
                mismatches.append(f"{key}.{field_name}")
    if mismatches:
        return _check(context=context, channel=EvidenceChannel.INDEPENDENT_EVIDENCE, category="INDEPENDENT_MATCH", status=CheckStatus.FAIL, message="candidate conflicts with independent evidence", evidence=evidence.evidence_refs, fields=tuple(item.split(".")[-1] for item in mismatches), critical=True, details={"mismatches": mismatches})
    return _check(context=context, channel=EvidenceChannel.INDEPENDENT_EVIDENCE, category="INDEPENDENT_MATCH", status=CheckStatus.PASS, message=f"candidate agrees with independent source {evidence.source}", evidence=evidence.evidence_refs)


def verify_candidate(context: VerificationContext) -> VerificationResult:
    """Evaluate all four channels; UNKNOWN remains UNKNOWN and never becomes PASS."""

    started = utc_now()
    checks = (
        verify_contract(context),
        verify_history(context),
        verify_semantics(context),
        verify_independent_evidence(context),
    )
    failed = tuple(check.check_id for check in checks if check.status is CheckStatus.FAIL)
    checks_by_channel = {check.channel: check for check in checks}
    required_channels = (
        EvidenceChannel.CONTRACT,
        EvidenceChannel.SEMANTIC_INVARIANT,
        EvidenceChannel.INDEPENDENT_EVIDENCE,
    )
    required_pass = all(checks_by_channel[channel].status is CheckStatus.PASS for channel in required_channels)
    unknown = any(check.status is CheckStatus.UNKNOWN for check in checks)
    optional_unknown_only = unknown and all(
        check.status is not CheckStatus.UNKNOWN or check.channel is EvidenceChannel.HISTORY
        for check in checks
    )
    overall = (
        VerificationOverallStatus.FAIL
        if failed
        else VerificationOverallStatus.PASS
        if required_pass and (not unknown or optional_unknown_only)
        else VerificationOverallStatus.INCONCLUSIVE
    )
    refs = tuple(sorted(set(context.evidence_refs) | {ref for check in checks for ref in check.evidence_refs}))
    provenance = tuple(dict.fromkeys(check.provenance for check in checks))
    return VerificationResult(
        candidate_id=context.candidate.candidate_id,
        checks=checks,
        overall_status=overall,
        failed_checks=failed,
        evidence_refs=refs,
        verification_provenance=provenance,
        correlation_id=context.correlation_id,
        started_at=started,
        completed_at=utc_now(),
        eligible_for_future_commit=overall is VerificationOverallStatus.PASS,
    )
