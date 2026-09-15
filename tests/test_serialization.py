from game.models import ActionType, AxisPolarity, BloodRank, ClanNightOrders, GameAction, PrimogenVote
from game.serialization import (
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_dict,
    game_state_from_json,
    game_state_to_dict,
    game_state_to_json,
)
from game.world import create_initial_game_state


def test_game_state_json_roundtrip_preserves_v07_character_sheet():
    state = create_initial_game_state()
    restored = game_state_from_json(game_state_to_json(state))
    claire = restored.characters["ventrue_claire"]
    assert restored.night == state.night
    assert restored.clan_states["ventrue"].clan.primogen_id == state.clan_states["ventrue"].clan.primogen_id
    assert claire.humanity_axis == AxisPolarity.PLUS
    assert claire.tradition_axis == AxisPolarity.MINUS
    assert (claire.physical, claire.social, claire.mental) == (0, 2, 1)
    assert claire.expertises == ("Diplomatie", "Politique")
    assert claire.disciplines["presence"] == 2
    assert claire.blood_rank == BloodRank.NEWBORN
    assert claire.backgrounds["Contacts"] == 2


def test_v06_character_payload_is_enriched_on_read_without_losing_live_politics():
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

    # La politique vivante vient toujours de la sauvegarde V0.6.
    assert claire.personal_influence == 19
    assert claire.loyalty == 37
    assert claire.ambition == 84
    assert claire.humanity_axis == AxisPolarity.PLUS
    assert claire.tradition_axis == AxisPolarity.MINUS

    # Les nouveaux champs absents sont récupérés depuis la fiche canonique V0.7.
    assert (claire.physical, claire.social, claire.mental) == (0, 2, 1)
    assert claire.expertises == ("Diplomatie", "Politique")
    assert claire.disciplines == {"domination": 1, "presence": 2}
    assert claire.blood_rank == BloodRank.NEWBORN
    assert claire.backgrounds == {"Contacts": 2, "Influence politique": 1}


def test_orders_json_roundtrip():
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(GameAction("ventrue", ActionType.BUILD_INFLUENCE),),
        vote=PrimogenVote("primogen_ventrue", "primogen_ventrue"),
    )
    restored = clan_orders_from_json(clan_orders_to_json(orders))
    assert restored == orders
