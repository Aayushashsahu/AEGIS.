"""Append-only correction for a derived Mission 048C dotted-field classification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from scripts.mission048c_evidence_preserving_rerun import MISSION_DIR, _field_state


def main() -> int:
    source = MISSION_DIR / "normalized_analysis.json"
    raw_path = MISSION_DIR / "raw_response.bin"
    output = MISSION_DIR / "normalized_analysis_correction.json"
    if output.exists():
        raise FileExistsError(output)
    analysis = json.loads(source.read_text(encoding="utf-8"))
    rows = analysis.get("decoded_rows")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], Mapping):
        raise RuntimeError("captured analysis does not contain a decoded provider row")
    states = {field: _field_state(rows[0], field) for field in ("input.url", "title", "price", "availability")}
    evidence: dict[str, Any] = {
        "schema_version": "mission-048c-normalized-analysis-correction-v1",
        "source_analysis": "normalized_analysis.json",
        "source_raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "correction": "The original derived analysis treated input.url as a literal top-level key. This append-only correction resolves dotted paths without altering raw evidence, decoded rows, verification, risk, or commit records.",
        "corrected_raw_field_states": states,
        "first_field_loss_point": analysis.get("first_field_loss_point"),
    }
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
