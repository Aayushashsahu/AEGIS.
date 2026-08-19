from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import mission033_live_operation as operation


def test_create_command_is_documented_and_bounded() -> None:
    command = operation.build_command(
        operation="create",
        collector_id=None,
        target_url="https://example.test/target",
        description_or_prompt="Extract title, price, availability.",
    )

    assert command[:6] == ["npx", "-p", "@brightdata/cli", "bdata", "--timing", "scraper"]
    assert command[6] == "create"
    assert "--name" in command
    assert "--auto-approve" not in command


def test_heal_command_disables_retries_and_auto_approval() -> None:
    command = operation.build_command(
        operation="heal",
        collector_id="c_demo",
        target_url="https://example.test/target",
        description_or_prompt="The price field is missing. Restore the existing price field.",
    )

    assert command[6] == "heal"
    assert command[command.index("--max-retries") + 1] == "0"
    assert "--auto-approve" not in command
    assert "approve" not in command


def test_heal_rejects_prompt_over_documented_limit() -> None:
    with pytest.raises(ValueError, match="1000-character"):
        operation.build_command(
            operation="heal",
            collector_id="c_demo",
            target_url="https://example.test/target",
            description_or_prompt="x" * 1001,
        )


def test_budget_refuses_an_over_budget_provider_operation() -> None:
    ledger = {"counts": {"bright_data_collector_create": 1}}

    with pytest.raises(RuntimeError, match="budget exhausted"):
        operation.assert_budget(ledger, "create")


def test_driver_requires_explicit_execution_and_redacts_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_path = tmp_path / "operation_ledger.json"
    ledger_path.write_text(json.dumps({"counts": {"bright_data_collector_create": 0}, "records": []}), encoding="utf-8")
    monkeypatch.setattr(operation, "LEDGER_PATH", ledger_path)
    monkeypatch.setattr(operation, "OPERATION_DIR", tmp_path / "provider_operations")

    with pytest.raises(RuntimeError, match="--execute"):
        operation.run_operation(
            operation="create",
            collector_id=None,
            target_url="https://example.test/target",
            description_or_prompt="Extract title.",
            execute=False,
        )

    assert operation.redact("Bearer sk-exampletokenmaterial123456") == "Bearer [REDACTED]"
