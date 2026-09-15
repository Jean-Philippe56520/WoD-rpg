from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .chronicle import CLAN_DISCIPLINES, create_player_character
from .chronicle_instance import ensure_personal_chronicle
from .chronicle_simulation import ensure_character_links, grant_boon
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .relationship_memory import memories_for_character, record_relationship_memory
from .situations import generate_situations
from .vampire_profile import default_profile
from .vampire_profile_store import VampireProfileStore


@dataclass(frozen=True)
class QaScenario:
    id: str
    label: str
    description: str
    clan_id: str
    character_name: str
    hunger: int = 2
    status: int = 0
    personal_influence: float = 0.0
    sire_relation: int = 2
    segment: int = 1
    local_night: int = 1
    goal_progress: int = 0
    ready_for_convergence: bool = False
    memory_profile: str = "neutral"
    prestation_profile: str = "none"


@dataclass(frozen=True)
class QaScenarioContext:
    scenario: QaScenario
    player_id: str
    game_id: str
    character_id: str


QA_SCENARIOS: tuple[QaScenario, ...] = (
    QaScenario(
        id="first_night",
        label="Première nuit — Toréador",
        description="Parcours nominal d'un infant Toréador au début de la Chronique.",
        clan_id="toreador",
        character_name="Agnès de Chartres",
    ),
    QaScenario(
        id="high_hunger",
        label="Faim élevée — Brujah",
        description="Le personnage commence à Faim 4 afin de vérifier la priorité donnée à la chasse.",
        clan_id="brujah",
        character_name="Jehan le Roux",
        hunger=4,
    ),
    QaScenario(
        id="trusted_sire",
        label="Sire très favorable — Ventrue",
        description="Confiance, disposition et respect élevés : les interactions sociales doivent être facilitées.",
        clan_id="ventrue",
        character_name="Martin de Meaux",
        memory_profile="trusted",
    ),
    QaScenario(
        id="hostile_sire",
        label="Sire hostile — Toréador",
        description="Relation dégradée et griefs persistants : les interactions sociales doivent être plus difficiles.",
        clan_id="toreador",
        character_name="Colin des Halles",
        memory_profile="hostile",
    ),
    QaScenario(
        id="release_candidate",
        label="Émancipation possible — Brujah",
        description="Statut suffisant pour faire apparaître la négociation d'autonomie avec le sire.",
        clan_id="brujah",
        character_name="Hugues de Saint-Marcel",
        status=1,
    ),
    QaScenario(
        id="convergence_ready",
        label="Convergence narrative — Ventrue",
        description="Cycle 2 achevé avec un tournant narratif suffisant pour tester continuation et clôture du chapitre.",
        clan_id="ventrue",
        character_name="Alix de Provins",
        segment=2,
        local_night=3,
        goal_progress=5,
        ready_for_convergence=True,
    ),
    QaScenario(
        id="prestation_due",
        label="Prestation active — Toréador",
        description="Le sire doit une Prestation majeure au PJ afin de vérifier dette, lien et affichage.",
        clan_id="toreador",
        character_name="Perrine des Quais",
        prestation_profile="sire_owes_player",
    ),
)

_SCENARIOS = {scenario.id: scenario for scenario in QA_SCENARIOS}


def qa_scenario(scenario_id: str) -> QaScenario:
    try:
        return _SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown QA scenario: {scenario_id}") from exc


def qa_player_id(scenario_id: str) -> str:
    qa_scenario(scenario_id)
    return f"qa:{scenario_id}"


def qa_default_database_path(scenario_id: str) -> Path:
    qa_scenario(scenario_id)
    return Path("data") / "qa" / f"{scenario_id}.sqlite3"


def reset_sqlite_database(path: str | Path) -> None:
    """Delete only an explicitly supplied QA SQLite database and its sidecars."""

    resolved = Path(path).expanduser().resolve()
    for suffix in ("", "-wal", "-shm"):
        target = Path(f"{resolved}{suffix}")
        if target.exists():
            target.unlink()


