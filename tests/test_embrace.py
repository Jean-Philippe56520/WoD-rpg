import pytest

from game.config import DEFAULT_RULES
from game.coteries import coterie_influence
from game.embrace import (
    calculate_embrace_cost,
    create_embrace_request,
    decide_embrace_request,
    process_primogen_petition,
)
from game.models import (
    Candidate,
    CoterieSide,
    EmbracePetitionOrder,
    EmbraceStatus,
    PrimogenPosition,
)
from game.offices import install_prince
from game.world import create_initial_game_state


def state_with_ventrue_prince():
    state = create_initial_game_state()
    install_prince(
        state,
        Candidate("primogen_ventrue", "Adrien de Keravel", "ventrue", True),
    )
    return state


def test_embrace_cost_rewards_external_and_primogen_coterie_request():
    state = state_with_ventrue_prince()
    cost = calculate_embrace_cost(state, "toreador_camille", PrimogenPosition.SUPPORT)
    assert cost == 4


def test_embrace_cost_penalises_same_clan_opposition_request_against_primogen():
    state = state_with_ventrue_prince()
    assert state.clan_states["ventrue"].coterie_memberships["ventrue_claire"] == CoterieSide.OPPOSITION
    cost = calculate_embrace_cost(state, "ventrue_claire", PrimogenPosition.OPPOSE)
    assert cost == 20


def test_approval_deducts_capital_and_strengthens_requesters_coterie_influence():
    state = state_with_ventrue_prince()
    before_coterie = coterie_influence(state, "toreador", CoterieSide.PRIMOGEN)
    before_personal = state.characters["toreador_camille"].personal_influence
    state = create_embrace_request(
        state, "toreador_camille", "Adele", PrimogenPosition.SUPPORT
    )
    state = decide_embrace_request(state, "embrace_1", True)
    request = state.embrace_requests["embrace_1"]
    assert request.status == EmbraceStatus.APPROVED
    assert state.prince_political_capital == DEFAULT_RULES.prince_initial_capital - request.political_cost
    assert state.characters["toreador_camille"].personal_influence == before_personal + DEFAULT_RULES.embrace_requester_influence_gain
    assert coterie_influence(state, "toreador", CoterieSide.PRIMOGEN) == before_coterie + DEFAULT_RULES.embrace_requester_influence_gain
    assert state.prince_relations["toreador"] == DEFAULT_RULES.approve_relation_support


def test_refusal_changes_prince_relation_without_artificially_moving_opposition_member():
    state = state_with_ventrue_prince()
    sarah = state.characters["brujah_sarah"]
    before_relation = sarah.relation_to_primogen
    before_side = state.clan_states["brujah"].coterie_memberships[sarah.id]
    state = create_embrace_request(state, sarah.id, "Noe", PrimogenPosition.OPPOSE)
    state = decide_embrace_request(state, "embrace_1", False)
    assert state.embrace_requests["embrace_1"].status == EmbraceStatus.REFUSED
    assert state.prince_relations["brujah"] == DEFAULT_RULES.refuse_relation_oppose
    assert state.characters[sarah.id].relation_to_primogen == before_relation
    assert state.clan_states["brujah"].coterie_memberships[sarah.id] == before_side


def test_primogen_coterie_request_remains_in_same_coterie_after_refusal():
    state = state_with_ventrue_prince()
    before = state.clan_states["toreador"].coterie_memberships["toreador_camille"]
    state = create_embrace_request(state, "toreador_camille", "Mila", PrimogenPosition.SUPPORT)
    state = decide_embrace_request(state, "embrace_1", False)
    assert state.clan_states["toreador"].coterie_memberships["toreador_camille"] == before


def test_approval_fails_when_prince_lacks_capital():
    state = state_with_ventrue_prince()
    state = create_embrace_request(state, "ventrue_claire", "Alix", PrimogenPosition.OPPOSE)
    state.prince_political_capital = 0
    with pytest.raises(ValueError, match="Insufficient"):
        decide_embrace_request(state, "embrace_1", True)


def test_primogen_must_submit_request_for_another_member():
    state = state_with_ventrue_prince()
    current_primogen = state.clan_states["ventrue"].clan.primogen_id
    with pytest.raises(ValueError, match="another clan member"):
        create_embrace_request(
            state,
            current_primogen,
            "Alix",
            PrimogenPosition.SUPPORT,
            submitted_by_primogen_id=current_primogen,
        )


def test_primogen_petition_records_official_submitter():
    state = state_with_ventrue_prince()
    current_primogen = state.clan_states["toreador"].clan.primogen_id
    state = process_primogen_petition(
        state,
        "toreador",
        EmbracePetitionOrder("toreador_camille", "Adele"),
    )
    request = list(state.embrace_requests.values())[-1]
    assert request.submitted_by_primogen_id == current_primogen
    assert request.requester_id == "toreador_camille"
