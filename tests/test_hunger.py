import pytest

from game.character_rules import attribute_value
from game.domains import grant_hunting_right
from game.hunger import (
    active_hunting_access_domains,
    hunger_penalty,
    resolve_hunger,
)
from game.models import ActionType, Character, CharacterAttribute, GameAction
from game.serialization import game_state_from_dict, game_state_from_json, game_state_to_dict, game_state_to_json
from game.simultaneous import resolve_actions_simultaneously
from game.world import create_initial_game_state


def test_character_hunger_is_bounded_zero_to_five():
    assert Character("test", "Test", hunger=0).hunger == 0
    assert Character("test", "Test", hunger=5).hunger == 5
    with pytest.raises(ValueError, match="Hunger"):
        Character("test", "Test", hunger=6)


def test_hunger_round_trip_is_persistent_and_old_states_default_to_one():
    state = create_initial_game_state()
    state.characters["ventrue_victor"].hunger = 4

    restored = game_state_from_json(game_state_to_json(state))
    assert restored.characters["ventrue_victor"].hunger == 4

    legacy = game_state_to_dict(state)
    for character in legacy["characters"].values():
        character.pop("hunger", None)
    restored_legacy = game_state_from_dict(legacy)
    assert all(character.hunger == 1 for character in restored_legacy.characters.values())


def test_legal_hunting_access_reduces_hunger_without_spending_action():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    victor.hunger = 4
    grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id=victor.id,
        granted_by_id="primogen_ventrue",
        duration_nights=3,
    )

    assert "quartier_affaires" in active_hunting_access_domains(state, victor.id)
    events = resolve_hunger(state)

    assert victor.hunger == 3
    assert any(victor.name in event.message for event in events)


def test_vampire_without_hunting_access_gets_hungrier():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    assert active_hunting_access_domains(state, victor.id) == ()

    resolve_hunger(state)

    assert victor.hunger == 2


def test_hunting_right_is_not_usable_after_its_expiry_night():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id=victor.id,
        granted_by_id="primogen_ventrue",
        duration_nights=1,
    )
    assert active_hunting_access_domains(state, victor.id) == ("quartier_affaires",)

    state.night = 2
    assert active_hunting_access_domains(state, victor.id) == ()


def test_high_hunger_penalises_social_and_mental_but_not_physical():
    vampire = Character("test", "Test", social=2, mental=2, physical=2, hunger=5)
    assert hunger_penalty(vampire.hunger) == 2
    assert attribute_value(vampire, CharacterAttribute.SOCIAL) == 0
    assert attribute_value(vampire, CharacterAttribute.MENTAL) == 0
    assert attribute_value(vampire, CharacterAttribute.PHYSICAL) == 2


def test_successful_braconnage_feeds_before_end_of_night_hunger_pressure():
    state = create_initial_game_state()
    gabriel = state.characters["toreador_gabriel"]
    gabriel.hunger = 4
    action = GameAction(
        clan_id="toreador",
        action_type=ActionType.BRACONNAGE,
        actor_character_id=gabriel.id,
        target_domain_id="docks",
    )

    events = resolve_actions_simultaneously(state, [action])
    assert gabriel.hunger == 2
    assert any("apaise sa Faim" in event.message for event in events)

    resolve_hunger(state)
    assert gabriel.hunger == 3
