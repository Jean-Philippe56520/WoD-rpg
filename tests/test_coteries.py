import pytest

from game.coteries import (
    coterie_influence,
    effective_relation_to_primogen,
    ideology_relation_modifier,
    initialize_coteries,
    set_coterie_side,
)
from game.models import CoterieSide
from game.world import create_initial_game_state


def test_each_clan_has_exactly_two_political_sides():
    state = create_initial_game_state()
    for clan_id, clan_state in state.clan_states.items():
        sides = set(clan_state.coterie_memberships.values())
        assert sides == {CoterieSide.PRIMOGEN, CoterieSide.OPPOSITION}
        assert clan_state.coterie_memberships[clan_state.clan.primogen_id] == CoterieSide.PRIMOGEN


def test_opposition_leader_is_distinct_and_ideologically_different_from_primogen():
    state = create_initial_game_state()
    for clan_state in state.clan_states.values():
        primogen = state.characters[clan_state.clan.primogen_id]
        leader = state.characters[clan_state.opposition_leader_id]
        assert leader.id != primogen.id
        assert clan_state.coterie_memberships[leader.id] == CoterieSide.OPPOSITION
        assert (
            leader.humanity_axis != primogen.humanity_axis
            or leader.tradition_axis != primogen.tradition_axis
        )


def test_ideological_modifier_is_plus_zero_or_minus_one():
    state = create_initial_game_state()
    adrien = state.characters["primogen_ventrue"]
    victor = state.characters["ventrue_victor"]
    helene = state.characters["ventrue_helene"]
    claire = state.characters["ventrue_claire"]
    assert ideology_relation_modifier(victor, adrien) == 1
    assert ideology_relation_modifier(helene, adrien) == 0
    assert ideology_relation_modifier(claire, adrien) == -1


def test_effective_relation_combines_personal_relation_and_ideology():
    state = create_initial_game_state()
    assert effective_relation_to_primogen(state, "ventrue_victor") == 3
    assert effective_relation_to_primogen(state, "ventrue_helene") == 1
    assert effective_relation_to_primogen(state, "ventrue_claire") == -1


def test_coterie_influence_is_sum_of_member_influence():
    state = create_initial_game_state()
    assert coterie_influence(state, "ventrue", CoterieSide.PRIMOGEN) == 40
    assert coterie_influence(state, "ventrue", CoterieSide.OPPOSITION) == 27


def test_primogen_cannot_join_opposition():
    state = create_initial_game_state()
    with pytest.raises(ValueError, match="Primogen"):
        set_coterie_side(state, "primogen_ventrue", CoterieSide.OPPOSITION)


def test_missing_opposition_leader_is_rebuilt_without_resetting_memberships():
    state = create_initial_game_state()
    state.clan_states["ventrue"].opposition_leader_id = None
    before = dict(state.clan_states["ventrue"].coterie_memberships)
    initialize_coteries(state)
    leader_id = state.clan_states["ventrue"].opposition_leader_id
    assert leader_id is not None
    assert state.clan_states["ventrue"].coterie_memberships[leader_id] == CoterieSide.OPPOSITION
    assert state.clan_states["ventrue"].coterie_memberships["ventrue_victor"] == before["ventrue_victor"]
