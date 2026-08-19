#!/usr/bin/env python3
"""Run one bounded, redacted Mission 033 Bright Data CLI operation.

The command driver is deliberately narrow. It records the exact CLI argv,
timing, and redacted output for one create, run, or heal operation, enforces
the owner-approved budget, and contains no approval, commit, rollback,
benchmark, NVIDIA, or Gemini capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MISSION_DIR = ROOT / "experiments" / "mission_033_live_bright_data_success"
LEDGER_PATH = MISSION_DIR / "operation_ledger.json"
OPERATION_DIR = MISSION_DIR / "provider_operations"
ALLOWED_COUNTS = {"create": 1, "run": 2, "heal": 1}
TIMEOUT_SECONDS = {"create": 1800, "run": 900, "heal": 900}
SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|token|password|secret)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(r"\b(?:sk|nvapi|bdapi|bearer)[_-]?[A-Za-z0-9._-]{12,}\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SECRET_KEY_RE.search(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(value), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def operation_key(operation: str) -> str:
    return f"bright_data_collector_{operation}"


def existing_operation_count(ledger: dict[str, Any], operation: str) -> int:
    return int(ledger["counts"].get(operation_key(operation), 0))


def assert_budget(ledger: dict[str, Any], operation: str) -> None:
    if operation not in ALLOWED_COUNTS:
        raise ValueError(f"Unsupported operation: {operation}")
    if existing_operation_count(ledger, operation) >= ALLOWED_COUNTS[operation]:
        raise RuntimeError(f"Mission 033 {operation} budget exhausted; refusing provider invocation.")


def build_command(
    *,
    operation: str,
    collector_id: str | None,
    target_url: str,
    description_or_prompt: str | None,
) -> list[str]:
    command = ["npx", "-p", "@brightdata/cli", "bdata", "--timing", "scraper", operation]
    if operation == "create":
        if not description_or_prompt:
            raise ValueError("Create requires a data-extraction description.")
        return [*command, target_url, description_or_prompt, "--name", "aegis-mission-033-v1", "--json"]
    if not collector_id:
        raise ValueError(f"{operation} requires a collector ID.")
    if operation == "run":
        return [*command, collector_id, target_url, "--timeout", "600", "--json"]
    if operation == "heal":
        if not description_or_prompt:
            raise ValueError("Heal requires a compact repair prompt.")
        if len(description_or_prompt) > 1000:
            raise ValueError("Heal prompt exceeds Bright Data's documented 1000-character limit.")
        return [
            *command,
            collector_id,
            description_or_prompt,
            "--url",
            target_url,
            "--timeout",
            "900",
            "--max-retries",
            "0",
            "--json",
        ]
    raise ValueError(f"Unsupported operation: {operation}")


def parse_output(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"unparsed_text": stripped}


def run_operation(
    *,
    operation: str,
    collector_id: str | None,
    target_url: str,
    description_or_prompt: str | None,
    execute: bool,
) -> dict[str, Any]:
    if not execute:
        raise RuntimeError("Provider execution is disabled unless --execute is supplied explicitly.")
    ledger = load_json(LEDGER_PATH)
    assert_budget(ledger, operation)
    command = build_command(
        operation=operation,
        collector_id=collector_id,
        target_url=target_url,
        description_or_prompt=description_or_prompt,
    )
    if "--auto-approve" in command or "approve" in command:
        raise RuntimeError("Approval capability is forbidden for Mission 033.")
    started_at = utc_now()
    started_monotonic = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS[operation],
        )
        timed_out = False
        stdout, stderr, returncode = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = None
    elapsed_ms = round((time.monotonic() - started_monotonic) * 1000)
    operation_id = f"operation_{existing_operation_count(ledger, operation) + 1:03d}_{operation}"
    output = parse_output(stdout)
    result = {
        "schema_version": "mission-033-provider-operation-v1",
        "operation_id": operation_id,
        "operation": f"bright_data_collector_{operation}",
        "status": "TIMED_OUT" if timed_out else ("COMPLETED" if returncode == 0 else "FAILED"),
        "started_at": started_at,
        "completed_at": utc_now(),
        "elapsed_ms": elapsed_ms,
        "command": command,
        "command_sha256": hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest(),
        "target_url": target_url,
        "collector_id": collector_id,
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": output,
        "stderr": stderr.strip(),
        "prompt_sha256": (
            hashlib.sha256(description_or_prompt.encode("utf-8")).hexdigest()
            if operation == "heal" and description_or_prompt
            else None
        ),
        "prompt_length": len(description_or_prompt) if operation == "heal" and description_or_prompt else None,
        "auto_approval_used": False,
        "provider_approval_executed": False,
        "production_commit_executed": False,
    }
    OPERATION_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OPERATION_DIR / f"{operation_id}.json", result)
    ledger["counts"][operation_key(operation)] = existing_operation_count(ledger, operation) + 1
    ledger["updated_at"] = result["completed_at"]
    ledger.setdefault("records", []).append(
        {
            "operation": result["operation"],
            "operation_id": operation_id,
            "status": result["status"],
            "elapsed_ms": elapsed_ms,
            "artifact": f"provider_operations/{operation_id}.json",
        }
    )
    write_json(LEDGER_PATH, ledger)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute one bounded Mission 033 Bright Data CLI operation")
    parser.add_argument("operation", choices=sorted(ALLOWED_COUNTS))
    parser.add_argument("--collector-id")
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--text", help="Extraction description for create or repair prompt for heal")
    parser.add_argument("--execute", action="store_true", help="Required explicit opt-in for the external provider call")
    args = parser.parse_args()
    result = run_operation(
        operation=args.operation,
        collector_id=args.collector_id,
        target_url=args.target_url,
        description_or_prompt=args.text,
        execute=args.execute,
    )
    print(json.dumps(redact(result), sort_keys=True, indent=2))
    return 0 if result["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
