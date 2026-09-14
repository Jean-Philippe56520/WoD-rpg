from game.ideology import (
    build_currents,
    character_affinity,
    character_current_id,
    clan_total_influence,
    ideological_affinity_values,
    quadrant_for_values,
    shift_ideology,
)
from game.models import IdeologyQuadrant
from game.world import create_initial_game_state


def test_four_ideology_quadrants_are_derived_from_axes():
    assert quadrant_for_values(10, 10) == IdeologyQuadrant.HUMANIST_TRADITIONAL
    assert quadrant_for_values(10, -10) == IdeologyQuadrant.HUMANIST_REFORMIST
    assert quadrant_for_values(-10, 10) == IdeologyQuadrant.PREDATORY_TRADITIONAL
    assert quadrant_for_values(-10, -10) == IdeologyQuadrant.PREDATORY_RADICAL


def test_toreador_initially_exposes_all_four_possible_currents():
    state = create_initial_game_state()
    currents = build_currents(state, "toreador")
    assert len(currents) == 4
    assert {current.quadrant for current in currents.values()} == set(IdeologyQuadrant)


def test_current_influence_is_derived_from_member_influence():
    state = create_initial_game_state()
    current_id = "ventrue__predatory_traditional"
    assert build_currents(state, "ventrue")[current_id].influence == 40
    state.characters["ventrue_victor"].personal_influence += 5
    assert build_currents(state, "ventrue")[current_id].influence == 45
    assert clan_total_influence(state, "ventrue") == 72


def test_ideological_affinity_ranges_from_identical_to_opposite():
    assert ideological_affinity_values(50, -40, 50, -40) == 100
    assert ideological_affinity_values(100, 100, -100, -100) == -100
    assert ideological_affinity_values(50, 50, 50, -50) == 50


def test_character_affinity_uses_both_axes():
    state = create_initial_game_state()
    claire = state.characters["ventrue_claire"]
    lucien = state.characters["toreador_lucien"]
    adrien = state.characters["primogen_ventrue"]
    assert character_affinity(claire, lucien) > character_affinity(claire, adrien)


def test_crossing_an_axis_moves_character_to_another_current_without_changing_humanity():
    state = create_initial_game_state()
    claire = state.characters["ventrue_claire"]
    humanity_before = claire.humanity
    before = character_current_id(claire)
    previous, after = shift_ideology(state, claire.id, humanism_delta=-80)
    assert previous == before
    assert after == "ventrue__predatory_radical"
    assert claire.humanity == humanity_before
    assert after in build_currents(state, "ventrue")
    assert after in state.clan_states["ventrue"].current_allies
