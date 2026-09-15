from __future__ import annotations

import hashlib
from typing import Mapping, Sequence

from .chronicle import PersonalAction, PlayerCharacter
from .chronicle_simulation import SimulationState
from .narrative_state import IntelligenceState, StoryHookState, reliability_label
from .praxis import assess_praxis_pressure
from .situations import Situation, SituationChoice


def _deterministic_score(seed: str, modulus: int = 100) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:4], "big") % modulus


def _source_for_category(category: str) -> tuple[str, str]:
    if category in {"alliance_building", "political_rivalry"}:
        return "Les habitués des lieux de rencontre caïnites", "court_gossip"
    if category in {"prestation", "political_patronage", "hunting_patronage"}:
        return "Un intermédiaire qui dit avoir vu passer les messagers", "intermediary"
    if category == "hunter_pressure":
        return "Des serviteurs mortels et des rumeurs de rue", "mortal_rumor"
    if category == "historical_milestone":
        return "Des voyageurs et des nouvelles venues de l'extérieur", "travellers"
    if category == "praxis_pressure":
        return "Des conversations recoupées dans plusieurs cercles de la Cour", "court_gossip"
    return "Des voix concordantes dans la nuit parisienne", "rumor"


def intelligence_from_world_event(event: Mapping) -> IntelligenceState:
    event_id = str(event.get("id", "world_event"))
    category = str(event.get("category", "world_event"))
    source_label, source_kind = _source_for_category(category)
    reliability = 1 + _deterministic_score(f"intel:{event_id}:{category}", 3)
    # A world event is a real change in the canonical state, but what reaches the
    # player is deliberately only a public fragment. ``truth_state`` is never
    # rendered by the player UI.
    truth_state = "true" if reliability >= 3 else "partial"
    return IntelligenceState(
        id=f"intel_{event_id}",
        subject_id=str(event.get("actor_id", "paris")),
        claim=str(event.get("public_text", "Une affaire a fait bouger les équilibres de Paris.")),
        source_label=source_label,
        source_actor_id=(str(event["actor_id"]) if event.get("actor_id") else None),
        source_kind=source_kind,
        reliability=reliability,
        truth_state=truth_state,
        known_to_player=True,
        acquired_year=int(event.get("year", 1435)),
        acquired_chapter=int(event.get("chapter", 1)),
        acquired_cycle=int(event.get("segment", 1)),
        status="active",
        related_hook_id=f"hook_{event_id}",
    )


def hook_from_world_event(event: Mapping, intelligence: IntelligenceState) -> StoryHookState:
    category = str(event.get("category", "world_event"))
    title = "Un mouvement dans la nuit parisienne"
    stakes = "Comprendre ce mouvement peut éviter d'être utilisé par d'autres Caïnites."
    tags: tuple[str, ...] = ("politics", "information")
    urgency = 1

    if category == "alliance_building":
        title = "Une alliance attire l'attention"
        stakes = "Un rapprochement peut redistribuer soutiens, accès et dettes autour de vous."
        tags = ("politics", "alliance", "information")
        urgency = 2
    elif category == "political_rivalry":
        title = "Une rivalité cherche des témoins"
        stakes = "Les deux camps pourraient bientôt demander des appuis, des informations ou un silence."
        tags = ("politics", "rivalry", "information")
        urgency = 3
    elif category == "prestation":
        title = "Une Prestation change de poids"
        stakes = "Une dette privée peut devenir un levier politique si vous découvrez ce qu'elle recouvre réellement."
        tags = ("politics", "prestation", "information")
        urgency = 2
    elif category in {"political_patronage", "hunting_patronage"}:
        title = "Un patronage crée une dépendance"
        stakes = "Un service accordé aujourd'hui peut déterminer qui devra soutenir qui lors d'une prochaine crise."
        tags = ("politics", "patronage", "information")
        urgency = 2
    elif category == "hunter_pressure":
        title = "Les mortels posent trop de questions"
        stakes = "Une zone compromise menace la chasse, les refuges et tous ceux dont les habitudes deviennent visibles."
        tags = ("hunters", "masquerade", "information")
        urgency = 3
    elif category == "historical_milestone":
        title = "Le monde extérieur atteint Paris"
        stakes = "Les bouleversements mortels et caïnites créent de nouveaux rapports de force que personne ne contrôle complètement."
        tags = ("history", "politics", "information")
        urgency = 2
    elif category == "praxis_pressure":
        title = "La Praxis vacille"
        stakes = (
            "Une succession prématurée peut fracturer la Cour, mais soutenir une autorité affaiblie peut être tout aussi coûteux."
        )
        tags = ("politics", "praxis", "information")
        urgency = 3

    return StoryHookState(
        id=f"hook_{event.get('id', 'world_event')}",
        category=category,
        actor_id=str(event.get("actor_id", "paris")),
        target_id=None,
        title=title,
        premise=intelligence.claim,
        stakes=stakes,
        tags=tags,
        created_year=int(event.get("year", 1435)),
        created_chapter=int(event.get("chapter", 1)),
        created_cycle=int(event.get("segment", 1)),
        urgency=urgency,
        status="active",
        intelligence_id=intelligence.id,
    )


