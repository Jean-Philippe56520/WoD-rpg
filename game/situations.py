from __future__ import annotations

from dataclasses import dataclass, replace

from .chronicle import NightOutcome, PersonalAction, PlayerCharacter
from .chronicle_simulation import (
    SimulationState,
    active_hunting_access,
    grant_boon,
)
from .clans import situation_bonus
from .dice import DiceResult, difficulty_band, difficulty_hint, roll_pool
from .era import CamarillaStage, era_for_year
from .relationship_memory import (
    record_relationship_memory,
    relationship_difficulty_adjustment,
    relationship_tags,
)
from .sire_relations import sire_bond
from .vampire_profile import VampireProfile


RELATIONAL_EFFECTS = frozenset(
    {
        "sire_service",
        "sire_negotiate",
        "sire_refuse",
        "seek_release",
        "political_voice",
        "protect_touchstone",
        "cautious_distance",
    }
)


@dataclass(frozen=True)
class SituationChoice:
    id: str
    label: str
    description: str
    attribute: str
    skill: str
    difficulty: int
    legacy_action: PersonalAction
    effect: str


@dataclass(frozen=True)
class Situation:
    id: str
    title: str
    body: str
    source_actor_id: str | None
    tags: tuple[str, ...]
    choices: tuple[SituationChoice, ...]


@dataclass(frozen=True)
class SituationResolution:
    situation: Situation
    choice: SituationChoice
    dice: DiceResult
    outcome: NightOutcome
    simulation: SimulationState
    profile: VampireProfile


@dataclass(frozen=True)
class ActionRiskPreview:
    """Player-facing estimate of a check without exposing its numeric target."""

    attribute: str
    skill: str
    band: str
    hint: str


def effective_difficulty(
    character: PlayerCharacter,
    simulation: SimulationState,
    situation: Situation,
    choice: SituationChoice,
) -> tuple[int, int]:
    """Return exact hidden difficulty and contextual adjustment.

    Character capability changes the dice pool elsewhere. Circumstances change
    the target here. Keeping those two axes separate makes political preparation,
    relationships and leverage useful without pretending the vampire's raw skill
    score has changed.
    """

    relation_adjustment = (
        relationship_difficulty_adjustment(simulation, situation.source_actor_id, character)
        if choice.effect in RELATIONAL_EFFECTS
        else 0
    )
    return max(1, choice.difficulty + relation_adjustment), relation_adjustment


def action_risk_preview(
    character: PlayerCharacter,
    simulation: SimulationState,
    situation: Situation,
    choice: SituationChoice,
) -> ActionRiskPreview:
    """Describe risk in broad bands; never return the exact target to the UI."""

    difficulty, _ = effective_difficulty(character, simulation, situation, choice)
    return ActionRiskPreview(
        attribute=choice.attribute,
        skill=choice.skill,
        band=difficulty_band(difficulty),
        hint=difficulty_hint(difficulty),
    )


def _sire_situation(character: PlayerCharacter) -> Situation:
    return Situation(
        id="sire_accounting",
        title=f"{character.sire_name} vous fait demander",
        body=(
            "Votre sire rappelle qu'il répond encore de vos actes devant les autres Caïnites. Un messager a besoin "
            "d'être escorté avant l'aube, et votre sire considère ce service comme une évidence plutôt que comme une faveur."
        ),
        source_actor_id=character.sire_id,
        tags=("authority", "oath", "sire"),
        choices=(
            SituationChoice(
                "obey",
                "Accepter sans marchander",
                "Vous remplissez le service attendu et consolidez la confiance de votre sire.",
                "resolve",
                "etiquette",
                2,
                PersonalAction.VISIT_SIRE,
                "sire_service",
            ),
            SituationChoice(
                "negotiate",
                "Accepter, mais demander que le service soit reconnu",
                "Vous tentez de transformer l'obéissance attendue en dette explicite.",
                "manipulation",
                "politics",
                3,
                PersonalAction.VISIT_SIRE,
                "sire_negotiate",
            ),
            SituationChoice(
                "refuse",
                "Refuser et défendre votre autonomie",
                "Vous risquez de rappeler brutalement que votre indépendance n'est pas encore reconnue.",
                "composure",
                "persuasion",
                3,
                PersonalAction.VISIT_SIRE,
                "sire_refuse",
            ),
        ),
    )


