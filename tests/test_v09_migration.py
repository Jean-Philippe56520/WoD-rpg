from game.models import (
    ClanFactionSide,
    ClanNightOrders,
    MortalStance,
    OrderStance,
    PoliticalRequestDecisionOrder,
    RequestDecision,
)
from game.serialization import (
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_dict,
    game_state_to_dict,
)
from game.world import create_initial_game_state


def test_v08_state_migrates_coteries_and_ideology_names_without_data_loss():
    state = create_initial_game_state()
    data = game_state_to_dict(state)

    # Simule une sauvegarde V0.8 : anciennes clés et absence des champs sociaux V0.9.
    claire = data["characters"]["ventrue_claire"]
    claire["humanity_axis"] = "+"
    claire["tradition_axis"] = "-"
    claire.pop("mortal_stance")
    claire.pop("order_stance")
    claire.pop("status")
    claire.pop("reputation")
    claire.pop("political_ambition")
    clan = data["clan_states"]["ventrue"]
    clan["coterie_memberships"] = clan.pop("faction_memberships")
    data.pop("boons")
    data.pop("grievances")
    data.pop("political_requests")
    data.pop("promises")

    restored = game_state_from_dict(data)
    restored_claire = restored.characters["ventrue_claire"]
    assert restored_claire.mortal_stance == MortalStance.HUMANIST
    assert restored_claire.order_stance == OrderStance.REFORMIST
    assert restored_claire.personal_influence == state.characters["ventrue_claire"].personal_influence
    assert (
        restored.clan_states["ventrue"].faction_memberships["ventrue_claire"]
        == ClanFactionSide.OPPOSITION
    )
    assert len(restored.political_requests) == 3


def test_true_humanity_is_independent_from_mortal_stance():
    state = create_initial_game_state()
    claire = state.characters["ventrue_claire"]
    assert claire.mortal_stance == MortalStance.HUMANIST
    claire.humanity = 3
    assert claire.mortal_stance == MortalStance.HUMANIST
    claire.humanity_axis = "-"
    assert claire.mortal_stance == MortalStance.PREDATORY
    assert claire.humanity == 3


def test_v09_orders_roundtrip_request_decisions():
    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(),
        request_decisions=(
            PoliticalRequestDecisionOrder("request_1", RequestDecision.NEGOTIATE),
        ),
        version=3,
    )
    restored = clan_orders_from_json(clan_orders_to_json(orders))
    assert restored == orders


def test_new_serialization_uses_faction_and_lore_keys_not_v08_names():
    data = game_state_to_dict(create_initial_game_state())
    claire = data["characters"]["ventrue_claire"]
    assert "mortal_stance" in claire
    assert "order_stance" in claire
    assert "humanity_axis" not in claire
    assert "tradition_axis" not in claire
    assert "faction_memberships" in data["clan_states"]["ventrue"]
    assert "coterie_memberships" not in data["clan_states"]["ventrue"]