def _previous_cycle_events(
    character: PlayerCharacter,
    world_events: Sequence[Mapping],
) -> tuple[Mapping, ...]:
    if not world_events:
        return ()

    if character.segment > 1:
        return tuple(
            event
            for event in world_events
            if int(event.get("chapter", -1)) == character.chapter
            and int(event.get("segment", -1)) == character.segment - 1
        )

    if character.chapter <= 1:
        return ()

    previous_chapter = [
        event for event in world_events if int(event.get("chapter", -1)) == character.chapter - 1
    ]
    if not previous_chapter:
        return ()
    latest_cycle = max(int(event.get("segment", 0)) for event in previous_chapter)
    return tuple(event for event in previous_chapter if int(event.get("segment", -1)) == latest_cycle)


def _assigned_night(event_id: str, nights_per_cycle: int) -> int:
    nights = max(1, nights_per_cycle)
    return 1 + _deterministic_score(f"night:{event_id}", nights)


def _choices_for_hook(
    hook: StoryHookState,
    intelligence: IntelligenceState,
    character: PlayerCharacter,
    simulation: SimulationState,
) -> tuple[SituationChoice, ...]:
    difficulty = max(2, 4 - intelligence.reliability)
    verify = SituationChoice(
        "verify",
        "Vérifier avant de choisir un camp",
        "Recouper les témoins, les silences et les incohérences sans annoncer vos conclusions.",
        "wits",
        "insight",
        difficulty,
        PersonalAction.INVESTIGATE,
        "political_intel",
    )
    distance = SituationChoice(
        "distance",
        "Rester en retrait et observer",
        "Vous refusez d'être enrôlé immédiatement tout en surveillant les conséquences.",
        "composure",
        "etiquette",
        2,
        PersonalAction.INVESTIGATE,
        "cautious_distance",
    )

    if hook.category == "praxis_pressure":
        choices: list[SituationChoice] = [verify]
        choices.append(
            SituationChoice(
                "support_praxis",
                "Soutenir publiquement la Praxis en place",
                "Vous faites de votre soutien un acte politique visible, avec les alliances et inimitiés que cela implique.",
                "charisma",
                "politics",
                3,
                PersonalAction.ELYSIUM,
                "political_voice",
            )
        )
        pressure = assess_praxis_pressure(simulation, (character,))
        if pressure.is_critical and character.character_id in pressure.player_candidate_ids:
            choices.append(
                SituationChoice(
                    "claim_praxis",
                    "Faire connaître votre propre prétention",
                    "Vous ne demandez pas une promotion : vous affirmez que votre pouvoir peut remplacer celui du Prince.",
                    "charisma",
                    "politics",
                    5,
                    PersonalAction.ELYSIUM,
                    "praxis_claim",
                )
            )
        choices.append(distance)
        return tuple(choices)

    return (
        verify,
        SituationChoice(
            "approach",
            "Approcher l'acteur concerné",
            "Vous transformez une rumeur en relation politique, au risque de révéler votre intérêt.",
            "charisma",
            "persuasion",
            3,
            PersonalAction.BUILD_RELATION,
            "political_voice",
        ),
        distance,
    )


def world_event_situations(
    character: PlayerCharacter,
    simulation: SimulationState,
    world_events: Sequence[Mapping],
    *,
    nights_per_cycle: int = 3,
) -> tuple[Situation, ...]:
    """Turn last Convergence's actual changes into imperfect playable hooks.

    No hidden intent or raw relation score is exposed. A persistent event is
    deterministically assigned to one significant night of the following Cycle,
    which prevents it from repeating every night without adding a consumption
    column to the database.
    """

    situations: list[tuple[int, Situation]] = []
    for event in _previous_cycle_events(character, world_events):
        event_id = str(event.get("id", "world_event"))
        if _assigned_night(event_id, nights_per_cycle) != character.local_night:
            continue

        intelligence = intelligence_from_world_event(event)
        hook = hook_from_world_event(event, intelligence)
        actor_id = str(event.get("actor_id", ""))
        source_actor_id = actor_id if actor_id in simulation.npcs else None
        body = (
            f"{hook.premise} {hook.stakes} "
            f"Source : {intelligence.source_label} — {reliability_label(intelligence.reliability)}. "
            "Ce que vous en savez peut être incomplet, orienté ou déjà dépassé."
        )
        situations.append(
            (
                hook.urgency,
                Situation(
                    id=f"world_event_{event_id}",
                    title=hook.title,
                    body=body,
                    source_actor_id=source_actor_id,
                    tags=hook.tags,
                    choices=_choices_for_hook(hook, intelligence, character, simulation),
                ),
            )
        )

    situations.sort(key=lambda item: (-item[0], item[1].id))
    return tuple(item[1] for item in situations)
