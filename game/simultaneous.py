"""Résolution simultanée des missions de nuit.

Chaque mission est évaluée sur le même état de référence, puis ses deltas sont
fusionnés. Ainsi, un ordre ne devient pas plus facile ou plus difficile simplement
parce qu'il a été parcouru avant un autre dans la liste des soumissions.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .actions import apply_action
from .config import DEFAULT_RULES, GameRules
from .coteries import initialize_coteries
from .domains import open_domain_dispute
from .factions import initialize_factions
from .models import ClanFactionSide, GameAction, GameEvent, GameState
from .social_politics import add_grievance


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _action_key(action: GameAction) -> tuple[str, str, str, str, str, str]:
    """Ordre d'affichage stable uniquement ; il ne modifie pas les calculs."""

    return (
        action.clan_id,
        action.actor_character_id or "",
        action.action_type.value,
        action.target_character_id or "",
        action.target_clan_id or "",
        action.target_domain_id or "",
    )


def resolve_actions_simultaneously(
    state: GameState,
    actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Évalue toutes les actions sur un snapshot puis applique leurs effets cumulés.

    Les modifications numériques s'additionnent depuis le même état initial. Les
    changements de faction contradictoires sur une même cible s'annulent et la
    cible conserve sa faction de début de phase. Les nouveaux griefs et litiges
    sont recréés via leurs APIs afin de conserver des identifiants uniques.
    """

    if not actions:
        return []

    # Les liens canoniques doivent déjà exister avant de figer le snapshot, sinon
    # leur initialisation dans chaque simulation serait elle-même comptée en delta.
    initialize_coteries(state)
    baseline = deepcopy(state)

    influence_delta: dict[str, float] = defaultdict(float)
    primogen_relation_delta: dict[str, int] = defaultdict(int)
    personal_relation_delta: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    clan_relation_delta: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    character_intel_delta: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    domain_intel_delta: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    domain_pressure_delta: dict[str, int] = defaultdict(int)
    faction_proposals: dict[tuple[str, str], set[ClanFactionSide]] = defaultdict(set)
    boon_updates: dict[str, object] = {}
    new_grievances: list[object] = []
    new_disputes: list[object] = []
    events: list[GameEvent] = []

    for action in sorted(actions, key=_action_key):
        trial = deepcopy(baseline)
        event = apply_action(trial, action, rules)
        events.append(event)

        for character_id, before in baseline.characters.items():
            after = trial.characters[character_id]
            influence_delta[character_id] += after.personal_influence - before.personal_influence
            primogen_relation_delta[character_id] += (
                after.relation_to_primogen - before.relation_to_primogen
            )
            relation_targets = set(before.relations) | set(after.relations)
            for target_id in relation_targets:
                personal_relation_delta[character_id][target_id] += (
                    after.relations.get(target_id, 0) - before.relations.get(target_id, 0)
                )

        for clan_id, before_clan in baseline.clan_states.items():
            after_clan = trial.clan_states[clan_id]
            relation_targets = set(before_clan.relations) | set(after_clan.relations)
            for target_clan_id in relation_targets:
                clan_relation_delta[clan_id][target_clan_id] += (
                    after_clan.relations.get(target_clan_id, 0.0)
                    - before_clan.relations.get(target_clan_id, 0.0)
                )

            intel_targets = set(before_clan.known_character_intel) | set(
                after_clan.known_character_intel
            )
            for target_id in intel_targets:
                character_intel_delta[clan_id][target_id] += (
                    after_clan.known_character_intel.get(target_id, 0)
                    - before_clan.known_character_intel.get(target_id, 0)
                )

            domain_targets = set(before_clan.known_domain_intel) | set(after_clan.known_domain_intel)
            for domain_id in domain_targets:
                domain_intel_delta[clan_id][domain_id] += (
                    after_clan.known_domain_intel.get(domain_id, 0)
                    - before_clan.known_domain_intel.get(domain_id, 0)
                )

            membership_targets = set(before_clan.faction_memberships) | set(
                after_clan.faction_memberships
            )
            for character_id in membership_targets:
                before_side = before_clan.faction_memberships.get(character_id)
                after_side = after_clan.faction_memberships.get(character_id)
                if after_side is not None and after_side != before_side:
                    faction_proposals[(clan_id, character_id)].add(ClanFactionSide(after_side))

        for domain_id, before_domain in baseline.domains.items():
            domain_pressure_delta[domain_id] += (
                trial.domains[domain_id].pressure - before_domain.pressure
            )

        for boon_id, before_boon in baseline.boons.items():
            after_boon = trial.boons[boon_id]
            if (
                after_boon.status != before_boon.status
                or after_boon.called_night != before_boon.called_night
                or after_boon.resolved_night != before_boon.resolved_night
            ):
                boon_updates[boon_id] = deepcopy(after_boon)

        for grievance_id in set(trial.grievances) - set(baseline.grievances):
            new_grievances.append(deepcopy(trial.grievances[grievance_id]))
        for dispute_id in set(trial.domain_disputes) - set(baseline.domain_disputes):
            new_disputes.append(deepcopy(trial.domain_disputes[dispute_id]))

    # Les deltas sont appliqués depuis le snapshot, jamais depuis le résultat de
    # l'action précédente. Deux effets opposés peuvent donc réellement s'annuler.
    for character_id, before in baseline.characters.items():
        character = state.characters[character_id]
        character.personal_influence = max(
            0.0, before.personal_influence + influence_delta[character_id]
        )
        character.relation_to_primogen = _clamp(
            before.relation_to_primogen + primogen_relation_delta[character_id], 0, 2
        )
        relation_targets = set(before.relations) | set(personal_relation_delta[character_id])
        for target_id in relation_targets:
            character.relations[target_id] = _clamp(
                before.relations.get(target_id, 0)
                + personal_relation_delta[character_id][target_id],
                0,
                2,
            )

    for clan_id, before_clan in baseline.clan_states.items():
        clan_state = state.clan_states[clan_id]
        for target_clan_id, delta in clan_relation_delta[clan_id].items():
            clan_state.relations[target_clan_id] = (
                before_clan.relations.get(target_clan_id, 0.0) + delta
            )
        for target_id, delta in character_intel_delta[clan_id].items():
            clan_state.known_character_intel[target_id] = _clamp(
                before_clan.known_character_intel.get(target_id, 0) + delta,
                0,
                rules.max_intel_level,
            )
        for domain_id, delta in domain_intel_delta[clan_id].items():
            clan_state.known_domain_intel[domain_id] = _clamp(
                before_clan.known_domain_intel.get(domain_id, 0) + delta,
                0,
                rules.max_intel_level,
            )

    for domain_id, before_domain in baseline.domains.items():
        state.domains[domain_id].pressure = max(
            0, before_domain.pressure + domain_pressure_delta[domain_id]
        )

    for (clan_id, character_id), proposals in faction_proposals.items():
        if len(proposals) == 1:
            state.clan_states[clan_id].faction_memberships[character_id] = next(iter(proposals))
        else:
            # Deux manœuvres incompatibles de la même nuit se neutralisent.
            original = baseline.clan_states[clan_id].faction_memberships.get(character_id)
            if original is not None:
                state.clan_states[clan_id].faction_memberships[character_id] = original
            character = state.characters[character_id]
            events.append(
                GameEvent(
                    night=state.night,
                    category="faction",
                    message=(
                        f"Des pressions politiques contradictoires s'exercent simultanément sur "
                        f"{character.name}; aucun changement de faction ne s'impose cette nuit."
                    ),
                    audience_clan_ids=(clan_id,),
                )
            )

    for boon_id, updated in boon_updates.items():
        state.boons[boon_id] = updated

    for grievance in new_grievances:
        add_grievance(
            state,
            owner_id=grievance.owner_id,
            target_id=grievance.target_id,
            reason=grievance.reason,
            severity=grievance.severity,
        )

    for dispute in new_disputes:
        open_domain_dispute(
            state,
            domain_id=dispute.domain_id,
            claimant_id=dispute.claimant_id,
            respondent_id=dispute.respondent_id,
            reason=dispute.reason,
            severity=dispute.severity,
            public=dispute.public,
        )

    initialize_factions(state)
    return events
