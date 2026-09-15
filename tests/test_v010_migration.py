from game.domains import grant_hunting_right, open_domain_dispute
from game.models import (
    ActionType,
    BoonLevel,
    ClanNightOrders,
    DomainDecisionOrder,
    DomainDecisionType,
    GameAction,
    PrimogenVote,
)
from game.serialization import (
    clan_orders_from_dict,
    clan_orders_to_dict,
    game_state_from_dict,
    game_state_to_dict,
)
from game.world import create_initial_game_state


def test_v09_state_without_territorial_fields_migrates_on_read():
    state = create_initial_game_state()
    payload = game_state_to_dict(state)
    payload.pop("domains")
    payload.pop("hunting_rights")
    payload.pop("domain_disputes")
    for clan_payload in payload["clan_states"].values():
        clan_payload.pop("known_domain_intel", None)

    migrated = game_state_from_dict(payload)

    assert len(migrated.domains) == 6
    assert migrated.domains["quartier_affaires"].holder_id == "primogen_ventrue"
    assert migrated.domains["vieux_centre"].holder_id == "ventrue_claire"
    assert migrated.hunting_rights == {}
    assert migrated.domain_disputes == {}
    assert all(not clan_state.known_domain_intel for clan_state in migrated.clan_states.values())


def test_v010_roundtrip_preserves_pressure_rights_disputes_and_domain_intel():
    state = create_initial_game_state()
    state.domains["quartier_affaires"].pressure = 3
    state.clan_states["toreador"].known_domain_intel["quartier_affaires"] = 2
    right = grant_hunting_right(
        state,
        domain_id="quartier_affaires",
        beneficiary_id="toreador_lucien",
        granted_by_id="primogen_ventrue",
        duration_nights=4,
    )
    dispute = open_domain_dispute(
        state,
        domain_id="quartier_affaires",
        claimant_id="primogen_ventrue",
        respondent_id="toreador_lucien",
        reason="Intrusion répétée",
        severity=2,
    )

    restored = game_state_from_dict(game_state_to_dict(state))

    assert restored.domains["quartier_affaires"].pressure == 3
    assert restored.hunting_rights[right.id].beneficiary_id == "toreador_lucien"
    assert restored.hunting_rights[right.id].expires_night == right.expires_night
    assert restored.domain_disputes[dispute.id].severity == 2
    assert restored.clan_states["toreador"].known_domain_intel["quartier_affaires"] == 2


def test_v09_orders_remain_readable_with_empty_v010_fields():
    payload = {
        "version": 3,
        "clan_id": "ventrue",
        "actions": [
            {
                "clan_id": "ventrue",
                "action_type": "build_influence",
                "actor_character_id": "primogen_ventrue",
                "target_character_id": None,
                "target_clan_id": None,
                "target_current_id": None,
            }
        ],
        "vote": {
            "primogen_id": "primogen_ventrue",
            "candidate_id": "primogen_ventrue",
        },
        "embrace_petitions": [],
        "request_decisions": [],
    }

    orders = clan_orders_from_dict(payload)

    assert orders.version == 3
    assert orders.domain_decisions == ()
    assert orders.promise_fulfillments == ()
    assert orders.actions[0].target_domain_id is None


def test_v010_orders_roundtrip_preserves_domain_target_decision_and_promise():
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction(
                clan_id="ventrue",
                action_type=ActionType.DOMAIN_INTRUSION,
                actor_character_id="ventrue_victor",
                target_domain_id="quartier_arts",
            ),
        ),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        domain_decisions=(
            DomainDecisionOrder(
                decision=DomainDecisionType.GRANT_HUNTING_RIGHT,
                domain_id="quartier_affaires",
                beneficiary_id="ventrue_helene",
                duration_nights=5,
                boon_level=BoonLevel.MINOR,
            ),
        ),
        promise_fulfillments=("promise_7",),
        version=4,
    )

    restored = clan_orders_from_dict(clan_orders_to_dict(orders))

    assert restored.version == 4
    assert restored.actions[0].target_domain_id == "quartier_arts"
    assert restored.domain_decisions[0].domain_id == "quartier_affaires"
    assert restored.domain_decisions[0].duration_nights == 5
    assert restored.domain_decisions[0].boon_level == BoonLevel.MINOR
    assert restored.promise_fulfillments == ("promise_7",)
