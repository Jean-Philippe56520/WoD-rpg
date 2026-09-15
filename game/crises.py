"""Crises jouables issues des pressions extérieures.

Une pression Anarch ou Chasseurs devient ici une situation concrète liée à un
Domaine. Les crises sont event-sourcées : elles restent persistantes sans nouvelle
table, et les ordres existants n'ont besoin que de nouveaux types d'action.
"""

from __future__ import annotations

from dataclasses import dataclass

from .character_rules import attribute_value, has_expertise
from .config import DEFAULT_RULES, GameRules
from .factions import effective_relation_to_primogen
from .models import (
    ActionType,
    CharacterAttribute,
    ClanFactionSide,
    GameAction,
    GameEvent,
    GameState,
    OrderStance,
)
from .social_politics import add_grievance


ANARCHS = "anarchs"
HUNTERS = "hunters"
CRISIS_STATE_PREFIX = "crisis_state"
CRISIS_RESPONSE_PREFIX = "crisis_response"
CRISIS_INTEL_PREFIX = "crisis_intel"

CRISIS_ACTION_TYPES = frozenset(
    {
        ActionType.CRISIS_INVESTIGATE,
        ActionType.CRISIS_INFILTRATE,
        ActionType.CRISIS_NEGOTIATE,
        ActionType.CRISIS_CONTAIN,
        ActionType.CRISIS_EXPLOIT,
    }
)

CRISIS_ACTION_LABELS = {
    ActionType.CRISIS_INVESTIGATE: "Enquêter sur une crise",
    ActionType.CRISIS_INFILTRATE: "Infiltrer une crise",
    ActionType.CRISIS_NEGOTIATE: "Négocier une crise",
    ActionType.CRISIS_CONTAIN: "Étouffer / contenir une crise",
    ActionType.CRISIS_EXPLOIT: "Exploiter politiquement une crise",
}


@dataclass(frozen=True)
class Crisis:
    id: str
    faction: str
    domain_id: str
    stage: int
    created_night: int
    next_escalation_night: int
    status: str = "active"


@dataclass(frozen=True)
class CrisisResponse:
    crisis_id: str
    action_type: ActionType
    outcome: str
    progress: int
    intel_gain: int
    actor_id: str


def _state_category(crisis: Crisis) -> str:
    return "|".join(
        (
            CRISIS_STATE_PREFIX,
            crisis.id,
            crisis.faction,
            crisis.domain_id,
            str(crisis.stage),
            str(crisis.created_night),
            str(crisis.next_escalation_night),
            crisis.status,
        )
    )


def _parse_crisis_event(event: GameEvent) -> Crisis | None:
    parts = event.category.split("|")
    if len(parts) != 8 or parts[0] != CRISIS_STATE_PREFIX:
        return None
    try:
        return Crisis(
            id=parts[1],
            faction=parts[2],
            domain_id=parts[3],
            stage=int(parts[4]),
            created_night=int(parts[5]),
            next_escalation_night=int(parts[6]),
            status=parts[7],
        )
    except ValueError:
        return None


def all_crises(state: GameState) -> dict[str, Crisis]:
    crises: dict[str, Crisis] = {}
    for event in state.events:
        parsed = _parse_crisis_event(event)
        if parsed is not None:
            crises[parsed.id] = parsed
    return crises


def active_crises(state: GameState) -> list[Crisis]:
    return sorted(
        (crisis for crisis in all_crises(state).values() if crisis.status == "active"),
        key=lambda crisis: (-crisis.stage, crisis.next_escalation_night, crisis.id),
    )


def active_crisis_for_domain(state: GameState, domain_id: str) -> Crisis | None:
    matches = [crisis for crisis in active_crises(state) if crisis.domain_id == domain_id]
    return matches[0] if matches else None


def has_active_crisis_for_faction(state: GameState, faction: str) -> bool:
    return any(crisis.faction == faction for crisis in active_crises(state))


