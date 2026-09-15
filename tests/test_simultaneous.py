from copy import deepcopy

from game.models import ActionType, GameAction, PrimogenVote
from game.resolution import resolve_night
from game.world import create_initial_game_state, seed_candidates


def _self_votes(state):
    return {
        clan_state.clan.primogen_id: PrimogenVote(
            clan_state.clan.primogen_id,
            clan_state.clan.primogen_id,
        )
        for clan_state in state.clan_states.values()
    }


def _prepared_state():
    state = create_initial_game_state()
    # Adrien réussit contre une cible difficile ; Hélène seulement contre la cible
    # la plus facile. Dans l'ancien moteur séquentiel, celui qui passait en premier
    # pouvait donc changer la cible choisie automatiquement par le second.
    state.characters["primogen_ventrue"].backgrounds["Contacts"] = 2
    camille = state.characters["toreador_camille"]
    if "Subterfuge" not in camille.expertises:
        camille.expertises = (*camille.expertises, "Subterfuge")
    return state


def _investigation_actions():
    return [
        GameAction(
            "ventrue",
            ActionType.INVESTIGATE,
            target_clan_id="toreador",
            actor_character_id="primogen_ventrue",
        ),
        GameAction(
            "ventrue",
            ActionType.INVESTIGATE,
            target_clan_id="toreador",
            actor_character_id="ventrue_helene",
        ),
    ]


def test_night_actions_are_independent_from_submission_order():
    first = _prepared_state()
    second = deepcopy(first)
    actions = _investigation_actions()

    result_a = resolve_night(first, actions, _self_votes(first), seed_candidates()).state
    result_b = resolve_night(second, list(reversed(actions)), _self_votes(second), seed_candidates()).state

    assert result_a.clan_states["ventrue"].known_character_intel == result_b.clan_states["ventrue"].known_character_intel
    assert result_a.characters["primogen_ventrue"].personal_influence == result_b.characters["primogen_ventrue"].personal_influence
    assert result_a.characters["ventrue_helene"].personal_influence == result_b.characters["ventrue_helene"].personal_influence


def test_two_simultaneous_investigators_use_the_same_starting_intel_snapshot():
    state = _prepared_state()
    result = resolve_night(
        state,
        _investigation_actions(),
        _self_votes(state),
        seed_candidates(),
    ).state

    # Les deux enquêteurs avaient Noémie comme meilleure cible au début de la
    # phase. Leurs deux succès se cumulent donc sur elle, jusqu'au niveau 2.
    assert result.clan_states["ventrue"].known_character_intel["toreador_noemie"] == 2
    # Camille était déjà connue via les coteries et ne devient pas artificiellement
    # la cible du second enquêteur à cause d'un effet de séquencement.
    assert result.clan_states["ventrue"].known_character_intel["toreador_camille"] == 1
