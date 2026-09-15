from game.config import DEFAULT_RULES
from game.crises import ANARCHS, HUNTERS, active_crises
from game.external_pressures import (
    current_external_pressures,
    resolve_external_pressures,
)
from game.models import Candidate, GameEvent
from game.offices import install_prince
from game.serialization import game_state_from_json, game_state_to_json
from game.world import create_initial_game_state


def recognized_state():
    state = create_initial_game_state()
    install_prince(state, Candidate("prince_test", "Prince Test", None, False))
    return state


def seed_level(state, faction, level):
    state.events.append(
        GameEvent(
            night=state.night,
            category=f"external_pressure|{faction}|level|{level}",
            message="seed",
        )
    )


def test_stable_recognized_city_does_not_create_external_pressure():
    state = recognized_state()

    events = resolve_external_pressures(state)

    assert events == []
    assert current_external_pressures(state).anarch_pressure == 0
    assert current_external_pressures(state).hunter_attention == 0


def test_contested_praxis_builds_anarch_pressure():
    state = recognized_state()
    state.prince_id = None
    state.praxis_status = "contested"

    events = resolve_external_pressures(state)
    state.events.extend(events)

    pressure = current_external_pressures(state)
    assert pressure.anarch_pressure == DEFAULT_RULES.anarch_pressure_gain_contested
    assert pressure.hunter_attention == 0
    assert any("agitation anarch" in event.message for event in events)


def test_low_stability_builds_anarch_pressure_even_with_recognized_prince():
    state = recognized_state()
    state.camarilla_stability = DEFAULT_RULES.anarch_stability_threshold - 1

    events = resolve_external_pressures(state)
    state.events.extend(events)

    assert current_external_pressures(state).anarch_pressure == DEFAULT_RULES.anarch_pressure_gain_unstable


def test_damaged_masquerade_builds_and_critical_damage_accelerates_hunter_attention():
    exposed = recognized_state()
    exposed.masquerade_integrity = DEFAULT_RULES.hunter_masquerade_threshold - 1
    events = resolve_external_pressures(exposed)
    exposed.events.extend(events)
    assert current_external_pressures(exposed).hunter_attention == DEFAULT_RULES.hunter_attention_gain_exposed

    critical = recognized_state()
    critical.masquerade_integrity = DEFAULT_RULES.hunter_critical_masquerade_threshold - 1
    events = resolve_external_pressures(critical)
    critical.events.extend(events)
    assert current_external_pressures(critical).hunter_attention == DEFAULT_RULES.hunter_attention_gain_critical


def test_high_stability_and_clean_masquerade_reduce_existing_pressures():
    state = recognized_state()
    seed_level(state, ANARCHS, 2)
    seed_level(state, HUNTERS, 2)

    events = resolve_external_pressures(state)
    state.events.extend(events)
    pressure = current_external_pressures(state)

    assert pressure.anarch_pressure == 1
    assert pressure.hunter_attention == 1


def test_anarch_threshold_opens_playable_crisis_and_consumes_part_of_pressure():
    state = recognized_state()
    state.camarilla_stability = DEFAULT_RULES.anarch_stability_threshold - 1
    seed_level(state, ANARCHS, DEFAULT_RULES.anarch_incident_threshold - 1)
    expected_domain = min(
        state.domains.values(),
        key=lambda domain: (domain.rempart, -domain.viandis, -domain.pressure, domain.id),
    )
    pressure_before = expected_domain.pressure
    stability_before = state.camarilla_stability

    events = resolve_external_pressures(state)
    state.events.extend(events)

    assert expected_domain.pressure == pressure_before
    assert state.camarilla_stability == stability_before
    assert current_external_pressures(state).anarch_pressure == (
        DEFAULT_RULES.anarch_incident_threshold - DEFAULT_RULES.anarch_incident_pressure_relief
    )
    crises = active_crises(state)
    assert len(crises) == 1
    assert crises[0].faction == ANARCHS
    assert crises[0].domain_id == expected_domain.id
    assert crises[0].stage == 1


def test_hunter_threshold_opens_playable_crisis_and_consumes_attention():
    state = recognized_state()
    state.masquerade_integrity = DEFAULT_RULES.hunter_masquerade_threshold - 1
    seed_level(state, HUNTERS, DEFAULT_RULES.hunter_incident_threshold - 1)
    expected_domain = max(
        state.domains.values(),
        key=lambda domain: (domain.masquerade_risk, domain.pressure, -domain.rempart, domain.id),
    )
    pressure_before = expected_domain.pressure
    masquerade_before = state.masquerade_integrity

    events = resolve_external_pressures(state)
    state.events.extend(events)

    assert expected_domain.pressure == pressure_before
    assert state.masquerade_integrity == masquerade_before
    assert current_external_pressures(state).hunter_attention == (
        DEFAULT_RULES.hunter_incident_threshold - DEFAULT_RULES.hunter_incident_attention_relief
    )
    crises = active_crises(state)
    assert len(crises) == 1
    assert crises[0].faction == HUNTERS
    assert crises[0].domain_id == expected_domain.id
    assert crises[0].stage == 1


def test_active_crisis_prevents_duplicate_from_same_external_faction():
    state = recognized_state()
    state.camarilla_stability = DEFAULT_RULES.anarch_stability_threshold - 1
    seed_level(state, ANARCHS, DEFAULT_RULES.anarch_incident_threshold - 1)
    first = resolve_external_pressures(state)
    state.events.extend(first)
    seed_level(state, ANARCHS, DEFAULT_RULES.anarch_incident_threshold)

    second = resolve_external_pressures(state)
    state.events.extend(second)

    assert len([crisis for crisis in active_crises(state) if crisis.faction == ANARCHS]) == 1


def test_external_pressure_levels_survive_state_serialization():
    state = recognized_state()
    seed_level(state, ANARCHS, 3)
    seed_level(state, HUNTERS, 2)

    restored = game_state_from_json(game_state_to_json(state))
    pressure = current_external_pressures(restored)

    assert pressure.anarch_pressure == 3
    assert pressure.hunter_attention == 2
