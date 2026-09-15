from game.external_pressures import current_external_pressures
from game.models import ActionType, Candidate, GameAction
from game.offices import install_prince
from game.resolution import resolve_night
from game.world import candidates_from_state, create_initial_game_state


def challenge_action(state, clan_id):
    return GameAction(
        clan_id=clan_id,
        action_type=ActionType.CHALLENGE_PRAXIS,
        actor_character_id=state.clan_states[clan_id].clan.primogen_id,
    )


def test_successful_praxis_challenge_immediately_opens_anarch_window():
    state = create_initial_game_state()
    install_prince(state, Candidate("prince_test", "Prince Test", None, False))

    result = resolve_night(
        state,
        actions=[challenge_action(state, "ventrue"), challenge_action(state, "toreador")],
        votes={},
        candidates=candidates_from_state(state),
    )

    assert result.state.prince_id is None
    pressure = current_external_pressures(result.state)
    assert pressure.anarch_pressure > 0
    assert any("agitation anarch" in event.message for event in result.state.events)
