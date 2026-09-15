import pytest

from game.actions import apply_action
from game.domains import (
    assign_domain_holder,
    expire_hunting_rights,
    grant_hunting_right,
    has_hunting_access,
    resolve_domain_pressure,
    revoke_hunting_right,
)
from game.models import (
    ActionType,
    BoonLevel,
    DomainDisputeStatus,
    GameAction,
    HuntingRightStatus,
    PoliticalRequestStatus,
    PoliticalRequestType,
    RequestDecision,
)
from game.offices import install_prince
from game.social_politics import fulfill_promise, generate_requests_for_night, process_request_decision
from game.world import candidates_from_state, create_initial_game_state


def test_initial_city_has_six_asymmetric_domains_with_canonical_terms():
    state = create_initial_game_state()
    assert len(state.domains) == 6
    assert state.domains["quartier_affaires"].viandis == 2
    assert state.domains["quartier_affaires"].servage == 3
    assert state.domains["vieux_centre"].rempart == 3
    assert state.domains["quartier_arts"].viandis == 3


def test_opposition_members_can_hold_domains_independently_from_primogen():
    state = create_initial_game_state()
    assert state.domains["vieux_centre"].holder_id == "ventrue_claire"
    assert state.domains["faubourgs"].holder_id == "brujah_sarah"
    assert state.clan_states["ventrue"].opposition_leader_id == "ventrue_claire"
    assert state.clan_states["brujah"].opposition_leader_id == "brujah_sarah"


def test_hunting_right_is_distinct_from_domain_ownership():
    state = create_initial_game_state()
    right = grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id="ventrue_helene",
        granted_by_id="primogen_ventrue",
        duration_nights=3,
    )
    assert right.status == HuntingRightStatus.ACTIVE
    assert state.domains["quartier_affaires"].holder_id == "primogen_ventrue"
    assert has_hunting_access(state, "ventrue_helene", "quartier_affaires")


def test_hunting_right_duration_counts_exact_nights_from_grant_night():
    state = create_initial_game_state()
    right = grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id="ventrue_helene",
        granted_by_id="primogen_ventrue",
        duration_nights=3,
    )
    assert right.expires_night == state.night + 2
    state.night = right.expires_night
    assert expire_hunting_rights(state) == []
    assert right.status == HuntingRightStatus.ACTIVE
    state.night += 1
    assert expire_hunting_rights(state) == [right]
    assert right.status == HuntingRightStatus.EXPIRED


def test_non_holder_cannot_grant_hunting_right_without_being_prince():
    state = create_initial_game_state()
    with pytest.raises(ValueError, match="holder or Prince"):
        grant_hunting_right(
            state,
            domain_id="quartier_affaires",
            beneficiary_id="ventrue_helene",
            granted_by_id="ventrue_victor",
        )


def test_holder_can_revoke_a_right_without_transferring_domain():
    state = create_initial_game_state()
    right = grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id="ventrue_helene",
        granted_by_id="primogen_ventrue",
    )
    revoke_hunting_right(state, right.id, "primogen_ventrue")
    assert right.status == HuntingRightStatus.REVOKED
    assert state.domains["quartier_affaires"].holder_id == "primogen_ventrue"


def test_too_many_hunting_rights_create_pressure_beyond_viandis_capacity():
    state = create_initial_game_state()
    for beneficiary_id in ("ventrue_helene", "ventrue_victor", "toreador_lucien"):
        grant_hunting_right(
            state,
            domain_id="quartier_affaires",
            beneficiary_id=beneficiary_id,
            granted_by_id="primogen_ventrue",
        )
    assert state.domains["quartier_affaires"].pressure == 0
    resolve_domain_pressure(state)
    assert state.domains["quartier_affaires"].pressure == 1


def test_braconnage_raises_pressure_and_detected_intrusion_opens_dispute():
    state = create_initial_game_state()
    before = state.domains["vieux_centre"].pressure
    event = apply_action(
        state,
        GameAction(
            clan_id="brujah",
            action_type=ActionType.BRACONNAGE,
            actor_character_id="primogen_brujah",
            target_domain_id="vieux_centre",
        ),
    )
    assert state.domains["vieux_centre"].pressure > before
    assert state.domain_disputes
    dispute = next(iter(state.domain_disputes.values()))
    assert dispute.domain_id == "vieux_centre"
    assert dispute.status == DomainDisputeStatus.OPEN
    assert "Rempart" in event.message


