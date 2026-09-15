from game.paris_coverage import (
    PARIS_CORPUS_AREAS,
    REQUIRED_AREA_IDS,
    coverage_area,
    coverage_report,
    validate_paris_coverage,
)
from scripts.lore_audit_report import build_report


EXPECTED_MASTER_AREAS = {
    "history_timeline",
    "mortal_history",
    "characters",
    "lineages",
    "clans",
    "presence_location",
    "anarchs",
    "sabbat",
    "camarilla_institutions",
    "offices_power",
    "praxis_succession",
    "factions_coteries",
    "relationships",
    "prestations",
    "blood_bonds",
    "mortal_influences",
    "domains_territory",
    "historical_geography",
    "elysium_court_customs",
    "secrets_information",
    "events_incidents",
    "external_powers",
    "other_supernaturals",
    "character_chronologies",
    "office_chronologies",
    "npc_presence_chronology",
    "sun_calendar",
    "story_seeds",
}


def test_master_index_families_are_locked_as_a_coverage_contract():
    validate_paris_coverage()
    ids = {area.id for area in PARIS_CORPUS_AREAS}
    assert REQUIRED_AREA_IDS == EXPECTED_MASTER_AREAS
    assert EXPECTED_MASTER_AREAS <= ids


def test_no_required_family_is_completely_untracked():
    report = coverage_report()
    assert report["areas_total"] == len(EXPECTED_MASTER_AREAS)
    assert report["missing"] == 0
    assert report["structured"] > 0
    assert report["partial"] > 0
    assert report["indexed"] > 0


def test_every_1435_priority_family_has_a_source_anchor_and_engine_target():
    priority = [area for area in PARIS_CORPUS_AREAS if area.priority_1435]
    assert priority
    for area in priority:
        assert area.coverage_status != "missing"
        assert area.source_keys
        assert area.engine_target.strip()


def test_modern_material_is_explicitly_guarded_from_medieval_retroprojection():
    guarded = {
        area.id for area in PARIS_CORPUS_AREAS if area.modern_only_guard
    }
    assert {
        "sabbat",
        "office_chronologies",
        "prestations",
        "blood_bonds",
        "mortal_influences",
        "domains_territory",
        "elysium_court_customs",
        "secrets_information",
        "story_seeds",
    } <= guarded


def test_critical_1435_gaps_remain_visible_instead_of_being_marked_complete():
    assert coverage_area("characters").coverage_status == "partial"
    assert coverage_area("lineages").coverage_status == "partial"
    assert coverage_area("anarchs").coverage_status == "partial"
    assert coverage_area("blood_bonds").coverage_status == "indexed"
    assert coverage_area("external_powers").coverage_status == "partial"
    assert coverage_area("npc_presence_chronology").coverage_status == "indexed"


def test_lore_audit_report_lists_priority_1435_gaps_by_name():
    report = build_report(1435)
    assert report["schema_version"] == 3
    assert report["coverage"]["areas_total"] == len(EXPECTED_MASTER_AREAS)
    assert report["roster_1435"]["entries_total"] > 0
    incomplete_ids = {item["id"] for item in report["priority_1435_incomplete"]}
    assert "characters" in incomplete_ids
    assert "blood_bonds" in incomplete_ids
    assert "external_powers" in incomplete_ids
    assert "historical_geography" in incomplete_ids
    assert "history_timeline" not in incomplete_ids
