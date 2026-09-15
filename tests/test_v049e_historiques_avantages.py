from dataclasses import replace

from game.backgrounds import (
    APPROACH_BACKGROUNDS,
    apply_background_leverage,
    background_leverage,
    background_rating,
)
from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, create_player_character
from game.chronicle_simulation import ensure_character_links, initial_simulation
from game.night_cycle import resolve_night_event
from game.situations import generate_situations
from game.vampire_profile import default_profile


def make_character(clan_id: str = "toreador", *, character_id: str = "pc-v049e"):
    disciplines = {
        "brujah": "Présence",
        "toreador": "Présence",
        "ventrue": "Domination",
    }
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=f"player-{character_id}",
        player_name="Joueur",
        character_id=character_id,
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=disciplines[clan_id],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Comprendre Paris",
        chapter_goal="Nouer des relais",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
    )


def situation_by_id(character, profile, simulation, situation_id: str):
    return next(
        item
        for item in generate_situations(character, profile, simulation, year=1435)
        if item.id == situation_id
    )


def test_contacts_reduisent_la_difficulte_pas_le_pool_sur_une_ecoute_politique():
    character = make_character()
    profile = default_profile(character)
    without_contacts = replace(profile, backgrounds={**profile.backgrounds, "contacts": 0})
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = situation_by_id(character, profile, simulation, "political_current")
    choice = next(item for item in situation.choices if item.id == "listen")

    contextual, leverage = apply_background_leverage(character, profile, situation, choice)
    plain, none = apply_background_leverage(character, without_contacts, situation, choice)

    assert leverage is not None
    assert leverage.id == "contacts"
    assert leverage.rating == 1
    assert contextual.difficulty == choice.difficulty - 1
    assert plain.difficulty == choice.difficulty
    assert none is None

    with_contacts = resolve_night_event(
        character, profile, simulation, situation, choice.id, nights_per_segment=3
    )
    without = resolve_night_event(
        character, without_contacts, simulation, situation, choice.id, nights_per_segment=3
    )

    assert with_contacts.resolution.dice.pool == without.resolution.dice.pool
    assert with_contacts.resolution.dice.difficulty == without.resolution.dice.difficulty - 1
    assert "Historique — Contacts 1" in with_contacts.resolution.outcome.detail


def test_statut_utilise_la_valeur_du_personnage_pas_le_champ_legacy_du_profil():
    character = make_character(character_id="pc-status-v049e")
    profile = default_profile(character)
    profile_with_legacy_status = replace(
        profile,
        backgrounds={**profile.backgrounds, "status": 5},
    )

    assert background_rating(character, profile_with_legacy_status, "status") == 0

    recognized = replace(character, status=1)
    assert background_rating(recognized, profile, "status") == 1

    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), recognized)
    situation = situation_by_id(recognized, profile, simulation, "political_current")
    choice = next(item for item in situation.choices if item.id == "support_order")
    contextual, leverage = apply_background_leverage(recognized, profile, situation, choice)

    assert leverage is not None
    assert leverage.id == "status"
    assert contextual.difficulty == choice.difficulty - 1


def test_ressources_peuvent_ameliorer_une_protection_sans_devenir_une_competence():
    character = make_character(character_id="pc-resources-v049e")
    profile = default_profile(character)
    wealthy = replace(profile, backgrounds={**profile.backgrounds, "resources": 2})
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = situation_by_id(character, wealthy, simulation, "toreador_patronage")
    choice = next(item for item in situation.choices if item.id == "protect_artist")

    contextual, leverage = apply_background_leverage(character, wealthy, situation, choice)

    assert leverage is not None
    assert leverage.id == "resources"
    assert leverage.rating == 2
    assert contextual.difficulty == choice.difficulty - 1
    assert wealthy.pool(choice.attribute, choice.skill) == profile.pool(choice.attribute, choice.skill)


def test_un_seul_historique_principal_est_applique_par_approche():
    character = make_character(character_id="pc-one-lever-v049e")
    profile = default_profile(character)
    profile = replace(profile, backgrounds={**profile.backgrounds, "contacts": 1, "resources": 3})
    leverage = background_leverage(character, profile, ("contacts", "resources"))

    assert leverage is not None
    assert leverage.id == "resources"
    assert leverage.difficulty_adjustment == -1


def test_sire_est_un_historique_d_acces_sans_double_bonus_de_difficulte():
    character = make_character(character_id="pc-sire-v049e")
    profile = default_profile(character)
    leverage = background_leverage(character, profile, ("sire",))

    assert leverage is not None
    assert leverage.id == "sire"
    assert leverage.rating == 1
    assert leverage.difficulty_adjustment == 0


def test_seules_les_approches_explicitement_declarees_peuvent_utiliser_un_historique():
    assert ("political_current", "listen") in APPROACH_BACKGROUNDS
    assert ("toreador_patronage", "protect_artist") in APPROACH_BACKGROUNDS
    assert ("brujah_revolt", "protect") not in APPROACH_BACKGROUNDS
