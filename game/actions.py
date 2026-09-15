from __future__ import annotations

from .character_rules import attribute_value, has_expertise
from .config import DEFAULT_RULES, GameRules
from .coteries import (
    coterie_conflict_penalty,
    coterie_cooperation_bonus,
    hostile_coterie_target_id,
    initialize_coteries,
    shared_coterie,
    should_refuse_coterie_conflict,
    strain_coterie_bond,
)
from .domains import (
    has_hunting_access,
    intrusion_detected,
    open_domain_dispute,
    register_braconnage,
    steward_domain,
)
from .factions import (
    effective_relation_to_primogen,
    ideology_relation_modifier,
    set_faction_side,
)
from .models import (
    ActionType,
    Character,
    CharacterAttribute,
    ClanFactionSide,
    GameAction,
    GameEvent,
    GameState,
)
from .social_politics import add_grievance, call_boon


ACTION_LABELS = {
    ActionType.BUILD_INFLUENCE: "Développer son influence",
    ActionType.DIPLOMACY: "Diplomatie",
    ActionType.CONSOLIDATE_RELATION: "Consolider une relation",
    ActionType.RECRUIT: "Recruter dans sa faction",
    ActionType.UNDERMINE: "Fragiliser un membre",
    ActionType.POACH: "Débaucher vers l'opposition",
    ActionType.INVESTIGATE: "Enquêter",
    ActionType.CALL_BOON: "Réclamer une faveur",
    ActionType.DOMAIN_STEWARD: "Administrer son Domaine",
    ActionType.DOMAIN_INTRUSION: "Infiltrer un Domaine",
    ActionType.BRACONNAGE: "Braconner sur un Domaine",
    ActionType.CONSOLIDATE: "Consolider le courant du Primogène (legacy)",
    ActionType.RALLY_OPPOSITION: "Rallier un courant rival (legacy)",
}


def _clamp_int(value: int, minimum: int = 0, maximum: int = 2) -> int:
    return max(minimum, min(maximum, value))


def _best_support(
    character: Character,
    backgrounds: tuple[str, ...] = (),
    disciplines: tuple[str, ...] = (),
) -> int:
    ratings = [character.backgrounds.get(name, 0) for name in backgrounds]
    ratings.extend(character.disciplines.get(name, 0) for name in disciplines)
    return max(ratings, default=0)


def _best_expertise_bonus(character: Character, names: tuple[str, ...]) -> int:
    return 1 if any(has_expertise(character, name) for name in names) else 0


def _political_score(
    character: Character,
    attribute: CharacterAttribute,
    *,
    expertises: tuple[str, ...] = (),
    backgrounds: tuple[str, ...] = (),
    disciplines: tuple[str, ...] = (),
) -> int:
    return (
        attribute_value(character, attribute)
        + _best_expertise_bonus(character, expertises)
        + _best_support(character, backgrounds, disciplines)
    )


def _resolve_actor(state: GameState, action: GameAction) -> Character:
    clan_state = state.clan_states[action.clan_id]
    actor_id = action.actor_character_id or clan_state.clan.primogen_id
    actor = state.characters.get(actor_id)
    if actor is None or actor.clan_id != action.clan_id:
        raise ValueError("Action actor must be a member of the acting clan")
    if actor.id == state.prince_id:
        raise ValueError("The Prince cannot be used as a clan action actor")
    return actor


def _resolve_target_character(state: GameState, action: GameAction) -> Character:
    target = state.characters.get(action.target_character_id or "")
    if target is None:
        raise ValueError("This action requires a target character")
    return target


def _resolve_target_domain(state: GameState, action: GameAction):
    domain = state.domains.get(action.target_domain_id or "")
    if domain is None:
        raise ValueError("This action requires a target domain")
    return domain


