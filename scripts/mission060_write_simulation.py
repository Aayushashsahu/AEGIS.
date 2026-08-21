"""Write Mission 060 TEST_DOUBLE future-loop evidence without provider access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aegis.mission060_simulation import run_mission060_future_loop_simulation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(run_mission060_future_loop_simulation(), handle, sort_keys=True, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
