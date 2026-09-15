from game.chronicle_simulation import initial_simulation
from game.lore_catalog import (
    PARIS_CORPUS_SOURCES,
    corpus_audit_report,
    lore_source,
    validate_source_catalog,
)
from game.paris_corpus import (
    CONFLICTS,
    FACTS,
    FACT_BY_ID,
    PARIS_1435_FACTION_PRESENCE,
    PARIS_1435_PRESENCE,
    facts_for,
    paris_1435_audit_report,
    presence_for,
    validate_paris_corpus,
)
from game.paris_lore import PARIS_1435_FACTIONS, paris_npc_seed
from game.paris_simulation import parisify_simulation


def test_source_catalog_is_structured_and_valid():
    validate_source_catalog()
    assert len(PARIS_CORPUS_SOURCES) >= 20
    assert lore_source("chronologie").audit_status == "audited"
    assert "timeline" in lore_source("chronologie").categories
    assert lore_source("us_coutumes").relevant_from == 1804
    assert lore_source("alexandre").official_refs
    assert all("/index.php/index.php?" not in source.url for source in PARIS_CORPUS_SOURCES.values())


def test_corpus_report_exposes_remaining_audit_work():
    report = corpus_audit_report(1435)
    assert report["sources_total"] >= 20
    assert report["audited"] > 0
    assert report["partial"] > 0
    assert report["linked_unverified"] > 0
    assert report["relevant_audited"] <= report["relevant_total"]


def test_every_external_fact_has_a_registered_source_and_no_simulation_scores_leak_into_lore():
    validate_paris_corpus()
    simulation_only_predicates = {
        "loyalty",
        "aggression",
        "influence",
        "status_score",
        "ambition",
        "short_goal",
        "active_plan",
        "relations",
    }
    for fact in FACTS:
        if fact.tier in {"A", "B"}:
            assert fact.source_keys
            assert all(key in PARIS_CORPUS_SOURCES for key in fact.source_keys)
        assert fact.predicate not in simulation_only_predicates


def test_saviarre_lineage_is_recorded_per_fact_and_seed_is_aligned():
    facts = facts_for("npc_saviarre", 1435)
    assert any(fact.predicate == "clan" and fact.value == "ventrue" for fact in facts)
    assert any(fact.predicate == "embraced_year" and fact.value == 481 for fact in facts)

    seed = paris_npc_seed("npc_saviarre")
    assert seed.clan_id == "ventrue"
    assert seed.generation == 5
    assert seed.sire_id == "npc_alexandre"


def test_court_of_miracles_keeps_sourced_clans_without_inventing_named_leaders():
    faction = next(item for item in PARIS_1435_FACTION_PRESENCE if item.id == "faction_court_miracles")
    assert set(faction.member_clans) == {"brujah", "malkavian", "gangrel", "nosferatu"}
    assert faction.member_ids == ()

    legacy_seed = next(item for item in PARIS_1435_FACTIONS if item.id == "faction_court_miracles")
    assert set(legacy_seed.member_clans) == set(faction.member_clans)


def test_uncertain_1435_actors_are_indexed_but_not_injected_as_false_certainties():
    childeberd = presence_for("npc_childeberd")
    tremere = presence_for("collective_tremere_paris")
    assert childeberd.status_1435 == "unverified"
    assert tremere.status_1435 == "unverified"
    assert childeberd.inject_into_simulation is False
    assert tremere.inject_into_simulation is False

    state = parisify_simulation(initial_simulation("v047a-audit"))
    assert "npc_childeberd" not in state.npcs
    assert "collective_tremere_paris" not in state.npcs


def test_known_source_conflicts_are_preserved_instead_of_silently_overwritten():
    conflicts = {item.id: item for item in CONFLICTS}
    violetta = conflicts["violetta_justicar_timing"]
    assert violetta.preferred_fact_id == "violetta_justicar_1666"
    assert set(violetta.fact_ids) == {"violetta_justicar_pbn_early", "violetta_justicar_1666"}
    assert FACT_BY_ID["violetta_justicar_pbn_early"].tier == "B"
    assert FACT_BY_ID["violetta_justicar_1666"].tier == "A"

    camarilla = conflicts["camarilla_consolidation_timing"]
    assert "camarilla_effective_pbn_1444" in camarilla.fact_ids
    assert "camarilla_conclave_model_1486" in camarilla.fact_ids


def test_reference_future_facts_do_not_become_runtime_death_flags():
    destruction = FACT_BY_ID["alexandre_reference_destruction"]
    assert destruction.value == 1481
    assert destruction.reference_only is True

    state = parisify_simulation(initial_simulation("v047a-divergence", year=1481))
    assert state.npcs["npc_alexandre"].alive is True


def test_1435_audit_report_counts_confirmed_and_unverified_presence():
    report = paris_1435_audit_report()
    assert report["facts"] >= 20
    assert report["conflicts"] >= 2
    assert report["factions"] >= 3
    assert report["confirmed_or_high_presence"] > 0
    assert report["unverified_presence"] >= 2


def test_presence_registry_does_not_duplicate_entities():
    entity_ids = [item.entity_id for item in PARIS_1435_PRESENCE]
    assert len(entity_ids) == len(set(entity_ids))
