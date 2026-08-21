"""Write the provider-free Mission 056 lifecycle simulation once.

This script imports no provider transport and performs no network I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

from aegis.mission056_simulation import run_mission056_simulation


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "experiments" / "mission_056_full_scale_recovery" / "local_lifecycle_simulation.json"


def main() -> int:
    simulation = run_mission056_simulation()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(simulation, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(OUTPUT_PATH.relative_to(ROOT)), "provenance": simulation["provenance"], "provider_operations": simulation["provider_operations"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