def _release_situation(character: PlayerCharacter) -> Situation:
    return Situation(
        id="sire_release",
        title="Faire reconnaître votre autonomie",
        body=(
            f"Vous avez désormais assez de poids pour que {character.sire_name} ne puisse plus traiter votre autonomie "
            "comme une simple insolence. Demander votre libération signifie toutefois perdre le droit implicite de vous "
            "abriter et de chasser sous sa responsabilité."
        ),
        source_actor_id=character.sire_id,
        tags=("authority", "oath", "court", "politics"),
        choices=(
            SituationChoice(
                "formal_release",
                "Demander une reconnaissance devant témoins",
                "Vous faites de votre autonomie une question de réputation et d'usage public.",
                "charisma",
                "politics",
                3,
                PersonalAction.ELYSIUM,
                "seek_release",
            ),
            SituationChoice(
                "private_release",
                "Négocier d'abord seul à seul avec votre sire",
                "Vous cherchez un accord sans transformer immédiatement la discussion en affrontement public.",
                "manipulation",
                "persuasion",
                3,
                PersonalAction.VISIT_SIRE,
                "seek_release",
            ),
        ),
    )


def _hunting_situation(
    character: PlayerCharacter,
    profile: VampireProfile,
    simulation: SimulationState,
    year: int,
) -> Situation:
    rights = active_hunting_access(simulation, character.character_id, year)
    preference_text = ""
    if profile.feeding_preference:
        preference_text = f" Votre Sang vous contraint ou vous attire vers : {profile.feeding_preference}."
    if rights:
        right = rights[0]
        domain = simulation.domains[right.domain_id]
        body = (
            f"Vous êtes autorisé à chasser sur {domain.name}. La zone offre un Viandis de {domain.viandis}/3, "
            f"mais sa pression actuelle est de {domain.pressure}. Votre accès dépend encore de : {right.source}."
            + preference_text
        )
    else:
        domain = sorted(simulation.domains.values(), key=lambda item: (item.pressure, -item.viandis, item.id))[0]
        body = (
            f"Vous ne disposez d'aucun droit de chasse reconnu. {domain.name} semble accessible, mais vous y nourrir "
            "sans permission peut créer une dette ou un conflit de Domaine."
            + preference_text
        )
    return Situation(
        id=f"hunt_{domain.id}",
        title="La Faim réclame une décision",
        body=body,
        source_actor_id=domain.holder_id,
        tags=("domain", "hunt", "survival"),
        choices=(
            SituationChoice(
                "careful_hunt",
                "Chasser avec prudence",
                "Vous privilégiez la discrétion et acceptez d'y consacrer la majeure partie de la nuit.",
                "wits",
                "survival",
                2 + domain.pressure,
                PersonalAction.HUNT,
                "hunt",
            ),
            SituationChoice(
                "social_hunt",
                "Trouver une proie par le contact social",
                "Vous cherchez une proie correspondant à votre besoin sans la traquer ouvertement.",
                "charisma",
                "insight",
                2 + domain.masquerade_risk,
                PersonalAction.HUNT,
                "hunt_social",
            ),
            SituationChoice(
                "go_hungry",
                "Renoncer pour cette nuit",
                "Vous évitez un risque territorial immédiat, mais la Bête n'oublie pas.",
                "resolve",
                "awareness",
                2,
                PersonalAction.HUNT,
                "abstain",
            ),
        ),
    )


