"""Append-only, redaction-safe metadata for exact provider response mirrors.

This module contains no network or provider execution code. Callers retain
their own raw bytes in explicitly approved evidence paths before parsing; this
helper only validates the evidence boundary and refuses to persist content that
appears credential-like.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path


_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SECRET_LIKE_VALUE = re.compile(r"\b(?:sk|nvapi|bdapi|bearer)[_-]?[A-Za-z0-9._-]{12,}\b", re.IGNORECASE)


@dataclass(frozen=True)
class RawResponseMirror:
    """Safe metadata for a one-time raw response mirror; never includes bytes."""

    aegis_operation_id: str
    correlation_id: str
    sha256: str
    byte_count: int
    persisted: bool
    path: str | None
    secret_like_content: bool
    schema_version: str = "raw-response-mirror-v1"

    def to_evidence_dict(self) -> dict[str, object]:
        return asdict(self)


def preserve_raw_response_once(
    raw_response: bytes,
    *,
    path: Path,
    aegis_operation_id: str,
    correlation_id: str,
) -> RawResponseMirror:
    """Persist exact bytes once before decoding, or fail closed on secret-like data.

    The caller chooses a predeclared controlled path. Existing paths are never
    overwritten. No response value is copied into returned metadata.
    """

    if not _SAFE_ID.fullmatch(aegis_operation_id):
        raise ValueError("aegis_operation_id must be a safe opaque identifier")
    if not correlation_id.strip():
        raise ValueError("correlation_id is required")
    if not isinstance(raw_response, bytes):
        raise TypeError("raw_response must be bytes")
    digest = hashlib.sha256(raw_response).hexdigest()
    secret_like = bool(_SECRET_LIKE_VALUE.search(raw_response.decode("utf-8", errors="ignore")))
    if secret_like:
        return RawResponseMirror(
            aegis_operation_id=aegis_operation_id,
            correlation_id=correlation_id,
            sha256=digest,
            byte_count=len(raw_response),
            persisted=False,
            path=None,
            secret_like_content=True,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw_response)
    return RawResponseMirror(
        aegis_operation_id=aegis_operation_id,
        correlation_id=correlation_id,
        sha256=digest,
        byte_count=len(raw_response),
        persisted=True,
        path=str(path),
        secret_like_content=False,
    )
