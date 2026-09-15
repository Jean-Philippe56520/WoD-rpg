from copy import deepcopy

from game.config import DEFAULT_RULES
from game.diplomatic_pacts import (
    ACTIVE,
    BROKEN,
    EXPIRED,
    active_pact_between,
    list_diplomatic_pacts,
    register_reciprocal_diplomatic_pacts,
)
from game.models import ActionType, GameAction
from game.serialization import game_state_from_json, game_state_to_json
from game.simultaneous import resolve_actions_simultaneously
from game.world import create_initial_game_state


def reciprocal_primogen_diplomacy():
    return [
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.DIPLOMACY,
            actor_character_id="primogen_ventrue",
            target_character_id="primogen_toreador",
        ),
        GameAction(
            clan_id="toreador",
            action_type=ActionType.DIPLOMACY,
            actor_character_id="primogen_toreador",
            target_character_id="primogen_ventrue",
        ),
    ]


def seed_pact(state, first="ventrue", second="toreador"):
    actions = {
        ("ventrue", "toreador"): reciprocal_primogen_diplomacy(),
        ("brujah", "ventrue"): [
            GameAction(
                clan_id="brujah",
                action_type=ActionType.DIPLOMACY,
                actor_character_id="primogen_brujah",
                target_character_id="primogen_ventrue",
            ),
            GameAction(
                clan_id="ventrue",
                action_type=ActionType.DIPLOMACY,
                actor_character_id="primogen_ventrue",
                target_character_id="primogen_brujah",
            ),
        ],
    }[(first, second)]
    events = register_reciprocal_diplomatic_pacts(state, actions)
    assert len(events) == 1
    state.events.extend(events)
    return events[0]


def test_reciprocal_primogen_diplomacy_creates_public_pact():
    state = create_initial_game_state()
    events = resolve_actions_simultaneously(state, reciprocal_primogen_diplomacy())
    state.events.extend(events)

    pact = active_pact_between(state, "ventrue", "toreador")
    assert pact is not None
    assert pact.status == ACTIVE
    assert pact.created_night == 1
    assert pact.expires_night == DEFAULT_RULES.diplomatic_pact_duration_nights
    assert any("pacte de coopération" in event.message for event in events)


def test_one_sided_diplomacy_does_not_create_pact():
    state = create_initial_game_state()
    action = reciprocal_primogen_diplomacy()[0]
    events = resolve_actions_simultaneously(state, [action])
    state.events.extend(events)

    assert active_pact_between(state, "ventrue", "toreador") is None


def test_existing_pact_adds_configured_bonus_to_future_diplomacy():
    pact_state = create_initial_game_state()
    seed_pact(pact_state)
    pact_state.night = 2
    control_state = deepcopy(pact_state)
    control_state.events = [
        event for event in control_state.events if not event.category.startswith("diplomatic_pact|")
    ]

    action = GameAction(
        clan_id="ventrue",
        action_type=ActionType.DIPLOMACY,
        actor_character_id="primogen_ventrue",
        target_character_id="primogen_toreador",
    )
    pact_before = pact_state.clan_states["ventrue"].relations.get("toreador", 0.0)
    control_before = control_state.clan_states["ventrue"].relations.get("toreador", 0.0)
    pact_events = resolve_actions_simultaneously(pact_state, [action])
    resolve_actions_simultaneously(control_state, [action])

    pact_gain = pact_state.clan_states["ventrue"].relations["toreador"] - pact_before
    control_gain = control_state.clan_states["ventrue"].relations["toreador"] - control_before
    assert pact_gain == control_gain + DEFAULT_RULES.diplomatic_pact_diplomacy_bonus
    assert any("pacte actif" in event.message.lower() for event in pact_events)


def test_hostile_executed_action_breaks_active_pact_with_consequences():
    state = create_initial_game_state()
    seed_pact(state)
    state.night = 2
    relation_before = state.clan_states["ventrue"].relations.get("toreador", 0.0)
    stability_before = state.camarilla_stability

    action = GameAction(
        clan_id="ventrue",
        action_type=ActionType.UNDERMINE,
        actor_character_id="primogen_ventrue",
        target_character_id="toreador_camille",
    )
    events = resolve_actions_simultaneously(state, [action])
    state.events.extend(events)

    pact = list_diplomatic_pacts(state)[0]
    assert pact.status == BROKEN
    assert pact.broken_by_clan_id == "ventrue"
    assert state.clan_states["ventrue"].relations["toreador"] == (
        relation_before - DEFAULT_RULES.diplomatic_pact_breach_relation_loss
    )
    assert state.camarilla_stability == (
        stability_before - DEFAULT_RULES.diplomatic_pact_breach_stability_loss
    )
    assert any(
        grievance.owner_id == "primogen_toreador"
        and grievance.target_id == "primogen_ventrue"
        for grievance in state.grievances.values()
    )
    assert any("rompt son pacte" in event.message for event in events)


def test_refused_hostile_order_does_not_break_pact():
    state = create_initial_game_state()
    seed_pact(state, "brujah", "ventrue")
    state.night = 2
    action = GameAction(
        clan_id="brujah",
        action_type=ActionType.UNDERMINE,
        actor_character_id="brujah_sarah",
        target_character_id="ventrue_victor",
    )

    events = resolve_actions_simultaneously(state, [action])
    state.events.extend(events)

    assert any(event.category == "opposition" for event in events)
    assert active_pact_between(state, "brujah", "ventrue") is not None
    assert not any("rompt son pacte" in event.message for event in events)


def test_pact_survives_serialization_and_expires_after_configured_duration():
    state = create_initial_game_state()
    seed_pact(state)

    restored = game_state_from_json(game_state_to_json(state))
    assert active_pact_between(restored, "ventrue", "toreador") is not None

    restored.night = 1 + DEFAULT_RULES.diplomatic_pact_duration_nights
    pact = list_diplomatic_pacts(restored)[0]
    assert pact.status == EXPIRED
    assert active_pact_between(restored, "ventrue", "toreador") is None
