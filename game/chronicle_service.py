from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .chronicle import ChronicleProgress, PlayerCharacter
from .chronicle_politics import validate_political_state
from .chronicle_simulation import SimulationBeat
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
from .era import era_for_year, milestones_crossed
from .paris_simulation import advance_paris_simulation


MONTH_NAMES = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


@dataclass(frozen=True)
class ChronicleTimeState:
    game_id: str
    month: int = 1
    minimum_cycles_per_chapter: int = 2
    cycle_months: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError("Chronicle month must be between 1 and 12")
        if self.minimum_cycles_per_chapter < 1:
            raise ValueError("Minimum cycles per chapter must be positive")
        if not 1 <= self.cycle_months <= 12:
            raise ValueError("Cycle duration must be between 1 and 12 months")


@dataclass(frozen=True)
class ChapterClosureAssessment:
    closable: bool
    reason: str
    ready_characters: int
    strong_characters: int
    active_characters: int


@dataclass(frozen=True)
class ConvergenceResolution:
    previous_progress: ChronicleProgress
    next_progress: ChronicleProgress
    world_beats: tuple[SimulationBeat, ...]
    previous_time: ChronicleTimeState
    next_time: ChronicleTimeState
    chapter_closed: bool = False
    ellipse_months: int = 0


def advance_months(year: int, month: int, months: int) -> tuple[int, int]:
    if year < 1 or not 1 <= month <= 12 or months < 0:
        raise ValueError("Invalid Chronicle calendar transition")
    absolute = year * 12 + (month - 1) + months
    return absolute // 12, absolute % 12 + 1


def chronicle_time_label(year: int, month: int) -> str:
    if month in (12, 1, 2):
        season = "Hiver"
    elif month in (3, 4, 5):
        season = "Printemps"
    elif month in (6, 7, 8):
        season = "Été"
    else:
        season = "Automne"
    return f"{season} {year} · {MONTH_NAMES[month - 1]}"


def ellipse_label(months: int) -> str:
    labels = {
        0: "sans ellipse",
        1: "quelques semaines",
        3: "une saison",
        6: "quelques mois",
        12: "un an",
        24: "deux ans",
    }
    if months in labels:
        return labels[months]
    if months % 12 == 0:
        return f"{months // 12} ans"
    return f"{months} mois"


def recommended_ellipse_months(
    progress: ChronicleProgress,
    characters: list[PlayerCharacter],
) -> int:
    active = [character for character in characters if character.is_active]
    if not active:
        return 1
    oldest_age = max(max(0, progress.year - character.embraced_year) for character in active)
    highest_status = max(character.status for character in active)
    if oldest_age >= 300 or progress.chapter >= 30:
        return 120
    if oldest_age >= 150 or progress.chapter >= 20:
        return 60
    if oldest_age >= 50 or progress.chapter >= 12 or highest_status >= 4:
        return 24
    if oldest_age >= 20 or progress.chapter >= 8 or highest_status >= 3:
        return 12
    if oldest_age >= 5 or progress.chapter >= 4 or highest_status >= 2:
        return 3
    return 1


