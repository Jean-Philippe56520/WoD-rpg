from dataclasses import replace

from game.chronicle_simulation import grant_boon, initial_simulation
from game.lore_sources import PARIS_BY_NIGHT_ROOT, lore_source
from game.paris_lore import CANONICAL_PRESSURES, paris_npc_seed
from game.paris_simulation import LEGACY_EXTRA_IDS, advance_paris_simulation, parisify_simulation


def _relations_snapshot(state):
    return {npc_id: dict(npc.relations) for npc_id, npc in state.npcs.items()}


def test_paris_by_night_is_a_registered_recurring_lore_source():
    assert PARIS_BY_NIGHT_ROOT.url == "https://parisbynight.quelquesmots.fr/"
    assert PARIS_BY_NIGHT_ROOT.tier == "B"
    assert "récurrente" in PARIS_BY_NIGHT_ROOT.note
    assert "François Villon" in lore_source("francois_villon").label
    assert lore_source("violetta").url.endswith("/Violetta")


def test_villon_and_violetta_use_vampire_chronology_not_mortal_poet_dates():
    villon = paris_npc_seed("npc_villon")
    violetta = paris_npc_seed("npc_violetta")

    assert villon.clan_id == "toreador"
    assert villon.birth_year == 1197
    assert villon.embraced_year == 1230
    assert villon.generation == 5
    assert villon.role_1435 != "Prince de Paris"

    assert violetta.embraced_year == 1250
    assert violetta.generation == 6
    assert violetta.sire_id == "npc_villon"


def test_henri_le_preux_is_not_treated_as_physically_present_in_paris_in_1435():
    henri = paris_npc_seed("npc_henri_preux")
    assert henri.location_1435 == "Bourges"

    state = parisify_simulation(initial_simulation("paris-locality"))
    _, beats = advance_paris_simulation(
        state,
        year=1435,
        chapter=1,
        segment=1,
        characters=[],
    )

    assert beats
    assert all(beat.actor_id != "npc_henri_preux" for beat in beats)


def test_paris_seed_replaces_only_the_legacy_default_prince():
    state = parisify_simulation(initial_simulation("paris-seed"))

    assert state.offices["prince"] == "npc_alexandre"
    assert state.domains["domain_citadelle"].holder_id == "npc_alexandre"
    assert state.npcs["npc_alexandre"].role == "Prince de Paris"
    assert "npc_villon" in state.npcs
    assert "npc_beatrix" in state.npcs
    assert not (LEGACY_EXTRA_IDS & set(state.npcs))

    custom = initial_simulation("paris-custom-prince")
    custom = replace(custom, offices={"prince": "pc-custom"})
    custom = parisify_simulation(custom)
    assert custom.offices["prince"] == "pc-custom"


def test_paris_migration_keeps_legacy_actor_when_persistent_state_still_references_it():
    state = initial_simulation("paris-legacy-ref")
    state = grant_boon(
        state,
        creditor_id="npc_prince_godefroy",
        debtor_id="sire_ventrue_aymon",
        level="minor",
        origin="Dette antérieure à V0.43",
    )

    migrated = parisify_simulation(state)

    assert migrated.offices["prince"] == "npc_alexandre"
    assert "npc_prince_godefroy" in migrated.npcs
    assert any(boon.creditor_id == "npc_prince_godefroy" for boon in migrated.boons.values())


def test_autonomous_paris_actions_change_real_social_state_not_only_agenda_progress():
    state = parisify_simulation(initial_simulation("paris-social"))
    before_relations = _relations_snapshot(state)
    before_boons = dict(state.boons)
    before_rights = dict(state.hunting_rights)

    advanced, beats = advance_paris_simulation(
        state,
        year=1435,
        chapter=1,
        segment=1,
        characters=[],
    )

    assert len(beats) >= 4
    assert (
        _relations_snapshot(advanced) != before_relations
        or advanced.boons != before_boons
        or advanced.hunting_rights != before_rights
    )
    assert any(
        beat.category in {"alliance_building", "political_rivalry", "prestation", "political_patronage", "hunting_patronage"}
        for beat in beats
    )


def test_reference_future_is_pressure_data_not_an_automatic_death_script():
    pressure = next(item for item in CANONICAL_PRESSURES if item.id == "pressure_alexandre_1481")
    assert pressure.around_year == 1481
    assert pressure.required_state
    assert pressure.possible_divergences

    state = parisify_simulation(initial_simulation("paris-divergence", year=1481))
    assert state.npcs["npc_alexandre"].alive is True
    assert state.offices["prince"] == "npc_alexandre"
