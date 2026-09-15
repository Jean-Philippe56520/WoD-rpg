from game.action_resolution import resolve_all_actions_simultaneously
from game.config import DEFAULT_RULES
from game.crises import (
    ANARCHS,
    HUNTERS,
    active_crises,
    current_crisis_intel,
    open_crisis,
    resolve_crisis_cycle,
)
from game.models import ActionType, ClanNightOrders, GameAction, PrimogenVote
from game.multiplayer import MultiplayerGameService
from game.persistence import SQLiteGameRepository
from game.serialization import clan_orders_from_dict, clan_orders_to_dict, game_state_from_json, game_state_to_json
from game.world import create_initial_game_state


def seed_crisis(state, faction=ANARCHS, domain_id=None):
    domain_id = domain_id or next(iter(state.domains))
    state.events.append(open_crisis(state, faction, domain_id))
    return active_crises(state)[0]


def primogen(state, clan_id):
    return state.characters[state.clan_states[clan_id].clan.primogen_id]


def tune_for_score_three(character, expertise="Subterfuge"):
    character.mental = 2
    character.expertises = (expertise,)
    character.backgrounds.clear()
    character.disciplines.clear()


def test_two_clans_can_cooperate_on_same_crisis_and_resolve_stage_one():
    state = create_initial_game_state()
    crisis = seed_crisis(state, ANARCHS)
    ventrue = primogen(state, "ventrue")
    toreador = primogen(state, "toreador")
    tune_for_score_three(ventrue)
    tune_for_score_three(toreador)

    actions = [
        GameAction(
            clan_id="ventrue",
            action_type=ActionType.CRISIS_INFILTRATE,
            actor_character_id=ventrue.id,
            target_domain_id=crisis.domain_id,
        ),
        GameAction(
            clan_id="toreador",
            action_type=ActionType.CRISIS_INFILTRATE,
            actor_character_id=toreador.id,
            target_domain_id=crisis.domain_id,
        ),
    ]
    events = resolve_all_actions_simultaneously(state, actions)
    state.events.extend(events)
    state.events.extend(resolve_crisis_cycle(state))

    assert active_crises(state) == []
    assert any("2/2 progrès" in event.message for event in state.events)


def test_investigation_reveals_private_crisis_intel_without_solving_it():
    state = create_initial_game_state()
    crisis = seed_crisis(state, HUNTERS)
    actor = primogen(state, "toreador")
    actor.mental = 2
    actor.expertises = ("Investigation",)
    actor.backgrounds["Contacts"] = 2

    action = GameAction(
        clan_id="toreador",
        action_type=ActionType.CRISIS_INVESTIGATE,
        actor_character_id=actor.id,
        target_domain_id=crisis.domain_id,
    )
    events = resolve_all_actions_simultaneously(state, [action])
    state.events.extend(events)
    state.events.extend(resolve_crisis_cycle(state))

    assert current_crisis_intel(state, crisis.id, "toreador") == 2
    assert current_crisis_intel(state, crisis.id, "ventrue") == 0
    assert active_crises(state)[0].stage == 1


def test_unanswered_hunter_crisis_escalates_then_causes_major_failure():
    state = create_initial_game_state()
    domain_id = next(iter(state.domains))
    crisis = seed_crisis(state, HUNTERS, domain_id)
    original_servage = state.domains[domain_id].servage
    original_masquerade = state.masquerade_integrity

    state.night = crisis.next_escalation_night
    state.events.extend(resolve_crisis_cycle(state))
    assert active_crises(state)[0].stage == 2

    state.night = active_crises(state)[0].next_escalation_night
    state.events.extend(resolve_crisis_cycle(state))
    assert active_crises(state)[0].stage == 3

    state.night = active_crises(state)[0].next_escalation_night
    state.events.extend(resolve_crisis_cycle(state))

    assert active_crises(state) == []
    assert state.masquerade_integrity == (
        original_masquerade
        - DEFAULT_RULES.hunter_crisis_stage3_masquerade_loss
        - DEFAULT_RULES.hunter_crisis_failure_masquerade_loss
    )
    assert state.domains[domain_id].servage == max(
        0, original_servage - DEFAULT_RULES.hunter_crisis_failure_servage_loss
    )


