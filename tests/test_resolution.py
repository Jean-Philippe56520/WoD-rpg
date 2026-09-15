from copy import deepcopy

import pytest

from game.actions import apply_action
from game.config import DEFAULT_RULES
from game.ideology import build_currents
from game.models import ActionType, AxisPolarity, Candidate, GameAction, PrimogenVote
from game.politics import determine_current_stances
from game.resolution import resolve_night
from game.world import create_initial_game_state, seed_candidates


def self_votes(state):
    return {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, cs.clan.primogen_id)
        for cs in state.clan_states.values()
    }


def test_rally_action_can_flip_one_specific_current_support():
    state = create_initial_game_state()
    target = "ventrue__humanist_reformist"
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.RALLY_OPPOSITION, target_current_id=target)],
        self_votes(state),
        seed_candidates(),
    )
    assert resolution.state.clan_states["ventrue"].current_loyalties[target] == 60
    assert determine_current_stances(resolution.state)[target].supports_primogen is True
    assert state.clan_states["ventrue"].current_loyalties[target] == 48


def test_consolidate_strengthens_primogen_but_irritates_rival_currents():
    state = create_initial_game_state()
    before = state.characters["primogen_ventrue"].personal_influence
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.CONSOLIDATE)],
        self_votes(state),
        seed_candidates(),
    )
    new_state = resolution.state
    assert new_state.characters["primogen_ventrue"].personal_influence == before + 3
    assert new_state.clan_states["ventrue"].current_loyalties["ventrue__humanist_reformist"] == 44
    assert new_state.clan_states["ventrue"].current_loyalties["ventrue__humanist_traditional"] == 51
    assert new_state.night == 2


def test_build_influence_changes_members_and_therefore_current_influence():
    state = create_initial_game_state()
    before = build_currents(state, "ventrue")["ventrue__predatory_traditional"].influence
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.BUILD_INFLUENCE)],
        self_votes(state),
        seed_candidates(),
    )
    new_state = resolution.state
    after = build_currents(new_state, "ventrue")["ventrue__predatory_traditional"].influence
    assert new_state.characters["primogen_ventrue"].personal_influence == 24
    assert new_state.characters["ventrue_victor"].personal_influence == 19
    assert after == before + 3


def test_diplomacy_is_easier_between_ideologically_aligned_primogens():
    aligned = create_initial_game_state()
    opposed = deepcopy(aligned)
    a = aligned.characters["primogen_ventrue"]
    b = aligned.characters["primogen_toreador"]
    b.humanity_axis, b.tradition_axis = a.humanity_axis, a.tradition_axis
    a2 = opposed.characters["primogen_ventrue"]
    b2 = opposed.characters["primogen_toreador"]
    b2.humanity_axis = (
        AxisPolarity.MINUS if a2.humanity_axis == AxisPolarity.PLUS else AxisPolarity.PLUS
    )
    b2.tradition_axis = (
        AxisPolarity.MINUS if a2.tradition_axis == AxisPolarity.PLUS else AxisPolarity.PLUS
    )
    apply_action(aligned, GameAction("ventrue", ActionType.DIPLOMACY, "toreador"))
    apply_action(opposed, GameAction("ventrue", ActionType.DIPLOMACY, "toreador"))
    assert aligned.clan_states["ventrue"].relations["toreador"] > opposed.clan_states["ventrue"].relations["toreador"]


def test_more_than_action_budget_is_rejected():
    state = create_initial_game_state()
    actions = [
        GameAction("ventrue", ActionType.CONSOLIDATE),
        GameAction("ventrue", ActionType.BUILD_INFLUENCE),
        GameAction("ventrue", ActionType.DIPLOMACY, "toreador"),
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


def test_primogen_majority_becomes_prince_and_seat_is_replaced():
    state = create_initial_game_state()
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_ventrue"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }
    resolution = resolve_night(state, [], votes, seed_candidates())
    new_state = resolution.state
    assert new_state.prince_id == "primogen_ventrue"
    assert new_state.characters["primogen_ventrue"].is_primogen is False
    assert new_state.clan_states["ventrue"].clan.primogen_id == "ventrue_victor"
    assert new_state.prince_political_capital == DEFAULT_RULES.prince_initial_capital


def test_non_primogen_majority_can_become_prince():
    state = create_initial_game_state()
    outsider = Candidate(id="outsider_test", name="Helene d'Arvor", is_primogen=False)
    candidates = seed_candidates() + [outsider]
    votes = {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, outsider.id)
        for cs in state.clan_states.values()
    }
    resolution = resolve_night(state, [], votes, candidates)
    assert resolution.state.prince_id == outsider.id
    assert resolution.state.characters[outsider.id].is_primogen is False
