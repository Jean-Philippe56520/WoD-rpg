import pytest

from game.config import DEFAULT_RULES
from game.models import ActionType, GameAction, PrimogenVote
from game.politics import determine_opposition_stances
from game.resolution import resolve_night
from game.world import create_initial_game_state, seed_candidates


def self_votes(state):
    return {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, cs.clan.primogen_id)
        for cs in state.clan_states.values()
    }


def test_initial_opposition_decisions_are_autonomous():
    state = create_initial_game_state()
    stances = determine_opposition_stances(state)

    assert stances["ventrue"].supports_primogen is False
    assert stances["ventrue"].allied_primogen_id == "primogen_toreador"
    assert stances["toreador"].supports_primogen is True


def test_rally_action_can_flip_opposition_support():
    state = create_initial_game_state()
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.RALLY_OPPOSITION)],
        self_votes(state),
        seed_candidates(),
    )

    assert resolution.state.clan_states["ventrue"].opposition_loyalty == 60
    assert determine_opposition_stances(resolution.state)["ventrue"].supports_primogen is True
    assert state.clan_states["ventrue"].opposition_loyalty == 48


def test_consolidate_moves_influence_and_advances_night():
    state = create_initial_game_state()
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.CONSOLIDATE)],
        self_votes(state),
        seed_candidates(),
    )

    ventrue = resolution.state.clan_states["ventrue"]
    assert ventrue.clan.dominant_current.influence == 64
    assert ventrue.clan.opposition_current.influence == 36
    assert resolution.state.night == 2
    assert resolution.state.events


def test_more_than_action_budget_is_rejected():
    state = create_initial_game_state()
    actions = [
        GameAction("ventrue", ActionType.RALLY_OPPOSITION),
        GameAction("ventrue", ActionType.BUILD_INFLUENCE),
        GameAction("ventrue", ActionType.CONSOLIDATE),
    ]

    with pytest.raises(ValueError, match="maximum"):
        resolve_night(state, actions, self_votes(state), seed_candidates())


def test_disputed_praxis_weakens_camarilla_and_masquerade():
    state = create_initial_game_state()
    resolution = resolve_night(state, [], self_votes(state), seed_candidates())

    assert resolution.vote is not None and resolution.vote.disputed is True
    assert resolution.state.praxis_status == "contested"
    assert resolution.state.camarilla_stability == 100 - DEFAULT_RULES.disputed_stability_loss
    assert resolution.state.masquerade_integrity == 100 - DEFAULT_RULES.disputed_masquerade_loss


def test_primogen_majority_enters_transition_not_dual_office():
    state = create_initial_game_state()
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_ventrue"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }
    resolution = resolve_night(state, [], votes, seed_candidates())

    assert resolution.vote is not None
    assert resolution.vote.winner_id == "primogen_ventrue"
    assert resolution.state.praxis_status == "transition"
    assert resolution.state.prince_id is None


def test_non_primogen_majority_can_become_prince():
    from game.models import Candidate

    state = create_initial_game_state()
    outsider = Candidate(id="outsider_test", name="Hélène d'Arvor", is_primogen=False)
    candidates = seed_candidates() + [outsider]
    votes = {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, outsider.id)
        for cs in state.clan_states.values()
    }

    resolution = resolve_night(state, [], votes, candidates)

    assert resolution.vote is not None and resolution.vote.winner_id == outsider.id
    assert resolution.state.prince_id == outsider.id
    assert resolution.state.praxis_status == "recognized"
