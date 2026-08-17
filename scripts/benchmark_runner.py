from __future__ import annotations

import argparse
from pathlib import Path

from aegis.benchmark_config import load_benchmark_config
from aegis.benchmark_runner import BenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AEGIS benchmark contract validator")
    parser.add_argument(
        "--config",
        default="benchmarks/configs/mission_011_validation_floor.json",
        help="frozen BenchmarkConfig JSON path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate participants and print an unexecuted plan",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run:
        raise SystemExit("Only --dry-run is implemented in Mission 012; benchmark execution is intentionally unavailable.")
    config = load_benchmark_config(Path(args.config))
    result = BenchmarkRunner(config).dry_run()
    print(result.to_json(), end="")
    return 0 if result.status.value in {"VALIDATION_ONLY", "READY_TO_EXECUTE", "BLOCKED_NOT_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
