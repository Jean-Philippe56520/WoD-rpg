from game.agency import evaluate_member_mission, member_reliability
from game.models import ActionType, GameAction
from game.simultaneous import resolve_actions_simultaneously
from game.social_politics import add_grievance
from game.world import create_initial_game_state


def test_primogen_faction_member_can_refuse_conflicting_order_after_serious_grievance():
    state = create_initial_game_state()
    add_grievance(
        state,
        owner_id="brujah_ines",
        target_id="primogen_brujah",
        reason="Marcus a sacrifié un intérêt personnel d'Ines",
        severity=2,
    )
    action = GameAction(
        clan_id="brujah",
        action_type=ActionType.UNDERMINE,
        actor_character_id="brujah_ines",
        target_character_id="ventrue_victor",
    )
    before_influence = state.characters["brujah_ines"].personal_influence
    before_relation = state.characters["ventrue_victor"].relation_to_primogen

    decision = evaluate_member_mission(state, action)
    assert decision is not None
    assert decision.obeys is False
    assert decision.alignment == -1

    events = resolve_actions_simultaneously(state, [action])

    assert state.characters["brujah_ines"].personal_influence == before_influence + 1
    assert state.characters["ventrue_victor"].relation_to_primogen == before_relation
    assert any(event.category == "autonomie" and "refuse" in event.message for event in events)


def test_same_member_accepts_mission_that_serves_her_rapprochement_ambition():
    state = create_initial_game_state()
    add_grievance(
        state,
        owner_id="brujah_ines",
        target_id="primogen_brujah",
        reason="Désaccord sérieux avec Marcus",
        severity=2,
    )
    action = GameAction(
        clan_id="brujah",
        action_type=ActionType.DIPLOMACY,
        actor_character_id="brujah_ines",
        target_character_id="primogen_ventrue",
    )
    before = state.clan_states["brujah"].relations["ventrue"]

    decision = evaluate_member_mission(state, action)
    assert decision is not None
    assert decision.obeys is True
    assert decision.alignment == 1

    events = resolve_actions_simultaneously(state, [action])

    assert state.clan_states["brujah"].relations["ventrue"] > before
    assert not any(event.category == "autonomie" for event in events)


def test_strongly_loyal_member_obeys_even_a_mission_opposed_to_personal_ambition():
    state = create_initial_game_state()
    action = GameAction(
        clan_id="ventrue",
        action_type=ActionType.BRACONNAGE,
        actor_character_id="ventrue_victor",
        target_domain_id="docks",
    )

    decision = evaluate_member_mission(state, action)

    assert decision is not None
    assert decision.alignment == -1
    assert decision.effective_relation >= 2
    assert decision.obeys is True


def test_opposition_remains_managed_by_existing_opposition_rules():
    state = create_initial_game_state()
    action = GameAction(
        clan_id="brujah",
        action_type=ActionType.DIPLOMACY,
        actor_character_id="brujah_sarah",
        target_character_id="primogen_ventrue",
    )

    assert evaluate_member_mission(state, action) is None


def test_reliability_exposes_political_risk_without_hiding_primogen_authority():
    state = create_initial_game_state()
    assert member_reliability(state, "primogen_ventrue") == "direct"
    assert member_reliability(state, "ventrue_victor") == "forte"
    assert member_reliability(state, "brujah_sarah") == "faible"

    add_grievance(
        state,
        owner_id="brujah_ines",
        target_id="primogen_brujah",
        reason="Grief sérieux",
        severity=2,
    )
    assert member_reliability(state, "brujah_ines") == "faible"
