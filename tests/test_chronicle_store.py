from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
    resolve_personal_night,
)
from game.chronicle_store import ChronicleStore
from game.models import GameState
from game.persistence import SQLiteGameRepository


def make_store(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "chronicle.sqlite3")
    repo.ensure_game(
        CHRONICLE_GAME_ID,
        "Chronique 1435",
        GameState(),
        ("ventrue", "toreador", "brujah"),
    )
    store = ChronicleStore(repo)
    progress = store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    return store, progress


def make_character(progress, player_id="player-1", character_id="pc-1", name="Jehan"):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=player_id,
        player_name=player_id,
        character_id=character_id,
        name=name,
        clan_id="brujah",
        concept="Chevalier déchu",
        starting_discipline=CLAN_DISCIPLINES["brujah"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Obtenir un domaine",
        chapter_goal="Comprendre mon sire",
        progress=progress,
    )


def test_store_persists_character_and_night_history(tmp_path):
    store, progress = make_store(tmp_path)
    character = make_character(progress)
    store.create_character(character)

    outcome = resolve_personal_night(character, PersonalAction.INVESTIGATE)
    saved = store.advance_personal_night(character, outcome, free_intent="Suivre le messager")

    assert saved.local_night == 2
    history = store.list_history(CHRONICLE_GAME_ID, character.character_id)
    assert len(history) == 1
    assert history[0]["action"] == PersonalAction.INVESTIGATE.value
    assert history[0]["outcome_json"]["free_intent"] == "Suivre le messager"


def test_store_allows_multiple_players_of_same_clan(tmp_path):
    store, progress = make_store(tmp_path)
    first = make_character(progress, player_id="player-1", character_id="pc-1", name="Jehan")
    second = make_character(progress, player_id="player-2", character_id="pc-2", name="Aelis")

    store.create_character(first)
    store.create_character(second)

    characters = store.list_characters(CHRONICLE_GAME_ID)
    assert {item.player_id for item in characters} == {"player-1", "player-2"}
    assert {item.clan_id for item in characters} == {"brujah"}


def test_convergence_waits_until_every_active_character_is_ready(tmp_path):
    store, progress = make_store(tmp_path)
    first = make_character(progress, player_id="player-1", character_id="pc-1", name="Jehan")
    second = make_character(progress, player_id="player-2", character_id="pc-2", name="Aelis")
    store.create_character(first)
    store.create_character(second)

    for player_id in ("player-1", "player-2"):
        character = store.get_character(CHRONICLE_GAME_ID, player_id)
        assert character is not None
        for action in (PersonalAction.HUNT, PersonalAction.INVESTIGATE, PersonalAction.ELYSIUM):
            outcome = resolve_personal_night(character, action)
            character = store.advance_personal_night(character, outcome)
        if player_id == "player-1":
            assert not store.all_ready_for_convergence(CHRONICLE_GAME_ID)

    assert store.all_ready_for_convergence(CHRONICLE_GAME_ID)
    next_progress = store.resolve_convergence(CHRONICLE_GAME_ID)
    assert next_progress.segment == 2
    assert next_progress.chapter == 1
    assert next_progress.year == 1435

    first_after = store.get_character(CHRONICLE_GAME_ID, "player-1")
    assert first_after is not None
    assert first_after.local_night == 1
    assert not first_after.ready_for_convergence


def test_end_of_chapter_applies_historical_ellipse(tmp_path):
    store, progress = make_store(tmp_path)
    character = make_character(progress)
    store.create_character(character)

    current = character
    for expected_segment in (1, 2, 3):
        for action in (PersonalAction.HUNT, PersonalAction.INVESTIGATE, PersonalAction.PURSUE_GOAL):
            outcome = resolve_personal_night(current, action)
            current = store.advance_personal_night(current, outcome)
        assert current.ready_for_convergence
        next_progress = store.resolve_convergence(CHRONICLE_GAME_ID)
        current = store.get_character(CHRONICLE_GAME_ID, "player-1")
        assert current is not None
        if expected_segment < 3:
            assert next_progress.segment == expected_segment + 1

    assert next_progress.chapter == 2
    assert next_progress.segment == 1
    assert next_progress.year == 1437
    assert current.chronicle_year == 1437
    assert current.goal_progress == 0
