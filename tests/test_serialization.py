from game.models import ActionType, ClanNightOrders, GameAction, PrimogenVote
from game.serialization import (
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_json,
    game_state_to_json,
)
from game.world import create_initial_game_state


def test_game_state_json_roundtrip():
    state = create_initial_game_state()
    restored = game_state_from_json(game_state_to_json(state))
    assert restored.night == state.night
    assert restored.clan_states["ventrue"].clan.primogen_id == state.clan_states["ventrue"].clan.primogen_id
    assert restored.characters["ventrue_claire"].humanism == 60


def test_orders_json_roundtrip():
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(GameAction("ventrue", ActionType.BUILD_INFLUENCE),),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
    )
    restored = clan_orders_from_json(clan_orders_to_json(orders))
    assert restored == orders
