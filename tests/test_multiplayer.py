import pytest

from game.models import (
    ActionType,
    ClanNightOrders,
    DomainDecisionOrder,
    DomainDecisionType,
    GameAction,
    PoliticalRequestDecisionOrder,
    PoliticalRequestStatus,
    PrimogenVote,
    RequestDecision,
)
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.persistence import SQLiteGameRepository
from game.world import REQUIRED_CLANS


def make_service(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "game.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    return service, repo


def legacy_orders_for(state, clan_id, action_type=ActionType.BUILD_INFLUENCE):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    return ClanNightOrders(
        clan_id=clan_id,
        actions=(GameAction(clan_id, action_type),),
        vote=PrimogenVote(primogen_id, primogen_id),
        version=1,
    )


def v08_orders_for(state, clan_id):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    members = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id and character.id != state.prince_id
    ]
    return ClanNightOrders(
        clan_id=clan_id,
        actions=tuple(
            GameAction(
                clan_id,
                ActionType.BUILD_INFLUENCE,
                actor_character_id=member.id,
            )
            for member in members
        ),
        vote=PrimogenVote(primogen_id, primogen_id),
        version=2,
    )


def v09_orders_for(state, clan_id):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    members = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id and character.id != state.prince_id
    ]
    open_requests = [
        request
        for request in state.political_requests.values()
        if request.clan_id == clan_id and request.status == PoliticalRequestStatus.OPEN
    ]
    return ClanNightOrders(
        clan_id=clan_id,
        actions=tuple(
            GameAction(
                clan_id,
                ActionType.BUILD_INFLUENCE,
                actor_character_id=member.id,
            )
            for member in members
        ),
        vote=PrimogenVote(primogen_id, primogen_id),
        request_decisions=tuple(
            PoliticalRequestDecisionOrder(request.id, RequestDecision.ACCEPT)
            for request in open_requests
        ),
        version=3,
    )


def v010_orders_for(state, clan_id):
    previous = v09_orders_for(state, clan_id)
    return ClanNightOrders(
        clan_id=previous.clan_id,
        actions=previous.actions,
        vote=previous.vote,
        embrace_petitions=previous.embrace_petitions,
        request_decisions=previous.request_decisions,
        domain_decisions=(),
        promise_fulfillments=(),
        version=4,
    )


def test_players_submit_only_their_own_clan(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    with pytest.raises(ValueError, match="player's clan"):
        service.submit_orders("p1", v08_orders_for(state, "brujah"))


def test_v08_requires_exactly_one_action_for_every_active_member(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    primogen_id = state.clan_states["ventrue"].clan.primogen_id
    incomplete = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction(
                "ventrue",
                ActionType.BUILD_INFLUENCE,
                actor_character_id=primogen_id,
            ),
        ),
        vote=PrimogenVote(primogen_id, primogen_id),
        version=2,
    )
    with pytest.raises(ValueError, match="exactly one action"):
        service.submit_orders("p1", incomplete)


def test_v08_rejects_duplicate_actor_even_when_action_count_matches(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    primogen_id = state.clan_states["ventrue"].clan.primogen_id
    duplicate = ClanNightOrders(
        clan_id="ventrue",
        actions=tuple(
            GameAction(
                "ventrue",
                ActionType.BUILD_INFLUENCE,
                actor_character_id=primogen_id,
            )
            for _ in range(4)
        ),
        vote=PrimogenVote(primogen_id, primogen_id),
        version=2,
    )
    with pytest.raises(ValueError, match="only one action"):
        service.submit_orders("p1", duplicate)


def test_third_v08_submission_resolves_once_and_advances_global_night(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)

    assert service.submit_orders("p1", v08_orders_for(state, "ventrue")) is False
    assert service.submit_orders("p2", v08_orders_for(state, "toreador")) is False
    assert service.submit_orders("p3", v08_orders_for(state, "brujah")) is True

    info = repo.get_game_info(DEFAULT_GAME_ID)
    assert info["current_night"] == 2
    assert repo.try_begin_resolution(DEFAULT_GAME_ID) is None
    for clan_id in REQUIRED_CLANS:
        report = repo.get_report(DEFAULT_GAME_ID, 1, clan_id)
        assert report is not None


def test_mixed_v07_and_v08_submissions_can_finish_same_persisted_night(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)

    assert service.submit_orders("p1", legacy_orders_for(state, "ventrue", ActionType.CONSOLIDATE)) is False
    assert service.submit_orders("p2", v08_orders_for(state, "toreador")) is False
    assert service.submit_orders("p3", v08_orders_for(state, "brujah")) is True
    assert repo.get_game_info(DEFAULT_GAME_ID)["current_night"] == 2


def test_live_style_legacy_ventrue_can_resolve_with_v09_other_clans(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)

    legacy_ventrue = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction("ventrue", ActionType.CONSOLIDATE),
            GameAction("ventrue", ActionType.BUILD_INFLUENCE),
        ),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        version=1,
    )
    assert service.submit_orders("p1", legacy_ventrue) is False
    assert service.submit_orders("p2", v09_orders_for(state, "toreador")) is False
    assert service.submit_orders("p3", v09_orders_for(state, "brujah")) is True
    assert repo.get_game_info(DEFAULT_GAME_ID)["current_night"] == 2
    assert repo.get_report(DEFAULT_GAME_ID, 1, "ventrue") is not None


