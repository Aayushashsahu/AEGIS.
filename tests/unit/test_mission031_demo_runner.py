from pathlib import Path

from scripts.run_demo import run_demo


ROOT = Path(__file__).resolve().parents[2]


def test_default_demo_runner_prepares_replay_without_any_provider_operation() -> None:
    result = run_demo(ROOT)
    assert result["status"] == "REPLAY_READY"
    assert result["live_provider_invoked"] is False
    assert result["bright_data_create_operations"] == 0
    assert result["bright_data_run_operations"] == 0
    assert result["bright_data_heal_operations"] == 0
    assert result["production_commits"] == 0
    assert result["controlled_replay_mode"] == "TEST_DOUBLE_CONTROLLED_REPLAY"
    assert result["controlled_replay_output_eligible"] is False


def test_live_demo_mode_fails_closed_without_provider_execution() -> None:
    result = run_demo(ROOT, live=True)
    assert result["status"] == "BLOCKED_PROVIDER_AUTHORIZATION_REQUIRED"
    assert result["live_provider_invoked"] is False
    assert result["bright_data_heal_operations"] == 0
    assert result["approval_operations"] == 0
    assert result["production_commits"] == 0
