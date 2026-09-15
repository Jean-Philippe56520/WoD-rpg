from dataclasses import replace

import pytest

from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, PoliticalOffice, create_player_character
from game.chronicle_politics import (
    actor_offices,
    assign_office,
    political_actor,
    primary_office,
    validate_political_state,
)
from game.chronicle_simulation import ensure_character_links, grant_boon, initial_simulation
from game.era import era_for_year


def make_character(*, character_id="pc-v041", clan_id="brujah", office="none"):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=f"player-{character_id}",
        player_name="Joueur",
        character_id=character_id,
        name="Jehan",
        clan_id=clan_id,
        concept="Érudit",
        starting_discipline={
            "brujah": "Présence",
            "toreador": "Auspex",
            "ventrue": "Domination",
        }[clan_id],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="",
        chapter_goal="",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
        sire_id={
            "brujah": "sire_brujah_guilhem",
            "toreador": "sire_toreador_isabeau",
            "ventrue": "sire_ventrue_aymon",
        }[clan_id],
        sire_name={
            "brujah": "Guilhem d'Aquitaine",
            "toreador": "Isabeau de Valois",
            "ventrue": "Aymon de Montfort",
        }[clan_id],
    ) if office == "none" else replace(
        create_player_character(
            game_id=CHRONICLE_GAME_ID,
            player_id=f"player-{character_id}",
            player_name="Joueur",
            character_id=character_id,
            name="Jehan",
            clan_id=clan_id,
            concept="Érudit",
            starting_discipline={
                "brujah": "Présence",
                "toreador": "Auspex",
                "ventrue": "Domination",
            }[clan_id],
            mortal_stance="humanist",
            order_stance="orthodox",
            long_term_goal="",
            chapter_goal="",
            progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
            sire_id={
                "brujah": "sire_brujah_guilhem",
                "toreador": "sire_toreador_isabeau",
                "ventrue": "sire_ventrue_aymon",
            }[clan_id],
            sire_name={
                "brujah": "Guilhem d'Aquitaine",
                "toreador": "Isabeau de Valois",
                "ventrue": "Aymon de Montfort",
            }[clan_id],
        ),
        office=office,
    )


def test_political_actor_unifies_player_and_npc_read_model_without_copying_player():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)

    player = political_actor(state, [character], character.character_id)
    prince = political_actor(state, [character], "npc_prince_godefroy")

    assert player.source == "player"
    assert player.name == character.name
    assert player.influence == character.personal_influence
    assert prince.source == "npc"
    assert prince.name == "Godefroy de Brienne"


def test_player_character_office_field_is_not_canonical_anymore():
    character = make_character(office=PoliticalOffice.PRINCE.value)
    state = initial_simulation(CHRONICLE_GAME_ID)

    assert primary_office(state, character.character_id) == PoliticalOffice.NONE.value
    assert state.offices["prince"] == "npc_prince_godefroy"


def test_domain_holder_is_derived_from_real_domain_ownership():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)
    domains = dict(state.domains)
    domain = domains["domain_faubourgs"]
    domains[domain.id] = replace(domain, holder_id=character.character_id)
    state = replace(state, domains=domains)

    validate_political_state(state, [character], era_for_year(1435))

    assert actor_offices(state, character.character_id) == (PoliticalOffice.DOMAIN_HOLDER.value,)
    assert primary_office(state, character.character_id) == PoliticalOffice.DOMAIN_HOLDER.value


def test_primogen_cannot_be_standardized_in_1435():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID)

    with pytest.raises(ValueError, match="primogen"):
        assign_office(
            state,
            [character],
            actor_id=character.character_id,
            office=PoliticalOffice.PRIMOGEN.value,
            era=era_for_year(1435),
        )


def test_prince_and_primogen_are_mutually_exclusive_in_canonical_registry():
    character = make_character()
    state = initial_simulation(CHRONICLE_GAME_ID, year=1493)
    state = assign_office(
        state,
        [character],
        actor_id=character.character_id,
        office=PoliticalOffice.PRIMOGEN.value,
        era=era_for_year(1493),
    )

    with pytest.raises(ValueError, match="Prince and Primogen"):
        assign_office(
            state,
            [character],
            actor_id=character.character_id,
            office=PoliticalOffice.PRINCE.value,
            era=era_for_year(1493),
        )


def test_canonical_prince_assignment_replaces_holder_without_mutating_character():
    character = replace(make_character(clan_id="ventrue"), status=4, personal_influence=8.0)
    state = initial_simulation(CHRONICLE_GAME_ID)

    updated = assign_office(
        state,
        [character],
        actor_id=character.character_id,
        office=PoliticalOffice.PRINCE.value,
        era=era_for_year(1435),
    )

    assert updated.offices["prince"] == character.character_id
    assert primary_office(updated, character.character_id) == PoliticalOffice.PRINCE.value
    assert character.office == PoliticalOffice.NONE.value


def test_validation_covers_domain_right_boon_and_office_references():
    character = make_character()
    state = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    state = grant_boon(
        state,
        creditor_id=character.character_id,
        debtor_id=character.sire_id,
        level="minor",
        origin="Service reconnu",
    )

    validate_political_state(state, [character], era_for_year(1435))

    broken = grant_boon(
        state,
        creditor_id="missing-character",
        debtor_id=character.sire_id,
        level="minor",
        origin="Référence invalide",
    )
    with pytest.raises(ValueError, match="Unknown boon participant"):
        validate_political_state(broken, [character], era_for_year(1435))