def test_anarch_major_failure_weakens_holder_and_strengthens_internal_opposition():
    state = create_initial_game_state()
    domain = next(domain for domain in state.domains.values() if domain.holder_id)
    crisis = seed_crisis(state, ANARCHS, domain.id)
    holder = state.characters[domain.holder_id]
    holder_before = holder.personal_influence
    opposition_id = state.clan_states[holder.clan_id].opposition_leader_id
    opposition = state.characters[opposition_id]
    opposition_before = opposition.personal_influence

    for _ in range(3):
        current = active_crises(state)[0]
        state.night = current.next_escalation_night
        state.events.extend(resolve_crisis_cycle(state))

    assert active_crises(state) == []
    assert holder.personal_influence == max(
        0.0, holder_before - DEFAULT_RULES.anarch_crisis_failure_holder_influence_loss
    )
    if opposition.id != holder.id:
        assert opposition.personal_influence == (
            opposition_before + DEFAULT_RULES.anarch_crisis_failure_opposition_influence_gain
        )


def test_exploit_turns_foreign_crisis_into_influence_without_reducing_threat():
    state = create_initial_game_state()
    foreign_domain = next(
        domain
        for domain in state.domains.values()
        if state.characters[domain.holder_id].clan_id != "toreador"
    )
    crisis = seed_crisis(state, ANARCHS, foreign_domain.id)
    actor = primogen(state, "toreador")
    holder = state.characters[foreign_domain.holder_id]
    actor.social = 2
    actor.expertises = ("Subterfuge",)
    actor.backgrounds["Contacts"] = 2
    actor_before = actor.personal_influence
    holder_before = holder.personal_influence

    action = GameAction(
        clan_id="toreador",
        action_type=ActionType.CRISIS_EXPLOIT,
        actor_character_id=actor.id,
        target_domain_id=foreign_domain.id,
    )
    events = resolve_all_actions_simultaneously(state, [action])
    state.events.extend(events)
    state.events.extend(resolve_crisis_cycle(state))

    assert actor.personal_influence > actor_before
    assert holder.personal_influence < holder_before
    assert active_crises(state)[0].id == crisis.id
    assert active_crises(state)[0].stage == 1


def test_crisis_state_and_action_survive_serialization():
    state = create_initial_game_state()
    crisis = seed_crisis(state, HUNTERS)
    restored_state = game_state_from_json(game_state_to_json(state))
    restored_crisis = active_crises(restored_state)[0]
    assert restored_crisis == crisis

    orders = ClanNightOrders(
        clan_id="ventrue",
        actions=(
            GameAction(
                clan_id="ventrue",
                action_type=ActionType.CRISIS_CONTAIN,
                actor_character_id=state.clan_states["ventrue"].clan.primogen_id,
                target_domain_id=crisis.domain_id,
            ),
        ),
        version=4,
    )
    restored_orders = clan_orders_from_dict(clan_orders_to_dict(orders))
    assert restored_orders.actions[0].action_type == ActionType.CRISIS_CONTAIN
    assert restored_orders.actions[0].target_domain_id == crisis.domain_id


def test_server_rejects_crisis_action_without_active_crisis(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "crisis.sqlite3")
    service = MultiplayerGameService(repo)
    service.ensure_default_game()
    state = repo.get_game_state("main")
    clan_id = "ventrue"
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    actions = []
    for character in state.characters.values():
        if character.clan_id != clan_id or character.id == state.prince_id:
            continue
        if character.id == primogen_id:
            actions.append(
                GameAction(
                    clan_id=clan_id,
                    action_type=ActionType.CRISIS_CONTAIN,
                    actor_character_id=character.id,
                    target_domain_id=next(iter(state.domains)),
                )
            )
        else:
            actions.append(
                GameAction(
                    clan_id=clan_id,
                    action_type=ActionType.BUILD_INFLUENCE,
                    actor_character_id=character.id,
                )
            )
    orders = ClanNightOrders(
        clan_id=clan_id,
        actions=tuple(actions),
        vote=PrimogenVote(primogen_id, primogen_id),
        version=2,
    )

    try:
        service.validate_orders(state, clan_id, orders)
    except ValueError as exc:
        assert "No active crisis" in str(exc)
    else:
        raise AssertionError("Forged crisis order should be rejected")
