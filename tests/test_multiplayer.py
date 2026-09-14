import pytest

from game.models import ActionType, ClanNightOrders, GameAction, PrimogenVote
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.persistence import SQLiteGameRepository
from game.world import REQUIRED_CLANS


def make_service(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "game.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    return service, repo


def orders_for(state, clan_id, action_type=ActionType.BUILD_INFLUENCE):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    return ClanNightOrders(
        clan_id=clan_id,
        actions=(GameAction(clan_id, action_type),),
        vote=PrimogenVote(primogen_id, primogen_id),
    )


def test_players_submit_only_their_own_clan(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    with pytest.raises(ValueError, match="player's clan"):
        service.submit_orders("p1", orders_for(state, "brujah"))


def test_third_submission_resolves_once_and_advances_global_night(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)

    assert service.submit_orders("p1", orders_for(state, "ventrue")) is False
    assert service.submit_orders("p2", orders_for(state, "toreador")) is False
    assert service.submit_orders("p3", orders_for(state, "brujah")) is True

    info = repo.get_game_info(DEFAULT_GAME_ID)
    assert info["current_night"] == 2
    assert repo.try_begin_resolution(DEFAULT_GAME_ID) is None
    for clan_id in REQUIRED_CLANS:
        report = repo.get_report(DEFAULT_GAME_ID, 1, clan_id)
        assert report is not None


def test_reports_hide_other_clans_private_actions(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)
    service.submit_orders("p1", orders_for(state, "ventrue", ActionType.CONSOLIDATE))
    service.submit_orders("p2", orders_for(state, "toreador", ActionType.BUILD_INFLUENCE))
    service.submit_orders("p3", orders_for(state, "brujah", ActionType.BUILD_INFLUENCE))

    ventrue = " ".join(repo.get_report(DEFAULT_GAME_ID, 1, "ventrue").items)
    toreador = " ".join(repo.get_report(DEFAULT_GAME_ID, 1, "toreador").items)
    assert "Ventrue consolide" in ventrue
    assert "Ventrue consolide" not in toreador
