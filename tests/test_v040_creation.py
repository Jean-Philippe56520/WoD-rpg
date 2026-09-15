from dataclasses import replace

from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, create_player_character
from game.creation_rules import choose_sire_from_creation, concept_from_origin
from game.era import era_for_year
from game.sire_relations import SireBondStage, sire_bond
from game.vampire_profile import profile_for_creation


def make_character(*, sire_id: str, sire_name: str, clan_id: str = "brujah", discipline: str = "Présence"):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-v040",
        name="Jehan",
        clan_id=clan_id,
        concept="Érudit",
        starting_discipline=discipline,
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="",
        chapter_goal="",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
        sire_id=sire_id,
        sire_name=sire_name,
    )


def test_brujah_sire_is_derived_from_creation_choices():
    learned = choose_sire_from_creation(
        clan_id="brujah",
        origin_id="scholar",
        conviction_id="keep_word",
        starting_discipline="Présence",
        stable_key="learned",
    )
    rebel = choose_sire_from_creation(
        clan_id="brujah",
        origin_id="outlaw",
        conviction_id="resist_tyranny",
        starting_discipline="Puissance",
        stable_key="rebel",
    )

    assert learned.id == "sire_brujah_guilhem"
    assert rebel.id == "sire_brujah_ysabeau"


def test_ventrue_sire_is_derived_from_creation_choices():
    lordly = choose_sire_from_creation(
        clan_id="ventrue",
        origin_id="noble",
        conviction_id="keep_word",
        starting_discipline="Domination",
        stable_key="lordly",
    )
    mercantile = choose_sire_from_creation(
        clan_id="ventrue",
        origin_id="merchant",
        conviction_id="repay_debts",
        starting_discipline="Présence",
        stable_key="mercantile",
    )

    assert lordly.id == "sire_ventrue_aymon"
    assert mercantile.id == "sire_ventrue_heloise"


def test_creation_profile_uses_humanitatis_without_touchstone_and_conviction_is_moral_not_skill_bonus():
    character = make_character(
        sire_id="sire_brujah_ysabeau",
        sire_name="Ysabeau des Cendres",
        discipline="Puissance",
    )
    profile = profile_for_creation(
        character,
        conviction_id="resist_tyranny",
        feeding_preference="should be ignored for a Brujah",
    )

    assert profile.road_affinity == "humanitatis"
    assert profile.touchstones == ()
    assert profile.convictions == ("resist_tyranny",)
    # V0.49b retire l'ancienne règle maison +1 Politique liée à cette Conviction.
    assert profile.skills["politics"] == 1
    assert profile.humanity_stains == 0
    assert profile.feeding_preference is None


def test_ventrue_feeding_restriction_is_persisted():
    character = make_character(
        sire_id="sire_ventrue_aymon",
        sire_name="Aymon de Montfort",
        clan_id="ventrue",
        discipline="Domination",
    )
    profile = profile_for_creation(
        character,
        conviction_id="keep_word",
        feeding_preference="Nobles et membres de leur maison",
    )

    assert profile.feeding_preference == "Nobles et membres de leur maison"


def test_free_text_origin_detail_is_narrative_only():
    assert concept_from_origin("soldier", " ancien sergent d'une compagnie ") == (
        "Soldat ou homme d'armes — ancien sergent d'une compagnie"
    )


def test_generic_goal_progress_no_longer_unlocks_release():
    character = make_character(
        sire_id="sire_brujah_guilhem",
        sire_name="Guilhem d'Aquitaine",
    )
    character = replace(character, goal_progress=99, status=0, personal_influence=0.0)
    profile = profile_for_creation(character, conviction_id="keep_word")

    bond = sire_bond(character, profile, era_for_year(1435))

    assert bond.stage == SireBondStage.ACCOUNTING
    assert not bond.can_seek_release
