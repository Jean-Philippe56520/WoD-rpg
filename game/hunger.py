"""Faim vampirique simplifiée pour le moteur politique asynchrone.

La chasse de routine ne consomme pas une action : disposer d'un Domaine personnel
ou d'un droit de chasse actif permet de se nourrir discrètement entre les scènes.
Sans accès exploitable, la Faim monte. Le braconnage reste l'option active d'urgence.
"""

from __future__ import annotations

from .clan_identity import routine_feeding_allowed
from .models import GameEvent, GameState, HuntingRightStatus


def active_hunting_access_domains(state: GameState, character_id: str) -> tuple[str, ...]:
    """Domaines où le vampire possède légalement un droit de chasse cette nuit."""

    domain_ids = {
        domain.id
        for domain in state.domains.values()
        if domain.holder_id == character_id
    }
    for right in state.hunting_rights.values():
        if right.beneficiary_id != character_id:
            continue
        if right.status != HuntingRightStatus.ACTIVE:
            continue
        if right.expires_night is not None and state.night > right.expires_night:
            continue
        domain_ids.add(right.domain_id)
    return tuple(sorted(domain_ids))


def exploitable_hunting_domains(state: GameState, character_id: str) -> tuple[str, ...]:
    character = state.characters[character_id]
    return tuple(
        domain_id
        for domain_id in active_hunting_access_domains(state, character_id)
        if routine_feeding_allowed(character, state.domains[domain_id])
    )


def preferred_hunting_domain(state: GameState, character_id: str) -> str | None:
    candidates = [
        state.domains[domain_id]
        for domain_id in exploitable_hunting_domains(state, character_id)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda domain: (domain.viandis, -domain.pressure, domain.id)).id


def hunger_penalty(hunger: int) -> int:
    """Malus politique compact : 0 jusqu'à 3, -1 à 4, -2 à 5."""

    return max(0, min(2, hunger - 3))


def resolve_hunger(state: GameState) -> list[GameEvent]:
    """Résout la chasse de routine en fin de nuit."""

    events: list[GameEvent] = []
    for character in state.characters.values():
        if not character.clan_id or character.id == state.prince_id:
            continue

        before = character.hunger
        legal_domains = active_hunting_access_domains(state, character.id)
        domain_id = preferred_hunting_domain(state, character.id)
        if domain_id is not None:
            character.hunger = max(1, character.hunger - 1)
            if character.hunger < before:
                domain = state.domains[domain_id]
                events.append(
                    GameEvent(
                        night=state.night,
                        category="faim",
                        message=(
                            f"{character.name} se nourrit légalement sur {domain.name} : "
                            f"Faim {before} → {character.hunger}."
                        ),
                        audience_clan_ids=(character.clan_id,),
                    )
                )
            continue

        character.hunger = min(5, character.hunger + 1)
        if character.hunger > before:
            if legal_domains and character.clan_id == "ventrue":
                cause = "ses accès légaux ne permettent pas de satisfaire son goût raffiné"
            else:
                cause = "il ne dispose d'aucun droit de chasse exploitable"
            warning = (
                " La Bête perturbera fortement ses actions politiques."
                if character.hunger >= 5
                else (
                    " La pression de la Bête commence à affecter ses capacités sociales et mentales."
                    if character.hunger >= 4
                    else ""
                )
            )
            events.append(
                GameEvent(
                    night=state.night,
                    category="faim",
                    message=(
                        f"{character.name} ne se nourrit pas correctement car {cause} : "
                        f"Faim {before} → {character.hunger}.{warning}"
                    ),
                    audience_clan_ids=(character.clan_id,),
                )
            )
    return events
