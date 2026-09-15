"""Pactes diplomatiques formalisés par les Primogènes.

La négociation reste libre à l'Elysium. La force mécanique apparaît lorsqu'au
cours d'une même nuit deux Primogènes choisissent réciproquement l'action
Diplomatie. Le pacte est conservé dans l'historique d'événements : aucune table
ou migration de sauvegarde supplémentaire n'est nécessaire.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .config import DEFAULT_RULES, GameRules
from .models import ActionType, GameAction, GameEvent, GameState
from .social_politics import add_grievance


PACT_EVENT_PREFIX = "diplomatic_pact"
ACTIVE = "active"
BROKEN = "broken"
EXPIRED = "expired"

HOSTILE_PACT_ACTIONS = frozenset(
    {
        ActionType.UNDERMINE,
        ActionType.POACH,
        ActionType.DOMAIN_INTRUSION,
        ActionType.BRACONNAGE,
    }
)


@dataclass(frozen=True)
class DiplomaticPactView:
    id: str
    clan_a_id: str
    clan_b_id: str
    created_night: int
    expires_night: int
    status: str = ACTIVE
    broken_by_clan_id: str | None = None
    resolved_night: int | None = None

    def involves(self, clan_id: str) -> bool:
        return clan_id in {self.clan_a_id, self.clan_b_id}

    def other_clan(self, clan_id: str) -> str:
        if clan_id == self.clan_a_id:
            return self.clan_b_id
        if clan_id == self.clan_b_id:
            return self.clan_a_id
        raise ValueError("Clan is not part of this diplomatic pact")


def _pair(first: str, second: str) -> tuple[str, str]:
    if first == second:
        raise ValueError("A diplomatic pact requires two different clans")
    return tuple(sorted((first, second)))  # type: ignore[return-value]


def _pact_id(first: str, second: str, night: int) -> str:
    clan_a, clan_b = _pair(first, second)
    return f"pact_{clan_a}_{clan_b}_{night}"


def _active_category(pact: DiplomaticPactView) -> str:
    return "|".join(
        (
            PACT_EVENT_PREFIX,
            pact.id,
            ACTIVE,
            pact.clan_a_id,
            pact.clan_b_id,
            str(pact.created_night),
            str(pact.expires_night),
        )
    )


def _broken_category(pact_id: str, breaking_clan_id: str, night: int) -> str:
    return "|".join(
        (PACT_EVENT_PREFIX, pact_id, BROKEN, breaking_clan_id, str(night))
    )


def list_diplomatic_pacts(state: GameState) -> tuple[DiplomaticPactView, ...]:
    """Reconstruit l'état courant des pactes à partir de l'historique persistant."""

    pacts: dict[str, DiplomaticPactView] = {}
    for event in state.events:
        parts = event.category.split("|")
        if not parts or parts[0] != PACT_EVENT_PREFIX or len(parts) < 3:
            continue
        pact_id = parts[1]
        status = parts[2]
        if status == ACTIVE and len(parts) == 7:
            try:
                pact = DiplomaticPactView(
                    id=pact_id,
                    clan_a_id=parts[3],
                    clan_b_id=parts[4],
                    created_night=int(parts[5]),
                    expires_night=int(parts[6]),
                )
            except ValueError:
                continue
            pacts[pact_id] = pact
        elif status == BROKEN and len(parts) == 5 and pact_id in pacts:
            try:
                resolved_night = int(parts[4])
            except ValueError:
                continue
            pacts[pact_id] = replace(
                pacts[pact_id],
                status=BROKEN,
                broken_by_clan_id=parts[3],
                resolved_night=resolved_night,
            )

    values: list[DiplomaticPactView] = []
    for pact in pacts.values():
        if pact.status == ACTIVE and state.night > pact.expires_night:
            pact = replace(
                pact,
                status=EXPIRED,
                resolved_night=pact.expires_night,
            )
        values.append(pact)
    return tuple(sorted(values, key=lambda item: (item.created_night, item.id), reverse=True))


def active_pact_between(
    state: GameState,
    first_clan_id: str,
    second_clan_id: str,
) -> DiplomaticPactView | None:
    target_pair = _pair(first_clan_id, second_clan_id)
    for pact in list_diplomatic_pacts(state):
        if pact.status != ACTIVE:
            continue
        if _pair(pact.clan_a_id, pact.clan_b_id) == target_pair:
            return pact
    return None


def diplomatic_pact_bonus(
    state: GameState,
    first_clan_id: str,
    second_clan_id: str,
    rules: GameRules = DEFAULT_RULES,
) -> int:
    return (
        rules.diplomatic_pact_diplomacy_bonus
        if active_pact_between(state, first_clan_id, second_clan_id)
        else 0
    )


def _diplomacy_intent(state: GameState, action: GameAction) -> tuple[str, str] | None:
    if action.action_type != ActionType.DIPLOMACY:
        return None
    clan_state = state.clan_states.get(action.clan_id)
    if clan_state is None:
        return None
    actor_id = action.actor_character_id or clan_state.clan.primogen_id
    if actor_id != clan_state.clan.primogen_id:
        return None

    target_clan_id: str | None = None
    if action.target_character_id:
        target = state.characters.get(action.target_character_id)
        if target is None or not target.clan_id:
            return None
        target_clan_id = target.clan_id
        if target.id != state.clan_states[target_clan_id].clan.primogen_id:
            return None
    elif action.target_clan_id:
        target_clan_id = action.target_clan_id

    if not target_clan_id or target_clan_id == action.clan_id:
        return None
    if target_clan_id not in state.clan_states:
        return None
    return action.clan_id, target_clan_id


def register_reciprocal_diplomatic_pacts(
    state: GameState,
    actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Formalise les intentions réciproques des Primogènes pour les nuits suivantes."""

    intents = {
        intent
        for action in actions
        if (intent := _diplomacy_intent(state, action)) is not None
    }
    events: list[GameEvent] = []
    handled: set[tuple[str, str]] = set()
    for first, second in sorted(intents):
        pair = _pair(first, second)
        if pair in handled or (second, first) not in intents:
            continue
        handled.add(pair)
        if active_pact_between(state, first, second):
            continue

        clan_a, clan_b = pair
        pact = DiplomaticPactView(
            id=_pact_id(clan_a, clan_b, state.night),
            clan_a_id=clan_a,
            clan_b_id=clan_b,
            created_night=state.night,
            expires_night=state.night + rules.diplomatic_pact_duration_nights - 1,
        )
        primogen_a = state.characters[state.clan_states[clan_a].clan.primogen_id]
        primogen_b = state.characters[state.clan_states[clan_b].clan.primogen_id]
        events.append(
            GameEvent(
                night=state.night,
                category=_active_category(pact),
                message=(
                    f"{primogen_a.name} et {primogen_b.name} formalisent un pacte de coopération "
                    f"entre {state.clan_states[clan_a].clan.name} et "
                    f"{state.clan_states[clan_b].clan.name}, valable jusqu'à la fin de la nuit "
                    f"{pact.expires_night}."
                ),
            )
        )
    return events