def test_successful_domain_intrusion_builds_territorial_intelligence():
    state = create_initial_game_state()
    event = apply_action(
        state,
        GameAction(
            clan_id="toreador",
            action_type=ActionType.DOMAIN_INTRUSION,
            actor_character_id="toreador_camille",
            target_domain_id="vieux_centre",
        ),
    )
    assert state.clan_states["toreador"].known_domain_intel["vieux_centre"] == 1
    assert "renseignement territorial" in event.message


def test_holder_can_use_servage_to_reduce_pressure():
    state = create_initial_game_state()
    state.domains["quartier_affaires"].pressure = 4
    event = apply_action(
        state,
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.DOMAIN_STEWARD,
            actor_character_id="primogen_ventrue",
            target_domain_id="quartier_affaires",
        ),
    )
    assert state.domains["quartier_affaires"].pressure < 4
    assert "Servage" in event.message


def test_excessive_pressure_can_damage_masquerade():
    state = create_initial_game_state()
    domain = state.domains["quartier_arts"]
    domain.pressure = 10
    before = state.masquerade_integrity
    events = resolve_domain_pressure(state)
    assert state.masquerade_integrity == before - domain.masquerade_risk
    assert any(event.category == "mascarade" for event in events)


def test_gain_domain_ambition_generates_concrete_access_request():
    state = create_initial_game_state()
    state.political_requests.clear()
    state.characters["ventrue_helene"].ambition = 100
    created = generate_requests_for_night(state)
    request = next(item for item in created if item.clan_id == "ventrue")
    assert request.requester_id == "ventrue_helene"
    assert request.request_type == PoliticalRequestType.DOMAIN_ACCESS
    assert request.target_id == "quartier_affaires"


def test_accepting_domain_request_grants_access_and_can_create_boon():
    state = create_initial_game_state()
    state.political_requests.clear()
    state.characters["ventrue_helene"].ambition = 100
    request = next(
        item for item in generate_requests_for_night(state) if item.clan_id == "ventrue"
    )
    assert request.offered_boon_level == BoonLevel.MINOR
    process_request_decision(state, "ventrue", request.id, RequestDecision.ACCEPT)
    assert request.status == PoliticalRequestStatus.ACCEPTED
    assert has_hunting_access(state, "ventrue_helene", "quartier_affaires")
    assert any(
        boon.creditor_id == "primogen_ventrue"
        and boon.debtor_id == "ventrue_helene"
        for boon in state.boons.values()
    )


def test_promised_domain_access_can_be_explicitly_fulfilled():
    state = create_initial_game_state()
    state.political_requests.clear()
    state.characters["ventrue_helene"].ambition = 100
    request = next(
        item for item in generate_requests_for_night(state) if item.clan_id == "ventrue"
    )
    process_request_decision(state, "ventrue", request.id, RequestDecision.PROMISE)
    promise = next(
        promise for promise in state.promises.values() if promise.request_id == request.id
    )
    fulfill_promise(state, promise.id)
    assert request.status == PoliticalRequestStatus.RESOLVED
    assert has_hunting_access(state, "ventrue_helene", "quartier_affaires")


def test_primogen_succession_does_not_transfer_personal_domain_to_successor():
    state = create_initial_game_state()
    winner = next(
        candidate for candidate in candidates_from_state(state) if candidate.id == "primogen_ventrue"
    )
    install_prince(state, winner)
    assert state.prince_id == "primogen_ventrue"
    assert state.clan_states["ventrue"].clan.primogen_id != "primogen_ventrue"
    assert state.domains["quartier_affaires"].holder_id == "primogen_ventrue"


def test_only_recognized_prince_can_reassign_domain_and_old_holder_can_contest():
    state = create_initial_game_state()
    with pytest.raises(ValueError, match="recognized Prince"):
        assign_domain_holder(
            state,
            domain_id="vieux_centre",
            new_holder_id="ventrue_victor",
            granted_by_id="primogen_ventrue",
        )

    winner = next(
        candidate for candidate in candidates_from_state(state) if candidate.id == "primogen_ventrue"
    )
    install_prince(state, winner)
    assign_domain_holder(
        state,
        domain_id="vieux_centre",
        new_holder_id="ventrue_victor",
        granted_by_id="primogen_ventrue",
    )

    assert state.domains["vieux_centre"].holder_id == "ventrue_victor"
    assert state.domains["vieux_centre"].grantor_id == "primogen_ventrue"
    assert any(
        dispute.domain_id == "vieux_centre"
        and dispute.claimant_id == "ventrue_claire"
        and dispute.public
        for dispute in state.domain_disputes.values()
    )
