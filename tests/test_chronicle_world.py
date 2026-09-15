from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
    resolve_personal_night,
)
from game.chronicle_service import ChronicleService
from game.chronicle_store import ChronicleStore
from game.chronicle_world import autonomous_world_beats
from game.chronicle_world_store import ChronicleWorldStore
from game.models import GameState
from game.persistence import SQLiteGameRepository


def make_character(progress):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-1",
        name="Jehan",
        clan_id="brujah",
        concept="Chevalier déchu",
        starting_discipline=CLAN_DISCIPLINES["brujah"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Obtenir un Domaine",
        chapter_goal="Comprendre mon sire",
        progress=progress,
    )


def setup_store(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "world.sqlite3")
    repo.ensure_game(
        CHRONICLE_GAME_ID,
        "Chronique 1435",
        GameState(),
        ("ventrue", "toreador", "brujah"),
    )
    store = ChronicleStore(repo)
    progress = store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    character = make_character(progress)
    store.create_character(character)
    return repo, store, progress, character


def test_world_beats_are_deterministic_and_never_control_player(tmp_path):
    _repo, _store, progress, character = setup_store(tmp_path)
    first = autonomous_world_beats(progress, [character])
    second = autonomous_world_beats(progress, [character])

    assert first == second
    assert first
    assert all(beat.actor_id != character.character_id for beat in first)
    assert all(beat.public_text for beat in first)


def test_convergence_advances_world_and_persists_npc_actions(tmp_path):
    repo, store, progress, character = setup_store(tmp_path)
    current = character
    for action in (PersonalAction.HUNT, PersonalAction.INVESTIGATE, PersonalAction.ELYSIUM):
        outcome = resolve_personal_night(current, action)
        current = store.advance_personal_night(current, outcome)

    result = ChronicleService(repo).resolve_convergence(CHRONICLE_GAME_ID)

    assert result.previous_progress == progress
    assert result.next_progress.segment == 2
    assert result.world_beats
    events = ChronicleWorldStore(repo).list_events(CHRONICLE_GAME_ID)
    assert len(events) == len(result.world_beats)
    assert all(event["public_text"] for event in events)