def _diplomacy_target(state: GameState, action: GameAction) -> Character:
    if action.target_character_id:
        target = _resolve_target_character(state, action)
        if not target.clan_id or target.clan_id == action.clan_id:
            raise ValueError("Diplomacy requires a vampire from another clan")
        return target
    target_clan_id = action.target_clan_id
    if not target_clan_id or target_clan_id == action.clan_id:
        raise ValueError("Diplomacy requires another target clan")
    if target_clan_id not in state.clan_states:
        raise ValueError(f"Unknown target clan: {target_clan_id}")
    return state.characters[state.clan_states[target_clan_id].clan.primogen_id]


def _investigation_target(state: GameState, action: GameAction) -> Character:
    if action.target_character_id:
        target = _resolve_target_character(state, action)
        if target.clan_id == action.clan_id:
            raise ValueError("Investigation is intended for another clan")
        return target

    target_clan_id = action.target_clan_id
    if not target_clan_id or target_clan_id == action.clan_id:
        raise ValueError("Investigation requires another target clan")
    if target_clan_id not in state.clan_states:
        raise ValueError(f"Unknown target clan: {target_clan_id}")

    target_primogen_id = state.clan_states[target_clan_id].clan.primogen_id
    candidates = [
        character
        for character in state.characters.values()
        if character.clan_id == target_clan_id
        and character.id != target_primogen_id
        and character.id != state.prince_id
    ]
    if not candidates:
        raise ValueError("No hidden clan member is available to investigate")
    intel = state.clan_states[action.clan_id].known_character_intel
    return min(
        candidates,
        key=lambda character: (
            intel.get(character.id, 0),
            -character.personal_influence,
            character.id,
        ),
    )


def _opposition_accepts(state: GameState, action: GameAction, actor: Character) -> bool:
    clan_state = state.clan_states[action.clan_id]
    side = clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN)
    if side != ClanFactionSide.OPPOSITION:
        return True
    if action.action_type in {
        ActionType.BUILD_INFLUENCE,
        ActionType.CALL_BOON,
        ActionType.DOMAIN_STEWARD,
    }:
        return True

    relation = effective_relation_to_primogen(state, actor.id)
    if relation >= 2:
        return True
    if relation <= 0:
        return False

    if action.action_type in {ActionType.INVESTIGATE, ActionType.DOMAIN_INTRUSION}:
        return True
    if action.action_type == ActionType.DIPLOMACY:
        target = _diplomacy_target(state, action)
        return (
            ideology_relation_modifier(actor, target)
            + coterie_cooperation_bonus(state, actor.id, target.id)
            >= 0
        )
    return False


def _opposition_refusal_event(
    state: GameState,
    action: GameAction,
    actor: Character,
    rules: GameRules,
) -> GameEvent:
    actor.personal_influence += rules.influence_action_min_gain
    return GameEvent(
        night=state.night,
        category="opposition",
        message=(
            f"{actor.name} refuse la mission demandée par le Primogène et consacre sa nuit "
            f"à ses propres réseaux : influence +{rules.influence_action_min_gain:.0f}."
        ),
        audience_clan_ids=(action.clan_id,),
    )


def _coterie_refusal_event(state: GameState, action: GameAction, actor: Character) -> GameEvent:
    target_id = hostile_coterie_target_id(state, action)
    target = state.characters.get(target_id or "")
    coterie = shared_coterie(actor.id, target.id) if target else None
    return GameEvent(
        night=state.night,
        category="coterie",
        message=(
            f"{actor.name} refuse d'agir contre {target.name if target else 'un compagnon'} : "
            f"sa loyauté envers {coterie.name if coterie else 'sa coterie'} l'emporte sur l'ordre du Primogène."
        ),
        audience_clan_ids=(action.clan_id,),
    )


def _detected_domain_audience(state: GameState, acting_clan_id: str, holder_id: str | None):
    clans = {acting_clan_id}
    holder = state.characters.get(holder_id or "")
    if holder and holder.clan_id:
        clans.add(holder.clan_id)
    return tuple(sorted(clans))


