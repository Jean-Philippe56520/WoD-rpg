from game.actions import apply_action
from game.coteries import (
    canonical_coteries,
    coterie_cooperation_bonus,
    effective_coterie_cohesion,
    shared_coterie,
)
from game.models import ActionType, GameAction
from game.world import create_initial_game_state


def test_three_canonical_coteries_are_transclan_and_distinct_from_factions():
    state = create_initial_game_state()
    coteries = canonical_coteries()

    assert len(coteries) == 3
    for coterie in coteries:
        clans = {state.characters[member_id].clan_id for member_id in coterie.member_ids}
        assert clans == {"ventrue", "toreador", "brujah"}
        assert coterie.leader_id in coterie.member_ids


def test_coterie_members_reveal_each_other_at_identity_intel_only():
    state = create_initial_game_state()

    assert state.clan_states["brujah"].known_character_intel["toreador_camille"] == 1
    assert state.clan_states["brujah"].known_character_intel["ventrue_helene"] == 1
    assert state.clan_states["ventrue"].known_character_intel["toreador_lucien"] == 1
    assert state.clan_states["toreador"].known_character_intel["brujah_yann"] == 1


def test_coterie_cohesion_is_derived_from_persistent_relationships():
    state = create_initial_game_state()
    coterie = shared_coterie("brujah_ines", "toreador_camille")
    assert coterie is not None
    assert effective_coterie_cohesion(state, coterie) == 2

    for first_id in coterie.member_ids:
        for second_id in coterie.member_ids:
            if first_id != second_id:
                state.characters[first_id].relations[second_id] = 0

    assert effective_coterie_cohesion(state, coterie) == 1


def test_shared_coterie_gives_cooperation_bonus_to_diplomacy_and_investigation_context():
    state = create_initial_game_state()
    assert coterie_cooperation_bonus(state, "ventrue_helene", "toreador_camille") == 1
    assert coterie_cooperation_bonus(state, "ventrue_helene", "toreador_noemie") == 0

    with_coterie = create_initial_game_state()
    without_coterie = create_initial_game_state()

    apply_action(
        with_coterie,
        GameAction(
            "ventrue",
            ActionType.DIPLOMACY,
            actor_character_id="ventrue_helene",
            target_character_id="toreador_camille",
        ),
    )
    apply_action(
        without_coterie,
        GameAction(
            "ventrue",
            ActionType.DIPLOMACY,
            actor_character_id="ventrue_helene",
            target_character_id="primogen_toreador",
        ),
    )

    assert with_coterie.clan_states["ventrue"].relations["toreador"] > without_coterie.clan_states["ventrue"].relations["toreador"]


def test_member_with_weak_primogen_relation_refuses_attack_on_coterie_companion():
    state = create_initial_game_state()
    helene = state.characters["ventrue_helene"]
    before = helene.relation_to_primogen

    event = apply_action(
        state,
        GameAction(
            "brujah",
            ActionType.UNDERMINE,
            actor_character_id="brujah_ines",
            target_character_id="ventrue_helene",
        ),
    )

    assert event.category == "coterie"
    assert "refuse" in event.message
    assert "Concorde des Trois" in event.message
    assert helene.relation_to_primogen == before


def test_loyal_member_obeys_hostile_order_but_suffers_coterie_conflict_penalty():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    assert victor.relation_to_primogen == 2

    event = apply_action(
        state,
        GameAction(
            "ventrue",
            ActionType.UNDERMINE,
            actor_character_id="ventrue_victor",
            target_character_id="toreador_gabriel",
        ),
    )

    assert event.category == "action"
    assert "refuse" not in event.message


def test_detected_intrusion_against_coterie_companion_strains_relationship():
    state = create_initial_game_state()
    lucien = state.characters["toreador_lucien"]
    claire = state.characters["ventrue_claire"]
    lucien.relation_to_primogen = 2
    before_lucien = lucien.relations[claire.id]
    before_claire = claire.relations[lucien.id]

    event = apply_action(
        state,
        GameAction(
            "toreador",
            ActionType.DOMAIN_INTRUSION,
            actor_character_id=lucien.id,
            target_domain_id="vieux_centre",
        ),
    )

    assert "repérée" in event.message
    assert "Cendres Libres" in event.message
    assert lucien.relations[claire.id] == max(0, before_lucien - 1)
    assert claire.relations[lucien.id] == max(0, before_claire - 1)
