from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_executor import BenchmarkExecutor, GeminiDeveloperCaller
from aegis.benchmark_runner import BenchmarkRunner

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "benchmarks/configs/mission_011_validation_floor.json"
DEFAULT_EXECUTION_OUTPUT = "benchmarks/runs/mission_020_floor_2a80a8cf8d989326"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AEGIS benchmark validation and explicitly authorized execution boundary")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="frozen BenchmarkConfig JSON path",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate participants and print an unexecuted plan",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help="explicitly authorize the frozen benchmark execution boundary",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"benchmark artifact root; required with --run (default future root: {DEFAULT_EXECUTION_OUTPUT})",
    )
    return parser


def _blocked(message: str) -> int:
    print(
        json.dumps(
            {
                "status": "BLOCKED_NOT_READY",
                "notice": "NO BENCHMARK EXECUTED",
                "planned_runs": 180,
                "completed_runs": 0,
                "failed_runs": 0,
                "timed_out_runs": 0,
                "invalidated_runs": 0,
                "execution_authorized": False,
                "errors": [message],
            },
            sort_keys=True,
            indent=2,
        )
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.dry_run and not args.run:
        return _blocked("choose either --dry-run or --run; execution is never the default")
    if args.run and not args.output:
        return _blocked("--output is required with --run")

    config = load_benchmark_config(Path(args.config))
    if args.dry_run:
        result = BenchmarkRunner(config).dry_run()
        print(result.to_json(), end="")
        return 0 if result.status.value in {"VALIDATION_ONLY", "READY_TO_EXECUTE", "BLOCKED_NOT_READY"} else 2

    api_key = os.environ.get("GEMINI_API_KEY")
    model_caller = GeminiDeveloperCaller(api_key) if api_key else None
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    try:
        executor = BenchmarkExecutor(
            config,
            repository_root=ROOT,
            output_root=output_path,
            model_caller=model_caller,
        )
    except (OSError, ValueError) as exc:
        return _blocked(str(exc))
    summary = executor.execute()
    print(summary.to_json(), end="")
    return 0 if summary.status == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