def crisis_title(state: GameState, crisis: Crisis) -> str:
    domain = state.domains.get(crisis.domain_id)
    domain_name = domain.name if domain else crisis.domain_id
    if crisis.faction == HUNTERS:
        return f"Surveillance des chasseurs — {domain_name}"
    return f"Agitation anarch — {domain_name}"


def crisis_stage_label(stage: int) -> str:
    return {1: "I — Signes", 2: "II — Implantation", 3: "III — Menace imminente"}.get(
        stage, f"{stage}"
    )


def crisis_public_description(crisis: Crisis) -> str:
    if crisis.faction == HUNTERS:
        return {
            1: "Des mortels recoupent des anomalies locales et observent le secteur.",
            2: "Une enquête structurée vise désormais des lieux et des relais précis.",
            3: "Une opération contre les réseaux vampiriques paraît imminente.",
        }[crisis.stage]
    return {
        1: "Des relais anarchs testent le terrain et diffusent leur discours.",
        2: "Une cellule locale recrute et consolide ses appuis dans le secteur.",
        3: "La contestation est prête à se transformer en offensive politique et territoriale.",
    }[crisis.stage]


def current_crisis_intel(state: GameState, crisis_id: str, clan_id: str) -> int:
    level = 0
    prefix = f"{CRISIS_INTEL_PREFIX}|{crisis_id}|{clan_id}|"
    for event in state.events:
        if not event.category.startswith(prefix):
            continue
        try:
            level = max(level, int(event.category[len(prefix) :]))
        except ValueError:
            continue
    return min(2, level)


def crisis_clues(crisis: Crisis, intel_level: int) -> list[str]:
    clues: list[str] = []
    if intel_level >= 1:
        if crisis.faction == HUNTERS:
            clues.append("La surveillance est organisée : ce n'est plus une présence fortuite.")
        else:
            clues.append("Le recrutement vise des vampires ou relais marginalisés du secteur.")
    if intel_level >= 2:
        if crisis.faction == HUNTERS:
            clues.append("Les enquêteurs cherchent un témoin ou une trace administrative exploitable.")
        else:
            clues.append(
                "La cellule cherche surtout accès, autonomie et droits de chasse plutôt qu'un affrontement immédiat."
            )
    return clues


