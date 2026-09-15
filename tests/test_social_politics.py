from game.autonomy import resolve_autonomous_reactions
from game.models import (
    BoonLevel,
    BoonStatus,
    ClanFactionSide,
    PoliticalRequestStatus,
    PromiseStatus,
    RequestDecision,
)
from game.social_politics import (
    active_grievance_score,
    add_grievance,
    call_boon,
    create_boon,
    fulfill_boon,
    generate_requests_for_night,
    process_request_decision,
    refuse_boon,
)
from game.world import create_initial_game_state


def test_boon_lifecycle_records_prestation_and_reputation():
    state = create_initial_game_state()
    boon = create_boon(
        state,
        creditor_id="ventrue_claire",
        debtor_id="ventrue_victor",
        level=BoonLevel.MINOR,
        origin="Accord politique",
    )
    assert boon.status == BoonStatus.DUE
    call_boon(state, boon.id, "ventrue_claire")
    assert boon.status == BoonStatus.CALLED
    before = state.characters["ventrue_victor"].reputation
    fulfill_boon(state, boon.id)
    assert boon.status == BoonStatus.FULFILLED
    assert state.characters["ventrue_victor"].reputation == min(3, before + 1)


def test_refusing_major_boon_creates_serious_grievance_and_reputation_loss():
    state = create_initial_game_state()
    boon = create_boon(
        state,
        creditor_id="ventrue_claire",
        debtor_id="ventrue_victor",
        level=BoonLevel.MAJOR,
        origin="Soutien à une Praxis",
    )
    before = state.characters["ventrue_victor"].reputation
    refuse_boon(state, boon.id)
    assert boon.status == BoonStatus.REFUSED
    assert state.characters["ventrue_victor"].reputation == max(-3, before - 2)
    assert active_grievance_score(state, "ventrue_claire", "ventrue_victor") == 2


def test_accepting_request_improves_relation_and_can_create_counter_boon():
    state = create_initial_game_state()
    request = next(
        request
        for request in state.political_requests.values()
        if request.clan_id == "ventrue"
    )
    requester = state.characters[request.requester_id]
    request.offered_boon_level = BoonLevel.MINOR
    before = requester.relation_to_primogen
    event = process_request_decision(state, "ventrue", request.id, RequestDecision.ACCEPT)
    assert request.status == PoliticalRequestStatus.ACCEPTED
    assert requester.relation_to_primogen == min(2, before + 1)
    assert any(
        boon.creditor_id == "primogen_ventrue" and boon.debtor_id == requester.id
        for boon in state.boons.values()
    )
    assert event.audience_clan_ids == ("ventrue",)


def test_refusing_request_creates_explicit_grievance_not_hidden_discontent():
    state = create_initial_game_state()
    request = next(
        request
        for request in state.political_requests.values()
        if request.clan_id == "toreador"
    )
    requester = state.characters[request.requester_id]
    before = requester.relation_to_primogen
    process_request_decision(state, "toreador", request.id, RequestDecision.REFUSE)
    assert request.status == PoliticalRequestStatus.REFUSED
    assert requester.relation_to_primogen == max(0, before - 1)
    assert active_grievance_score(state, requester.id, "primogen_toreador") >= 1


def test_promise_becomes_a_serious_grievance_when_it_is_not_kept():
    state = create_initial_game_state()
    request = next(
        request
        for request in state.political_requests.values()
        if request.clan_id == "brujah"
    )
    requester = state.characters[request.requester_id]
    process_request_decision(state, "brujah", request.id, RequestDecision.PROMISE)
    promise = next(iter(state.promises.values()))
    assert promise.status == PromiseStatus.PENDING

    state.night = promise.due_night + 1
    resolve_autonomous_reactions(state)
    assert promise.status == PromiseStatus.BROKEN
    assert active_grievance_score(state, requester.id, "primogen_brujah") >= 2
    assert state.characters["primogen_brujah"].reputation <= 0


def test_no_defection_without_grievance_even_with_bad_effective_relation():
    state = create_initial_game_state()
    helene = state.characters["ventrue_helene"]
    state.clan_states["ventrue"].faction_memberships[helene.id] = ClanFactionSide.PRIMOGEN
    helene.relation_to_primogen = 0
    resolve_autonomous_reactions(state)
    assert state.clan_states["ventrue"].faction_memberships[helene.id] == ClanFactionSide.PRIMOGEN


def test_grievance_plus_bad_relation_can_trigger_deterministic_defection():
    state = create_initial_game_state()
    helene = state.characters["ventrue_helene"]
    state.clan_states["ventrue"].faction_memberships[helene.id] = ClanFactionSide.PRIMOGEN
    helene.relation_to_primogen = 0
    add_grievance(
        state,
        owner_id=helene.id,
        target_id="primogen_ventrue",
        reason="Adrien a sacrifié ses intérêts",
        severity=2,
    )
    events = resolve_autonomous_reactions(state)
    assert state.clan_states["ventrue"].faction_memberships[helene.id] == ClanFactionSide.OPPOSITION
    assert any("rejoint ouvertement" in event.message for event in events)


def test_only_one_new_request_per_clan_and_night_is_generated():
    state = create_initial_game_state()
    counts_before = {
        clan_id: sum(
            request.clan_id == clan_id and request.created_night == state.night
            for request in state.political_requests.values()
        )
        for clan_id in state.clan_states
    }
    generate_requests_for_night(state)
    counts_after = {
        clan_id: sum(
            request.clan_id == clan_id and request.created_night == state.night
            for request in state.political_requests.values()
        )
        for clan_id in state.clan_states
    }
    assert counts_before == counts_after == {"ventrue": 1, "toreador": 1, "brujah": 1}
