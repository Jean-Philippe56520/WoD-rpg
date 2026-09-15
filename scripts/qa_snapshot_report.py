from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from game.editable_repository import EditableSQLiteGameRepository
from game.qa_scenarios import QA_SCENARIOS, ensure_qa_scenario, qa_snapshot


def build_report() -> dict:
    scenarios: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="wod-rpg-qa-") as directory:
        root = Path(directory)
        for scenario in QA_SCENARIOS:
            repository = EditableSQLiteGameRepository(root / f"{scenario.id}.sqlite3")
            ensure_qa_scenario(repository, scenario.id)
            scenarios.append(qa_snapshot(repository, scenario.id))
    return {
        "schema_version": 1,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic WoD-rpg QA snapshots")
    parser.add_argument("--output", default="qa-report.json")
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QA report: {report['scenario_count']} scenarios -> {output}")
    for scenario in report["scenarios"]:
        character = scenario["character"]
        print(
            f"- {scenario['scenario']['id']}: {character['clan']} | "
            f"hunger={character['hunger']} | night={character['local_night']} | "
            f"situations={len(scenario['situations'])} | prince={scenario['world']['prince_id']}"
        )


if __name__ == "__main__":
    main()