def open_crisis(
    state: GameState,
    faction: str,
    domain_id: str,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    if faction not in {ANARCHS, HUNTERS}:
        raise ValueError("Unknown crisis faction")
    if domain_id not in state.domains:
        raise ValueError("Unknown crisis domain")
    if active_crisis_for_domain(state, domain_id) is not None:
        raise ValueError("A Domain cannot host two active crises in the MVP")
    crisis = Crisis(
        id=f"crisis_{faction}_{domain_id}_{state.night}",
        faction=faction,
        domain_id=domain_id,
        stage=1,
        created_night=state.night,
        next_escalation_night=state.night + rules.crisis_stage_duration_nights,
    )
    return GameEvent(
        night=state.night,
        category=_state_category(crisis),
        message=(
            f"Nouvelle crise : {crisis_title(state, crisis)}. Stade {crisis_stage_label(1)} ; "
            f"escalade prévue à la nuit {crisis.next_escalation_night} si la situation n'est pas maîtrisée."
        ),
    )


def _best_support(character, *, backgrounds=(), disciplines=()) -> int:
    ratings = [character.backgrounds.get(name, 0) for name in backgrounds]
    ratings.extend(character.disciplines.get(name, 0) for name in disciplines)
    return max(ratings, default=0)


def _expertise_bonus(character, names: tuple[str, ...]) -> int:
    return 1 if any(has_expertise(character, name) for name in names) else 0


def _score_for_response(
    state: GameState,
    crisis: Crisis,
    action: GameAction,
    rules: GameRules,
) -> tuple[int, int]:
    actor = state.characters[
        action.actor_character_id or state.clan_states[action.clan_id].clan.primogen_id
    ]
    intel = current_crisis_intel(state, crisis.id, action.clan_id)

    if action.action_type == ActionType.CRISIS_INVESTIGATE:
        score = (
            attribute_value(actor, CharacterAttribute.MENTAL)
            + _expertise_bonus(actor, ("Investigation", "Technologie", "Rue", "Occultisme"))
            + _best_support(actor, backgrounds=("Contacts", "Ressources"), disciplines=("auspex",))
        )
        modifier = 0
    elif action.action_type == ActionType.CRISIS_INFILTRATE:
        score = (
            attribute_value(actor, CharacterAttribute.MENTAL)
            + _expertise_bonus(actor, ("Subterfuge", "Rue", "Investigation", "Technologie"))
            + _best_support(actor, backgrounds=("Contacts", "Alliés"), disciplines=("auspex", "celerite"))
        )
        modifier = -1 if crisis.faction == ANARCHS else 1
    elif action.action_type == ActionType.CRISIS_NEGOTIATE:
        score = (
            attribute_value(actor, CharacterAttribute.SOCIAL)
            + _expertise_bonus(actor, ("Diplomatie", "Politique", "Subterfuge", "Rue"))
            + _best_support(
                actor,
                backgrounds=("Contacts", "Influence politique", "Influence syndicale", "Alliés"),
                disciplines=("presence", "domination"),
            )
        )
        modifier = -1 if crisis.faction == ANARCHS else 2
    elif action.action_type == ActionType.CRISIS_CONTAIN:
        score = (
            attribute_value(actor, CharacterAttribute.MENTAL)
            + _expertise_bonus(actor, ("Investigation", "Technologie", "Finance", "Médecine"))
            + _best_support(
                actor,
                backgrounds=("Contacts", "Ressources", "Serviteurs", "Alliés"),
                disciplines=("domination", "auspex"),
            )
        )
        modifier = -1 if crisis.faction == HUNTERS else 1
    elif action.action_type == ActionType.CRISIS_EXPLOIT:
        score = (
            attribute_value(actor, CharacterAttribute.SOCIAL)
            + _expertise_bonus(actor, ("Subterfuge", "Politique", "Intimidation", "Rue"))
            + _best_support(
                actor,
                backgrounds=("Contacts", "Influence politique", "Influence syndicale"),
                disciplines=("presence", "domination"),
            )
        )
        modifier = 1
    else:
        raise ValueError("Not a crisis-response action")

    difficulty = max(2, rules.crisis_base_difficulty + crisis.stage - 1 + modifier)
    return score + intel, difficulty


def _response_category(
    crisis: Crisis,
    action: GameAction,
    outcome: str,
    progress: int,
    intel_gain: int,
    actor_id: str,
) -> str:
    return "|".join(
        (
            CRISIS_RESPONSE_PREFIX,
            crisis.id,
            action.action_type.value,
            outcome,
            str(progress),
            str(intel_gain),
            actor_id,
        )
    )


def _parse_response_event(event: GameEvent) -> CrisisResponse | None:
    parts = event.category.split("|")
    if len(parts) != 7 or parts[0] != CRISIS_RESPONSE_PREFIX:
        return None
    try:
        return CrisisResponse(
            crisis_id=parts[1],
            action_type=ActionType(parts[2]),
            outcome=parts[3],
            progress=int(parts[4]),
            intel_gain=int(parts[5]),
            actor_id=parts[6],
        )
    except (ValueError, KeyError):
        return None


def crisis_member_accepts(state: GameState, action: GameAction) -> bool:
    """Les opposants peuvent servir la ville/clan sans servir aveuglément le Primogène."""

    if action.actor_character_id is None:
        return True
    actor = state.characters[action.actor_character_id]
    clan_state = state.clan_states[action.clan_id]
    if actor.id == clan_state.clan.primogen_id:
        return True
    if clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN) != ClanFactionSide.OPPOSITION:
        return True
    crisis = active_crisis_for_domain(state, action.target_domain_id or "")
    if crisis is None:
        return False
    domain = state.domains[crisis.domain_id]
    holder = state.characters.get(domain.holder_id or "")
    if domain.holder_id == actor.id or (holder and holder.clan_id == actor.clan_id):
        return True
    if action.action_type in {ActionType.CRISIS_INVESTIGATE, ActionType.CRISIS_INFILTRATE}:
        return True
    if action.action_type == ActionType.CRISIS_NEGOTIATE and actor.order_stance == OrderStance.REFORMIST:
        return True
    if action.action_type == ActionType.CRISIS_EXPLOIT and holder and holder.clan_id != actor.clan_id:
        return True
    return effective_relation_to_primogen(state, actor.id) >= 1


