"""Pressions extérieures opportunistes sur la Camarilla locale.

La faiblesse politique attire les Anarchs ; les atteintes à la Mascarade attirent
les chasseurs mortels. Les niveaux sont event-sourcés afin de rester persistants
sans nouvelle table ni migration de sauvegarde.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_RULES, GameRules
from .models import Domain, GameEvent, GameState


PRESSURE_PREFIX = "external_pressure"
INCIDENT_PREFIX = "external_incident"
ANARCHS = "anarchs"
HUNTERS = "hunters"


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
    if faction == ANARCHS:
        label = "L'agitation anarch"
    else:
        label = "L'attention des chasseurs mortels"
    direction = "progresse" if value > previous else "recule"
    return GameEvent(
        night=state.night,
        category=f"{PRESSURE_PREFIX}|{faction}|level|{value}",
        message=f"{label} {direction} ({previous} → {value}).",
    )


def _choose_anarch_target(state: GameState) -> Domain | None:
    if not state.domains:
        return None
    # Les Anarchs cherchent une position exploitable : faible Rempart, Viandis
    # intéressant, puis pression déjà existante qui facilite l'agitation locale.
    return min(
        state.domains.values(),
        key=lambda domain: (
            domain.rempart,
            -domain.viandis,
            -domain.pressure,
            domain.id,
        ),
    )


def _choose_hunter_target(state: GameState) -> Domain | None:
    if not state.domains:
        return None
    # Les chasseurs suivent d'abord les zones où les incidents sont les plus
    # dangereux pour la Mascarade, puis les endroits déjà sous pression.
    return max(
        state.domains.values(),
        key=lambda domain: (
            domain.masquerade_risk,
            domain.pressure,
            -domain.rempart,
            domain.id,
        ),
    )


def _next_anarch_pressure(
    state: GameState,
    current: int,
    rules: GameRules,
) -> int:
    if state.prince_id is None or state.praxis_status == "contested":
        return _clamp(current + rules.anarch_pressure_gain_contested, rules)
    if state.camarilla_stability < rules.anarch_stability_threshold:
        return _clamp(current + rules.anarch_pressure_gain_unstable, rules)
    if state.camarilla_stability >= rules.anarch_recovery_stability_threshold:
        return _clamp(current - rules.anarch_pressure_relief, rules)
    return current


def _next_hunter_attention(
    state: GameState,
    current: int,
    rules: GameRules,
) -> int:
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
    """Fait évoluer les menaces et applique les incidents de seuil.

    Un incident consomme une partie de la pression accumulée sans l'annuler : une
    ville durablement faible continuera donc d'attirer les opportunistes.
    """

    previous = current_external_pressures(state)
    anarch_pressure = _next_anarch_pressure(state, previous.anarch_pressure, rules)
    hunter_attention = _next_hunter_attention(state, previous.hunter_attention, rules)
    events: list[GameEvent] = []

    if anarch_pressure >= rules.anarch_incident_threshold:
        domain = _choose_anarch_target(state)
        if domain is not None:
            domain.pressure += rules.anarch_incident_domain_pressure_gain
            state.camarilla_stability = max(
                0.0,
                state.camarilla_stability - rules.anarch_incident_stability_loss,
            )
            anarch_pressure = _clamp(
                anarch_pressure - rules.anarch_incident_pressure_relief,
                rules,
            )
            events.append(
                GameEvent(
                    night=state.night,
                    category=f"{INCIDENT_PREFIX}|{ANARCHS}|{domain.id}|{state.night}",
                    message=(
                        f"Les Anarchs exploitent les fissures de la Camarilla autour de {domain.name}. "
                        f"Agitation locale : pression du Domaine +{rules.anarch_incident_domain_pressure_gain} "
                        f"et stabilité -{rules.anarch_incident_stability_loss:.0f}."
                    ),
                )
            )

    if hunter_attention >= rules.hunter_incident_threshold:
        domain = _choose_hunter_target(state)
        if domain is not None:
            domain.pressure += rules.hunter_incident_domain_pressure_gain
            state.masquerade_integrity = max(
                0.0,
                state.masquerade_integrity - rules.hunter_incident_masquerade_loss,
            )
            hunter_attention = _clamp(
                hunter_attention - rules.hunter_incident_attention_relief,
                rules,
            )
            events.append(
                GameEvent(
                    night=state.night,
                    category=f"{INCIDENT_PREFIX}|{HUNTERS}|{domain.id}|{state.night}",
                    message=(
                        f"Des chasseurs mortels resserrent leur surveillance autour de {domain.name}. "
                        f"Pression du Domaine +{rules.hunter_incident_domain_pressure_gain} et "
                        f"Mascarade -{rules.hunter_incident_masquerade_loss:.0f}."
                    ),
                )
            )

    if anarch_pressure != previous.anarch_pressure:
        events.append(_level_event(state, ANARCHS, anarch_pressure, previous.anarch_pressure))
    if hunter_attention != previous.hunter_attention:
        events.append(_level_event(state, HUNTERS, hunter_attention, previous.hunter_attention))
    return events
