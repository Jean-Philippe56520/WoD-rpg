from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping


AGENDA_STAGES = ("probe", "recruit", "commit", "consolidate")
AGENDA_STATUSES = {"active", "blocked", "completed", "abandoned"}
INTELLIGENCE_TRUTH_STATES = {"true", "partial", "false", "unknown"}
INTELLIGENCE_STATUSES = {"active", "stale", "superseded"}
HOOK_STATUSES = {"active", "resolved", "expired"}


@dataclass(frozen=True)
class NpcAgendaState:
    id: str
    owner_id: str
    objective: str
    current_step: str
    stage_index: int = 0
    stage_progress: int = 0
    target_id: str | None = None
    ally_ids: tuple[str, ...] = ()
    opponent_ids: tuple[str, ...] = ()
    visibility: str = "hidden"
    status: str = "active"
    updated_year: int = 1435
    updated_chapter: int = 1
    updated_cycle: int = 1

    @property
    def stage(self) -> str:
        return AGENDA_STAGES[max(0, min(len(AGENDA_STAGES) - 1, self.stage_index))]


@dataclass(frozen=True)
class IntelligenceState:
    id: str
    subject_id: str
    claim: str
    source_label: str
    source_actor_id: str | None = None
    source_kind: str = "rumor"
    reliability: int = 1
    truth_state: str = "unknown"
    known_to_player: bool = True
    acquired_year: int = 1435
    acquired_chapter: int = 1
    acquired_cycle: int = 1
    status: str = "active"
    related_hook_id: str | None = None


@dataclass(frozen=True)
class StoryHookState:
    id: str
    category: str
    actor_id: str
    target_id: str | None
    title: str
    premise: str
    stakes: str
    tags: tuple[str, ...]
    created_year: int
    created_chapter: int
    created_cycle: int
    urgency: int = 1
    status: str = "active"
    intelligence_id: str | None = None
    agenda_id: str | None = None
    domain_id: str | None = None


def agenda_to_dict(item: NpcAgendaState) -> dict:
    return {
        "id": item.id,
        "owner_id": item.owner_id,
        "objective": item.objective,
        "current_step": item.current_step,
        "stage_index": item.stage_index,
        "stage_progress": item.stage_progress,
        "target_id": item.target_id,
        "ally_ids": list(item.ally_ids),
        "opponent_ids": list(item.opponent_ids),
        "visibility": item.visibility,
        "status": item.status,
        "updated_year": item.updated_year,
        "updated_chapter": item.updated_chapter,
        "updated_cycle": item.updated_cycle,
    }


def agenda_from_dict(value: Mapping) -> NpcAgendaState:
    stage_index = int(value.get("stage_index", 0))
    return NpcAgendaState(
        id=str(value["id"]),
        owner_id=str(value["owner_id"]),
        objective=str(value.get("objective", "")),
        current_step=str(value.get("current_step", "")),
        stage_index=max(0, min(len(AGENDA_STAGES) - 1, stage_index)),
        stage_progress=max(0, int(value.get("stage_progress", 0))),
        target_id=(str(value["target_id"]) if value.get("target_id") is not None else None),
        ally_ids=tuple(str(item) for item in value.get("ally_ids", ())),
        opponent_ids=tuple(str(item) for item in value.get("opponent_ids", ())),
        visibility=str(value.get("visibility", "hidden")),
        status=str(value.get("status", "active")),
        updated_year=int(value.get("updated_year", 1435)),
        updated_chapter=int(value.get("updated_chapter", 1)),
        updated_cycle=int(value.get("updated_cycle", 1)),
    )


def intelligence_to_dict(item: IntelligenceState) -> dict:
    return {
        "id": item.id,
        "subject_id": item.subject_id,
        "claim": item.claim,
        "source_label": item.source_label,
        "source_actor_id": item.source_actor_id,
        "source_kind": item.source_kind,
        "reliability": item.reliability,
        "truth_state": item.truth_state,
        "known_to_player": item.known_to_player,
        "acquired_year": item.acquired_year,
        "acquired_chapter": item.acquired_chapter,
        "acquired_cycle": item.acquired_cycle,
        "status": item.status,
        "related_hook_id": item.related_hook_id,
    }


def intelligence_from_dict(value: Mapping) -> IntelligenceState:
    truth_state = str(value.get("truth_state", "unknown"))
    if truth_state not in INTELLIGENCE_TRUTH_STATES:
        truth_state = "unknown"
    status = str(value.get("status", "active"))
    if status not in INTELLIGENCE_STATUSES:
        status = "active"
    return IntelligenceState(
        id=str(value["id"]),
        subject_id=str(value.get("subject_id", "unknown")),
        claim=str(value.get("claim", "")),
        source_label=str(value.get("source_label", "Source non précisée")),
        source_actor_id=(str(value["source_actor_id"]) if value.get("source_actor_id") is not None else None),
        source_kind=str(value.get("source_kind", "rumor")),
        reliability=max(0, min(3, int(value.get("reliability", 1)))),
        truth_state=truth_state,
        known_to_player=bool(value.get("known_to_player", True)),
        acquired_year=int(value.get("acquired_year", 1435)),
        acquired_chapter=int(value.get("acquired_chapter", 1)),
        acquired_cycle=int(value.get("acquired_cycle", 1)),
        status=status,
        related_hook_id=(str(value["related_hook_id"]) if value.get("related_hook_id") is not None else None),
    )


def hook_to_dict(item: StoryHookState) -> dict:
    return {
        "id": item.id,
        "category": item.category,
        "actor_id": item.actor_id,
        "target_id": item.target_id,
        "title": item.title,
        "premise": item.premise,
        "stakes": item.stakes,
        "tags": list(item.tags),
        "created_year": item.created_year,
        "created_chapter": item.created_chapter,
        "created_cycle": item.created_cycle,
        "urgency": item.urgency,
        "status": item.status,
        "intelligence_id": item.intelligence_id,
        "agenda_id": item.agenda_id,
        "domain_id": item.domain_id,
    }


def hook_from_dict(value: Mapping) -> StoryHookState:
    status = str(value.get("status", "active"))
    if status not in HOOK_STATUSES:
        status = "active"
    return StoryHookState(
        id=str(value["id"]),
        category=str(value.get("category", "world_event")),
        actor_id=str(value.get("actor_id", "world")),
        target_id=(str(value["target_id"]) if value.get("target_id") is not None else None),
        title=str(value.get("title", "Une affaire circule dans la nuit")),
        premise=str(value.get("premise", "")),
        stakes=str(value.get("stakes", "")),
        tags=tuple(str(item) for item in value.get("tags", ())),
        created_year=int(value.get("created_year", 1435)),
        created_chapter=int(value.get("created_chapter", 1)),
        created_cycle=int(value.get("created_cycle", 1)),
        urgency=max(1, min(3, int(value.get("urgency", 1)))),
        status=status,
        intelligence_id=(str(value["intelligence_id"]) if value.get("intelligence_id") is not None else None),
        agenda_id=(str(value["agenda_id"]) if value.get("agenda_id") is not None else None),
        domain_id=(str(value["domain_id"]) if value.get("domain_id") is not None else None),
    )


def reliability_label(value: int) -> str:
    if value >= 3:
        return "information recoupée"
    if value == 2:
        return "source plausible"
    if value == 1:
        return "rumeur fragile"
    return "origine très incertaine"


def mark_hook_resolved(hook: StoryHookState) -> StoryHookState:
    return hook if hook.status == "resolved" else replace(hook, status="resolved")
