from game.chronicle import CHRONICLE_GAME_ID, CLAN_DISCIPLINES, ChronicleProgress, create_player_character
from game.chronicle_simulation import initial_simulation, simulation_from_dict, simulation_to_dict
from game.paris_simulation import parisify_simulation
from game.relationship_memory import (
    events_from_history,
    memory_for,
    prestation_balance,
    record_relationship_memory,
    relationship_difficulty_adjustment,
)
from game.situations import generate_situations, resolve_situation
from game.vampire_profile import default_profile


def make_character():
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-v044",
        player_name="Joueur",
        character_id="pc-v044",
        name="Jehan",
        clan_id="toreador",
        concept="Copiste",
        starting_discipline=CLAN_DISCIPLINES["toreador"][0],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="",
        chapter_goal="",
        progress=progress,
    )


def test_sire_memory_has_backward_compatible_baseline_without_migration():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)

    memory = memory_for(state, character.sire_id, character)

    assert memory is not None
    assert memory.trust == character.sire_relation - 1
    assert memory.last_interaction_year is None
    assert "Lien : sire" in memory.known_facts


def test_relational_dimensions_persist_inside_existing_simulation_json():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)
    state = record_relationship_memory(
        state,
        character,
        character.sire_id,
        year=1435,
        disposition_delta=2,
        trust_delta=2,
        respect_delta=2,
    )

    loaded = simulation_from_dict(simulation_to_dict(state))
    memory = memory_for(loaded, character.sire_id, character)

    assert memory is not None
    assert memory.disposition == 2
    assert memory.trust == 3
    assert memory.respect == 2
    assert memory.last_interaction_year == 1435
    assert relationship_difficulty_adjustment(loaded, character.sire_id, character) == -1


def test_grievances_and_hostility_make_future_social_exchange_harder():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)
    for _ in range(2):
        state = record_relationship_memory(
            state,
            character,
            character.sire_id,
            year=1435,
            disposition_delta=-2,
            trust_delta=-2,
            grievance=True,
        )

    memory = memory_for(state, character.sire_id, character)

    assert memory is not None
    assert memory.grievance_count == 2
    assert memory.disposition == -3
    assert memory.trust == -3
    assert relationship_difficulty_adjustment(state, character.sire_id, character) == 1


def test_prestation_balance_is_derived_from_boon_ledger_not_duplicated_memory():
    from game.chronicle_simulation import grant_boon

    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)
    state = grant_boon(
        state,
        creditor_id=character.character_id,
        debtor_id=character.sire_id,
        level="major",
        origin="Service politique",
    )

    assert prestation_balance(state, character.sire_id, character.character_id) == -2


def test_paris_political_situation_targets_current_prince_not_legacy_godefroy():
    character = make_character()
    profile = default_profile(character)
    state = parisify_simulation(initial_simulation(CHRONICLE_GAME_ID))

    political = next(
        situation
        for situation in generate_situations(character, profile, state, year=1435)
        if situation.id == "political_current"
    )

    assert state.offices["prince"] == "npc_alexandre"
    assert political.source_actor_id == "npc_alexandre"


def test_resolving_visible_social_action_records_actor_and_memory_history_tags():
    character = make_character()
    profile = default_profile(character)
    state = parisify_simulation(initial_simulation(CHRONICLE_GAME_ID))
    sire_situation = next(
        situation
        for situation in generate_situations(character, profile, state, year=1435)
        if situation.id == "sire_accounting"
    )

    resolution = resolve_situation(
        character,
        profile,
        state,
        sire_situation,
        "obey",
        nights_per_segment=3,
    )

    actor_tag = f"actor:{character.sire_id}"
    assert actor_tag in resolution.outcome.tags
    assert "relation:sire_service" in resolution.outcome.tags
    memory = memory_for(resolution.simulation, character.sire_id, character)
    assert memory is not None
    assert memory.last_interaction_year == 1435

    history = [
        {
            "chapter": character.chapter,
            "segment": character.segment,
            "night_number": character.local_night,
            "action": resolution.outcome.action.value,
            "outcome_json": {
                "summary": resolution.outcome.summary,
                "detail": resolution.outcome.detail,
                "tags": list(resolution.outcome.tags),
            },
        }
    ]
    events = events_from_history(history, character.sire_id)
    assert len(events) == 1
    assert events[0].category == "sire_service"


def test_favorable_memory_reduces_actual_social_difficulty():
    character = make_character()
    profile = default_profile(character)
    state = parisify_simulation(initial_simulation(CHRONICLE_GAME_ID))
    state = record_relationship_memory(
        state,
        character,
        character.sire_id,
        year=1435,
        disposition_delta=2,
        trust_delta=2,
        respect_delta=2,
    )
    sire_situation = next(
        situation
        for situation in generate_situations(character, profile, state, year=1435)
        if situation.id == "sire_accounting"
    )
    choice = next(choice for choice in sire_situation.choices if choice.id == "obey")

    resolution = resolve_situation(
        character,
        profile,
        state,
        sire_situation,
        choice.id,
        nights_per_segment=3,
    )

    assert choice.difficulty == 2
    assert resolution.dice.difficulty == 1
    assert "confiance acquise" in resolution.outcome.detail
