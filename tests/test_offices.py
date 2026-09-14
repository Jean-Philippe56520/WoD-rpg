from game.config import DEFAULT_RULES
from game.ideology import primogen_current_id
from game.models import Candidate
from game.offices import install_prince, succession_score
from game.world import create_initial_game_state


def ventrue_winner(state):
    return Candidate(
        id="primogen_ventrue",
        name=state.characters["primogen_ventrue"].name,
        clan_id="ventrue",
        is_primogen=True,
    )


def test_installing_primogen_prince_updates_foreign_current_alliances():
    state = create_initial_game_state()
    current_id = "toreador__predatory_traditional"
    assert state.clan_states["toreador"].current_allies[current_id] == "primogen_ventrue"
    install_prince(state, ventrue_winner(state))
    successor_id = state.clan_states["ventrue"].clan.primogen_id
    assert state.clan_states["toreador"].current_allies[current_id] == successor_id


def test_successor_selection_uses_dynamic_current_influence():
    state = create_initial_game_state()
    install_prince(state, ventrue_winner(state))
    assert state.clan_states["ventrue"].clan.primogen_id == "ventrue_victor"
    assert primogen_current_id(state, "ventrue") == "ventrue__predatory_traditional"


def test_rival_current_candidate_can_take_primogeniture_if_balance_changes():
    state = create_initial_game_state()
    state.characters["ventrue_claire"].personal_influence = 100
    install_prince(state, ventrue_winner(state), DEFAULT_RULES)
    assert state.clan_states["ventrue"].clan.primogen_id == "ventrue_claire"
    assert primogen_current_id(state, "ventrue") == "ventrue__humanist_reformist"
    assert "ventrue__predatory_traditional" in state.clan_states["ventrue"].current_loyalties


def test_current_weight_contributes_to_succession_score():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    helene = state.characters["ventrue_helene"]
    assert succession_score(state, victor) > succession_score(state, helene)
