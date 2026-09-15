from game.information import investigation_rumor_event, rumor_views
from game.models import ActionType, GameAction
from game.serialization import game_state_from_json, game_state_to_json
from game.simultaneous import resolve_actions_simultaneously
from game.world import create_initial_game_state


def _successful_ventrue_investigation(state):
    # Adrien atteint précisément la difficulté de Noémie avec Contacts 2.
    state.characters["primogen_ventrue"].backgrounds["Contacts"] = 2
    return GameAction(
        clan_id="ventrue",
        action_type=ActionType.INVESTIGATE,
        actor_character_id="primogen_ventrue",
        target_character_id="toreador_noemie",
    )


def test_successful_investigation_creates_private_unverified_rumor():
    state = create_initial_game_state()
    events = resolve_actions_simultaneously(state, [_successful_ventrue_investigation(state)])
    state.events.extend(events)

    ventrue_rumors = rumor_views(state, "ventrue")
    assert len(ventrue_rumors) == 1
    assert ventrue_rumors[0].subject_id == "toreador_noemie"
    assert ventrue_rumors[0].status == "unverified"
    assert ventrue_rumors[0].confidence == 1
    assert rumor_views(state, "brujah") == ()
    assert rumor_views(state, "toreador") == ()


def test_second_successful_investigation_verifies_existing_rumor():
    state = create_initial_game_state()
    action = _successful_ventrue_investigation(state)
    state.events.extend(resolve_actions_simultaneously(state, [action]))
    first = rumor_views(state, "ventrue")[0]
    assert first.status == "unverified"

    state.night += 1
    state.events.extend(resolve_actions_simultaneously(state, [action]))
    verified = rumor_views(state, "ventrue")[0]

    assert verified.id == first.id
    assert verified.confidence == 2
    assert verified.status in {"confirmed", "disproved"}


def test_rumor_truth_is_persistent_through_existing_event_serialization():
    state = create_initial_game_state()
    event = investigation_rumor_event(
        state,
        "ventrue",
        "toreador_noemie",
        "primogen_ventrue",
    )
    state.events.append(event)
    before = rumor_views(state, "ventrue")[0]

    restored = game_state_from_json(game_state_to_json(state))
    after = rumor_views(restored, "ventrue")[0]

    assert after.id == before.id
    assert after.claim == before.claim
    assert after.truth == before.truth
    assert after.status == "unverified"


def test_information_system_can_generate_false_leads_without_revealing_them_early():
    targets = (
        "ventrue_claire",
        "ventrue_victor",
        "ventrue_helene",
        "toreador_lucien",
        "toreador_camille",
        "toreador_gabriel",
        "toreador_noemie",
        "brujah_sarah",
        "brujah_yann",
        "brujah_ines",
    )
    false_views = []
    for target_id in targets:
        state = create_initial_game_state()
        target = state.characters[target_id]
        observer = next(clan for clan in state.clan_states if clan != target.clan_id)
        actor_id = state.clan_states[observer].clan.primogen_id
        state.events.append(investigation_rumor_event(state, observer, target_id, actor_id))
        view = rumor_views(state, observer)[0]
        if not view.truth:
            false_views.append(view)

    assert false_views, "The deterministic rumor pool must contain actual false leads"
    assert all(view.status == "unverified" for view in false_views)


def test_two_independent_same_night_sources_can_corroborate_or_disprove_a_rumor():
    state = create_initial_game_state()
    first = investigation_rumor_event(
        state, "ventrue", "toreador_noemie", "primogen_ventrue"
    )
    second = investigation_rumor_event(
        state, "ventrue", "toreador_noemie", "ventrue_helene"
    )
    state.events.extend([first, second])

    view = rumor_views(state, "ventrue")[0]
    assert view.confidence == 2
    assert view.status in {"confirmed", "disproved"}
