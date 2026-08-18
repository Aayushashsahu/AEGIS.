#!/usr/bin/env python3
"""Derive corrected collection metadata from the preserved raw CLI envelope only."""

from __future__ import annotations

import json
import re
from pathlib import Path

from aegis.audit_store import _redact, _to_jsonable


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(_redact(_to_jsonable(value)), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "experiments" / "mission_029"
    operation = json.loads((evidence / "provider_operations" / "operation_002.json").read_text(encoding="utf-8"))
    original_handle = json.loads((evidence / "collection_handle.json").read_text(encoding="utf-8"))
    original_summary = json.loads((evidence / "collection_summary.json").read_text(encoding="utf-8"))
    trace = f"{operation.get('stdout', '')}\n{operation.get('stderr', '')}"
    response = re.search(r"response_id:\s*([^\s)]+)", trace)
    batch = re.search(r"Batch job:\s*(j_[A-Za-z0-9]+)", trace)
    if "switching to batch mode" not in trace.lower() or response is None or batch is None:
        raise RuntimeError("preserved raw CLI trace does not prove the expected batch fallback")
    corrected_ids = {"response_id": response.group(1), "batch_job_id": batch.group(1)}
    reconciled_handle = {**original_handle, "mode": "BATCH", "provider_operation_ids": corrected_ids}
    reconciled_summary = {**original_summary, "mode": "BATCH", "provider_operation_ids": corrected_ids}
    correction = {
        "correction_id": "mission029_collection_metadata_from_stderr_v1",
        "source_artifact": "provider_operations/operation_002.json",
        "reason": "The initial adapter release parsed realtime-to-batch fallback only from stdout, while the live CLI emitted it on stderr.",
        "original_mode": original_handle.get("mode"),
        "corrected_mode": "BATCH",
        "corrected_provider_operation_ids": corrected_ids,
        "provider_operations_executed_by_correction": 0,
    }
    write_json(evidence / "collection_handle_reconciled.json", reconciled_handle)
    write_json(evidence / "collection_summary_reconciled.json", reconciled_summary)
    write_json(evidence / "collection_metadata_correction.json", correction)
    print(json.dumps(correction, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
