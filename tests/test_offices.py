from game.config import DEFAULT_RULES
from game.models import Candidate
from game.offices import install_prince
from game.world import create_initial_game_state


def test_installing_primogen_prince_updates_foreign_opposition_alliance():
    state = create_initial_game_state()
    assert state.clan_states["toreador"].opposition_ally_id == "primogen_ventrue"
    winner = Candidate(
        id="primogen_ventrue",
        name=state.characters["primogen_ventrue"].name,
        clan_id="ventrue",
        is_primogen=True,
    )
    install_prince(state, winner)
    successor_id = state.clan_states["ventrue"].clan.primogen_id
    assert state.clan_states["toreador"].opposition_ally_id == successor_id


def test_successor_selection_uses_internal_political_weight():
    state = create_initial_game_state()
    winner = Candidate(
        id="primogen_ventrue",
        name=state.characters["primogen_ventrue"].name,
        clan_id="ventrue",
        is_primogen=True,
    )
    install_prince(state, winner)
    assert state.clan_states["ventrue"].clan.primogen_id == "ventrue_victor"
    assert state.clan_states["ventrue"].clan.dominant_current.leader_name == "Victor de Keravel"


def test_opposition_candidate_can_take_primogeniture_if_balance_changes():
    state = create_initial_game_state()
    clan = state.clan_states["ventrue"].clan
    clan.dominant_current.influence = 20
    clan.opposition_current.influence = 120
    winner = Candidate(
        id="primogen_ventrue",
        name=state.characters["primogen_ventrue"].name,
        clan_id="ventrue",
        is_primogen=True,
    )
    install_prince(state, winner, DEFAULT_RULES)
    assert clan.primogen_id == "ventrue_claire"
    assert clan.dominant_current.id == "ventrue_opposition"
    assert state.clan_states["ventrue"].opposition_loyalty == DEFAULT_RULES.succession_loyalty_reset
