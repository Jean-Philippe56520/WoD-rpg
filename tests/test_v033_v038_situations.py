from dataclasses import replace

from game.chronicle import CHRONICLE_GAME_ID, CLAN_DISCIPLINES, ChronicleProgress, create_player_character
from game.chronicle_simulation import (
    active_hunting_access,
    ensure_character_links,
    grant_boon,
    initial_simulation,
)
from game.clans import clan_identity
from game.situations import generate_situations, resolve_situation
from game.vampire_profile import default_profile


def make_character(clan_id="brujah"):
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-1",
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=CLAN_DISCIPLINES[clan_id][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Obtenir un Domaine",
        chapter_goal="Gagner mon autonomie",
        progress=progress,
    )


def test_three_playable_clans_have_distinct_medieval_identity_and_bane():
    identities = [clan_identity(clan_id) for clan_id in ("brujah", "toreador", "ventrue")]

    assert len({item.bane_name for item in identities}) == 3
    assert all(item.high_clan for item in identities)
    assert all(item.political_tension for item in identities)


def test_newborn_receives_hunting_access_through_sire_not_personal_domain():
    character = make_character("brujah")
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)

    rights = active_hunting_access(simulation, character.character_id, 1435)

    assert len(rights) == 1
    assert rights[0].granted_by_id == character.sire_id
    assert all(domain.holder_id != character.character_id for domain in simulation.domains.values())
    domain = simulation.domains[rights[0].domain_id]
    assert 0 <= domain.viandis <= 3
    assert 0 <= domain.servage <= 3
    assert 0 <= domain.rempart <= 3


def test_high_hunger_prioritizes_hunting_situation():
    character = replace(make_character("toreador"), hunger=4)
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)

    situations = generate_situations(character, profile, simulation, year=1435)

    assert situations[0].id.startswith("hunt_")
    assert len(situations) == 3


def test_situation_resolution_uses_character_sheet_and_advances_personal_night():
    character = make_character("ventrue")
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = generate_situations(character, profile, simulation, year=1435)[0]
    choice = situation.choices[0]

    resolution = resolve_situation(
        character,
        profile,
        simulation,
        situation,
        choice.id,
        nights_per_segment=3,
        free_intent="Je veux comprendre ce que mon sire ne dit pas.",
    )

    assert resolution.outcome.updated_character.local_night == 2
    assert resolution.dice.pool >= 1
    assert resolution.dice.difficulty == choice.difficulty
    assert resolution.outcome.detail


def test_prestation_is_persistent_world_state_not_abstract_currency():
    character = make_character()
    simulation = initial_simulation(CHRONICLE_GAME_ID)
    updated = grant_boon(
        simulation,
        creditor_id=character.character_id,
        debtor_id=character.sire_id,
        level="minor",
        origin="Service reconnu devant témoin",
    )

    assert len(updated.boons) == 1
    boon = next(iter(updated.boons.values()))
    assert boon.creditor_id == character.character_id
    assert boon.debtor_id == character.sire_id
    assert boon.status == "due"
