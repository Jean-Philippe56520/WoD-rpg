import pytest

from game.actions import apply_action
from game.config import DEFAULT_RULES
from game.coteries import effective_relation_to_primogen
from game.models import ActionType, Candidate, CoterieSide, GameAction, PrimogenVote
from game.resolution import resolve_night
from game.world import create_initial_game_state, seed_candidates


def self_votes(state):
    return {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, cs.clan.primogen_id)
        for cs in state.clan_states.values()
    }


def test_one_vampire_cannot_perform_two_actions_in_same_night():
    state = create_initial_game_state()
    actions = [
        GameAction("ventrue", ActionType.BUILD_INFLUENCE, actor_character_id="ventrue_victor"),
        GameAction("ventrue", ActionType.DIPLOMACY, actor_character_id="ventrue_victor", target_character_id="primogen_toreador"),
    ]
    with pytest.raises(ValueError, match="more than one action"):
        resolve_night(state, actions, self_votes(state), seed_candidates())


def test_each_member_can_build_their_own_influence():
    state = create_initial_game_state()
    before = state.characters["ventrue_victor"].personal_influence
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.BUILD_INFLUENCE, actor_character_id="ventrue_victor")],
        self_votes(state),
        seed_candidates(),
    )
    assert resolution.state.characters["ventrue_victor"].personal_influence == before + 2
    assert state.characters["ventrue_victor"].personal_influence == before


def test_ideologically_compatible_opposition_member_can_be_better_diplomat_than_primogen():
    primogen_state = create_initial_game_state()
    opposition_state = create_initial_game_state()

    apply_action(
        primogen_state,
        GameAction(
            "toreador",
            ActionType.DIPLOMACY,
            actor_character_id="primogen_toreador",
            target_character_id="primogen_brujah",
        ),
    )
    apply_action(
        opposition_state,
        GameAction(
            "toreador",
            ActionType.DIPLOMACY,
            actor_character_id="toreador_lucien",
            target_character_id="primogen_brujah",
        ),
    )

    assert opposition_state.clan_states["toreador"].relations["brujah"] > primogen_state.clan_states["toreador"].relations["brujah"]
    assert opposition_state.characters["toreador_lucien"].relations["primogen_brujah"] == 1


def test_hostile_opposition_member_can_refuse_mission_and_build_own_influence():
    state = create_initial_game_state()
    sarah = state.characters["brujah_sarah"]
    assert effective_relation_to_primogen(state, sarah.id) == 0
    before_influence = sarah.personal_influence
    before_relation = state.clan_states["brujah"].relations["ventrue"]

    event = apply_action(
        state,
        GameAction(
            "brujah",
            ActionType.DIPLOMACY,
            actor_character_id=sarah.id,
            target_character_id="primogen_ventrue",
        ),
    )

    assert "refuse" in event.message
    assert sarah.personal_influence == before_influence + 1
    assert state.clan_states["brujah"].relations["ventrue"] == before_relation


def test_recruitment_moves_member_between_internal_coteries():
    state = create_initial_game_state()
    assert state.clan_states["ventrue"].coterie_memberships["ventrue_helene"] == CoterieSide.OPPOSITION
    apply_action(
        state,
        GameAction(
            "ventrue",
            ActionType.RECRUIT,
            actor_character_id="primogen_ventrue",
            target_character_id="ventrue_helene",
        ),
    )
    assert state.clan_states["ventrue"].coterie_memberships["ventrue_helene"] == CoterieSide.PRIMOGEN


def test_undermine_can_reduce_foreign_member_relation_to_primogen():
    state = create_initial_game_state()
    ines = state.characters["brujah_ines"]
    assert ines.relation_to_primogen == 1
    apply_action(
        state,
        GameAction(
            "ventrue",
            ActionType.UNDERMINE,
            actor_character_id="primogen_ventrue",
            target_character_id="brujah_ines",
        ),
    )
    assert ines.relation_to_primogen == 0


def test_investigation_by_cooperative_opposition_reveals_foreign_member():
    state = create_initial_game_state()
    assert effective_relation_to_primogen(state, "ventrue_helene") == 1
    event = apply_action(
        state,
        GameAction(
            "ventrue",
            ActionType.INVESTIGATE,
            target_clan_id="toreador",
            actor_character_id="ventrue_helene",
        ),
    )
    assert "renseignements" in event.message
    assert state.clan_states["ventrue"].known_character_intel["toreador_camille"] == 1


def test_poach_can_move_fragile_foreign_member_to_their_opposition():
    state = create_initial_game_state()
    ines = state.characters["brujah_ines"]
    ines.relation_to_primogen = 0
    assert effective_relation_to_primogen(state, ines.id) == 0
    assert state.clan_states["brujah"].coterie_memberships[ines.id] == CoterieSide.PRIMOGEN

    apply_action(
        state,
        GameAction(
            "ventrue",
            ActionType.POACH,
            actor_character_id="primogen_ventrue",
            target_character_id=ines.id,
        ),
    )
    assert state.clan_states["brujah"].coterie_memberships[ines.id] == CoterieSide.OPPOSITION


def test_legacy_v07_action_still_resolves_for_already_submitted_night():
    state = create_initial_game_state()
    before = state.characters["primogen_ventrue"].personal_influence
    resolution = resolve_night(
        state,
        [GameAction("ventrue", ActionType.CONSOLIDATE)],
        self_votes(state),
        seed_candidates(),
    )
    assert resolution.state.characters["primogen_ventrue"].personal_influence == before + 3
    assert resolution.state.night == 2


def test_more_than_legacy_action_budget_is_rejected():
    state = create_initial_game_state()
    actions = [
        GameAction("ventrue", ActionType.CONSOLIDATE),
        GameAction("ventrue", ActionType.BUILD_INFLUENCE),
        GameAction("ventrue", ActionType.DIPLOMACY, "toreador"),
    ]
    with pytest.raises(ValueError, match="maximum"):
        resolve_night(state, actions, self_votes(state), seed_candidates())


def test_disputed_praxis_weakens_camarilla_and_masquerade():
    state = create_initial_game_state()
    resolution = resolve_night(state, [], self_votes(state), seed_candidates())
    assert resolution.vote is not None and resolution.vote.disputed is True
    assert resolution.state.praxis_status == "contested"
    assert resolution.state.camarilla_stability == 100 - DEFAULT_RULES.disputed_stability_loss
    assert resolution.state.masquerade_integrity == 100 - DEFAULT_RULES.disputed_masquerade_loss


def test_primogen_majority_becomes_prince_and_seat_is_replaced():
    state = create_initial_game_state()
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_ventrue"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }
    resolution = resolve_night(state, [], votes, seed_candidates())
    new_state = resolution.state
    assert new_state.prince_id == "primogen_ventrue"
    assert new_state.characters["primogen_ventrue"].is_primogen is False
    assert new_state.clan_states["ventrue"].clan.primogen_id == "ventrue_victor"
    assert new_state.prince_political_capital == DEFAULT_RULES.prince_initial_capital


def test_non_primogen_majority_can_become_prince():
    state = create_initial_game_state()
    outsider = Candidate(id="outsider_test", name="Helene d'Arvor", is_primogen=False)
    candidates = seed_candidates() + [outsider]
    votes = {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, outsider.id)
        for cs in state.clan_states.values()
    }
    resolution = resolve_night(state, [], votes, candidates)
    assert resolution.state.prince_id == outsider.id
    assert resolution.state.characters[outsider.id].is_primogen is False
