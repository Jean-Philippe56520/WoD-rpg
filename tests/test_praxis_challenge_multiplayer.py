import pytest

from game.models import (
    ActionType,
    Candidate,
    ClanNightOrders,
    GameAction,
    PoliticalRequestDecisionOrder,
    PoliticalRequestStatus,
    RequestDecision,
)
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.offices import install_prince
from game.persistence import SQLiteGameRepository


def service_and_recognized_state(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "praxis.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    state = repo.get_game_state(DEFAULT_GAME_ID)
    install_prince(state, Candidate("prince_test", "Prince Test", None, False))
    return service, state


def complete_orders_with_replacement(state, clan_id, replacement: GameAction):
    actions = []
    for character in state.characters.values():
        if character.clan_id != clan_id or character.id == state.prince_id:
            continue
        actions.append(
            replacement
            if character.id == replacement.actor_character_id
            else GameAction(
                clan_id=clan_id,
                action_type=ActionType.BUILD_INFLUENCE,
                actor_character_id=character.id,
            )
        )
    request_decisions = tuple(
        PoliticalRequestDecisionOrder(request.id, RequestDecision.ACCEPT)
        for request in state.political_requests.values()
        if request.clan_id == clan_id and request.status == PoliticalRequestStatus.OPEN
    )
    return ClanNightOrders(
        clan_id=clan_id,
        actions=tuple(actions),
        request_decisions=request_decisions,
        version=4,
    )


def test_service_accepts_current_primogen_praxis_challenge(tmp_path):
    service, state = service_and_recognized_state(tmp_path)
    primogen_id = state.clan_states["ventrue"].clan.primogen_id
    orders = complete_orders_with_replacement(
        state,
        "ventrue",
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.CHALLENGE_PRAXIS,
            actor_character_id=primogen_id,
        ),
    )

    service.validate_orders(state, "ventrue", orders)


def test_service_rejects_non_primogen_praxis_challenge(tmp_path):
    service, state = service_and_recognized_state(tmp_path)
    orders = complete_orders_with_replacement(
        state,
        "ventrue",
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.CHALLENGE_PRAXIS,
            actor_character_id="ventrue_victor",
        ),
    )

    with pytest.raises(ValueError, match="current Primogen"):
        service.validate_orders(state, "ventrue", orders)


def test_service_rejects_challenge_when_no_prince_is_recognized(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "vacant.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    state = repo.get_game_state(DEFAULT_GAME_ID)
    primogen_id = state.clan_states["ventrue"].clan.primogen_id
    orders = complete_orders_with_replacement(
        state,
        "ventrue",
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.CHALLENGE_PRAXIS,
            actor_character_id=primogen_id,
        ),
    )

    with pytest.raises(ValueError, match="recognized Prince"):
        service.validate_orders(state, "ventrue", orders)


def test_legacy_order_cannot_smuggle_praxis_challenge(tmp_path):
    service, state = service_and_recognized_state(tmp_path)
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(GameAction("ventrue", ActionType.CHALLENGE_PRAXIS),),
        version=1,
    )

    with pytest.raises(ValueError, match=r"V0\.8\+"):
        service.validate_orders(state, "ventrue", orders)
