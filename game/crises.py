"""Crises jouables issues des pressions extérieures.

Les crises sont persistées dans l'historique d'événements. Une réponse de crise
réutilise une famille de mission existante avec un Domaine en cible :
- Enquêter -> investigation ;
- Infiltrer -> intrusion territoriale ;
- Négocier -> diplomatie ;
- Contenir -> administration ;
- Exploiter -> développement d'influence.

Le contexte de crise change la résolution de la mission sans changer le format
des ordres persistés.
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

APPROACH_INVESTIGATE = "investigate"
APPROACH_INFILTRATE = "infiltrate"
APPROACH_NEGOTIATE = "negotiate"
APPROACH_CONTAIN = "contain"
APPROACH_EXPLOIT = "exploit"

CRISIS_APPROACH_LABELS = {
    APPROACH_INVESTIGATE: "Enquêter",
    APPROACH_INFILTRATE: "Infiltrer",
    APPROACH_NEGOTIATE: "Négocier",
    APPROACH_CONTAIN: "Étouffer / contenir",
    APPROACH_EXPLOIT: "Exploiter politiquement",
}

CRISIS_APPROACH_ACTIONS = {
    APPROACH_INVESTIGATE: ActionType.INVESTIGATE,
    APPROACH_INFILTRATE: ActionType.DOMAIN_INTRUSION,
    APPROACH_NEGOTIATE: ActionType.DIPLOMACY,
    APPROACH_CONTAIN: ActionType.DOMAIN_STEWARD,
    APPROACH_EXPLOIT: ActionType.BUILD_INFLUENCE,
}
_ACTION_APPROACHES = {value: key for key, value in CRISIS_APPROACH_ACTIONS.items()}


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
    approach: str
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


def crises_from_events(events: list[GameEvent]) -> dict[str, Crisis]:
    crises: dict[str, Crisis] = {}
    for event in events:
        parsed = _parse_crisis_event(event)
        if parsed is not None:
            crises[parsed.id] = parsed
    return crises


def all_crises(state: GameState) -> dict[str, Crisis]:
    return crises_from_events(state.events)


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
        stage, str(stage)
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
        3: "La contestation est prête à devenir une offensive politique et territoriale.",
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
                "La cellule recherche surtout accès, autonomie et droits de chasse : un accord est possible."
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
            f"escalade prévue à la nuit {crisis.next_escalation_night} si elle n'est pas maîtrisée."
        ),
    )


def crisis_approach_for_action(state: GameState, action: GameAction) -> str | None:
    if not action.target_domain_id or active_crisis_for_domain(state, action.target_domain_id) is None:
        return None
    approach = _ACTION_APPROACHES.get(action.action_type)
    if approach is None:
        return None
    if action.target_character_id or action.target_clan_id:
        return None
    return approach


def crisis_action(
    clan_id: str,
    actor_id: str,
    domain_id: str,
    approach: str,
) -> GameAction:
    if approach not in CRISIS_APPROACH_ACTIONS:
        raise ValueError("Unknown crisis approach")
    return GameAction(
        clan_id=clan_id,
        action_type=CRISIS_APPROACH_ACTIONS[approach],
        actor_character_id=actor_id,
        target_domain_id=domain_id,
    )


def _best_support(character, *, backgrounds=(), disciplines=()) -> int:
    ratings = [character.backgrounds.get(name, 0) for name in backgrounds]
    ratings.extend(character.disciplines.get(name, 0) for name in disciplines)
    return max(ratings, default=0)


def _expertise_bonus(character, names: tuple[str, ...]) -> int:
    return 1 if any(has_expertise(character, name) for name in names) else 0


def response_score(
    state: GameState,
    crisis: Crisis,
    action: GameAction,
    rules: GameRules = DEFAULT_RULES,
) -> tuple[int, int]:
    approach = crisis_approach_for_action(state, action)
    if approach is None:
        raise ValueError("Not a crisis-response action")
    actor = state.characters[
        action.actor_character_id or state.clan_states[action.clan_id].clan.primogen_id
    ]
    intel = current_crisis_intel(state, crisis.id, action.clan_id)

    if approach == APPROACH_INVESTIGATE:
        score = (
            attribute_value(actor, CharacterAttribute.MENTAL)
            + _expertise_bonus(actor, ("Investigation", "Technologie", "Rue", "Occultisme"))
            + _best_support(actor, backgrounds=("Contacts", "Ressources"), disciplines=("auspex",))
        )
        modifier = 0
    elif approach == APPROACH_INFILTRATE:
        score = (
            attribute_value(actor, CharacterAttribute.MENTAL)
            + _expertise_bonus(actor, ("Subterfuge", "Rue", "Investigation", "Technologie"))
            + _best_support(actor, backgrounds=("Contacts", "Alliés"), disciplines=("auspex", "celerite"))
        )
        modifier = -1 if crisis.faction == ANARCHS else 1
    elif approach == APPROACH_NEGOTIATE:
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
    elif approach == APPROACH_CONTAIN:
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
    else:
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

    difficulty = max(2, rules.crisis_base_difficulty + crisis.stage - 1 + modifier)
    return score + intel, difficulty


def _response_category(
    crisis: Crisis,
    approach: str,
    outcome: str,
    progress: int,
    intel_gain: int,
    actor_id: str,
) -> str:
    return "|".join(
        (
            CRISIS_RESPONSE_PREFIX,
            crisis.id,
            approach,
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
    if parts[2] not in CRISIS_APPROACH_ACTIONS:
        return None
    try:
        return CrisisResponse(
            crisis_id=parts[1],
            approach=parts[2],
            outcome=parts[3],
            progress=int(parts[4]),
            intel_gain=int(parts[5]),
            actor_id=parts[6],
        )
    except ValueError:
        return None


def crisis_member_accepts(state: GameState, action: GameAction) -> bool:
    if action.actor_character_id is None:
        return True
    actor = state.characters[action.actor_character_id]
    clan_state = state.clan_states[action.clan_id]
    if actor.id == clan_state.clan.primogen_id:
        return True
    if clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN) != ClanFactionSide.OPPOSITION:
        return True

    crisis = active_crisis_for_domain(state, action.target_domain_id or "")
    approach = crisis_approach_for_action(state, action)
    if crisis is None or approach is None:
        return False
    domain = state.domains[crisis.domain_id]
    holder = state.characters.get(domain.holder_id or "")
    if domain.holder_id == actor.id or (holder and holder.clan_id == actor.clan_id):
        return True
    if approach in {APPROACH_INVESTIGATE, APPROACH_INFILTRATE}:
        return True
    if approach == APPROACH_NEGOTIATE and actor.order_stance == OrderStance.REFORMIST:
        return True
    if approach == APPROACH_EXPLOIT and holder and holder.clan_id != actor.clan_id:
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
    approach = crisis_approach_for_action(state, action)
    crisis = active_crisis_for_domain(state, action.target_domain_id or "")
    if approach is None or crisis is None:
        raise ValueError("This action requires an active crisis on the selected Domain")
    actor_id = action.actor_character_id or state.clan_states[action.clan_id].clan.primogen_id
    actor = state.characters[actor_id]
    score, difficulty = response_score(state, crisis, action, rules)

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
    if approach == APPROACH_INVESTIGATE:
        intel_gain = 2 if outcome == "strong" else (1 if outcome == "success" else 0)
    elif approach != APPROACH_EXPLOIT:
        progress = 2 if outcome == "strong" else (1 if outcome == "success" else 0)

    if approach == APPROACH_INVESTIGATE:
        result = f"renseignements +{intel_gain}" if intel_gain else "aucune piste fiable"
    elif approach == APPROACH_EXPLOIT:
        result = "levier politique obtenu" if outcome in {"success", "strong"} else "aucun levier sûr"
    else:
        result = f"progrès {progress}" if progress else "menace non réduite"

    return GameEvent(
        night=state.night,
        category=_response_category(crisis, approach, outcome, progress, intel_gain, actor_id),
        message=(
            f"{actor.name} tente « {CRISIS_APPROACH_LABELS[approach]} » sur {crisis_title(state, crisis)} : "
            f"{result} (score {score} / difficulté {difficulty})."
        ),
        audience_clan_ids=(action.clan_id,),
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
    if crisis.stage == 1:
        return rules.crisis_stage1_required_progress
    return rules.crisis_late_stage_required_progress


def _transition_event(
    state: GameState,
    crisis: Crisis,
    *,
    stage: int,
    status: str,
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
            f"raid mortel sur {domain.name} : pression +{rules.hunter_crisis_failure_domain_pressure_gain}, "
            f"Mascarade -{rules.hunter_crisis_failure_masquerade_loss:.0f}, Servage {domain.servage}/3"
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
            f"offensive anarch sur {domain.name} : pression +{rules.anarch_crisis_failure_domain_pressure_gain}, "
            f"stabilité -{rules.anarch_crisis_failure_stability_loss:.0f}; l'autorité locale recule"
        )
    return _transition_event(
        state,
        crisis,
        stage=crisis.stage,
        status="failed",
        rules=rules,
        message=f"Crise non maîtrisée — {detail}.",
    )


def _apply_response_consequences(
    state: GameState,
    crisis: Crisis,
    response: CrisisResponse,
    rules: GameRules,
) -> list[GameEvent]:
    events: list[GameEvent] = []
    domain = state.domains[crisis.domain_id]
    actor = state.characters.get(response.actor_id)
    if actor is None:
        return events

    if response.approach == APPROACH_EXPLOIT:
        holder = state.characters.get(domain.holder_id or "")
        if holder is None or holder.clan_id == actor.clan_id:
            return events
        if response.outcome in {"success", "strong"}:
            multiplier = 2 if response.outcome == "strong" else 1
            gain = rules.crisis_exploit_influence_gain * multiplier
            loss = rules.crisis_exploit_target_influence_loss * multiplier
            actor.personal_influence += gain
            holder.personal_influence = max(0.0, holder.personal_influence - loss)
            events.append(
                GameEvent(
                    night=state.night,
                    category="crisis_exploit",
                    message=(
                        f"{actor.name} transforme la crise de {domain.name} en arme politique : "
                        f"influence +{gain:.0f}; {holder.name} perd {loss:.0f} influence. La crise reste active."
                    ),
                    audience_clan_ids=(actor.clan_id,),
                )
            )
        elif response.outcome == "setback":
            add_grievance(
                state,
                owner_id=holder.id,
                target_id=actor.id,
                reason=f"Manipulation découverte autour de la crise de {domain.name}",
                severity=1,
            )
            clans = tuple(sorted({actor.clan_id, holder.clan_id}))
            events.append(
                GameEvent(
                    night=state.night,
                    category="crisis_exploit",
                    message=(
                        f"La tentative de {actor.name} d'exploiter la crise de {domain.name} est découverte par "
                        f"{holder.name}. Un grief personnel est créé."
                    ),
                    audience_clan_ids=clans,
                )
            )

    if response.approach == APPROACH_CONTAIN and response.outcome == "setback":
        if crisis.faction == HUNTERS:
            state.masquerade_integrity = max(0.0, state.masquerade_integrity - 1.0)
            message = "Une couverture maladroite expose davantage la Mascarade (-1)."
        else:
            state.camarilla_stability = max(0.0, state.camarilla_stability - 1.0)
            message = "Une répression maladroite nourrit la contestation (stabilité -1)."
        events.append(
            GameEvent(
                night=state.night,
                category="crisis_setback",
                message=message,
                audience_clan_ids=(actor.clan_id,),
            )
        )
    return events


def resolve_crisis_cycle(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Résout les réponses de la nuit puis l'escalade éventuelle des crises."""

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
        for response in crisis_responses:
            events.extend(_apply_response_consequences(state, crisis, response, rules))

        intel_by_clan: dict[str, int] = {}
        for response in crisis_responses:
            if response.intel_gain <= 0:
                continue
            actor = state.characters.get(response.actor_id)
            if actor and actor.clan_id:
                intel_by_clan[actor.clan_id] = intel_by_clan.get(actor.clan_id, 0) + response.intel_gain
        for clan_id, gain in intel_by_clan.items():
            intel_event = _intel_event(state, crisis, clan_id, gain)
            if intel_event:
                events.append(intel_event)

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
                            f"{crisis_title(state, crisis)} est maîtrisée avant implantation durable "
                            f"({progress}/{required} progrès)."
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
                        status="active",
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
                    status="active",
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
