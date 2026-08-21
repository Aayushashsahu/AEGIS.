"""Append-only correlation records for bounded provider operations."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


def _target_url_hash(target_url: str) -> str:
    return hashlib.sha256(target_url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OperationCorrelationRecord:
    """Correlates one AEGIS operation without retaining its target URL or token."""

    aegis_operation_id: str
    collector_id: str
    target_url_sha256: str
    started_at_utc: str
    provider_run_id: str | None
    template_version: str | None
    operation_type: str
    correlation_id: str
    provider_revision: str | None = None
    requested_version: str | None = None
    selected_version: str | None = None
    version_evidence_source: str | None = None
    raw_response_sha256: str | None = None
    schema_version: str = "operation-correlation-v2"

    def to_evidence_dict(self) -> dict[str, object]:
        return asdict(self)


def build_operation_correlation(
    *,
    aegis_operation_id: str,
    collector_id: str,
    target_url: str,
    started_at_utc: str,
    provider_run_id: str | None,
    template_version: str | None,
    operation_type: str,
    correlation_id: str,
    provider_revision: str | None = None,
    requested_version: str | None = None,
    selected_version: str | None = None,
    version_evidence_source: str | None = None,
    raw_response_sha256: str | None = None,
) -> OperationCorrelationRecord:
    """Validate and construct one correlation record without provider access."""

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", aegis_operation_id):
        raise ValueError("aegis_operation_id must be a safe opaque identifier")
    if not collector_id.startswith("c_"):
        raise ValueError("collector_id must be a collector ID")
    if not target_url.startswith(("https://", "http://")):
        raise ValueError("target_url must be an HTTP(S) URL")
    if not started_at_utc.endswith("Z"):
        raise ValueError("started_at_utc must be UTC with a Z suffix")
    datetime.fromisoformat(started_at_utc.removesuffix("Z") + "+00:00")
    if not operation_type.strip():
        raise ValueError("operation_type is required")
    if not correlation_id.strip():
        raise ValueError("correlation_id is required")
    for field_name, value in {
        "template_version": template_version,
        "provider_revision": provider_revision,
        "requested_version": requested_version,
        "selected_version": selected_version,
    }.items():
        if value is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
            raise ValueError(f"{field_name} must be a safe opaque identifier when provided")
    if version_evidence_source is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", version_evidence_source):
        raise ValueError("version_evidence_source must be an uppercase safe code when provided")
    if raw_response_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", raw_response_sha256):
        raise ValueError("raw_response_sha256 must be a lowercase SHA-256 digest when provided")
    return OperationCorrelationRecord(
        aegis_operation_id=aegis_operation_id,
        collector_id=collector_id,
        target_url_sha256=_target_url_hash(target_url),
        started_at_utc=started_at_utc,
        provider_run_id=provider_run_id,
        template_version=template_version,
        operation_type=operation_type,
        correlation_id=correlation_id,
        provider_revision=provider_revision,
        requested_version=requested_version,
        selected_version=selected_version,
        version_evidence_source=version_evidence_source,
        raw_response_sha256=raw_response_sha256,
    )


def append_correlation_record(directory: Path, record: OperationCorrelationRecord) -> Path:
    """Append exactly one immutable operation record without overwriting another."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.aegis_operation_id}.json"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_evidence_dict(), sort_keys=True, indent=2) + "\n")
    return path
