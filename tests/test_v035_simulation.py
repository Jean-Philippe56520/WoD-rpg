from game.chronicle import CHRONICLE_GAME_ID, CLAN_DISCIPLINES, ChronicleProgress, create_player_character
from game.chronicle_simulation import advance_simulation, initial_simulation
from game.chronicle_simulation_store import ChronicleSimulationStore
from game.chronicle_store import ChronicleStore
from game.models import GameState
from game.persistence import SQLiteGameRepository


def make_character(progress):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-1",
        name="Jehan",
        clan_id="toreador",
        concept="Copiste",
        starting_discipline=CLAN_DISCIPLINES["toreador"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Devenir indispensable",
        chapter_goal="Comprendre la Cour",
        progress=progress,
    )


def test_world_contains_non_playable_clans_and_local_prince():
    state = initial_simulation(CHRONICLE_GAME_ID)

    clans = {npc.clan_id for npc in state.npcs.values()}
    assert {"lasombra", "tzimisce", "tremere", "nosferatu", "gangrel"}.issubset(clans)
    assert state.offices["prince"] == "npc_prince_godefroy"
    assert state.npcs["npc_prince_godefroy"].role == "Prince local"


def test_npcs_advance_without_player_control_and_hunters_affect_domains():
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    character = make_character(progress)
    state = initial_simulation(CHRONICLE_GAME_ID)

    advanced, beats = advance_simulation(
        state,
        year=1435,
        chapter=1,
        segment=1,
        characters=[character],
    )

    assert beats
    assert all(beat.actor_id != character.character_id for beat in beats)
    assert any(beat.category == "hunter_pressure" for beat in beats)
    assert any(domain.pressure > 0 for domain in advanced.domains.values())
    assert any(npc.agenda_progress > 0 for npc in advanced.npcs.values())


def test_simulation_store_roundtrip_preserves_world_state(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "simulation.sqlite3")
    repo.ensure_game(CHRONICLE_GAME_ID, "Chronique", GameState(), ("ventrue", "toreador", "brujah"))
    chronicle_store = ChronicleStore(repo)
    progress = chronicle_store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    character = make_character(progress)
    chronicle_store.create_character(character)

    store = ChronicleSimulationStore(repo)
    created = store.ensure(CHRONICLE_GAME_ID, year=1435)
    advanced, _ = advance_simulation(created, year=1435, chapter=1, segment=1, characters=[character])
    store.save(advanced)
    loaded = store.get(CHRONICLE_GAME_ID)

    assert loaded == advanced
    assert loaded is not None
    assert loaded.hunting_rights
