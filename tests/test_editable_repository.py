import pytest

from game.editable_repository import EditableSQLiteGameRepository
from game.models import ActionType, ClanNightOrders, GameAction, PrimogenVote
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService


def make_service(tmp_path):
    repo = EditableSQLiteGameRepository(tmp_path / "game.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    return service, repo


def orders_for(state, clan_id):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    return ClanNightOrders(
        clan_id=clan_id,
        actions=(GameAction(clan_id, ActionType.BUILD_INFLUENCE),),
        vote=PrimogenVote(primogen_id, primogen_id),
    )


def test_player_can_withdraw_orders_before_night_is_ready(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    service.claim_clan("p1", "Alice", "ventrue")

    assert service.submit_orders("p1", orders_for(state, "ventrue")) is False
    assert repo.submission_statuses(DEFAULT_GAME_ID)["ventrue"] is True
    assert repo.get_submitted_orders(DEFAULT_GAME_ID, "ventrue") is not None

    service.withdraw_orders("p1")

    assert repo.submission_statuses(DEFAULT_GAME_ID)["ventrue"] is False
    assert repo.get_submitted_orders(DEFAULT_GAME_ID, "ventrue") is None


def test_player_cannot_withdraw_another_clans_orders(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    service.claim_clan("p1", "Alice", "ventrue")
    service.claim_clan("p2", "Bob", "toreador")
    service.submit_orders("p1", orders_for(state, "ventrue"))

    with pytest.raises(ValueError, match="No submitted orders"):
        repo.withdraw_orders(DEFAULT_GAME_ID, "p2", "toreador")
