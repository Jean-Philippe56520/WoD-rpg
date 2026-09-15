from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    choose_sire,
    create_player_character,
    resolve_personal_night,
)


def make_character(**overrides):
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    payload = {
        "game_id": CHRONICLE_GAME_ID,
        "player_id": "player-1",
        "player_name": "JP",
        "character_id": "pc-1",
        "name": "Jehan de Kergoat",
        "clan_id": "brujah",
        "concept": "Chevalier déchu",
        "starting_discipline": CLAN_DISCIPLINES["brujah"][0],
        "mortal_stance": "humanist",
        "order_stance": "reformist",
        "long_term_goal": "Obtenir un domaine",
        "chapter_goal": "Me libérer de mon sire",
        "progress": progress,
    }
    payload.update(overrides)
    return create_player_character(**payload)


def test_new_player_character_starts_as_dependent_newborn():
    character = make_character()
    assert character.chronicle_year == 1435
    assert character.embraced_year == 1433
    assert character.status == 0
    assert character.personal_influence == 0
    assert character.sire_relation == 2
    assert character.local_night == 1
    assert not character.ready_for_convergence


def test_sire_assignment_is_clan_and_ideology_aware():
    sire = choose_sire("brujah", "reformist", "predatory")
    assert sire.clan_id == "brujah"
    assert sire.order_stance == "reformist"
    assert sire.mortal_stance == "predatory"


def test_player_controls_only_their_own_personal_night():
    character = make_character()
    outcome = resolve_personal_night(character, PersonalAction.INVESTIGATE)
    assert outcome.updated_character.character_id == character.character_id
    assert outcome.updated_character.local_night == 2
    assert outcome.updated_character.goal_progress >= character.goal_progress


def test_third_personal_night_reaches_convergence_without_advancing_world():
    character = make_character()
    first = resolve_personal_night(character, PersonalAction.PURSUE_GOAL).updated_character
    second = resolve_personal_night(first, PersonalAction.HUNT).updated_character
    third = resolve_personal_night(second, PersonalAction.ELYSIUM).updated_character

    assert third.local_night == 3
    assert third.ready_for_convergence
    assert third.chronicle_year == 1435
    assert third.segment == 1


def test_character_cannot_play_beyond_convergence():
    character = make_character()
    first = resolve_personal_night(character, PersonalAction.HUNT).updated_character
    second = resolve_personal_night(first, PersonalAction.HUNT).updated_character
    ready = resolve_personal_night(second, PersonalAction.HUNT).updated_character

    try:
        resolve_personal_night(ready, PersonalAction.HUNT)
    except ValueError as exc:
        assert "convergence" in str(exc).lower()
    else:
        raise AssertionError("A ready character must not advance beyond the convergence")


def test_free_intent_is_preserved_in_narrative_outcome():
    character = make_character()
    outcome = resolve_personal_night(
        character,
        PersonalAction.INVESTIGATE,
        free_intent="Je veux savoir qui emploie le copiste du port.",
    )
    assert "copiste du port" in outcome.detail
