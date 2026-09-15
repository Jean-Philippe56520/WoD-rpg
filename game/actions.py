from __future__ import annotations

from .character_rules import attribute_value, has_expertise
from .config import DEFAULT_RULES, GameRules
from .coteries import (
    effective_relation_to_primogen,
    ideology_relation_modifier,
    initialize_coteries,
    set_coterie_side,
)
from .models import (
    ActionType,
    Character,
    CharacterAttribute,
    CoterieSide,
    GameAction,
    GameEvent,
    GameState,
)


ACTION_LABELS = {
    ActionType.BUILD_INFLUENCE: "Développer son influence",
    ActionType.DIPLOMACY: "Diplomatie",
    ActionType.CONSOLIDATE_RELATION: "Consolider une relation",
    ActionType.RECRUIT: "Recruter dans sa coterie",
    ActionType.UNDERMINE: "Fragiliser un membre",
    ActionType.POACH: "Débaucher vers l'opposition",
    ActionType.INVESTIGATE: "Enquêter",
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


def _opposition_accepts(state: GameState, action: GameAction, actor: Character) -> bool:
    clan_state = state.clan_states[action.clan_id]
    side = clan_state.coterie_memberships.get(actor.id, CoterieSide.PRIMOGEN)
    if side != CoterieSide.OPPOSITION:
        return True
    if action.action_type == ActionType.BUILD_INFLUENCE:
        return True

    relation = effective_relation_to_primogen(state, actor.id)
    if relation >= 2:
        return True
    if relation <= 0:
        return False

    # À relation moyenne, l'opposant coopère surtout lorsque la mission correspond
    # à ses affinités ou sert clairement l'information du clan.
    if action.action_type == ActionType.INVESTIGATE:
        return True
    if action.action_type == ActionType.DIPLOMACY:
        target = _diplomacy_target(state, action)
        return ideology_relation_modifier(actor, target) >= 0
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
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Diplomatie", "Politique", "Subterfuge"),
            backgrounds=("Contacts", "Influence politique", "Milieu artistique", "Influence syndicale"),
            disciplines=("presence", "domination"),
        ) + affinity
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
        message = (
            f"{actor.name} négocie avec {target.name} : relation {clan.name}/"
            f"{state.clan_states[target_clan_id].clan.name} +{gain:.0f} "
            f"(affinité idéologique {affinity:+d})."
        )

    elif action.action_type == ActionType.CONSOLIDATE_RELATION:
        target = _resolve_target_character(state, action)
        if target.clan_id != action.clan_id or target.id == clan.primogen_id:
            raise ValueError("Consolidation must target another member of the acting clan")
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
            if clan_state.coterie_memberships.get(target.id) == CoterieSide.OPPOSITION
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
        actor_side = clan_state.coterie_memberships.get(actor.id, CoterieSide.PRIMOGEN)
        target_side = clan_state.coterie_memberships.get(target.id, CoterieSide.PRIMOGEN)
        if actor_side == target_side:
            raise ValueError("Recruitment requires a member of the other coterie")
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
            if actor_side == CoterieSide.PRIMOGEN
            else rules.recruit_base_difficulty - 1 + target_relation
        )
        if score >= difficulty:
            set_coterie_side(state, target.id, actor_side)
            message = f"{actor.name} rallie {target.name} à la coterie {actor_side.value}."
        else:
            message = f"{actor.name} tente de rallier {target.name}, qui reste dans sa coterie."

    elif action.action_type == ActionType.UNDERMINE:
        target = _resolve_target_character(state, action)
        if not target.clan_id or target.id == state.clan_states[target.clan_id].clan.primogen_id:
            raise ValueError("Undermining must target a non-Primogen clan member")
        affinity = ideology_relation_modifier(actor, target)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Subterfuge", "Politique", "Intimidation"),
            backgrounds=("Contacts", "Influence politique", "Rue"),
            disciplines=("presence", "domination"),
        ) + affinity
        difficulty = rules.undermine_base_difficulty + max(
            0, effective_relation_to_primogen(state, target.id)
        )
        if score >= difficulty and target.relation_to_primogen > 0:
            before = target.relation_to_primogen
            target.relation_to_primogen -= 1
            message = (
                f"{actor.name} fragilise la confiance de {target.name} envers son Primogène : "
                f"relation {before} → {target.relation_to_primogen}."
            )
        else:
            message = f"{actor.name} tente de fragiliser {target.name}, sans effet politique durable."

    elif action.action_type == ActionType.POACH:
        target = _resolve_target_character(state, action)
        if not target.clan_id or target.id == state.clan_states[target.clan_id].clan.primogen_id:
            raise ValueError("Poaching must target a non-Primogen clan member")
        target_state = state.clan_states[target.clan_id]
        if target_state.coterie_memberships.get(target.id) == CoterieSide.OPPOSITION:
            raise ValueError("Target already belongs to the opposition")
        if effective_relation_to_primogen(state, target.id) > 0:
            raise ValueError("Target is not politically fragile enough to be poached")
        affinity = ideology_relation_modifier(actor, target)
        score = _political_score(
            actor,
            CharacterAttribute.SOCIAL,
            expertises=("Subterfuge", "Politique", "Diplomatie"),
            backgrounds=("Contacts", "Influence politique", "Alliés"),
            disciplines=("presence", "domination"),
        ) + affinity
        if score >= rules.poach_base_difficulty:
            set_coterie_side(state, target.id, CoterieSide.OPPOSITION)
            actor.relations[target.id] = _clamp_int(actor.relations.get(target.id, 0) + 1)
            message = (
                f"{actor.name} convainc {target.name} de rejoindre l'opposition de son clan."
            )
        else:
            message = f"{actor.name} tente de débaucher {target.name}, sans provoquer de défection."

    elif action.action_type == ActionType.INVESTIGATE:
        target = _resolve_target_character(state, action)
        if target.clan_id == action.clan_id:
            raise ValueError("Investigation is intended for another clan")
        score = _political_score(
            actor,
            CharacterAttribute.MENTAL,
            expertises=("Investigation", "Subterfuge", "Technologie"),
            backgrounds=("Contacts", "Rue"),
            disciplines=("auspex",),
        )
        difficulty = rules.investigation_base_difficulty + target.mental
        if has_expertise(target, "Subterfuge"):
            difficulty += 1
        before = clan_state.known_character_intel.get(target.id, 0)
        if score >= difficulty:
            clan_state.known_character_intel[target.id] = min(
                rules.max_intel_level, before + 1
            )
            message = (
                f"{actor.name} obtient de nouveaux renseignements sur {target.name} : "
                f"niveau {before} → {clan_state.known_character_intel[target.id]}."
            )
        else:
            message = f"{actor.name} enquête sur {target.name}, sans information exploitable."

    elif action.action_type == ActionType.CONSOLIDATE:
        # Ancien ordre V0.7 : conservé pour qu'une nuit déjà soumise reste résoluble.
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
        audience_clan_ids=(action.clan_id,),
    )
