"""Evidence-only helpers for the Mission 059 one-heal boundary.

These functions deliberately do not create provider identifiers. They only
classify identifier fields observed in a decoded provider payload.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PROVIDER_IDENTIFIER_FIELDS = (
    "response_id",
    "collection_id",
    "operation_id",
    "provider_operation_id",
    "job_id",
    "request_id",
    "run_id",
    "id",
)
REQUIRED_FIELDS = ("title", "price", "availability")


def extract_provider_identifiers(payload: Any) -> dict[str, str]:
    """Return only non-empty identifier strings actually present in payload."""
    if not isinstance(payload, Mapping):
        return {}
    return {
        field: value
        for field in PROVIDER_IDENTIFIER_FIELDS
        if isinstance((value := payload.get(field)), str) and value.strip()
    }


def provider_id_status(payload: Any) -> str:
    """Classify only observed provider operation IDs; collector ID is not one."""
    identifiers = extract_provider_identifiers(payload)
    return "PRESENT" if identifiers else "ABSENT"


def preview_rows(payload: Any) -> list[Mapping[str, Any]] | None:
    if not isinstance(payload, Mapping):
        return None
    preview = payload.get("preview_result")
    if not isinstance(preview, Sequence) or isinstance(preview, (str, bytes)):
        return None
    if not all(isinstance(row, Mapping) for row in preview):
        return None
    return list(preview)


def candidate_field_states(rows: list[Mapping[str, Any]] | None) -> dict[str, str]:
    if not rows:
        return {field: "MISSING" for field in REQUIRED_FIELDS}
    row = rows[0]
    states: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        value = row.get(field)
        if field not in row:
            states[field] = "MISSING"
        elif value is None:
            states[field] = "NULL"
        elif isinstance(value, str) and not value.strip():
            states[field] = "EMPTY"
        else:
            states[field] = "PRESENT"
    return states


def candidate_status(payload: Any) -> tuple[str, list[Mapping[str, Any]] | None, dict[str, str]]:
    rows = preview_rows(payload)
    if rows is None:
        return "ABSENT", None, candidate_field_states(None)
    states = candidate_field_states(rows)
    return ("COMPLETE" if all(state == "PRESENT" for state in states.values()) else "INCOMPLETE"), rows, states
