import pytest

from game.editable_repository import EditableSQLiteGameRepository
from game.runtime import (
    PRODUCTION_MODE,
    WORKSHOP_GAME_ID,
    WORKSHOP_GAME_NAME,
    WORKSHOP_MODE,
    WORKSHOP_PLAYERS,
    RuntimeBackendLabel,
    RuntimeGameRepository,
    routed_game_id,
    set_runtime_mode,
)
from game.world import REQUIRED_CLANS, create_initial_game_state


@pytest.fixture(autouse=True)
def restore_production_runtime():
    set_runtime_mode(PRODUCTION_MODE)
    yield
    set_runtime_mode(PRODUCTION_MODE)


def test_runtime_routes_main_to_workshop_only_in_workshop_mode():
    assert routed_game_id("main") == "main"
    set_runtime_mode(WORKSHOP_MODE)
    assert routed_game_id("main") == WORKSHOP_GAME_ID
    assert routed_game_id(WORKSHOP_GAME_ID) == WORKSHOP_GAME_ID


def test_production_runtime_cannot_open_workshop_directly():
    with pytest.raises(ValueError, match="unavailable"):
        routed_game_id(WORKSHOP_GAME_ID)


def test_workshop_proxy_never_creates_or_reads_main(tmp_path):
    base = EditableSQLiteGameRepository(tmp_path / "runtime.sqlite3")
    repo = RuntimeGameRepository(base)
    set_runtime_mode(WORKSHOP_MODE)

    repo.ensure_game("main", "Chronique principale", create_initial_game_state(), REQUIRED_CLANS)
    info = base.get_game_info(WORKSHOP_GAME_ID)
    assert info["name"] == WORKSHOP_GAME_NAME
    with pytest.raises(ValueError, match="Unknown game: main"):
        base.get_game_info("main")


def test_workshop_technical_players_can_switch_between_all_three_clans(tmp_path):
    base = EditableSQLiteGameRepository(tmp_path / "players.sqlite3")
    repo = RuntimeGameRepository(base)
    set_runtime_mode(WORKSHOP_MODE)
    repo.ensure_game("main", "ignored", create_initial_game_state(), REQUIRED_CLANS)

    for clan_id, (player_id, player_name) in WORKSHOP_PLAYERS.items():
        repo.claim_clan("main", player_id, player_name, clan_id)

    assert {
        clan_id: repo.get_player_clan("main", player_id)
        for clan_id, (player_id, _name) in WORKSHOP_PLAYERS.items()
    } == {clan_id: clan_id for clan_id in REQUIRED_CLANS}


def test_workshop_reset_isolated_and_main_reset_is_forbidden(tmp_path):
    base = EditableSQLiteGameRepository(tmp_path / "reset.sqlite3")
    repo = RuntimeGameRepository(base)
    set_runtime_mode(WORKSHOP_MODE)
    repo.ensure_game("main", "ignored", create_initial_game_state(), REQUIRED_CLANS)
    player_id, player_name = WORKSHOP_PLAYERS["ventrue"]
    repo.claim_clan("main", player_id, player_name, "ventrue")
    assert repo.get_player_clan("main", player_id) == "ventrue"

    repo.reset_workshop_game(WORKSHOP_GAME_NAME, create_initial_game_state(), REQUIRED_CLANS)
    assert repo.get_player_clan("main", player_id) is None

    set_runtime_mode(PRODUCTION_MODE)
    with pytest.raises(ValueError, match="forbidden"):
        repo.reset_workshop_game(WORKSHOP_GAME_NAME, create_initial_game_state(), REQUIRED_CLANS)
    with pytest.raises(ValueError, match="production game cannot be reset"):
        base.reset_game("main", "bad", create_initial_game_state(), REQUIRED_CLANS)


def test_backend_label_disables_auth_only_in_workshop():
    label = RuntimeBackendLabel("Supabase")
    assert label == "Supabase"
    assert str(label) == "Supabase"

    set_runtime_mode(WORKSHOP_MODE)
    assert not (label == "Supabase")
    assert "Atelier isolé" in str(label)
