"""Deterministic provenance for the decoded-provider to normalized-output boundary.

This module never contacts a provider and never infers missing values. It
answers a narrow forensic question: did a required field arrive in decoded
provider rows and disappear during AEGIS normalization, or was it already
absent when AEGIS first observed the decoded provider payload?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence


def _field_names(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return sorted top-level field names, including fields whose value is null."""

    names = {
        key
        for row in rows
        for key in row
    }
    return tuple(sorted(names))


def _required_missing_in_any_row(rows: Sequence[Mapping[str, Any]], required: Sequence[str]) -> tuple[str, ...]:
    return tuple(name for name in required if any(name not in row for row in rows))


def _required_null_in_any_row(rows: Sequence[Mapping[str, Any]], required: Sequence[str]) -> tuple[str, ...]:
    return tuple(name for name in required if any(name in row and row[name] is None for row in rows))


def _required_empty_string_in_any_row(rows: Sequence[Mapping[str, Any]], required: Sequence[str]) -> tuple[str, ...]:
    return tuple(name for name in required if any(isinstance(row.get(name), str) and not row[name].strip() for row in rows))


@dataclass(frozen=True)
class OutputLineage:
    """A redaction-safe, value-presence-only output-boundary diagnostic."""

    decoded_provider_fields: tuple[str, ...]
    normalized_aegis_fields: tuple[str, ...]
    required_fields: tuple[str, ...]
    nonrequired_fields_dropped: tuple[str, ...]
    required_fields_missing_from_provider: tuple[str, ...]
    required_fields_dropped_by_normalization: tuple[str, ...]
    required_fields_missing_after_normalization: tuple[str, ...]
    required_fields_missing_in_any_provider_row: tuple[str, ...]
    required_fields_null_in_any_provider_row: tuple[str, ...]
    required_fields_missing_in_any_normalized_row: tuple[str, ...]
    required_fields_null_in_any_normalized_row: tuple[str, ...]
    required_fields_empty_string_in_any_provider_row: tuple[str, ...]
    required_fields_empty_string_in_any_normalized_row: tuple[str, ...]
    decoded_provider_row_count: int
    normalized_aegis_row_count: int

    @property
    def classification(self) -> str:
        if self.required_fields_dropped_by_normalization:
            return "AEGIS_NORMALIZATION_LOSS"
        if self.required_fields_missing_from_provider:
            return "DECODED_PROVIDER_OUTPUT_INCOMPLETE"
        if self.required_fields_missing_in_any_provider_row:
            return "DECODED_PROVIDER_OUTPUT_PARTIALLY_INCOMPLETE"
        if self.required_fields_null_in_any_provider_row:
            return "DECODED_PROVIDER_OUTPUT_NULL_REQUIRED_FIELD"
        if self.required_fields_empty_string_in_any_provider_row:
            return "DECODED_PROVIDER_OUTPUT_EMPTY_REQUIRED_FIELD"
        return "REQUIRED_FIELDS_PRESERVED"

    def to_evidence_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["classification"] = self.classification
        return result


def analyze_output_lineage(
    decoded_provider_rows: Sequence[Mapping[str, Any]],
    normalized_aegis_rows: Sequence[Mapping[str, Any]],
    required_fields: Iterable[str],
) -> OutputLineage:
    """Compare decoded provider rows with derived AEGIS rows without mutation.

    ``decoded_provider_rows`` must be the first JSON-decoded representation
    returned by the provider transport. It is not a claim that an original
    provider response body is retained. The diagnostic retains names only, not
    field values, so it can be included safely in evidence summaries.
    """

    required = tuple(dict.fromkeys(required_fields))
    raw_fields = _field_names(decoded_provider_rows)
    normalized_fields = _field_names(normalized_aegis_rows)
    raw_set = set(raw_fields)
    normalized_set = set(normalized_fields)
    required_set = set(required)

    missing_from_provider = tuple(name for name in required if name not in raw_set)
    dropped_by_normalization = tuple(name for name in required if name in raw_set and name not in normalized_set)
    missing_after_normalization = tuple(name for name in required if name not in normalized_set)

    return OutputLineage(
        decoded_provider_fields=raw_fields,
        normalized_aegis_fields=normalized_fields,
        required_fields=required,
        nonrequired_fields_dropped=tuple(sorted((raw_set - normalized_set) - required_set)),
        required_fields_missing_from_provider=missing_from_provider,
        required_fields_dropped_by_normalization=dropped_by_normalization,
        required_fields_missing_after_normalization=missing_after_normalization,
        required_fields_missing_in_any_provider_row=_required_missing_in_any_row(decoded_provider_rows, required),
        required_fields_null_in_any_provider_row=_required_null_in_any_row(decoded_provider_rows, required),
        required_fields_missing_in_any_normalized_row=_required_missing_in_any_row(normalized_aegis_rows, required),
        required_fields_null_in_any_normalized_row=_required_null_in_any_row(normalized_aegis_rows, required),
        required_fields_empty_string_in_any_provider_row=_required_empty_string_in_any_row(decoded_provider_rows, required),
        required_fields_empty_string_in_any_normalized_row=_required_empty_string_in_any_row(normalized_aegis_rows, required),
        decoded_provider_row_count=len(decoded_provider_rows),
        normalized_aegis_row_count=len(normalized_aegis_rows),
    )