def _action_target_clan(state: GameState, action: GameAction) -> str | None:
    if action.target_character_id:
        target = state.characters.get(action.target_character_id)
        return target.clan_id if target else None
    if action.target_domain_id:
        domain = state.domains.get(action.target_domain_id)
        holder = state.characters.get(domain.holder_id or "") if domain else None
        return holder.clan_id if holder else None
    if action.target_clan_id:
        return action.target_clan_id
    return None


def breach_diplomatic_pacts(
    state: GameState,
    executed_actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Rompt les pactes actifs lorsqu'un clan exécute une manœuvre hostile."""

    events: list[GameEvent] = []
    breached_ids: set[str] = set()
    for action in executed_actions:
        if action.action_type not in HOSTILE_PACT_ACTIONS:
            continue
        target_clan_id = _action_target_clan(state, action)
        if not target_clan_id or target_clan_id == action.clan_id:
            continue
        pact = active_pact_between(state, action.clan_id, target_clan_id)
        if pact is None or pact.id in breached_ids:
            continue
        breached_ids.add(pact.id)

        acting_state = state.clan_states[action.clan_id]
        target_state = state.clan_states[target_clan_id]
        acting_state.relations[target_clan_id] = (
            acting_state.relations.get(target_clan_id, 0.0)
            - rules.diplomatic_pact_breach_relation_loss
        )
        target_state.relations[action.clan_id] = (
            target_state.relations.get(action.clan_id, 0.0)
            - rules.diplomatic_pact_breach_relation_loss
        )
        state.camarilla_stability = max(
            0.0,
            state.camarilla_stability - rules.diplomatic_pact_breach_stability_loss,
        )

        offending_primogen_id = acting_state.clan.primogen_id
        offended_primogen_id = target_state.clan.primogen_id
        add_grievance(
            state,
            owner_id=offended_primogen_id,
            target_id=offending_primogen_id,
            reason=(
                f"Rupture du pacte diplomatique par une action {action.action_type.value} "
                f"contre {target_state.clan.name}"
            ),
            severity=1,
        )
        events.append(
            GameEvent(
                night=state.night,
                category=_broken_category(pact.id, action.clan_id, state.night),
                message=(
                    f"{acting_state.clan.name} rompt son pacte de coopération avec "
                    f"{target_state.clan.name} en lançant une manœuvre hostile "
                    f"({action.action_type.value}). La confiance politique et la stabilité de la "
                    "Camarilla en souffrent."
                ),
            )
        )
    return events