def _political_situation(character: PlayerCharacter, year: int, simulation: SimulationState) -> Situation:
    era = era_for_year(year)
    if era.camarilla_stage in {CamarillaStage.PROJECT, CamarillaStage.COALITION}:
        body = (
            "Un courrier scellé circule entre plusieurs lignages. Il évoque une alliance plus large contre les révoltés "
            "et les chasseurs, mais personne ne peut encore prétendre parler au nom de tous les Caïnites. Votre nom est "
            "trop mineur pour être consulté officiellement — ce qui n'empêche pas d'écouter."
        )
    else:
        body = (
            "Une querelle entre détenteurs de Domaines risque de devenir publique. Le Prince veut éviter qu'elle ne se "
            "règle dans la rue, mais chacun cherche déjà des témoins et des dettes."
        )
    return Situation(
        id="political_current",
        title="Des mots qui peuvent devenir des lois",
        body=body,
        source_actor_id=simulation.offices.get("prince"),
        tags=("court", "politics", "debate", "diplomacy"),
        choices=(
            SituationChoice(
                "listen",
                "Écouter sans prendre position",
                "Vous cherchez d'abord à savoir qui soutient réellement quoi.",
                "wits",
                "politics",
                2,
                PersonalAction.INVESTIGATE,
                "political_intel",
            ),
            SituationChoice(
                "support_order",
                "Défendre la nécessité d'un ordre commun",
                "Vous acceptez d'être associé, même modestement, au camp de ceux qui veulent coordonner les anciens.",
                "charisma",
                "persuasion",
                3,
                PersonalAction.ELYSIUM,
                "political_voice",
            ),
            SituationChoice(
                "defend_autonomy",
                "Défendre les libertés locales et les jeunes Caïnites",
                "Vous contestez qu'une nouvelle coalition puisse simplement remplacer les abus des anciens par d'autres.",
                "charisma",
                "politics",
                3,
                PersonalAction.ELYSIUM,
                "political_voice",
            ),
        ),
    )


def _clan_situation(character: PlayerCharacter) -> Situation:
    if character.clan_id == "brujah":
        return Situation(
            id="brujah_revolt",
            title="Un jeune Brujah demande votre témoignage",
            body=(
                "Il affirme qu'un ancien a fait battre un descendant pour avoir refusé un serment supplémentaire. "
                "Certains parlent de révolte, d'autres d'une affaire de lignage qui ne vous concerne pas."
            ),
            source_actor_id="sire_brujah_ysabeau",
            tags=("revolt", "debate", "protect_young"),
            choices=(
                SituationChoice("hear", "Entendre les témoins", "Chercher les faits avant le camp.", "wits", "insight", 2, PersonalAction.INVESTIGATE, "political_intel"),
                SituationChoice("protect", "Protéger publiquement le jeune", "Vous engagez votre réputation contre l'abus allégué.", "charisma", "persuasion", 3, PersonalAction.BUILD_RELATION, "political_voice"),
                SituationChoice("distance", "Refuser d'être entraîné", "Vous préservez votre position au prix d'une occasion d'influence.", "composure", "etiquette", 2, PersonalAction.BUILD_RELATION, "cautious_distance"),
            ),
        )
    if character.clan_id == "toreador":
        return Situation(
            id="toreador_patronage",
            title="Un mortel remarquable attire de mauvais regards",
            body=(
                "Un enlumineur protégé par votre lignée attire à la fois l'admiration de la Cour et l'appétit d'un autre "
                "prédateur. Le perdre serait une blessure esthétique, sociale et peut-être humaine."
            ),
            source_actor_id="sire_toreador_isabeau",
            tags=("court", "patronage", "art"),
            choices=(
                SituationChoice("protect_artist", "Organiser sa protection", "Mobiliser des relais mortels sans révéler la vraie menace.", "manipulation", "etiquette", 2, PersonalAction.BUILD_RELATION, "protect_touchstone"),
                SituationChoice("negotiate_predator", "Négocier avec le prédateur", "Transformer une rivalité en dette ou en limite reconnue.", "charisma", "persuasion", 3, PersonalAction.BUILD_RELATION, "political_voice"),
                SituationChoice("observe", "Observer qui s'y intéresse", "Utiliser le mortel comme révélateur des ambitions de la Cour.", "wits", "insight", 2, PersonalAction.INVESTIGATE, "political_intel"),
            ),
        )
    return Situation(
        id="ventrue_oath",
        title="Deux serments se contredisent",
        body=(
            "Un marchand protégé par votre lignée doit passage à deux puissants qui revendiquent chacun la priorité. "
            "Décider lequel des engagements compte le plus revient à choisir quel ordre vous considérez légitime."
        ),
        source_actor_id="sire_ventrue_heloise",
        tags=("authority", "oath", "administration"),
        choices=(
            SituationChoice("arbitrate", "Proposer un arbitrage", "Faire reconnaître une hiérarchie des obligations sans humilier personne.", "manipulation", "politics", 3, PersonalAction.BUILD_RELATION, "political_voice"),
            SituationChoice("old_oath", "Faire primer le serment le plus ancien", "Vous défendez la continuité des usages.", "resolve", "etiquette", 2, PersonalAction.ELYSIUM, "political_voice"),
            SituationChoice("useful_oath", "Faire primer l'engagement le plus utile", "Vous privilégiez l'efficacité politique sur l'ancienneté.", "intelligence", "politics", 2, PersonalAction.ELYSIUM, "political_intel"),
        ),
    )