class ChronicleService:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        self.store = ChronicleStore(repository)
        self.world_store = ChronicleWorldStore(repository)
        self.simulation_store = ChronicleSimulationStore(repository)
        if not self._is_supabase:
            self._ensure_time_schema()

    def _ensure_time_schema(self) -> None:
        with self.repository._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS wod_chronicle_time (
                    game_id TEXT PRIMARY KEY,
                    month INTEGER NOT NULL DEFAULT 1 CHECK (month BETWEEN 1 AND 12),
                    minimum_cycles_per_chapter INTEGER NOT NULL DEFAULT 2
                        CHECK (minimum_cycles_per_chapter BETWEEN 1 AND 20),
                    cycle_months INTEGER NOT NULL DEFAULT 1
                        CHECK (cycle_months BETWEEN 1 AND 12),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
                """
            )

    @staticmethod
    def _time_from_row(row: dict[str, Any]) -> ChronicleTimeState:
        return ChronicleTimeState(
            game_id=str(row["game_id"]),
            month=int(row.get("month", 1)),
            minimum_cycles_per_chapter=int(row.get("minimum_cycles_per_chapter", 2)),
            cycle_months=int(row.get("cycle_months", 1)),
        )

    def get_time_state(self, game_id: str) -> ChronicleTimeState:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_chronicle_time",
                "game_id,month,minimum_cycles_per_chapter,cycle_months",
                filters={"game_id": game_id},
                limit=1,
            )
            return self._time_from_row(rows[0]) if rows else ChronicleTimeState(game_id=game_id)
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT * FROM wod_chronicle_time WHERE game_id = ?",
                (game_id,),
            ).fetchone()
            if row is None:
                con.execute(
                    """
                    INSERT INTO wod_chronicle_time(
                        game_id,month,minimum_cycles_per_chapter,cycle_months
                    ) VALUES(?,?,?,?)
                    """,
                    (game_id, 1, 2, 1),
                )
                return ChronicleTimeState(game_id=game_id)
        return self._time_from_row(dict(row))

    def assess_chapter_closure(self, game_id: str) -> ChapterClosureAssessment:
        progress = self.store.get_progress(game_id)
        if progress is None:
            raise ValueError("Chronicle progress is missing")
        time_state = self.get_time_state(game_id)
        characters = [
            character for character in self.store.list_characters(game_id)
            if character.is_active
            and character.chapter == progress.chapter
            and character.segment == progress.segment
        ]
        if not characters:
            return ChapterClosureAssessment(False, "Aucun personnage actif n'est engagé dans ce Cycle.", 0, 0, 0)

        ready_count = sum(character.goal_progress >= 2 for character in characters)
        strong_count = sum(character.goal_progress >= 5 for character in characters)
        if progress.segment < time_state.minimum_cycles_per_chapter:
            remaining = time_state.minimum_cycles_per_chapter - progress.segment
            reason = f"Le chapitre est encore trop jeune : {remaining} Cycle(s) minimum restent à traverser."
            return ChapterClosureAssessment(False, reason, ready_count, strong_count, len(characters))
        if ready_count < len(characters):
            reason = "L'enjeu du chapitre n'a pas encore suffisamment progressé pour tous les protagonistes."
            return ChapterClosureAssessment(False, reason, ready_count, strong_count, len(characters))
        if strong_count == 0:
            reason = "L'enjeu progresse, mais aucun tournant décisif n'a encore été atteint."
            return ChapterClosureAssessment(False, reason, ready_count, strong_count, len(characters))
        return ChapterClosureAssessment(
            True,
            "Un tournant narratif suffisant a été atteint : le chapitre peut se clore à cette Convergence.",
            ready_count,
            strong_count,
            len(characters),
        )

    def _resolve_temporal_progress(
        self,
        game_id: str,
        *,
        close_chapter: bool,
    ) -> tuple[ChronicleProgress, ChronicleTimeState, int]:
        if self._is_supabase:
            raw = self.repository.client.rpc(
                "wod_resolve_temporal_convergence",
                {"p_game_id": game_id, "p_close_chapter": bool(close_chapter)},
            )
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected temporal convergence response")
            progress_raw = raw.get("progress")
            time_raw = raw.get("time")
            if not isinstance(progress_raw, dict) or not isinstance(time_raw, dict):
                raise RuntimeError("Incomplete temporal convergence response")
            return (
                ChronicleStore._progress_from_row(progress_raw),
                self._time_from_row(time_raw),
                int(raw.get("ellipse_months", 0)),
            )

        with self.repository._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            progress_row = con.execute(
                "SELECT * FROM wod_chronicle_progress WHERE game_id = ?",
                (game_id,),
            ).fetchone()
            if progress_row is None:
                raise ValueError("Chronicle progress is missing")
            progress = ChronicleStore._progress_from_row(dict(progress_row))

            time_row = con.execute(
                "SELECT * FROM wod_chronicle_time WHERE game_id = ?",
                (game_id,),
            ).fetchone()
            if time_row is None:
                con.execute(
                    """
                    INSERT INTO wod_chronicle_time(
                        game_id,month,minimum_cycles_per_chapter,cycle_months
                    ) VALUES(?,?,?,?)
                    """,
                    (game_id, 1, 2, 1),
                )
                time_state = ChronicleTimeState(game_id=game_id)
            else:
                time_state = self._time_from_row(dict(time_row))

            rows = con.execute(
                """
                SELECT * FROM wod_player_characters
                WHERE game_id = ? AND is_active = 1
                  AND chapter = ? AND segment = ?
                ORDER BY character_id
                """,
                (game_id, progress.chapter, progress.segment),
            ).fetchall()
            if not rows or any(not bool(row["ready_for_convergence"]) for row in rows):
                raise ValueError("All active characters must be ready for convergence")
            characters = [ChronicleStore._character_from_row(dict(row)) for row in rows]

            ready_count = sum(character.goal_progress >= 2 for character in characters)
            strong_count = sum(character.goal_progress >= 5 for character in characters)
            closable = (
                progress.segment >= time_state.minimum_cycles_per_chapter
                and ready_count == len(characters)
                and strong_count >= 1
            )
            if close_chapter and not closable:
                raise ValueError("Chapter cannot be closed at this convergence")

            ellipse_months = recommended_ellipse_months(progress, characters) if close_chapter else 0
            next_year, next_month = advance_months(
                progress.year,
                time_state.month,
                time_state.cycle_months + ellipse_months,
            )
            next_progress = replace(
                progress,
                year=next_year,
                chapter=progress.chapter + 1 if close_chapter else progress.chapter,
                segment=1 if close_chapter else progress.segment + 1,
            )

            con.execute(
                """
                UPDATE wod_chronicle_progress
                SET year=?, chapter=?, segment=?, updated_at=CURRENT_TIMESTAMP
                WHERE game_id=?
                """,
                (next_progress.year, next_progress.chapter, next_progress.segment, game_id),
            )
            con.execute(
                """
                UPDATE wod_chronicle_time
                SET month=?, updated_at=CURRENT_TIMESTAMP
                WHERE game_id=?
                """,
                (next_month, game_id),
            )
            con.execute(
                """
                UPDATE wod_player_characters
                SET chronicle_year=?, chapter=?, segment=?, local_night=1,
                    ready_for_convergence=0,
                    experience = experience + CASE
                        WHEN ? AND goal_progress >= 5 THEN 2
                        WHEN ? AND goal_progress >= 2 THEN 1 ELSE 0 END,
                    personal_influence = personal_influence + CASE
                        WHEN ? AND goal_progress >= 5 THEN 1.0
                        WHEN ? AND goal_progress >= 2 THEN 0.5 ELSE 0 END,
                    reputation = MIN(3, reputation + CASE
                        WHEN ? AND goal_progress >= 5 THEN 1 ELSE 0 END),
                    status = MIN(5, status + CASE
                        WHEN ? AND goal_progress >= 7 AND status = 0 THEN 1 ELSE 0 END),
                    goal_progress = CASE WHEN ? THEN 0 ELSE goal_progress END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE game_id=? AND is_active=1
                  AND chapter=? AND segment=?
                """,
                (
                    next_progress.year,
                    next_progress.chapter,
                    next_progress.segment,
                    int(close_chapter), int(close_chapter),
                    int(close_chapter), int(close_chapter),
                    int(close_chapter), int(close_chapter), int(close_chapter),
                    game_id, progress.chapter, progress.segment,
                ),
            )
            con.commit()

        return (
            next_progress,
            replace(time_state, month=next_month),
            ellipse_months,
        )

    def resolve_convergence(
        self,
        game_id: str,
        *,
        close_chapter: bool = False,
    ) -> ConvergenceResolution:
        progress = self.store.get_progress(game_id)
        if progress is None:
            raise ValueError("Chronicle progress is missing")
        characters = self.store.list_characters(game_id)
        if not self.store.all_ready_for_convergence(game_id):
            raise ValueError("All active characters must be ready for convergence")
        assessment = self.assess_chapter_closure(game_id)
        if close_chapter and not assessment.closable:
            raise ValueError(assessment.reason)

        previous_time = self.get_time_state(game_id)
        simulation = self.simulation_store.ensure(game_id, year=progress.year)
        advanced, beats = advance_paris_simulation(
            simulation,
            year=progress.year,
            chapter=progress.chapter,
            segment=progress.segment,
            characters=characters,
        )
        validate_political_state(advanced, characters, era_for_year(progress.year))
        next_progress, next_time, ellipse_months = self._resolve_temporal_progress(
            game_id,
            close_chapter=close_chapter,
        )

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
            previous_time=previous_time,
            next_time=next_time,
            chapter_closed=bool(close_chapter),
            ellipse_months=ellipse_months,
        )
