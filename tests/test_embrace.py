import pytest

from game.config import DEFAULT_RULES
from game.embrace import calculate_embrace_cost, create_embrace_request, decide_embrace_request
from game.models import Candidate, EmbraceStatus, PrimogenPosition
from game.offices import install_prince
from game.world import create_initial_game_state


def state_with_ventrue_prince():
    state = create_initial_game_state()
    install_prince(
        state,
        Candidate("primogen_ventrue", "Adrien de Keravel", "ventrue", True),
    )
    return state


def test_embrace_cost_rewards_external_and_primogen_aligned_request():
    state = state_with_ventrue_prince()
    cost = calculate_embrace_cost(
        state,
        "toreador_camille",
        PrimogenPosition.SUPPORT,
    )
    assert cost == 4


def test_embrace_cost_penalises_same_clan_opposition_against_primogen():
    state = state_with_ventrue_prince()
    cost = calculate_embrace_cost(
        state,
        "ventrue_claire",
        PrimogenPosition.OPPOSE,
    )
    assert cost == 20


def test_approval_deducts_capital_and_strengthens_requester_current():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "toreador_camille",
        "Adele",
        PrimogenPosition.SUPPORT,
    )
    before = state.clan_states["toreador"].clan.dominant_current.influence
    state = decide_embrace_request(state, "embrace_1", True)
    request = state.embrace_requests["embrace_1"]
    assert request.status == EmbraceStatus.APPROVED
    assert state.prince_political_capital == DEFAULT_RULES.prince_initial_capital - request.political_cost
    assert state.clan_states["toreador"].clan.dominant_current.influence == before + DEFAULT_RULES.embrace_current_influence_gain
    assert state.prince_relations["toreador"] == DEFAULT_RULES.approve_relation_support


def test_refusal_has_political_consequences():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "brujah_sarah",
        "Noe",
        PrimogenPosition.OPPOSE,
    )
    before = state.clan_states["brujah"].opposition_loyalty
    state = decide_embrace_request(state, "embrace_1", False)
    assert state.embrace_requests["embrace_1"].status == EmbraceStatus.REFUSED
    assert state.prince_relations["brujah"] == DEFAULT_RULES.refuse_relation_oppose
    assert state.clan_states["brujah"].opposition_loyalty == before + DEFAULT_RULES.opposition_loyalty_refuse_oppose


def test_approval_fails_when_prince_lacks_capital():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "ventrue_claire",
        "Alix",
        PrimogenPosition.OPPOSE,
    )
    state.prince_political_capital = 0
    with pytest.raises(ValueError, match="Insufficient"):
        decide_embrace_request(state, "embrace_1", True)