def generate_situations(
    character: PlayerCharacter,
    profile: VampireProfile,
    simulation: SimulationState,
    *,
    year: int,
) -> tuple[Situation, ...]:
    hunting = _hunting_situation(character, profile, simulation, year)
    political = _political_situation(character, year, simulation)
    clan = _clan_situation(character)
    bond = sire_bond(character, profile, era_for_year(year))

    if profile.released_from_sire:
        if character.hunger >= 4:
            return (hunting, clan, political)
        return (political, clan, hunting)

    sire = _sire_situation(character)
    release = _release_situation(character) if bond.can_seek_release else None
    if character.hunger >= 4:
        return (hunting, release or sire, clan)
    if release is not None:
        return (release, political if character.local_night % 2 == 0 else clan, hunting)
    return (sire, political if character.local_night % 2 == 1 else clan, hunting)


def _change_domain_risk(simulation: SimulationState, domain_id: str, delta: int) -> SimulationState:
    domain = simulation.domains.get(domain_id)
    if domain is None:
        return simulation
    domains = dict(simulation.domains)
    domains[domain_id] = replace(
        domain,
        masquerade_risk=max(0, min(3, domain.masquerade_risk + delta)),
        pressure=max(0, domain.pressure + (1 if delta > 0 else 0)),
    )
    return replace(simulation, domains=domains)


def _remove_sire_hunting_access(simulation: SimulationState, character_id: str) -> SimulationState:
    right_id = f"right_sire_{character_id}"
    right = simulation.hunting_rights.get(right_id)
    if right is None or not right.active:
        return simulation
    rights = dict(simulation.hunting_rights)
    rights[right_id] = replace(right, active=False, source="Accès expiré après émancipation du sire")
    return replace(simulation, hunting_rights=rights)


def _relationship_effect(
    simulation: SimulationState,
    character: PlayerCharacter,
    situation: Situation,
    choice: SituationChoice,
    dice: DiceResult,
) -> tuple[SimulationState, tuple[str, ...]]:
    actor_id = situation.source_actor_id
    if not actor_id or actor_id not in simulation.npcs:
        return simulation, ()

    # Listening or abstaining does not make the source actor remember the PJ.
    # Hunting becomes relational only if the action produces a political trace.
    if choice.effect in {"political_intel", "abstain"}:
        return simulation, ()
    if choice.effect in {"hunt", "hunt_social"} and not (dice.messy_critical or dice.bestial_failure):
        return simulation, ()

    disposition_delta = 0
    trust_delta = 0
    respect_delta = 0
    fear_delta = 0
    grievance = False
    valence = 0

    if choice.effect == "sire_service":
        disposition_delta = 1 if dice.success else -1
        trust_delta = 1 if dice.success else -1
        valence = 1 if dice.success else -1
    elif choice.effect == "sire_negotiate":
        respect_delta = 1 if dice.success else -1
        trust_delta = 1 if dice.success else -1
        grievance = not dice.success
        valence = 1 if dice.success else -1
    elif choice.effect == "sire_refuse":
        respect_delta = 1 if dice.success else -1
        trust_delta = -1
        grievance = not dice.success
        valence = 1 if dice.success else -1
    elif choice.effect == "seek_release":
        respect_delta = 2 if dice.success else -1
        trust_delta = 1 if dice.success else -1
        grievance = not dice.success
        valence = 2 if dice.success else -1
    elif choice.effect in {"political_voice", "protect_touchstone"}:
        respect_delta = 1 if dice.success else -1
        disposition_delta = 1 if dice.critical else 0
        grievance = dice.bestial_failure
        valence = 1 if dice.success else -1
    elif choice.effect == "cautious_distance":
        disposition_delta = 0 if dice.success else -1
        valence = 0 if dice.success else -1
    elif choice.effect in {"hunt", "hunt_social"}:
        disposition_delta = -1
        fear_delta = 1
        grievance = True
        valence = -1

    if dice.messy_critical:
        fear_delta += 1
    if dice.bestial_failure:
        disposition_delta -= 1
        fear_delta += 1
        grievance = True
        valence = -1

    updated = record_relationship_memory(
        simulation,
        character,
        actor_id,
        year=character.chronicle_year,
        disposition_delta=disposition_delta,
        trust_delta=trust_delta,
        respect_delta=respect_delta,
        fear_delta=fear_delta,
        awareness_delta=1,
        grievance=grievance,
    )
    return updated, relationship_tags(actor_id, choice.effect, valence)


