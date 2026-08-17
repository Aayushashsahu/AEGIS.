from __future__ import annotations

from pathlib import Path

from aegis.mutation_metrics import build_mission009_dataset, calculate_metrics, export_manifest


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"
GENERATED = ROOT / "docs" / "generated"


def main() -> None:
    runs, truths = build_mission009_dataset()
    manifest = export_manifest(runs, truths)
    report = calculate_metrics(runs, truths)
    EXPERIMENTS.mkdir(parents=True, exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    (EXPERIMENTS / "AEGIS-MISSION-010-MUTATION-MANIFEST.json").write_text(manifest, encoding="utf-8")
    (EXPERIMENTS / "AEGIS-MISSION-010-METRICS.json").write_text(report.to_json(), encoding="utf-8")
    (GENERATED / "mission_010_metrics.md").write_text(report.to_markdown(), encoding="utf-8")


if __name__ == "__main__":
    main()
