from game.models import (
    ActionType,
    AxisPolarity,
    BloodRank,
    ClanNightOrders,
    CoterieSide,
    GameAction,
    PrimogenVote,
)
from game.serialization import (
    clan_orders_from_dict,
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_dict,
    game_state_from_json,
    game_state_to_dict,
    game_state_to_json,
)
from game.world import create_initial_game_state


def test_game_state_json_roundtrip_preserves_v08_character_and_coterie_state():
    state = create_initial_game_state()
    state.characters["ventrue_claire"].relations["primogen_toreador"] = 2
    state.clan_states["ventrue"].known_character_intel["toreador_lucien"] = 2
    restored = game_state_from_json(game_state_to_json(state))
    claire = restored.characters["ventrue_claire"]
    clan_state = restored.clan_states["ventrue"]

    assert restored.night == state.night
    assert clan_state.clan.primogen_id == state.clan_states["ventrue"].clan.primogen_id
    assert claire.humanity_axis == AxisPolarity.PLUS
    assert claire.tradition_axis == AxisPolarity.MINUS
    assert (claire.physical, claire.social, claire.mental) == (0, 2, 1)
    assert claire.expertises == ("Diplomatie", "Politique")
    assert claire.disciplines["presence"] == 2
    assert claire.blood_rank == BloodRank.NEWBORN
    assert claire.backgrounds["Contacts"] == 2
    assert claire.relation_to_primogen == 0
    assert claire.relations["primogen_toreador"] == 2
    assert clan_state.coterie_memberships["ventrue_claire"] == CoterieSide.OPPOSITION
    assert clan_state.opposition_leader_id == "ventrue_claire"
    assert clan_state.known_character_intel["toreador_lucien"] == 2


def test_v07_state_is_migrated_to_relations_and_two_coteries_without_losing_live_politics():
    state = create_initial_game_state()
    data = game_state_to_dict(state)

    for payload in data["characters"].values():
        payload.pop("relation_to_primogen", None)
        payload.pop("relations", None)
    for clan_payload in data["clan_states"].values():
        clan_payload.pop("coterie_memberships", None)
        clan_payload.pop("opposition_leader_id", None)
        clan_payload.pop("opposition_allied_primogen_id", None)
        clan_payload.pop("known_character_intel", None)

    # Simule des valeurs politiques vivantes héritées d'une sauvegarde V0.7.
    data["characters"]["ventrue_claire"]["personal_influence"] = 19
    data["characters"]["ventrue_claire"]["loyalty"] = 30
    data["characters"]["ventrue_claire"]["ambition"] = 84

    restored = game_state_from_dict(data)
    claire = restored.characters["ventrue_claire"]
    victor = restored.characters["ventrue_victor"]
    clan_state = restored.clan_states["ventrue"]

    assert claire.personal_influence == 19
    assert claire.ambition == 84
    assert claire.relation_to_primogen == 0
    assert victor.relation_to_primogen == 2
    assert clan_state.coterie_memberships[claire.id] == CoterieSide.OPPOSITION
    assert clan_state.coterie_memberships[victor.id] == CoterieSide.PRIMOGEN
    assert clan_state.opposition_leader_id == claire.id
    assert set(clan_state.coterie_memberships.values()) == {
        CoterieSide.PRIMOGEN,
        CoterieSide.OPPOSITION,
    }


def test_v06_character_payload_is_enriched_without_losing_live_values():
    state = create_initial_game_state()
    data = game_state_to_dict(state)
    data["characters"]["ventrue_claire"] = {
        "id": "ventrue_claire",
        "name": "Claire Beaumont",
        "clan_id": "ventrue",
        "personal_influence": 19,
        "humanity": 7,
        "humanism": 60,
        "tradition": -65,
        "loyalty": 37,
        "ambition": 84,
        "is_primogen": False,
    }
    restored = game_state_from_dict(data)
    claire = restored.characters["ventrue_claire"]

    assert claire.personal_influence == 19
    assert claire.loyalty == 37
    assert claire.ambition == 84
    assert claire.humanity_axis == AxisPolarity.PLUS
    assert claire.tradition_axis == AxisPolarity.MINUS
    assert (claire.physical, claire.social, claire.mental) == (0, 2, 1)
    assert claire.expertises == ("Diplomatie", "Politique")
    assert claire.disciplines == {"domination": 1, "presence": 2}
    assert claire.blood_rank == BloodRank.NEWBORN
    assert claire.backgrounds == {"Contacts": 2, "Influence politique": 1}
    assert claire.relation_to_primogen == 0


def test_v08_orders_json_roundtrip_preserves_actor_and_target():
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction(
                "ventrue",
                ActionType.DIPLOMACY,
                actor_character_id="ventrue_claire",
                target_character_id="primogen_toreador",
            ),
        ),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        version=2,
    )
    restored = clan_orders_from_json(clan_orders_to_json(orders))
    assert restored == orders


def test_v07_orders_without_version_or_actor_remain_readable():
    restored = clan_orders_from_dict(
        {
            "clan_id": "ventrue",
            "actions": [
                {
                    "clan_id": "ventrue",
                    "action_type": "diplomacy",
                    "target_clan_id": "toreador",
                    "target_current_id": None,
                }
            ],
            "vote": {
                "primogen_id": "primogen_ventrue",
                "candidate_id": "primogen_ventrue",
            },
            "embrace_petitions": [],
        }
    )
    assert restored.version == 1
    assert restored.actions[0].actor_character_id is None
    assert restored.actions[0].target_clan_id == "toreador"
