from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .chronicle import ChronicleProgress
from .chronicle_store import ChronicleStore
from .chronicle_world import WorldBeat, autonomous_world_beats
from .chronicle_world_store import ChronicleWorldStore


@dataclass(frozen=True)
class ConvergenceResolution:
    previous_progress: ChronicleProgress
    next_progress: ChronicleProgress
    world_beats: tuple[WorldBeat, ...]


class ChronicleService:
    def __init__(self, repository: Any):
        self.store = ChronicleStore(repository)
        self.world_store = ChronicleWorldStore(repository)

    def resolve_convergence(self, game_id: str) -> ConvergenceResolution:
        progress = self.store.get_progress(game_id)
        if progress is None:
            raise ValueError("Chronicle progress is missing")
        characters = self.store.list_characters(game_id)
        if not self.store.all_ready_for_convergence(game_id):
            raise ValueError("All active characters must be ready for convergence")

        beats = autonomous_world_beats(progress, characters)
        next_progress = self.store.resolve_convergence(game_id)
        self.world_store.record_beats(progress, beats)
        return ConvergenceResolution(
            previous_progress=progress,
            next_progress=next_progress,
            world_beats=beats,
        )
