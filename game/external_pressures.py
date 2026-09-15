"""Pressions extérieures opportunistes sur la Camarilla locale.

La faiblesse politique attire les Anarchs ; les atteintes à la Mascarade attirent
les chasseurs mortels. Depuis la V0.20, atteindre un seuil n'inflige plus directement
la conséquence majeure : la pression ouvre d'abord une crise jouable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_RULES, GameRules
from .crises import (
    ANARCHS,
    HUNTERS,
    active_crises,
    has_active_crisis_for_faction,
    open_crisis,
    resolve_crisis_cycle,
)
from .models import Domain, GameEvent, GameState


PRESSURE_PREFIX = "external_pressure"


@dataclass(frozen=True)
class ExternalPressureState:
    anarch_pressure: int = 0
    hunter_attention: int = 0


def _clamp(value: int, rules: GameRules) -> int:
    return max(0, min(rules.external_pressure_max, value))


def _last_level(state: GameState, faction: str) -> int:
    value = 0
    prefix = f"{PRESSURE_PREFIX}|{faction}|level|"
    for event in state.events:
        if not event.category.startswith(prefix):
            continue
        try:
            value = int(event.category[len(prefix) :])
        except ValueError:
            continue
    return value


def current_external_pressures(state: GameState) -> ExternalPressureState:
    return ExternalPressureState(
        anarch_pressure=_last_level(state, ANARCHS),
        hunter_attention=_last_level(state, HUNTERS),
    )


def _level_event(
    state: GameState,
    faction: str,
    value: int,
    previous: int,
) -> GameEvent:
    label = "L'agitation anarch" if faction == ANARCHS else "L'attention des chasseurs mortels"
    direction = "progresse" if value > previous else "recule"
    return GameEvent(
        night=state.night,
        category=f"{PRESSURE_PREFIX}|{faction}|level|{value}",
        message=f"{label} {direction} ({previous} → {value}).",
    )


def _choose_anarch_target(state: GameState, excluded: set[str]) -> Domain | None:
    candidates = [domain for domain in state.domains.values() if domain.id not in excluded]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda domain: (
            domain.rempart,
            -domain.viandis,
            -domain.pressure,
            domain.id,
        ),
    )


def _choose_hunter_target(state: GameState, excluded: set[str]) -> Domain | None:
    candidates = [domain for domain in state.domains.values() if domain.id not in excluded]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda domain: (
            domain.masquerade_risk,
            domain.pressure,
            -domain.rempart,
            domain.id,
        ),
    )


def _next_anarch_pressure(state: GameState, current: int, rules: GameRules) -> int:
    if state.prince_id is None or state.praxis_status == "contested":
        return _clamp(current + rules.anarch_pressure_gain_contested, rules)
    if state.camarilla_stability < rules.anarch_stability_threshold:
        return _clamp(current + rules.anarch_pressure_gain_unstable, rules)
    if state.camarilla_stability >= rules.anarch_recovery_stability_threshold:
        return _clamp(current - rules.anarch_pressure_relief, rules)
    return current


def _next_hunter_attention(state: GameState, current: int, rules: GameRules) -> int:
    if state.masquerade_integrity < rules.hunter_critical_masquerade_threshold:
        return _clamp(current + rules.hunter_attention_gain_critical, rules)
    if state.masquerade_integrity < rules.hunter_masquerade_threshold:
        return _clamp(current + rules.hunter_attention_gain_exposed, rules)
    if state.masquerade_integrity >= rules.hunter_recovery_masquerade_threshold:
        return _clamp(current - rules.hunter_attention_relief, rules)
    return current


def resolve_external_pressures(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Résout les crises existantes, puis fait évoluer les pressions extérieures.

    Une crise active au début de la nuit bloque l'ouverture d'une deuxième crise
    de la même faction pendant cette résolution, même si elle vient d'être réglée.
    Cela évite une réapparition immédiate sans fenêtre politique intermédiaire.
    """

    active_at_start = active_crises(state)
    had_anarch_crisis = any(crisis.faction == ANARCHS for crisis in active_at_start)
    had_hunter_crisis = any(crisis.faction == HUNTERS for crisis in active_at_start)

    events = resolve_crisis_cycle(state, rules)

    previous = current_external_pressures(state)
    anarch_pressure = _next_anarch_pressure(state, previous.anarch_pressure, rules)
    hunter_attention = _next_hunter_attention(state, previous.hunter_attention, rules)

    # Les transitions de crise de cette nuit ne sont pas encore ajoutées à
    # state.events. On réserve donc au minimum tous les Domaines qui étaient sous
    # crise au début de cette phase de fin de nuit.
    reserved_domains = {crisis.domain_id for crisis in active_at_start}

    if anarch_pressure >= rules.anarch_incident_threshold and not had_anarch_crisis:
        domain = _choose_anarch_target(state, reserved_domains)
        if domain is not None:
            events.append(open_crisis(state, ANARCHS, domain.id, rules))
            reserved_domains.add(domain.id)
            anarch_pressure = _clamp(
                anarch_pressure - rules.anarch_incident_pressure_relief,
                rules,
            )

    if hunter_attention >= rules.hunter_incident_threshold and not had_hunter_crisis:
        domain = _choose_hunter_target(state, reserved_domains)
        if domain is not None:
            events.append(open_crisis(state, HUNTERS, domain.id, rules))
            reserved_domains.add(domain.id)
            hunter_attention = _clamp(
                hunter_attention - rules.hunter_incident_attention_relief,
                rules,
            )

    if anarch_pressure != previous.anarch_pressure:
        events.append(_level_event(state, ANARCHS, anarch_pressure, previous.anarch_pressure))
    if hunter_attention != previous.hunter_attention:
        events.append(_level_event(state, HUNTERS, hunter_attention, previous.hunter_attention))
    return events
