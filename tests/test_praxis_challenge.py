from dataclasses import replace

import pytest

from game.config import DEFAULT_RULES
from game.models import (
    ActionType,
    Candidate,
    EmbracePetitionOrder,
    GameAction,
    PrimogenVote,
)
from game.offices import install_prince
from game.politics import determine_current_stances, primogen_political_weights
from game.praxis_challenge import resolve_praxis_challenge
from game.resolution import resolve_night
from game.serialization import clan_orders_from_json, clan_orders_to_json
from game.models import ClanNightOrders
from game.world import candidates_from_state, create_initial_game_state


def state_with_external_prince():
    state = create_initial_game_state()
    install_prince(state, Candidate("prince_test", "Prince Test", None, False))
    return state


def challenge_action(state, clan_id):
    return GameAction(
        clan_id=clan_id,
        action_type=ActionType.CHALLENGE_PRAXIS,
        actor_character_id=state.clan_states[clan_id].clan.primogen_id,
    )


def test_two_weighted_primogens_can_break_recognition_of_praxis():
    state = state_with_external_prince()
    old_prince_id = state.prince_id
    old_status = state.characters[old_prince_id].status
    stability_before = state.camarilla_stability
    masquerade_before = state.masquerade_integrity

    result = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue"), challenge_action(state, "toreador")],
        votes={},
        candidates=candidates_from_state(state),
    )

    assert result.state.prince_id is None
    assert result.state.praxis_status == "contested"
    assert result.vote is None
    assert result.state.night == state.night + 1
    assert result.state.characters[old_prince_id].status == old_status - DEFAULT_RULES.deposed_prince_status_loss
    assert result.state.camarilla_stability == stability_before - DEFAULT_RULES.praxis_challenge_success_stability_loss
    assert result.state.masquerade_integrity == masquerade_before - DEFAULT_RULES.praxis_challenge_success_masquerade_loss
    assert any("reconnaissance" in event.message and "s'effondre" in event.message for event in result.state.events)


def test_single_primogen_challenge_fails_and_costs_prince_relation():
    state = state_with_external_prince()
    relation_before = state.prince_relations["ventrue"]
    stability_before = state.camarilla_stability
    prince_id = state.prince_id
    primogen_id = state.clan_states["ventrue"].clan.primogen_id

    result = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue")],
        votes={},
        candidates=candidates_from_state(state),
    )

    assert result.state.prince_id == prince_id
    assert result.state.praxis_status == "recognized"
    assert result.state.prince_relations["ventrue"] == (
        relation_before - DEFAULT_RULES.praxis_challenge_failure_prince_relation_loss
    )
    assert result.state.camarilla_stability == stability_before - DEFAULT_RULES.praxis_challenge_failure_stability_loss
    assert any(
        grievance.owner_id == prince_id and grievance.target_id == primogen_id
        for grievance in result.state.grievances.values()
    )


def test_challenge_weight_uses_beginning_of_action_phase_snapshot():
    state = state_with_external_prince()
    reference = state_with_external_prince()
    challenges = [challenge_action(state, "ventrue"), challenge_action(state, "toreador")]

    stances = determine_current_stances(reference)
    weights, _ = primogen_political_weights(
        reference,
        stances,
        DEFAULT_RULES.opposition_transfer_ratio,
    )
    expected_support = weights[reference.clan_states["ventrue"].clan.primogen_id] + weights[
        reference.clan_states["toreador"].clan.primogen_id
    ]

    # Simule un gain massif qui arrive après le snapshot : il ne doit pas changer
    # le poids déjà engagé dans la contestation.
    state.characters[state.clan_states["ventrue"].clan.primogen_id].personal_influence += 1000
    resolution, _ = resolve_praxis_challenge(
        state,
        challenges,
        reference_state=reference,
    )

    assert resolution is not None
    assert resolution.support_influence == expected_support


def test_deposed_prince_can_be_recognized_again_on_following_night():
    state = state_with_external_prince()
    old_prince_id = state.prince_id
    challenged = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue"), challenge_action(state, "toreador")],
        votes={},
        candidates=candidates_from_state(state),
    ).state
    assert challenged.prince_id is None

    votes = {
        clan_state.clan.primogen_id: PrimogenVote(clan_state.clan.primogen_id, old_prince_id)
        for clan_state in challenged.clan_states.values()
    }
    recognized = resolve_night(
        challenged,
        actions=[],
        votes=votes,
        candidates=candidates_from_state(challenged),
    )

    assert recognized.state.prince_id == old_prince_id
    assert recognized.state.praxis_status == "recognized"


def test_embrace_petition_same_night_as_successful_challenge_becomes_moot():
    state = state_with_external_prince()
    request_member = "toreador_camille"

    result = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue"), challenge_action(state, "toreador")],
        votes={},
        candidates=candidates_from_state(state),
        embrace_petitions=[("toreador", EmbracePetitionOrder(request_member, "Adele"))],
    )

    assert result.state.prince_id is None
    assert not result.state.embrace_requests
    assert any("n'est pas examinée" in event.message for event in result.state.events)


def test_custom_threshold_can_make_two_primogen_challenge_fail():
    state = state_with_external_prince()
    strict_rules = replace(DEFAULT_RULES, praxis_challenge_threshold=0.99)

    result = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue"), challenge_action(state, "toreador")],
        votes={},
        candidates=candidates_from_state(state),
        rules=strict_rules,
    )
    assert result.state.prince_id == "prince_test"


def test_challenge_action_round_trips_in_existing_order_format():
    state = state_with_external_prince()
    action = challenge_action(state, "ventrue")
    orders = ClanNightOrders(clan_id="ventrue", actions=(action,), version=4)

    restored = clan_orders_from_json(clan_orders_to_json(orders))
    assert restored.actions[0].action_type == ActionType.CHALLENGE_PRAXIS


def test_non_primogen_cannot_challenge_praxis():
    state = state_with_external_prince()
    action = GameAction(
        clan_id="ventrue",
        action_type=ActionType.CHALLENGE_PRAXIS,
        actor_character_id="ventrue_victor",
    )
    with pytest.raises(ValueError, match="current Primogen"):
        resolve_night(
            state,
            actions=[action],
            votes={},
            candidates=candidates_from_state(state),
        )