def apply_action(
    state: GameState,
    action: GameAction,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    if action.clan_id not in state.clan_states:
        raise ValueError(f"Unknown clan: {action.clan_id}")

    initialize_coteries(state)
    clan_state = state.clan_states[action.clan_id]
    clan = clan_state.clan
    actor = _resolve_actor(state, action)
    audience_clan_ids: tuple[str, ...] | None = (action.clan_id,)

    if action.actor_character_id is not None and should_refuse_coterie_conflict(
        state, action, actor.id
    ):
        return _coterie_refusal_event(state, action, actor)

    if action.actor_character_id is not None and not _opposition_accepts(state, action, actor):
        return _opposition_refusal_event(state, action, actor, rules)

    if action.action_type == ActionType.BUILD_INFLUENCE:
        score = _political_score(
            actor,
            CharacterAttribute.MENTAL,
            expertises=("Politique", "Finance", "Rue", "Art"),
            backgrounds=("Influence politique", "Ressources", "Contacts", "Alliés"),
        )
        gain = max(rules.influence_action_min_gain, float(1 + score // 2))
        actor.personal_influence += gain
        message = f"{actor.name} développe ses réseaux : influence +{gain:.0f}."

    elif action.action_type == ActionType.DIPLOMACY:
        target = _diplomacy_target(state, action)
        affinity = ideology_relation_modifier(actor, target)
        coterie_bonus = coterie_cooperation_bonus(state, actor.id, target.id)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Diplomatie", "Politique", "Subterfuge"),
            backgrounds=("Contacts", "Influence politique", "Milieu artistique", "Influence syndicale"),
            disciplines=("presence", "domination"),
        ) + affinity + coterie_bonus
        gain = max(rules.diplomacy_minimum_gain, rules.diplomacy_gain + score)
        target_clan_id = target.clan_id
        if not target_clan_id:
            raise ValueError("Diplomacy target must belong to a clan")
        clan_state.relations[target_clan_id] = clan_state.relations.get(target_clan_id, 0.0) + gain
        state.clan_states[target_clan_id].relations[action.clan_id] = (
            state.clan_states[target_clan_id].relations.get(action.clan_id, 0.0) + gain
        )
        if score >= rules.relation_action_threshold:
            actor.relations[target.id] = _clamp_int(actor.relations.get(target.id, 0) + 1)
            target.relations[actor.id] = _clamp_int(target.relations.get(actor.id, 0) + 1)
        coterie_note = f", lien de coterie +{coterie_bonus}" if coterie_bonus else ""
        message = (
            f"{actor.name} négocie avec {target.name} : relation {clan.name}/"
            f"{state.clan_states[target_clan_id].clan.name} +{gain:.0f} "
            f"(affinité politique {affinity:+d}{coterie_note})."
        )

    elif action.action_type == ActionType.CONSOLIDATE_RELATION:
        target = _resolve_target_character(state, action)
        if target.clan_id != action.clan_id or target.id == clan.primogen_id or target.id == actor.id:
            raise ValueError("Consolidation must target another non-Primogen member of the acting clan")
        affinity = ideology_relation_modifier(actor, target)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Diplomatie", "Politique"),
            backgrounds=("Contacts", "Influence politique", "Alliés"),
            disciplines=("presence",),
        ) + affinity
        difficulty = rules.relation_action_threshold + (
            1
            if clan_state.faction_memberships.get(target.id) == ClanFactionSide.OPPOSITION
            else 0
        )
        if score >= difficulty:
            before = target.relation_to_primogen
            target.relation_to_primogen = _clamp_int(before + 1)
            message = (
                f"{actor.name} rapproche {target.name} du Primogène : relation personnelle "
                f"{before} → {target.relation_to_primogen}."
            )
        else:
            message = f"{actor.name} tente de rapprocher {target.name} du Primogène, sans résultat."

    elif action.action_type == ActionType.RECRUIT:
        target = _resolve_target_character(state, action)
        if target.clan_id != action.clan_id or target.id == clan.primogen_id:
            raise ValueError("Recruitment must target another member of the acting clan")
        actor_side = clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN)
        target_side = clan_state.faction_memberships.get(target.id, ClanFactionSide.PRIMOGEN)
        if actor_side == target_side:
            raise ValueError("Recruitment requires a member of the other faction")
        target_relation = effective_relation_to_primogen(state, target.id)
        affinity = ideology_relation_modifier(actor, target)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Politique", "Diplomatie", "Subterfuge"),
            backgrounds=("Contacts", "Influence politique", "Alliés"),
            disciplines=("presence", "domination"),
        ) + affinity
        difficulty = (
            rules.recruit_base_difficulty - target_relation
            if actor_side == ClanFactionSide.PRIMOGEN
            else rules.recruit_base_difficulty - 1 + target_relation
        )
        if score >= difficulty:
            set_faction_side(state, target.id, actor_side)
            message = f"{actor.name} rallie {target.name} à la faction {actor_side.value}."
        else:
            message = f"{actor.name} tente de rallier {target.name}, qui reste dans sa faction."

    elif action.action_type == ActionType.UNDERMINE:
        target = _resolve_target_character(state, action)
        if not target.clan_id or target.id == state.clan_states[target.clan_id].clan.primogen_id:
            raise ValueError("Undermining must target a non-Primogen clan member")
        affinity = ideology_relation_modifier(actor, target)
        conflict_penalty = coterie_conflict_penalty(state, actor.id, target.id)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Subterfuge", "Politique", "Intimidation"),
            backgrounds=("Contacts", "Influence politique", "Rue"),
            disciplines=("presence", "domination"),
        ) + affinity - conflict_penalty
        difficulty = rules.undermine_base_difficulty + max(
            0, effective_relation_to_primogen(state, target.id)
        )
        if score >= difficulty and target.relation_to_primogen > 0:
            before = target.relation_to_primogen
            target.relation_to_primogen -= 1
            coterie_name = strain_coterie_bond(state, actor.id, target.id)
            coterie_note = f" Leur lien au sein de {coterie_name} se dégrade." if coterie_name else ""
            message = (
                f"{actor.name} fragilise la confiance de {target.name} envers son Primogène : "
                f"relation {before} → {target.relation_to_primogen}.{coterie_note}"
            )
        else:
            message = f"{actor.name} tente de fragiliser {target.name}, sans effet politique durable."

    elif action.action_type == ActionType.POACH:
        target = _resolve_target_character(state, action)
        if not target.clan_id or target.id == state.clan_states[target.clan_id].clan.primogen_id:
            raise ValueError("Poaching must target a non-Primogen clan member")
        target_state = state.clan_states[target.clan_id]
        if target_state.faction_memberships.get(target.id) == ClanFactionSide.OPPOSITION:
            raise ValueError("Target already belongs to the opposition")
        if effective_relation_to_primogen(state, target.id) > 0:
            raise ValueError("Target is not politically fragile enough to be poached")
        affinity = ideology_relation_modifier(actor, target)
        conflict_penalty = coterie_conflict_penalty(state, actor.id, target.id)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Subterfuge", "Politique", "Diplomatie"),
            backgrounds=("Contacts", "Influence politique", "Alliés"),
            disciplines=("presence", "domination"),
        ) + affinity - conflict_penalty
        if score >= rules.poach_base_difficulty:
            set_faction_side(state, target.id, ClanFactionSide.OPPOSITION)
            actor.relations[target.id] = _clamp_int(actor.relations.get(target.id, 0) + 1)
            coterie_name = strain_coterie_bond(state, actor.id, target.id)
            coterie_note = f" La manœuvre crée une tension dans {coterie_name}." if coterie_name else ""
            message = (
                f"{actor.name} convainc {target.name} de rejoindre l'opposition de son clan."
                f"{coterie_note}"
            )
        else:
            message = f"{actor.name} tente de débaucher {target.name}, sans provoquer de défection."

    elif action.action_type == ActionType.INVESTIGATE:
        target = _investigation_target(state, action)
        coterie_bonus = coterie_cooperation_bonus(state, actor.id, target.id)
        score = _political_score(
            actor,
            CharacterAttribute.MENTAL,
            expertises=("Investigation", "Subterfuge", "Technologie"),
            backgrounds=("Contacts", "Rue"),
            disciplines=("auspex",),
        ) + coterie_bonus
        difficulty = rules.investigation_base_difficulty + target.mental
        if has_expertise(target, "Subterfuge"):
            difficulty += 1
        before = clan_state.known_character_intel.get(target.id, 0)
        if score >= difficulty:
            clan_state.known_character_intel[target.id] = min(rules.max_intel_level, before + 1)
            coterie_note = " grâce à ses accès de coterie" if coterie_bonus else ""
            message = (
                f"{actor.name} obtient de nouveaux renseignements sur {target.name}{coterie_note} : "
                f"niveau {before} → {clan_state.known_character_intel[target.id]}."
            )
        else:
            message = f"{actor.name} enquête sur le réseau de {target.clan_id}, sans information exploitable."

    elif action.action_type == ActionType.CALL_BOON:
        target = _resolve_target_character(state, action)
        due = sorted(
            (
                boon
                for boon in state.boons.values()
                if boon.creditor_id == actor.id
                and boon.debtor_id == target.id
                and boon.status.value == "due"
            ),
            key=lambda boon: (boon.created_night, boon.id),
        )
        if not due:
            raise ValueError("No due boon exists between this creditor and debtor")
        boon = call_boon(state, due[0].id, actor.id)
        message = (
            f"{actor.name} réclame à {target.name} une faveur {boon.level.value} "
            f"issue de : {boon.origin}."
        )

    elif action.action_type == ActionType.DOMAIN_STEWARD:
        domain = _resolve_target_domain(state, action)
        if domain.holder_id != actor.id:
            raise ValueError("A vampire may only administer their own Domain")
        score = _political_score(
            actor,
            CharacterAttribute.MENTAL,
            expertises=("Politique", "Finance", "Rue", "Investigation"),
            backgrounds=("Contacts", "Ressources", "Alliés"),
        ) + domain.servage
        reduction = steward_domain(state, domain.id, actor.id, max(1, score // 3))
        if reduction:
            message = (
                f"{actor.name} mobilise son Servage sur {domain.name} et réduit la pression "
                f"territoriale de {reduction}."
            )
        else:
            message = (
                f"{actor.name} consolide son Servage sur {domain.name}; aucune pression immédiate "
                "ne nécessite d'intervention."
            )

    elif action.action_type == ActionType.DOMAIN_INTRUSION:
        domain = _resolve_target_domain(state, action)
        if domain.holder_id == actor.id:
            raise ValueError("A holder cannot infiltrate their own Domain")
        holder = state.characters.get(domain.holder_id or "")
        conflict_penalty = (
            coterie_conflict_penalty(state, actor.id, holder.id) if holder else 0
        )
        score = _political_score(
            actor,
            CharacterAttribute.MENTAL,
            expertises=("Investigation", "Subterfuge", "Technologie", "Rue"),
            backgrounds=("Contacts", "Rue"),
            disciplines=("auspex",),
        ) - conflict_penalty
        detected = intrusion_detected(domain, score)
        if not detected:
            before = clan_state.known_domain_intel.get(domain.id, 0)
            clan_state.known_domain_intel[domain.id] = min(rules.max_intel_level, before + 1)
            message = (
                f"{actor.name} infiltre discrètement {domain.name} et améliore le renseignement "
                f"territorial : niveau {before} → {clan_state.known_domain_intel[domain.id]}."
            )
        else:
            if holder:
                open_domain_dispute(
                    state,
                    domain_id=domain.id,
                    claimant_id=holder.id,
                    respondent_id=actor.id,
                    reason=f"Intrusion détectée sur {domain.name}",
                    severity=1,
                )
                add_grievance(
                    state,
                    owner_id=holder.id,
                    target_id=actor.id,
                    reason=f"Intrusion détectée sur le Domaine {domain.name}",
                    severity=1,
                )
            audience_clan_ids = _detected_domain_audience(state, action.clan_id, domain.holder_id)
            coterie_name = strain_coterie_bond(state, actor.id, holder.id) if holder else None
            coterie_note = f" La confiance au sein de {coterie_name} est atteinte." if coterie_name else ""
            message = (
                f"L'intrusion de {actor.name} sur {domain.name} est repérée par son Rempart. "
                f"Un litige territorial est ouvert.{coterie_note}"
            )

    elif action.action_type == ActionType.BRACONNAGE:
        domain = _resolve_target_domain(state, action)
        if has_hunting_access(state, actor.id, domain.id):
            raise ValueError("A vampire with hunting access is not braconning")
        holder = state.characters.get(domain.holder_id or "")
        conflict_penalty = (
            coterie_conflict_penalty(state, actor.id, holder.id) if holder else 0
        )
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Rue", "Subterfuge", "Intimidation"),
            backgrounds=("Contacts", "Rue"),
            disciplines=("presence", "celerite"),
        ) - conflict_penalty
        success = score >= 2
        detected = intrusion_detected(domain, score)
        if success:
            pressure_gain = register_braconnage(state, domain.id)
            message = (
                f"{actor.name} exploite clandestinement le Viandis de {domain.name} : "
                f"pression +{pressure_gain}."
            )
        else:
            message = f"{actor.name} tente de braconner sur {domain.name}, sans accès exploitable."
        if detected:
            if holder:
                open_domain_dispute(
                    state,
                    domain_id=domain.id,
                    claimant_id=holder.id,
                    respondent_id=actor.id,
                    reason=f"Braconnage détecté sur {domain.name}",
                    severity=2,
                )
                add_grievance(
                    state,
                    owner_id=holder.id,
                    target_id=actor.id,
                    reason=f"Braconnage sur le Domaine {domain.name}",
                    severity=1,
                )
            audience_clan_ids = _detected_domain_audience(state, action.clan_id, domain.holder_id)
            coterie_name = strain_coterie_bond(state, actor.id, holder.id) if holder else None
            message += " Le Rempart du Domaine révèle l'intrusion et ouvre un litige territorial."
            if coterie_name:
                message += f" La trahison fragilise {coterie_name}."
        else:
            message += " Le Rempart ne révèle pas l'auteur."

    elif action.action_type == ActionType.CONSOLIDATE:
        actor.personal_influence += rules.consolidate_influence_gain
        message = (
            f"{actor.name} termine une action de consolidation préparée avant la V0.8 : "
            f"influence +{rules.consolidate_influence_gain:.0f}."
        )

    elif action.action_type == ActionType.RALLY_OPPOSITION:
        leader_id = clan_state.opposition_leader_id
        if not leader_id:
            raise ValueError("Clan has no opposition leader")
        target = state.characters[leader_id]
        before = target.relation_to_primogen
        target.relation_to_primogen = _clamp_int(before + 1)
        message = (
            f"{actor.name} termine une action de ralliement préparée avant la V0.8 : "
            f"relation de {target.name} au Primogène {before} → {target.relation_to_primogen}."
        )

    else:
        raise ValueError(f"Unsupported action type: {action.action_type}")

    return GameEvent(
        night=state.night,
        category="action",
        message=message,
        audience_clan_ids=audience_clan_ids,
    )
