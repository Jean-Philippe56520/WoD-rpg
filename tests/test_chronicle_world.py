from dataclasses import replace

from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
    resolve_personal_night,
)
from game.chronicle_service import ChronicleService, recommended_ellipse_months
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


def _mark_ready(store, *, segment: int, goal_progress: int = 0):
    with store.repository._connect() as con:
        con.execute(
            "UPDATE wod_chronicle_progress SET segment=? WHERE game_id=?",
            (segment, CHRONICLE_GAME_ID),
        )
        con.execute(
            """
            UPDATE wod_player_characters
            SET segment=?, local_night=3, ready_for_convergence=1, goal_progress=?
            WHERE game_id=? AND player_id='player-1'
            """,
            (segment, goal_progress, CHRONICLE_GAME_ID),
        )


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
    assert result.next_progress.chapter == 1
    assert result.previous_time.month == 1
    assert result.next_time.month == 2
    assert result.chapter_closed is False
    assert result.world_beats
    events = ChronicleWorldStore(repo).list_events(CHRONICLE_GAME_ID)
    assert len(events) == len(result.world_beats)
    assert all(event["public_text"] for event in events)


def test_cycle_three_does_not_automatically_end_the_chapter(tmp_path):
    repo, store, _progress, _character = setup_store(tmp_path)
    _mark_ready(store, segment=3, goal_progress=0)

    result = ChronicleService(repo).resolve_convergence(CHRONICLE_GAME_ID)

    assert result.chapter_closed is False
    assert result.next_progress.chapter == 1
    assert result.next_progress.segment == 4
    assert result.next_progress.year == 1435


def test_narrative_turning_point_can_close_chapter_without_fixed_two_year_jump(tmp_path):
    repo, store, _progress, _character = setup_store(tmp_path)
    _mark_ready(store, segment=2, goal_progress=5)
    service = ChronicleService(repo)

    assessment = service.assess_chapter_closure(CHRONICLE_GAME_ID)
    assert assessment.closable is True

    result = service.resolve_convergence(CHRONICLE_GAME_ID, close_chapter=True)

    assert result.chapter_closed is True
    assert result.ellipse_months == 1
    assert result.next_progress.chapter == 2
    assert result.next_progress.segment == 1
    assert result.next_progress.year == 1435
    assert result.next_time.month == 3
    current = store.get_character(CHRONICLE_GAME_ID, "player-1")
    assert current is not None
    assert current.goal_progress == 0
    assert current.experience == 2
    assert current.personal_influence >= 1.0


def test_ellipse_scales_up_for_old_influential_vampires(tmp_path):
    _repo, _store, progress, character = setup_store(tmp_path)
    elder = replace(character, embraced_year=1235, status=4)

    assert recommended_ellipse_months(progress, [elder]) >= 60