def crisis_refusal_event(
    state: GameState,
    action: GameAction,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    actor = state.characters[action.actor_character_id]
    actor.personal_influence += rules.influence_action_min_gain
    return GameEvent(
        night=state.night,
        category="opposition",
        message=(
            f"{actor.name} refuse d'engager ses réseaux dans cette crise et travaille pour son propre camp : "
            f"influence +{rules.influence_action_min_gain:.0f}."
        ),
        audience_clan_ids=(action.clan_id,),
    )


def crisis_response_event(
    state: GameState,
    action: GameAction,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    if action.action_type not in CRISIS_ACTION_TYPES:
        raise ValueError("Not a crisis-response action")
    crisis = active_crisis_for_domain(state, action.target_domain_id or "")
    if crisis is None:
        raise ValueError("This action requires an active crisis on the selected Domain")
    actor_id = action.actor_character_id or state.clan_states[action.clan_id].clan.primogen_id
    actor = state.characters[actor_id]
    domain = state.domains[crisis.domain_id]
    score, difficulty = _score_for_response(state, crisis, action, rules)

    if score >= difficulty + 2:
        outcome = "strong"
    elif score >= difficulty:
        outcome = "success"
    elif score <= difficulty - 2:
        outcome = "setback"
    else:
        outcome = "failure"

    intel_gain = 0
    progress = 0
    if action.action_type == ActionType.CRISIS_INVESTIGATE:
        intel_gain = 2 if outcome == "strong" else (1 if outcome == "success" else 0)
    elif action.action_type != ActionType.CRISIS_EXPLOIT:
        progress = 2 if outcome == "strong" else (1 if outcome == "success" else 0)

    audience = (action.clan_id,)
    if action.action_type == ActionType.CRISIS_EXPLOIT:
        holder = state.characters.get(domain.holder_id or "")
        if holder is None or holder.clan_id == action.clan_id:
            raise ValueError("Exploiting a crisis requires a foreign Domain holder")
        if outcome in {"success", "strong"}:
            gain = rules.crisis_exploit_influence_gain * (2 if outcome == "strong" else 1)
            loss = rules.crisis_exploit_target_influence_loss * (2 if outcome == "strong" else 1)
            actor.personal_influence += gain
            holder.personal_influence = max(0.0, holder.personal_influence - loss)
            message = (
                f"{actor.name} transforme la crise de {domain.name} en arme politique : influence +{gain:.0f}, "
                f"tandis que {holder.name} perd {loss:.0f} influence. La menace elle-même n'est pas réduite."
            )
        elif outcome == "setback":
            add_grievance(
                state,
                owner_id=holder.id,
                target_id=actor.id,
                reason=f"Manipulation découverte autour de la crise de {domain.name}",
                severity=1,
            )
            audience = tuple(sorted({action.clan_id, holder.clan_id}))
            message = (
                f"La tentative de {actor.name} d'exploiter la crise de {domain.name} est découverte par "
                f"{holder.name}, qui en garde un grief."
            )
        else:
            message = f"{actor.name} tente d'exploiter la crise de {domain.name}, sans levier politique exploitable."
    elif action.action_type == ActionType.CRISIS_INVESTIGATE:
        if intel_gain:
            message = (
                f"{actor.name} enquête sur {crisis_title(state, crisis)} : renseignements +{intel_gain} "
                f"(score {score} / difficulté {difficulty})."
            )
        else:
            message = (
                f"{actor.name} enquête sur {crisis_title(state, crisis)}, sans obtenir de piste fiable "
                f"(score {score} / difficulté {difficulty})."
            )
    else:
        verb = {
            ActionType.CRISIS_INFILTRATE: "infiltre les réseaux liés à",
            ActionType.CRISIS_NEGOTIATE: "négocie autour de",
            ActionType.CRISIS_CONTAIN: "mobilise ses relais pour contenir",
        }[action.action_type]
        if progress:
            message = (
                f"{actor.name} {verb} {crisis_title(state, crisis)} : progrès {progress} "
                f"(score {score} / difficulté {difficulty})."
            )
        else:
            message = (
                f"{actor.name} {verb} {crisis_title(state, crisis)}, sans réduire la menace "
                f"(score {score} / difficulté {difficulty})."
            )

    if outcome == "setback" and action.action_type == ActionType.CRISIS_CONTAIN:
        if crisis.faction == HUNTERS:
            state.masquerade_integrity = max(0.0, state.masquerade_integrity - 1.0)
            message += " La couverture maladroite expose davantage la Mascarade (-1)."
        else:
            state.camarilla_stability = max(0.0, state.camarilla_stability - 1.0)
            message += " La répression maladroite nourrit la contestation (stabilité -1)."

    return GameEvent(
        night=state.night,
        category=_response_category(crisis, action, outcome, progress, intel_gain, actor_id),
        message=message,
        audience_clan_ids=audience,
    )


def _intel_event(state: GameState, crisis: Crisis, clan_id: str, gain: int) -> GameEvent | None:
    before = current_crisis_intel(state, crisis.id, clan_id)
    after = min(2, before + gain)
    if after <= before:
        return None
    clues = crisis_clues(crisis, after)
    clue = clues[-1] if clues else "Aucun détail supplémentaire."
    return GameEvent(
        night=state.night,
        category=f"{CRISIS_INTEL_PREFIX}|{crisis.id}|{clan_id}|{after}",
        message=f"Renseignement sur {crisis_title(state, crisis)} : {clue}",
        audience_clan_ids=(clan_id,),
    )


def _required_progress(crisis: Crisis, rules: GameRules) -> int:
    return (
        rules.crisis_stage1_required_progress
        if crisis.stage == 1
        else rules.crisis_late_stage_required_progress
    )


def _transition_event(
    state: GameState,
    crisis: Crisis,
    *,
    stage: int,
    status: str = "active",
    rules: GameRules,
    message: str,
) -> GameEvent:
    updated = Crisis(
        id=crisis.id,
        faction=crisis.faction,
        domain_id=crisis.domain_id,
        stage=stage,
        created_night=crisis.created_night,
        next_escalation_night=state.night + rules.crisis_stage_duration_nights,
        status=status,
    )
    return GameEvent(night=state.night, category=_state_category(updated), message=message)


def _major_failure(state: GameState, crisis: Crisis, rules: GameRules) -> GameEvent:
    domain = state.domains[crisis.domain_id]
    if crisis.faction == HUNTERS:
        domain.pressure += rules.hunter_crisis_failure_domain_pressure_gain
        state.masquerade_integrity = max(
            0.0,
            state.masquerade_integrity - rules.hunter_crisis_failure_masquerade_loss,
        )
        domain.servage = max(0, domain.servage - rules.hunter_crisis_failure_servage_loss)
        detail = (
            f"Raid mortel sur {domain.name} : pression +{rules.hunter_crisis_failure_domain_pressure_gain}, "
            f"Mascarade -{rules.hunter_crisis_failure_masquerade_loss:.0f} et Servage {domain.servage}/3."
        )
    else:
        domain.pressure += rules.anarch_crisis_failure_domain_pressure_gain
        state.camarilla_stability = max(
            0.0,
            state.camarilla_stability - rules.anarch_crisis_failure_stability_loss,
        )
        holder = state.characters.get(domain.holder_id or "")
        if holder is not None:
            holder.personal_influence = max(
                0.0,
                holder.personal_influence - rules.anarch_crisis_failure_holder_influence_loss,
            )
            if holder.clan_id and holder.clan_id in state.clan_states:
                opposition_id = state.clan_states[holder.clan_id].opposition_leader_id
                if opposition_id and opposition_id != holder.id:
                    state.characters[opposition_id].personal_influence += (
                        rules.anarch_crisis_failure_opposition_influence_gain
                    )
        detail = (
            f"Offensive anarch sur {domain.name} : pression +{rules.anarch_crisis_failure_domain_pressure_gain}, "
            f"stabilité -{rules.anarch_crisis_failure_stability_loss:.0f}; l'autorité locale est affaiblie."
        )
    return _transition_event(
        state,
        crisis,
        stage=crisis.stage,
        status="failed",
        rules=rules,
        message=f"Crise non maîtrisée — {detail}",
    )


def resolve_crisis_cycle(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Applique les réponses de la nuit puis fait éventuellement évoluer les crises."""

    events: list[GameEvent] = []
    responses = [
        parsed
        for event in state.events
        if event.night == state.night
        for parsed in [_parse_response_event(event)]
        if parsed is not None
    ]

    for crisis in active_crises(state):
        crisis_responses = [response for response in responses if response.crisis_id == crisis.id]
        intel_by_clan: dict[str, int] = {}
        for response in crisis_responses:
            if response.intel_gain <= 0 or response.actor_id not in state.characters:
                continue
            clan_id = state.characters[response.actor_id].clan_id
            if clan_id:
                intel_by_clan[clan_id] = intel_by_clan.get(clan_id, 0) + response.intel_gain
        for clan_id, gain in intel_by_clan.items():
            event = _intel_event(state, crisis, clan_id, gain)
            if event:
                events.append(event)

        progress = sum(response.progress for response in crisis_responses)
        required = _required_progress(crisis, rules)
        if progress >= required:
            if crisis.stage == 1:
                events.append(
                    _transition_event(
                        state,
                        crisis,
                        stage=1,
                        status="resolved",
                        rules=rules,
                        message=(
                            f"{crisis_title(state, crisis)} est maîtrisée avant son implantation durable. "
                            f"La coordination de la nuit produit {progress}/{required} progrès."
                        ),
                    )
                )
            else:
                new_stage = crisis.stage - 1
                events.append(
                    _transition_event(
                        state,
                        crisis,
                        stage=new_stage,
                        rules=rules,
                        message=(
                            f"{crisis_title(state, crisis)} recule au stade {crisis_stage_label(new_stage)} "
                            f"({progress}/{required} progrès)."
                        ),
                    )
                )
            continue

        if state.night < crisis.next_escalation_night:
            continue

        domain = state.domains[crisis.domain_id]
        if crisis.stage < 3:
            new_stage = crisis.stage + 1
            domain.pressure += rules.crisis_escalation_domain_pressure_gain
            extra = f" Pression de {domain.name} +{rules.crisis_escalation_domain_pressure_gain}."
            if new_stage == 3 and crisis.faction == HUNTERS:
                state.masquerade_integrity = max(
                    0.0,
                    state.masquerade_integrity - rules.hunter_crisis_stage3_masquerade_loss,
                )
                extra += f" Mascarade -{rules.hunter_crisis_stage3_masquerade_loss:.0f}."
            elif new_stage == 3 and crisis.faction == ANARCHS:
                state.camarilla_stability = max(
                    0.0,
                    state.camarilla_stability - rules.anarch_crisis_stage3_stability_loss,
                )
                extra += f" Stabilité -{rules.anarch_crisis_stage3_stability_loss:.0f}."
            events.append(
                _transition_event(
                    state,
                    crisis,
                    stage=new_stage,
                    rules=rules,
                    message=(
                        f"{crisis_title(state, crisis)} s'aggrave au stade {crisis_stage_label(new_stage)} : "
                        f"réponse insuffisante ({progress}/{required}).{extra}"
                    ),
                )
            )
        else:
            events.append(_major_failure(state, crisis, rules))

    return events