def test_live_style_legacy_ventrue_can_resolve_with_v010_other_clans(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)

    legacy_ventrue = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction("ventrue", ActionType.CONSOLIDATE),
            GameAction("ventrue", ActionType.BUILD_INFLUENCE),
        ),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        version=1,
    )
    assert service.submit_orders("p1", legacy_ventrue) is False
    assert service.submit_orders("p2", v010_orders_for(state, "toreador")) is False
    assert service.submit_orders("p3", v010_orders_for(state, "brujah")) is True
    assert repo.get_game_info(DEFAULT_GAME_ID)["current_night"] == 2
    assert repo.get_report(DEFAULT_GAME_ID, 1, "ventrue") is not None


def test_v09_requires_a_decision_for_each_open_clan_request(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    orders = v09_orders_for(state, "ventrue")
    incomplete = ClanNightOrders(
        clan_id=orders.clan_id,
        actions=orders.actions,
        vote=orders.vote,
        request_decisions=(),
        version=3,
    )
    with pytest.raises(ValueError, match="Every open political request"):
        service.submit_orders("p1", incomplete)


def test_v010_primogen_cannot_administer_opposition_leader_personal_domain(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    base = v010_orders_for(state, "ventrue")
    illegal = ClanNightOrders(
        clan_id=base.clan_id,
        actions=base.actions,
        vote=base.vote,
        request_decisions=base.request_decisions,
        domain_decisions=(
            DomainDecisionOrder(
                decision=DomainDecisionType.GRANT_HUNTING_RIGHT,
                domain_id="vieux_centre",
                beneficiary_id="ventrue_helene",
            ),
        ),
        version=4,
    )
    with pytest.raises(ValueError, match="personally hold"):
        service.submit_orders("p1", illegal)


def test_v010_allows_one_concession_on_primogen_personal_domain(tmp_path):
    service, repo = make_service(tmp_path)
    service.claim_clan("p1", "Alice", "ventrue")
    state = repo.get_game_state(DEFAULT_GAME_ID)
    base = v010_orders_for(state, "ventrue")
    legal = ClanNightOrders(
        clan_id=base.clan_id,
        actions=base.actions,
        vote=base.vote,
        request_decisions=base.request_decisions,
        domain_decisions=(
            DomainDecisionOrder(
                decision=DomainDecisionType.GRANT_HUNTING_RIGHT,
                domain_id="quartier_affaires",
                beneficiary_id="ventrue_victor",
                duration_nights=3,
            ),
        ),
        version=4,
    )
    service.validate_orders(state, "ventrue", legal)


def test_reports_hide_other_clans_private_member_actions(tmp_path):
    service, repo = make_service(tmp_path)
    state = repo.get_game_state(DEFAULT_GAME_ID)
    players = (("p1", "Alice", "ventrue"), ("p2", "Bob", "toreador"), ("p3", "Cara", "brujah"))
    for player_id, name, clan_id in players:
        service.claim_clan(player_id, name, clan_id)
    service.submit_orders("p1", v08_orders_for(state, "ventrue"))
    service.submit_orders("p2", v08_orders_for(state, "toreador"))
    service.submit_orders("p3", v08_orders_for(state, "brujah"))

    ventrue = " ".join(repo.get_report(DEFAULT_GAME_ID, 1, "ventrue").items)
    toreador = " ".join(repo.get_report(DEFAULT_GAME_ID, 1, "toreador").items)
    assert "Victor de Keravel développe ses réseaux" in ventrue
    assert "Victor de Keravel développe ses réseaux" not in toreador
