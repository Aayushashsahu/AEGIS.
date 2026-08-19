"""Provider-free integrity gate for the immutable evidence the webapp projects."""
from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = {
    "benchmarks/runs/mission_028_recovery_floor_4812160675146552/execution_log.json": "caf0308a833eb37e514a1bb500118181eb0b1e9e82140c4643f8c16f0e7e6968",
    "benchmarks/runs/mission_028_recovery_floor_4812160675146552/reports/mission-022-metric-boundary-compatibility.json": "f93a3757aa2a0cd0263ae42868de83c6ab8fc9d20f67fb8d565cde0c44fadfe3",
    "experiments/mission_029/demo_manifest.json": "6baf17f45a5dee21d5dfd65f6b43c021f1b52556a957883af9fbc8bd61a72bf9",
    "experiments/mission_029/repair_request.json": "8f1e355fdb12f3c4e8a7e173ad149ce2a85d778ddb14cb76c9087ea9a162e58d",
    "experiments/mission_029/pipeline_termination.json": "3671ba1dc2632775128a8248290cef76948afcb825331f0b7f50067e52b34407",
    "experiments/mission_030/live_heal_result.json": "b97d0fada4f6c272def4d16d2072c7d407804cd2ad18329b2c156e69307dffc9",
    "experiments/mission_030/provider_operations/operation_001.json": "90eaedfadafdead567289345e6e5ac62369bb01a7981eb1fb94871b95d17df3a",
    "experiments/mission_031/demo_session.json": "25e0edcd5eab8f797f7bc60c509c4f9750b7cd9d2452755c51c02cef5d43eb9a",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    mismatches: list[str] = []
    for relative_path, expected in EXPECTED_SHA256.items():
        path = ROOT / relative_path
        actual = digest(path) if path.is_file() else "MISSING"
        if actual != expected:
            mismatches.append(f"{relative_path}: expected {expected}, got {actual}")
    if (ROOT / "webapp" / "aegis_backend").exists():
        mismatches.append("webapp/aegis_backend must not exist; canonical root is the only AEGIS source of truth")
    if mismatches:
        raise SystemExit("Evidence integrity gate failed:\n" + "\n".join(mismatches))
    print(f"Validated {len(EXPECTED_SHA256)} immutable canonical evidence artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