def ensure_qa_scenario(repository: Any, scenario_id: str) -> QaScenarioContext:
    scenario = qa_scenario(scenario_id)
    player_id = qa_player_id(scenario.id)
    personal = ensure_personal_chronicle(repository, player_id=player_id)
    store = ChronicleStore(repository)
    profile_store = VampireProfileStore(repository)
    simulation_store = ChronicleSimulationStore(repository)

    existing = store.get_character(personal.game_id, player_id)
    if existing is not None:
        return QaScenarioContext(
            scenario=scenario,
            player_id=player_id,
            game_id=personal.game_id,
            character_id=existing.character_id,
        )

    progress = store.get_progress(personal.game_id)
    if progress is None:
        raise RuntimeError("QA Chronicle progress was not initialized")
    if progress.segment != scenario.segment:
        base = getattr(repository, "delegate", repository)
        if hasattr(base, "client"):
            raise RuntimeError("QA deterministic fixtures must remain SQLite-only")
        with base._connect() as con:
            con.execute(
                "UPDATE wod_chronicle_progress SET segment=? WHERE game_id=?",
                (scenario.segment, personal.game_id),
            )
        progress = replace(progress, segment=scenario.segment)

    character = create_player_character(
        game_id=personal.game_id,
        player_id=player_id,
        player_name="QA automatisé",
        character_id=f"qa_pc_{scenario.id}",
        name=scenario.character_name,
        clan_id=scenario.clan_id,
        concept="Personnage de scénario QA",
        starting_discipline=CLAN_DISCIPLINES[scenario.clan_id][0],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Tester les conséquences persistantes",
        chapter_goal="Valider ce scénario de gameplay",
        progress=progress,
    )
    character = replace(
        character,
        hunger=scenario.hunger,
        status=scenario.status,
        personal_influence=scenario.personal_influence,
        sire_relation=scenario.sire_relation,
        segment=scenario.segment,
        local_night=scenario.local_night,
        goal_progress=scenario.goal_progress,
        ready_for_convergence=scenario.ready_for_convergence,
    )
    store.create_character(character)
    profile_store.save(default_profile(character))

    simulation = simulation_store.ensure(personal.game_id, year=progress.year)
    simulation = ensure_character_links(simulation, character)

    if scenario.memory_profile == "trusted":
        simulation = record_relationship_memory(
            simulation,
            character,
            character.sire_id,
            year=progress.year,
            disposition_delta=2,
            trust_delta=2,
            respect_delta=2,
            awareness_delta=2,
        )
    elif scenario.memory_profile == "hostile":
        for _ in range(2):
            simulation = record_relationship_memory(
                simulation,
                character,
                character.sire_id,
                year=progress.year,
                disposition_delta=-2,
                trust_delta=-2,
                respect_delta=-1,
                awareness_delta=1,
                grievance=True,
            )

    if scenario.prestation_profile == "sire_owes_player":
        simulation = grant_boon(
            simulation,
            creditor_id=character.character_id,
            debtor_id=character.sire_id,
            level="major",
            origin="Fixture QA — service politique reconnu",
            public=True,
        )

    simulation_store.save(simulation)
    return QaScenarioContext(
        scenario=scenario,
        player_id=player_id,
        game_id=personal.game_id,
        character_id=character.character_id,
    )


def qa_snapshot(repository: Any, scenario_id: str) -> dict[str, Any]:
    context = ensure_qa_scenario(repository, scenario_id)
    store = ChronicleStore(repository)
    profile_store = VampireProfileStore(repository)
    simulation_store = ChronicleSimulationStore(repository)

    character = store.get_character(context.game_id, context.player_id)
    progress = store.get_progress(context.game_id)
    if character is None or progress is None:
        raise RuntimeError("QA scenario state is incomplete")
    profile = profile_store.ensure_for_character(character)
    simulation = simulation_store.ensure(context.game_id, year=progress.year)
    situations = generate_situations(character, profile, simulation, year=progress.year)
    memories = memories_for_character(simulation, character)

    return {
        "scenario": {
            "id": context.scenario.id,
            "label": context.scenario.label,
            "description": context.scenario.description,
        },
        "progress": {
            "year": progress.year,
            "chapter": progress.chapter,
            "segment": progress.segment,
            "nights_per_segment": progress.nights_per_segment,
        },
        "character": {
            "id": character.character_id,
            "name": character.name,
            "clan": character.clan_id,
            "hunger": character.hunger,
            "status": character.status,
            "reputation": character.reputation,
            "influence": character.personal_influence,
            "sire_id": character.sire_id,
            "sire_relation": character.sire_relation,
            "goal_progress": character.goal_progress,
            "local_night": character.local_night,
            "ready_for_convergence": character.ready_for_convergence,
        },
        "world": {
            "prince_id": simulation.offices.get("prince"),
            "npc_count": len(simulation.npcs),
            "boon_count": len(simulation.boons),
            "hunting_right_count": len(simulation.hunting_rights),
        },
        "situations": [
            {
                "id": situation.id,
                "title": situation.title,
                "source_actor_id": situation.source_actor_id,
                "choices": [
                    {
                        "id": choice.id,
                        "label": choice.label,
                        "base_difficulty": choice.difficulty,
                        "effect": choice.effect,
                    }
                    for choice in situation.choices
                ],
            }
            for situation in situations
        ],
        "memories": [
            {
                "npc_id": memory.npc_id,
                "disposition": memory.disposition,
                "trust": memory.trust,
                "respect": memory.respect,
                "fear": memory.fear,
                "awareness": memory.awareness,
                "grievance_count": memory.grievance_count,
                "last_interaction_year": memory.last_interaction_year,
            }
            for memory in memories
        ],
    }