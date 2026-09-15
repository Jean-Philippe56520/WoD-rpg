from dataclasses import replace

from game.chronicle import CHRONICLE_GAME_ID, CLAN_DISCIPLINES, ChronicleProgress, create_player_character
from game.chronicle_offices import office_eligibility
from game.chronicle_simulation import initial_simulation
from game.era import era_for_year
from game.sire_relations import SireBondStage, sire_bond
from game.vampire_profile import default_profile


def make_character():
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-1",
        name="Jehan",
        clan_id="brujah",
        concept="Nouveau-né",
        starting_discipline=CLAN_DISCIPLINES["brujah"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Devenir libre",
        chapter_goal="Me libérer de mon sire",
        progress=progress,
    )


def test_newborn_begins_under_sire_accounting():
    character = make_character()
    profile = default_profile(character)

    bond = sire_bond(character, profile, era_for_year(1435))

    assert bond.stage == SireBondStage.ACCOUNTING
    assert not bond.can_seek_release


def test_release_becomes_negotiable_through_social_progress_not_level_only():
    character = replace(make_character(), personal_influence=2.0)
    profile = default_profile(character)

    bond = sire_bond(character, profile, era_for_year(1435))

    assert bond.stage == SireBondStage.NEGOTIATING_RELEASE
    assert bond.can_seek_release


def test_primogen_is_not_standard_office_in_1435_but_can_exist_after_thorns():
    character = replace(make_character(), status=4, personal_influence=8.0)
    simulation = initial_simulation(CHRONICLE_GAME_ID)

    early = {item.office: item for item in office_eligibility(character, simulation, era_for_year(1435))}
    later = {item.office: item for item in office_eligibility(character, simulation, era_for_year(1493))}

    assert not early["primogen"].available
    assert not early["primogen"].eligible
    assert later["primogen"].available
    assert later["primogen"].eligible
    assert early["prince"].available
    assert early["prince"].eligible
