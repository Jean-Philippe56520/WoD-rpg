from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.lore_catalog import PARIS_CORPUS_SOURCES, corpus_audit_report, validate_source_catalog
from game.paris_corpus import CONFLICTS, paris_1435_audit_report, validate_paris_corpus
from game.paris_coverage import PARIS_CORPUS_AREAS, coverage_report, validate_paris_coverage
from game.paris_roster import (
    OPEN_ROSTER_GAPS,
    PARIS_1435_ROSTER,
    ROSTER_CONFLICTS,
    roster_audit_report,
    validate_paris_1435_roster,
)


def build_report(year: int = 1435) -> dict:
    validate_source_catalog()
    validate_paris_corpus()
    validate_paris_coverage()
    validate_paris_1435_roster()
    source_report = corpus_audit_report(year)
    paris_report = paris_1435_audit_report()
    area_report = coverage_report()
    roster_report = roster_audit_report()
    unresolved_sources = [
        {
            "key": source.key,
            "label": source.label,
            "audit_status": source.audit_status,
            "categories": list(source.categories),
        }
        for source in PARIS_CORPUS_SOURCES.values()
        if source.audit_status != "audited" and source.relevant_in(year)
    ]
    incomplete_areas = [
        {
            "id": area.id,
            "label": area.label,
            "coverage_status": area.coverage_status,
            "priority_1435": area.priority_1435,
            "engine_target": area.engine_target,
            "modern_only_guard": area.modern_only_guard,
            "source_keys": list(area.source_keys),
            "note": area.note,
        }
        for area in PARIS_CORPUS_AREAS
        if area.coverage_status != "structured"
    ]
    priority_1435_incomplete = [
        area for area in incomplete_areas if area["priority_1435"]
    ]
    roster_entries = [
        {
            "id": entry.id,
            "label": entry.label,
            "kind": entry.kind,
            "clan_id": entry.clan_id,
            "status": entry.status,
            "location": entry.location,
            "certainty": entry.certainty,
            "simulation_policy": entry.simulation_policy,
            "source_keys": list(entry.source_keys),
            "note": entry.note,
        }
        for entry in PARIS_1435_ROSTER
    ]
    return {
        "schema_version": 3,
        "year": year,
        "sources": source_report,
        "coverage": area_report,
        "paris_1435": paris_report,
        "roster_1435": roster_report,
        "roster_entries": roster_entries,
        "roster_open_gaps": list(OPEN_ROSTER_GAPS),
        "roster_conflicts": [
            {
                "id": conflict.id,
                "title": conflict.title,
                "source_keys": list(conflict.source_keys),
                "claims": list(conflict.claims),
                "preferred_interpretation": conflict.preferred_interpretation,
                "note": conflict.note,
            }
            for conflict in ROSTER_CONFLICTS
        ],
        "open_conflicts": [
            {
                "id": conflict.id,
                "title": conflict.title,
                "preferred_fact_id": conflict.preferred_fact_id,
                "fact_ids": list(conflict.fact_ids),
            }
            for conflict in CONFLICTS
        ],
        "unresolved_relevant_sources": unresolved_sources,
        "incomplete_coverage_areas": incomplete_areas,
        "priority_1435_incomplete": priority_1435_incomplete,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the WoD-rpg Paris lore coverage report")
    parser.add_argument("--year", type=int, default=1435)
    parser.add_argument("--output", default="lore-audit-report.json")
    args = parser.parse_args()

    report = build_report(args.year)
    output = Path(args.output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    sources = report["sources"]
    coverage = report["coverage"]
    paris = report["paris_1435"]
    roster = report["roster_1435"]
    print(
        f"Lore audit {args.year}: sources={sources['sources_total']} "
        f"audited={sources['audited']} relevant={sources['relevant_total']} "
        f"relevant_audited={sources['relevant_audited']}"
    )
    print(
        f"Coverage: areas={coverage['areas_total']} structured={coverage['structured']} "
        f"partial={coverage['partial']} indexed={coverage['indexed']} missing={coverage['missing']} "
        f"priority_1435_incomplete={coverage['priority_1435_incomplete']}"
    )
    print(
        f"Paris 1435: facts={paris['facts']} conflicts={paris['conflicts']} "
        f"presence={paris['presence_entries']} unverified={paris['unverified_presence']}"
    )
    print(
        f"Roster 1435: entries={roster['entries_total']} named={roster['named_total']} "
        f"collectives={roster['collective_total']} active_named={roster['simulation_active_named']} "
        f"open_gaps={roster['open_gaps']} conflicts={roster['roster_conflicts']}"
    )
    print(f"Report -> {output}")


if __name__ == "__main__":
    main()