def resolve_situation(
    character: PlayerCharacter,
    profile: VampireProfile,
    simulation: SimulationState,
    situation: Situation,
    choice_id: str,
    *,
    nights_per_segment: int,
    free_intent: str = "",
) -> SituationResolution:
    try:
        choice = next(item for item in situation.choices if item.id == choice_id)
    except StopIteration as exc:
        raise ValueError("Unknown situation choice") from exc

    bonus = situation_bonus(character.clan_id, situation.tags)
    pool = profile.pool(choice.attribute, choice.skill, bonus=bonus)
    difficulty, relation_adjustment = effective_difficulty(character, simulation, situation, choice)
    seed = (
        f"{character.character_id}:{character.chapter}:{character.segment}:"
        f"{character.local_night}:{situation.id}:{choice.id}"
    )
    dice = roll_pool(pool=pool, hunger=character.hunger, difficulty=difficulty, seed=seed)

    hunger = character.hunger
    reputation = character.reputation
    influence = character.personal_influence
    sire_relation = character.sire_relation
    goal_progress = character.goal_progress
    next_simulation = simulation
    next_profile = profile
    summary = f"{choice.label} — {dice.label}."
    details: list[str] = []
    if relation_adjustment < 0:
        details.append("La confiance acquise rend cet échange plus facile.")
    elif relation_adjustment > 0:
        details.append("Votre passif avec cet interlocuteur rend l'échange plus difficile.")

    if choice.effect in {"hunt", "hunt_social"}:
        if dice.success:
            hunger = max(0, hunger - (2 if dice.critical else 1))
            details.append("Vous apaisez la Faim sans devoir à votre sire une nouvelle intervention.")
        else:
            hunger = min(5, hunger + 1)
            details.append("La proie vous échappe et la Bête devient plus pressante.")
        if dice.messy_critical or dice.bestial_failure:
            domain_id = situation.id.removeprefix("hunt_")
            next_simulation = _change_domain_risk(next_simulation, domain_id, 1)
            details.append("Votre manière d'agir laisse cependant une trace dangereuse sur le Domaine.")
    elif choice.effect == "abstain":
        hunger = min(5, hunger + 1)
        details.append(
            "Vous tenez jusqu'à l'aube, mais votre Faim augmente."
            if dice.success
            else "Vous tenez à peine : la prochaine provocation de la Bête sera plus difficile à contenir."
        )
    elif choice.effect == "sire_service":
        if dice.success:
            sire_relation = min(3, sire_relation + 1)
            goal_progress += 1
            details.append("Votre sire considère que vous avez rempli votre part de responsabilité familiale.")
        else:
            sire_relation = max(0, sire_relation - 1)
            details.append("Le service est mal exécuté et votre sire doute de pouvoir encore répondre de vous sans risque.")
    elif choice.effect == "sire_negotiate":
        if dice.success:
            sire_relation = min(3, sire_relation + 1)
            next_simulation = grant_boon(
                next_simulation,
                creditor_id=character.character_id,
                debtor_id=character.sire_id,
                level="minor",
                origin="Service rendu au sire contre reconnaissance explicite",
            )
            details.append("Le service est reconnu : votre sire vous doit désormais une faveur mineure.")
        else:
            sire_relation = max(0, sire_relation - 1)
            details.append("Votre sire juge votre marchandage prématuré et le service reste attendu.")
    elif choice.effect == "sire_refuse":
        if dice.success:
            reputation = min(3, reputation + 1)
            goal_progress += 1
            details.append("Votre refus est entendu comme une revendication d'autonomie, pas comme une simple insolence.")
        else:
            sire_relation = max(0, sire_relation - 1)
            reputation = max(-3, reputation - 1)
            details.append("Votre refus vous isole sans vous libérer de la responsabilité de votre sire.")
    elif choice.effect == "seek_release":
        bond = sire_bond(character, profile, era_for_year(character.chronicle_year))
        if not bond.can_seek_release:
            raise ValueError("Character cannot seek release from sire yet")
        if dice.success:
            next_profile = replace(profile, released_from_sire=True)
            next_simulation = _remove_sire_hunting_access(next_simulation, character.character_id)
            reputation = min(3, reputation + 1)
            goal_progress += 2
            details.append(
                "Votre autonomie est reconnue. Votre sire ne répond plus automatiquement de vous, et son Domaine "
                "ne constitue plus un droit de chasse implicite."
            )
        else:
            sire_relation = max(0, sire_relation - 1)
            details.append("Votre demande est refusée. Vous avez néanmoins rendu votre volonté d'indépendance publique.")
    elif choice.effect == "political_intel":
        if dice.success:
            goal_progress += 2 if dice.critical else 1
            details.append("Vous apprenez qui agit, qui hésite et qui prétend seulement avoir choisi son camp.")
        else:
            details.append("Les informations obtenues restent contradictoires ou volontairement déformées.")
    elif choice.effect in {"political_voice", "protect_touchstone"}:
        if dice.success:
            influence += 1.0 if dice.critical else 0.5
            reputation = min(3, reputation + (1 if dice.critical else 0))
            details.append("Votre position devient connue d'au moins quelques acteurs qui pourront s'en souvenir.")
        else:
            details.append("Vous vous exposez sans obtenir immédiatement le résultat recherché.")
    elif choice.effect == "cautious_distance":
        if dice.success:
            details.append("Vous évitez l'engagement sans créer d'ennemi immédiat.")
        else:
            reputation = max(-3, reputation - 1)
            details.append("Votre prudence est interprétée comme de la lâcheté ou du mépris.")

    if dice.messy_critical:
        details.append("La Bête participe à votre réussite : le résultat est réel, mais votre méthode inquiète ou choque quelqu'un.")
    elif dice.bestial_failure:
        hunger = min(5, hunger + 1)
        details.append("L'échec nourrit la Bête et crée une impulsion dont vous devrez assumer la suite.")

    next_simulation, memory_tags = _relationship_effect(
        next_simulation,
        character,
        situation,
        choice,
        dice,
    )

    text = " ".join(free_intent.strip().split())
    if text:
        details.append(f"Intention déclarée : « {text[:240]} ».")

    ready = character.local_night >= nights_per_segment
    next_night = character.local_night if ready else character.local_night + 1
    updated = replace(
        character,
        local_night=next_night,
        hunger=hunger,
        reputation=reputation,
        personal_influence=influence,
        sire_relation=sire_relation,
        goal_progress=goal_progress,
        ready_for_convergence=ready,
    )
    outcome = NightOutcome(
        action=choice.legacy_action,
        roll=dice.successes,
        summary=summary,
        detail=" ".join(details),
        updated_character=updated,
        tags=tuple(sorted(set(situation.tags + (dice.label,) + memory_tags))),
    )
    return SituationResolution(
        situation=situation,
        choice=choice,
        dice=dice,
        outcome=outcome,
        simulation=next_simulation,
        profile=next_profile,
    )
