"""Contestation d'une Praxis reconnue.

La Camarilla n'applique pas ici une procédure constitutionnelle universelle : la
chronique modélise la perte de reconnaissance politique du Prince. Les Primogènes
qui engagent publiquement leur influence sont pondérés par le même système de
factions internes que lors de la reconnaissance d'une nouvelle Praxis.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_RULES, GameRules
from .factions import determine_faction_stances
from .models import ActionType, GameAction, GameEvent, GameState
from .politics import primogen_political_weights
from .social_politics import add_grievance


@dataclass(frozen=True)
class PraxisChallengeResolution:
    challenger_primogen_ids: tuple[str, ...]
    challenger_clan_ids: tuple[str, ...]
    support_influence: float
    total_influence: float
    required_influence: float
    success: bool


def validate_praxis_challenge_action(state: GameState, action: GameAction) -> str:
    if action.action_type != ActionType.CHALLENGE_PRAXIS:
        raise ValueError("Not a Praxis challenge action")
    if state.prince_id is None:
        raise ValueError("No recognized Prince can be challenged")
    clan_state = state.clan_states.get(action.clan_id)
    if clan_state is None:
        raise ValueError("Unknown clan in Praxis challenge")
    actor_id = action.actor_character_id or clan_state.clan.primogen_id
    if actor_id != clan_state.clan.primogen_id:
        raise ValueError("Only the current Primogen may challenge the Praxis")
    if actor_id not in state.characters:
        raise ValueError("Unknown Primogen in Praxis challenge")
    return actor_id


def challenge_intent_event(state: GameState, action: GameAction) -> GameEvent:
    actor_id = validate_praxis_challenge_action(state, action)
    actor = state.characters[actor_id]
    prince = state.characters[state.prince_id]
    return GameEvent(
        night=state.night,
        category="praxis_challenge",
        message=(
            f"{actor.name} conteste publiquement la reconnaissance de {prince.name} comme Prince "
            "et engage le poids politique de son clan contre la Praxis actuelle."
        ),
    )


def resolve_praxis_challenge(
    state: GameState,
    executed_actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
    *,
    reference_state: GameState | None = None,
) -> tuple[PraxisChallengeResolution | None, list[GameEvent]]:
    """Résout la coalition sur un état de référence, applique les effets sur ``state``."""

    if not 0 <= rules.praxis_challenge_threshold < 1:
        raise ValueError("praxis_challenge_threshold must be between 0 and 1")
    if rules.praxis_challenge_min_primogens < 1:
        raise ValueError("praxis_challenge_min_primogens must be positive")

    challenge_actions = [
        action
        for action in executed_actions
        if action.action_type == ActionType.CHALLENGE_PRAXIS
    ]
    if not challenge_actions:
        return None, []

    reference = reference_state or state
    if reference.prince_id is None or state.prince_id is None:
        raise ValueError("No recognized Prince can be challenged")
    if reference.prince_id != state.prince_id:
        raise ValueError("Praxis changed before challenge resolution")

    challenger_by_primogen: dict[str, str] = {}
    for action in challenge_actions:
        primogen_id = validate_praxis_challenge_action(reference, action)
        challenger_by_primogen[primogen_id] = action.clan_id

    stances = determine_faction_stances(reference)
    weights, _ = primogen_political_weights(
        reference,
        stances,
        rules.opposition_transfer_ratio,
    )
    total_influence = sum(weights.values())
    support_influence = sum(
        weights.get(primogen_id, 0.0)
        for primogen_id in challenger_by_primogen
    )
    required_influence = total_influence * rules.praxis_challenge_threshold
    success = (
        len(challenger_by_primogen) >= rules.praxis_challenge_min_primogens
        and total_influence > 0
        and support_influence > required_influence
    )

    resolution = PraxisChallengeResolution(
        challenger_primogen_ids=tuple(sorted(challenger_by_primogen)),
        challenger_clan_ids=tuple(sorted(challenger_by_primogen.values())),
        support_influence=support_influence,
        total_influence=total_influence,
        required_influence=required_influence,
        success=success,
    )

    prince_id = state.prince_id
    prince = state.characters[prince_id]
    challenger_names = ", ".join(
        state.characters[primogen_id].name
        for primogen_id in resolution.challenger_primogen_ids
    )

    if success:
        for primogen_id in resolution.challenger_primogen_ids:
            add_grievance(
                state,
                owner_id=prince_id,
                target_id=primogen_id,
                reason="Participation à la coalition ayant fait tomber la Praxis",
                severity=2,
            )
        prince.status = max(0, prince.status - rules.deposed_prince_status_loss)
        state.camarilla_stability = max(
            0.0,
            state.camarilla_stability - rules.praxis_challenge_success_stability_loss,
        )
        state.masquerade_integrity = max(
            0.0,
            state.masquerade_integrity - rules.praxis_challenge_success_masquerade_loss,
        )
        state.prince_id = None
        state.prince_political_capital = 0.0
        state.praxis_status = "contested"
        events = [
            GameEvent(
                night=state.night,
                category="praxis",
                message=(
                    f"La coalition menée par {challenger_names} rassemble {support_influence:.0f} "
                    f"d'influence sur {total_influence:.0f}. La reconnaissance de {prince.name} "
                    "s'effondre : la Praxis est ouverte et devra être reconnue de nouveau lors "
                    "de la prochaine nuit."
                ),
            )
        ]
    else:
        state.camarilla_stability = max(
            0.0,
            state.camarilla_stability - rules.praxis_challenge_failure_stability_loss,
        )
        for primogen_id, clan_id in challenger_by_primogen.items():
            state.prince_relations[clan_id] = (
                state.prince_relations.get(clan_id, 0.0)
                - rules.praxis_challenge_failure_prince_relation_loss
            )
            add_grievance(
                state,
                owner_id=prince_id,
                target_id=primogen_id,
                reason="Contestation publique infructueuse de la Praxis",
                severity=1,
            )
        minimum_note = (
            f" et {rules.praxis_challenge_min_primogens} Primogènes minimum"
            if len(challenger_by_primogen) < rules.praxis_challenge_min_primogens
            else ""
        )
        events = [
            GameEvent(
                night=state.night,
                category="praxis",
                message=(
                    f"La contestation portée par {challenger_names} échoue : "
                    f"{support_influence:.0f}/{total_influence:.0f} d'influence engagée, "
                    f"seuil strictement supérieur à {required_influence:.0f}{minimum_note}. "
                    f"{prince.name} conserve la reconnaissance de sa Praxis."
                ),
            )
        ]

    return resolution, events
