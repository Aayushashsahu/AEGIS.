"""Deterministic ExtractionContract helpers for Mission 002."""

from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .models import DetectionSignal, ExtractionContract, FieldContract


def default_extraction_contract() -> ExtractionContract:
    """Return the small contract used by the first vertical slice."""

    return ExtractionContract(
        contract_id="mission-002-hacker-news-top-stories-v1",
        fields=(
            FieldContract("title", expected_types=(str,)),
            FieldContract("url", expected_types=(str,)),
            FieldContract("points", expected_types=(int, float)),
            FieldContract("author", expected_types=(str,)),
            FieldContract("comment_count", expected_types=(int, float)),
        ),
        min_rows=1,
        numeric_bounds={"points": (0, None), "comment_count": (0, None)},
        invariants=("valid_url", "non_negative_numeric"),
        expected_schema=("title", "url", "points", "author", "comment_count"),
    )


def _type_name(types: tuple[type, ...]) -> str:
    return "/".join(item.__name__ for item in types)


def _is_expected_type(value: Any, expected_types: tuple[type, ...]) -> bool:
    return type(value) in expected_types


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _signals_for_row(row: Mapping[str, Any], contract: ExtractionContract, row_index: int) -> list[DetectionSignal]:
    signals: list[DetectionSignal] = []
    fields_by_name = {field.name: field for field in contract.fields}
    for field in contract.fields:
        if field.required and field.name not in row:
            signals.append(DetectionSignal(
                detector="schema",
                code="MISSING_FIELD",
                message=f"row {row_index} is missing required field {field.name}",
                severity="L2",
                affected_fields=(field.name,),
                evidence_refs=(f"observation://row/{row_index}/field/{field.name}",),
            ))
            continue
        value = row.get(field.name)
        if value is None and not field.allow_null:
            signals.append(DetectionSignal(
                detector="schema",
                code="NULL_FIELD",
                message=f"row {row_index} has unexpected null for {field.name}",
                severity="L2",
                affected_fields=(field.name,),
                evidence_refs=(f"observation://row/{row_index}/field/{field.name}",),
            ))
        elif value is not None and not _is_expected_type(value, field.expected_types):
            signals.append(DetectionSignal(
                detector="schema",
                code="INVALID_TYPE",
                message=f"row {row_index} field {field.name} expected {_type_name(field.expected_types)} but got {type(value).__name__}",
                severity="L2",
                affected_fields=(field.name,),
                evidence_refs=(f"observation://row/{row_index}/field/{field.name}",),
            ))
    if contract.expected_schema:
        allowed = set(fields_by_name)
        for field_name in sorted(set(row) - allowed):
            signals.append(DetectionSignal(
                detector="schema",
                code="UNEXPECTED_FIELD",
                message=f"row {row_index} contains unexpected field {field_name}",
                severity="L2",
                affected_fields=(field_name,),
                evidence_refs=(f"observation://row/{row_index}/field/{field_name}",),
            ))
    return signals


def evaluate_schema(observation_output: Iterable[Mapping[str, Any]], contract: ExtractionContract) -> tuple[DetectionSignal, ...]:
    signals: list[DetectionSignal] = []
    for row_index, row in enumerate(observation_output):
        signals.extend(_signals_for_row(row, contract, row_index))
    return tuple(signals)


def evaluate_statistical(observation_output: Iterable[Mapping[str, Any]], contract: ExtractionContract) -> tuple[DetectionSignal, ...]:
    rows = list(observation_output)
    signals: list[DetectionSignal] = []
    count = len(rows)
    if count < contract.min_rows:
        signals.append(DetectionSignal(
            detector="statistical",
            code="ROW_COUNT_TOO_LOW",
            message=f"row count {count} is below minimum {contract.min_rows}",
            severity="L3",
            evidence_refs=("observation://row_count",),
        ))
    if contract.max_rows is not None and count > contract.max_rows:
        signals.append(DetectionSignal(
            detector="statistical",
            code="ROW_COUNT_TOO_HIGH",
            message=f"row count {count} exceeds maximum {contract.max_rows}",
            severity="L3",
            evidence_refs=("observation://row_count",),
        ))
    if contract.expected_row_count is not None and abs(count - contract.expected_row_count) > contract.row_count_tolerance:
        signals.append(DetectionSignal(
            detector="statistical",
            code="ROW_COUNT_ANOMALY",
            message=f"row count {count} differs from expected {contract.expected_row_count}",
            severity="L3",
            evidence_refs=("observation://row_count",),
        ))
    for row_index, row in enumerate(rows):
        for field_name, (lower, upper) in contract.numeric_bounds.items():
            value = row.get(field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            if not isfinite(float(value)):
                signals.append(DetectionSignal(
                    detector="statistical",
                    code="IMPOSSIBLE_NUMERIC_VALUE",
                    message=f"row {row_index} field {field_name} is not finite",
                    severity="L3",
                    affected_fields=(field_name,),
                    evidence_refs=(f"observation://row/{row_index}/field/{field_name}",),
                ))
                continue
            if lower is not None and value < lower or upper is not None and value > upper:
                signals.append(DetectionSignal(
                    detector="statistical",
                    code="NUMERIC_OUT_OF_BOUNDS",
                    message=f"row {row_index} field {field_name}={value} is outside the contract bounds",
                    severity="L3",
                    affected_fields=(field_name,),
                    evidence_refs=(f"observation://row/{row_index}/field/{field_name}",),
                ))
    return tuple(signals)


def evaluate_semantic(observation_output: Iterable[Mapping[str, Any]], contract: ExtractionContract) -> tuple[DetectionSignal, ...]:
    signals: list[DetectionSignal] = []
    for row_index, row in enumerate(observation_output):
        url = row.get("url")
        if url is not None and not _valid_url(url):
            signals.append(DetectionSignal(
                detector="semantic",
                code="INVALID_URL",
                message=f"row {row_index} url is not a valid HTTP(S) URL",
                severity="L3",
                affected_fields=("url",),
                evidence_refs=(f"observation://row/{row_index}/field/url",),
            ))
        for field_name in ("points", "comment_count"):
            value = row.get(field_name)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
                signals.append(DetectionSignal(
                    detector="semantic",
                    code="NEGATIVE_NUMERIC_VALUE",
                    message=f"row {row_index} field {field_name} cannot be negative",
                    severity="L3",
                    affected_fields=(field_name,),
                    evidence_refs=(f"observation://row/{row_index}/field/{field_name}",),
                ))
        title = row.get("title")
        author = row.get("author")
        if isinstance(title, str) and isinstance(author, str) and not title.strip() and author.strip():
            signals.append(DetectionSignal(
                detector="semantic",
                code="EMPTY_REQUIRED_RELATION",
                message=f"row {row_index} has an author but an empty title",
                severity="L3",
                affected_fields=("title", "author"),
                evidence_refs=(f"observation://row/{row_index}",),
            ))
    return tuple(signals)
