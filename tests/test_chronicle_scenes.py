from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    create_player_character,
)
from game.chronicle_scenes import ChronicleSceneStore
from game.chronicle_store import ChronicleStore
from game.models import GameState
from game.persistence import SQLiteGameRepository


def setup_players(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "scenes.sqlite3")
    repo.ensure_game(
        CHRONICLE_GAME_ID,
        "Chronique 1435",
        GameState(),
        ("ventrue", "toreador", "brujah"),
    )
    store = ChronicleStore(repo)
    progress = store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    first = create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-a",
        player_name="A",
        character_id="pc-a",
        name="Jehan",
        clan_id="brujah",
        concept="Chevalier",
        starting_discipline=CLAN_DISCIPLINES["brujah"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Exister",
        chapter_goal="Comprendre",
        progress=progress,
    )
    second = create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-b",
        player_name="B",
        character_id="pc-b",
        name="Aelis",
        clan_id="toreador",
        concept="Copiste",
        starting_discipline=CLAN_DISCIPLINES["toreador"][0],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Influer",
        chapter_goal="Observer",
        progress=progress,
    )
    store.create_character(first)
    store.create_character(second)
    return repo, first, second


def test_scene_can_be_opened_and_answered_asynchronously(tmp_path):
    repo, first, second = setup_players(tmp_path)
    scenes = ChronicleSceneStore(repo)

    scene = scenes.create_scene(
        game_id=CHRONICLE_GAME_ID,
        from_character_id=first.character_id,
        to_character_id=second.character_id,
        chapter=1,
        segment=1,
        night_number=2,
        title="Rencontre discrète",
        opening_text="Je souhaite vous parler sans témoin.",
    )

    assert scene.status == "open"
    assert scenes.list_incoming(CHRONICLE_GAME_ID, second.character_id)[0].id == scene.id
    assert scenes.list_outgoing(CHRONICLE_GAME_ID, first.character_id)[0].id == scene.id

    answered = scenes.respond(
        scene,
        character_id=second.character_id,
        response_text="Retrouvez-moi après complies.",
    )
    assert answered.status == "responded"
    assert "complies" in answered.response_text


def test_only_target_character_can_answer_scene(tmp_path):
    repo, first, second = setup_players(tmp_path)
    scenes = ChronicleSceneStore(repo)
    scene = scenes.create_scene(
        game_id=CHRONICLE_GAME_ID,
        from_character_id=first.character_id,
        to_character_id=second.character_id,
        chapter=1,
        segment=1,
        night_number=1,
        title="Message",
        opening_text="Une proposition.",
    )

    try:
        scenes.respond(scene, character_id=first.character_id, response_text="Impossible")
    except ValueError as exc:
        assert "target" in str(exc).lower()
    else:
        raise AssertionError("The sender must not be able to answer for the target")
