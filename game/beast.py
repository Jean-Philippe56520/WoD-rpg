"""Conséquences de Bête à Faim critique.

WoD-rpg ne reproduit pas les jets de Frénésie du JDR papier. À Faim 5 sans route
de chasse exploitable, l'Humanité détermine le compromis entre maîtrise de soi et
conséquences politiques : les plus humains résistent mais restent affamés, les
plus prédateurs se nourrissent davantage au prix de la Mascarade et de leur image.
"""

from __future__ import annotations

from .hunger import preferred_hunting_domain
from .models import GameEvent, GameState


def _clamp_reputation(value: int) -> int:
    return max(-3, min(3, value))


def resolve_beast_pressure(state: GameState) -> list[GameEvent]:
    events: list[GameEvent] = []
    for character in state.characters.values():
        if not character.clan_id or character.id == state.prince_id:
            continue
        if character.hunger < 5:
            continue
        if preferred_hunting_domain(state, character.id) is not None:
            continue

        if character.humanity >= 7:
            before_influence = character.personal_influence
            character.personal_influence = max(0.0, character.personal_influence - 1)
            loss = before_influence - character.personal_influence
            events.append(
                GameEvent(
                    night=state.night,
                    category="bete",
                    message=(
                        f"{character.name} résiste à la Bête malgré une Faim extrême. "
                        f"Il évite de mettre la Mascarade en danger mais reste à Faim 5"
                        + (f" et abandonne {loss:.0f} point d'influence à cette lutte." if loss else ".")
                    ),
                    audience_clan_ids=(character.clan_id,),
                )
            )
            continue

        if character.humanity >= 5:
            character.hunger = 4
            state.masquerade_integrity = max(0.0, state.masquerade_integrity - 1)
            events.append(
                GameEvent(
                    night=state.night,
                    category="bete",
                    message=(
                        f"{character.name} cède partiellement à la Bête et trouve une proie hors des circuits autorisés : "
                        "Faim 5 → 4, intégrité de la Mascarade -1."
                    ),
                    audience_clan_ids=(character.clan_id,),
                )
            )
            continue

        character.hunger = 3
        character.reputation = _clamp_reputation(character.reputation - 1)
        state.masquerade_integrity = max(0.0, state.masquerade_integrity - 2)
        events.append(
            GameEvent(
                night=state.night,
                category="bete",
                message=(
                    f"{character.name} laisse la Bête prendre le dessus et se nourrit brutalement hors des règles : "
                    "Faim 5 → 3, intégrité de la Mascarade -2, réputation -1."
                ),
                audience_clan_ids=(character.clan_id,),
            )
        )
    return events
