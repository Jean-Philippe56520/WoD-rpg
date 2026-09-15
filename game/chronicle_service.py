from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .chronicle import ChronicleProgress
from .chronicle_politics import validate_political_state
from .chronicle_simulation import SimulationBeat, advance_simulation
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
from .era import era_for_year, milestones_crossed


@dataclass(frozen=True)
class ConvergenceResolution:
    previous_progress: ChronicleProgress
    next_progress: ChronicleProgress
    world_beats: tuple[SimulationBeat, ...]


class ChronicleService:
    def __init__(self, repository: Any):
        self.store = ChronicleStore(repository)
        self.world_store = ChronicleWorldStore(repository)
        self.simulation_store = ChronicleSimulationStore(repository)

    def resolve_convergence(self, game_id: str) -> ConvergenceResolution:
        progress = self.store.get_progress(game_id)
        if progress is None:
            raise ValueError("Chronicle progress is missing")
        characters = self.store.list_characters(game_id)
        if not self.store.all_ready_for_convergence(game_id):
            raise ValueError("All active characters must be ready for convergence")

        simulation = self.simulation_store.ensure(game_id, year=progress.year)
        advanced, beats = advance_simulation(
            simulation,
            year=progress.year,
            chapter=progress.chapter,
            segment=progress.segment,
            characters=characters,
        )
        validate_political_state(advanced, characters, era_for_year(progress.year))
        next_progress = self.store.resolve_convergence(game_id)

        self.world_store.record_beats(progress, beats)
        historical_beats: list[SimulationBeat] = []
        for milestone in milestones_crossed(progress.year, next_progress.year):
            beat = SimulationBeat(
                actor_id=f"history_{milestone.id}",
                actor_name="Chronique historique",
                category="historical_milestone",
                public_text=milestone.public_text,
                hidden_intent=milestone.title,
            )
            historical_beats.append(beat)
            milestone_progress = replace(progress, year=milestone.year)
            self.world_store.record_beats(milestone_progress, (beat,))

        next_era = era_for_year(next_progress.year)
        final_simulation = replace(
            advanced,
            year=next_progress.year,
            institution_stage=next_era.camarilla_stage.value,
        )
        validate_political_state(final_simulation, characters, next_era)
        self.simulation_store.save(final_simulation)

        all_beats = beats + tuple(historical_beats)
        return ConvergenceResolution(
            previous_progress=progress,
            next_progress=next_progress,
            world_beats=all_beats,
        )
