import pytest

from game.crises import ANARCHS, active_crises, open_crisis
from game.crisis_ui import apply_crisis_override
from game.models import ActionType, ClanNightOrders, GameAction, PrimogenVote
from game.world import create_initial_game_state


def _orders_for_clan(state, clan_id):
    actions = tuple(
        GameAction(
            clan_id=clan_id,
            action_type=ActionType.BUILD_INFLUENCE,
            actor_character_id=character.id,
        )
        for character in state.characters.values()
        if character.clan_id == clan_id and character.id != state.prince_id
    )
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    return ClanNightOrders(
        clan_id=clan_id,
        actions=actions,
        vote=PrimogenVote(primogen_id, primogen_id),
        version=4,
    )


def test_crisis_override_replaces_exactly_one_action_and_preserves_orders():
    state = create_initial_game_state()
    domain_id = next(iter(state.domains))
    state.events.append(open_crisis(state, ANARCHS, domain_id))
    crisis = active_crises(state)[0]
    orders = _orders_for_clan(state, "ventrue")
    actor_id = state.clan_states["ventrue"].clan.primogen_id
    payload = {
        "night": state.night,
        "clan_id": "ventrue",
        "actor_id": actor_id,
        "crisis_id": crisis.id,
        "action_type": ActionType.CRISIS_INVESTIGATE.value,
    }

    updated = apply_crisis_override(state, orders, payload)

    assert updated.vote == orders.vote
    assert updated.version == orders.version
    assert updated.request_decisions == orders.request_decisions
    assert updated.domain_decisions == orders.domain_decisions
    assert updated.promise_fulfillments == orders.promise_fulfillments
    assert len(updated.actions) == len(orders.actions)
    changed = [
        action
        for before, action in zip(orders.actions, updated.actions)
        if before != action
    ]
    assert len(changed) == 1
    assert changed[0].actor_character_id == actor_id
    assert changed[0].action_type == ActionType.CRISIS_INVESTIGATE
    assert changed[0].target_domain_id == domain_id


def test_crisis_override_rejects_stale_selection():
    state = create_initial_game_state()
    domain_id = next(iter(state.domains))
    state.events.append(open_crisis(state, ANARCHS, domain_id))
    crisis = active_crises(state)[0]
    orders = _orders_for_clan(state, "ventrue")
    actor_id = state.clan_states["ventrue"].clan.primogen_id

    with pytest.raises(ValueError, match="périmée"):
        apply_crisis_override(
            state,
            orders,
            {
                "night": state.night - 1,
                "clan_id": "ventrue",
                "actor_id": actor_id,
                "crisis_id": crisis.id,
                "action_type": ActionType.CRISIS_CONTAIN.value,
            },
        )
