from game.config import DEFAULT_RULES
from game.crises import ANARCHS, active_crises, open_crisis
from game.external_pressures import resolve_external_pressures
from game.models import GameEvent
from game.world import create_initial_game_state


def test_resolved_crisis_is_not_reopened_during_same_night():
    state = create_initial_game_state()
    domain_id = next(iter(state.domains))
    opened = open_crisis(state, ANARCHS, domain_id)
    state.events.append(opened)

    state.night += 1
    category = opened.category.split("|")
    category[-1] = "resolved"
    state.events.append(
        GameEvent(
            night=state.night,
            category="|".join(category),
            message="crise résolue",
        )
    )
    state.events.append(
        GameEvent(
            night=state.night - 1,
            category=(
                f"external_pressure|{ANARCHS}|level|"
                f"{DEFAULT_RULES.anarch_incident_threshold}"
            ),
            message="pression encore haute",
        )
    )
    state.camarilla_stability = DEFAULT_RULES.anarch_stability_threshold - 1

    events = resolve_external_pressures(state)
    state.events.extend(events)

    assert active_crises(state) == []
    assert not any(event.category.startswith("crisis_state|") for event in events)
