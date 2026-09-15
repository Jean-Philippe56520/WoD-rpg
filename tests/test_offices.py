from game.config import DEFAULT_RULES
from game.models import Candidate, CoterieSide
from game.offices import install_prince, succession_score
from game.world import create_initial_game_state


def ventrue_winner(state):
    return Candidate(
        id="primogen_ventrue",
        name=state.characters["primogen_ventrue"].name,
        clan_id="ventrue",
        is_primogen=True,
    )


def test_installing_primogen_prince_updates_foreign_opposition_alliance():
    state = create_initial_game_state()
    assert state.clan_states["brujah"].opposition_allied_primogen_id == "primogen_ventrue"
    install_prince(state, ventrue_winner(state))
    successor_id = state.clan_states["ventrue"].clan.primogen_id
    assert successor_id == "ventrue_victor"
    assert state.clan_states["brujah"].opposition_allied_primogen_id == successor_id


def test_successor_selection_uses_coterie_influence_and_personal_position():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    helene = state.characters["ventrue_helene"]
    assert succession_score(state, victor) > succession_score(state, helene)
    install_prince(state, ventrue_winner(state))
    assert state.clan_states["ventrue"].clan.primogen_id == "ventrue_victor"


def test_opposition_candidate_can_take_primogeniture_if_balance_changes():
    state = create_initial_game_state()
    state.characters["ventrue_claire"].personal_influence = 100
    install_prince(state, ventrue_winner(state), DEFAULT_RULES)

    clan_state = state.clan_states["ventrue"]
    assert clan_state.clan.primogen_id == "ventrue_claire"
    assert clan_state.coterie_memberships["ventrue_claire"] == CoterieSide.PRIMOGEN
    assert clan_state.opposition_leader_id == "ventrue_helene"

    claire = state.characters["ventrue_claire"]
    new_leader = state.characters[clan_state.opposition_leader_id]
    assert (
        new_leader.humanity_axis != claire.humanity_axis
        or new_leader.tradition_axis != claire.tradition_axis
    )


def test_prince_is_removed_from_clan_coterie_after_installation():
    state = create_initial_game_state()
    install_prince(state, ventrue_winner(state))
    assert "primogen_ventrue" not in state.clan_states["ventrue"].coterie_memberships
    assert state.characters["primogen_ventrue"].is_primogen is False
