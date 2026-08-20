from __future__ import annotations

from time import monotonic

from aegis.adapter import BrightDataCliAdapter, CommandResult, subprocess_runner


def test_subprocess_runner_terminates_a_stalled_local_process_group() -> None:
    started = monotonic()
    result = subprocess_runner(("sh", "-c", "exec sleep 10"), timeout_seconds=0.05)
    elapsed = monotonic() - started

    assert result.returncode == 124
    assert "bounded timeout" in result.stderr
    assert elapsed < 3


def test_default_adapter_runner_applies_the_lifecycle_deadline() -> None:
    with BrightDataCliAdapter() as adapter:
        result = adapter._run_with_timeout(("sh", "-c", "exec sleep 10"), timeout_seconds=0.05)

    assert result.returncode == 124
    assert "bounded timeout" in result.stderr
