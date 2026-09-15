from game.config import DEFAULT_RULES
from game.court import (
    current_court_issue,
    embrace_approval_score,
    prince_should_approve_embrace,
    resolve_court_agenda,
)
from game.domains import open_domain_dispute
from game.embrace import calculate_embrace_cost
from game.models import (
    Candidate,
    DomainDisputeStatus,
    PrimogenPosition,
)
from game.offices import install_prince
from game.resolution import resolve_night
from game.world import candidates_from_state, create_initial_game_state


def state_with_outsider_prince():
    state = create_initial_game_state()
    install_prince(state, Candidate("prince_test", "Ariane de Rohan"))
    return state


def state_with_ventrue_prince():
    state = create_initial_game_state()
    install_prince(
        state,
        Candidate("primogen_ventrue", "Adrien de Keravel", "ventrue", True),
    )
    return state


def test_no_court_agenda_exists_without_prince():
    state = create_initial_game_state()
    assert current_court_issue(state) is None


def test_new_domain_dispute_has_one_night_diplomatic_window_before_court():
    state = state_with_outsider_prince()
    dispute = open_domain_dispute(
        state,
        domain_id="vieux_centre",
        claimant_id="ventrue_claire",
        respondent_id="brujah_sarah",
        reason="Contestations croisées sur les limites de chasse",
        severity=2,
        public=True,
    )

    assert dispute.created_night == state.night
    assert current_court_issue(state) is None

    state.night += 1
    issue = current_court_issue(state)
    assert issue is not None
    assert issue.kind == "domain_arbitration"
    assert issue.reference_id == dispute.id


def test_prince_arbitrates_old_domain_dispute_from_status_relations_and_precedent():
    state = state_with_outsider_prince()
    dispute = open_domain_dispute(
        state,
        domain_id="vieux_centre",
        claimant_id="ventrue_claire",
        respondent_id="brujah_sarah",
        reason="Contestations croisées sur les limites de chasse",
        severity=2,
        public=True,
    )
    state.night += 1
    before_capital = state.prince_political_capital

    events = resolve_court_agenda(state)

    assert len(events) == 1
    assert "Claire Beaumont" in events[0].message
    assert state.domain_disputes[dispute.id].status == DomainDisputeStatus.RESOLVED
    assert state.prince_political_capital == before_capital - DEFAULT_RULES.prince_domain_arbitration_cost
    assert state.prince_relations["ventrue"] == 1
    assert state.prince_relations["brujah"] == -2
    assert any(
        grievance.owner_id == "brujah_sarah"
        and grievance.target_id == state.prince_id
        for grievance in state.grievances.values()
    )


def test_prince_confirming_own_decree_never_creates_self_grievance():
    state = state_with_outsider_prince()
    dispute = open_domain_dispute(
        state,
        domain_id="vieux_centre",
        claimant_id="ventrue_claire",
        respondent_id=state.prince_id,
        reason="Claire conteste un décret territorial du Prince",
        severity=2,
        public=True,
    )
    state.night += 1

    events = resolve_court_agenda(state)

    assert state.domain_disputes[dispute.id].status == DomainDisputeStatus.RESOLVED
    assert "confirme son autorité" in events[0].message
    assert any(
        grievance.owner_id == "ventrue_claire"
        and grievance.target_id == state.prince_id
        for grievance in state.grievances.values()
    )
    assert not any(
        grievance.owner_id == state.prince_id and grievance.target_id == state.prince_id
        for grievance in state.grievances.values()
    )


def test_humanist_prince_spends_capital_to_contain_masquerade_crisis():
    state = state_with_outsider_prince()
    state.masquerade_integrity = 95
    before_capital = state.prince_political_capital
    issue = current_court_issue(state)
    assert issue is not None and issue.kind == "masquerade_crisis"

    resolve_court_agenda(state)

    assert state.masquerade_integrity == 98
    assert state.camarilla_stability == 100
    assert state.prince_political_capital == before_capital - DEFAULT_RULES.prince_masquerade_response_cost


def test_prince_conciliates_weakest_clan_during_stability_crisis():
    state = state_with_outsider_prince()
    state.camarilla_stability = 93
    state.prince_relations.update({"brujah": -4, "toreador": 0, "ventrue": 1})
    before_capital = state.prince_political_capital
    issue = current_court_issue(state)
    assert issue is not None and issue.kind == "stability_crisis"

    resolve_court_agenda(state)

    assert state.camarilla_stability == 96
    assert state.prince_relations["brujah"] == -2
    assert state.prince_political_capital == before_capital - DEFAULT_RULES.prince_stability_response_cost


def test_embrace_decision_distinguishes_supported_member_from_opposition_member():
    state = state_with_ventrue_prince()
    camille_cost = calculate_embrace_cost(state, "toreador_camille", PrimogenPosition.SUPPORT)
    sarah_cost = calculate_embrace_cost(state, "brujah_sarah", PrimogenPosition.SUPPORT)

    camille_score = embrace_approval_score(state, "toreador_camille", camille_cost)
    sarah_score = embrace_approval_score(state, "brujah_sarah", sarah_cost)

    assert camille_score > sarah_score
    assert prince_should_approve_embrace(state, "toreador_camille", camille_cost) is True
    assert prince_should_approve_embrace(state, "brujah_sarah", sarah_cost) is False


def test_court_agenda_is_resolved_inside_night_pipeline_for_existing_prince():
    state = state_with_outsider_prince()
    dispute = open_domain_dispute(
        state,
        domain_id="vieux_centre",
        claimant_id="ventrue_claire",
        respondent_id="brujah_sarah",
        reason="Litige ancien soumis à la Cour",
        severity=2,
        public=True,
    )
    state.night = 2

    result = resolve_night(
        state,
        [],
        {},
        candidates_from_state(state),
    ).state

    assert result.domain_disputes[dispute.id].status == DomainDisputeStatus.RESOLVED
    assert any(event.category == "cour" for event in result.events)
