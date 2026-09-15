from __future__ import annotations

from dataclasses import replace

from game.agenda_engine import agenda_effect, agenda_stage
from game.chronicle_simulation import (
    SimulationBeat,
    simulation_from_dict,
    simulation_to_dict,
)
from game.chronicle_simulation_store import ChronicleSimulationStore
from game.chronicle_store import ChronicleStore
from game.chronicle_world_store import ChronicleWorldStore
from game.editable_repository import EditableSQLiteGameRepository
from game.night_cycle import choose_night_event, free_action_situations
from game.paris_simulation import parisify_simulation
from game.qa_scenarios import ensure_qa_scenario
from game.vampire_profile_store import VampireProfileStore
from game.world_situations import intelligence_from_world_event, world_event_situations


def _state(tmp_path, scenario_id: str = "first_night"):
    repo = EditableSQLiteGameRepository(tmp_path / f"{scenario_id}.sqlite3")
    context = ensure_qa_scenario(repo, scenario_id)
    store = ChronicleStore(repo)
    progress = store.get_progress(context.game_id)
    character = store.get_character(context.game_id, context.player_id)
    assert progress is not None and character is not None
    profile = VampireProfileStore(repo).ensure_for_character(character)
    simulation = ChronicleSimulationStore(repo).ensure(context.game_id, year=progress.year)
    simulation = parisify_simulation(simulation)
    return repo, context, store, progress, character, profile, simulation


def _world_event(*, event_id: str = "world_test_1", chapter: int = 1, segment: int = 1):
    return {
        "id": event_id,
        "game_id": "game",
        "year": 1435,
        "chapter": chapter,
        "segment": segment,
        "actor_id": "npc_beatrix",
        "actor_name": "Béatrix",
        "category": "political_rivalry",
        "public_text": "Une tension nouvelle autour de Béatrix modifie les conversations de la Cour.",
        "hidden_intent": "CE SECRET NE DOIT JAMAIS ETRE RENDU AU JOUEUR",
    }


def test_world_event_is_assigned_to_exactly_one_significant_night_of_next_cycle(tmp_path):
    _, _, _, _, character, _, simulation = _state(tmp_path)
    event = _world_event()
    matches = []
    for night in (1, 2, 3):
        current = replace(character, chapter=1, segment=2, local_night=night)
        hooks = world_event_situations(current, simulation, [event], nights_per_cycle=3)
        if hooks:
            matches.append((night, hooks[0]))

    assert len(matches) == 1
    _, situation = matches[0]
    assert situation.id == "world_event_world_test_1"
    assert "Source :" in situation.body
    assert "CE SECRET" not in situation.body
    assert "hidden_intent" not in situation.body


def test_old_world_events_do_not_repeat_after_the_immediately_following_cycle(tmp_path):
    _, _, _, _, character, _, simulation = _state(tmp_path)
    current = replace(character, chapter=1, segment=3, local_night=1)
    assert world_event_situations(current, simulation, [_world_event(segment=1)]) == ()


def test_previous_chapter_uses_only_its_latest_cycle_as_story_material(tmp_path):
    _, _, _, _, character, _, simulation = _state(tmp_path)
    current_base = replace(character, chapter=2, segment=1)
    events = [
        _world_event(event_id="old", chapter=1, segment=1),
        _world_event(event_id="latest", chapter=1, segment=4),
    ]
    seen_ids = set()
    for night in (1, 2, 3):
        current = replace(current_base, local_night=night)
        seen_ids.update(item.id for item in world_event_situations(current, simulation, events, nights_per_cycle=3))
    assert "world_event_latest" in seen_ids
    assert "world_event_old" not in seen_ids


def test_imperfect_information_exposes_source_reliability_but_not_truth_state():
    event = _world_event()
    intelligence = intelligence_from_world_event(event)
    assert intelligence.truth_state in {"true", "partial"}
    assert 1 <= intelligence.reliability <= 3

    # Truth is engine state; it is intentionally absent from the public event payload.
    assert "truth_state" not in event


def test_emergent_hook_beats_generic_event_but_not_personal_sire_priority(tmp_path):
    _, _, _, progress, character, profile, simulation = _state(tmp_path)
    event = _world_event()

    assigned_character = None
    for night in (1, 2, 3):
        candidate = replace(character, chapter=1, segment=2, local_night=night)
        if world_event_situations(candidate, simulation, [event], nights_per_cycle=3):
            assigned_character = candidate
            break
    assert assigned_character is not None

    selected = choose_night_event(
        assigned_character,
        profile,
        simulation,
        year=progress.year,
        world_events=[event],
        nights_per_cycle=3,
    )
    assert selected.id.startswith("world_event_")


def test_high_hunger_still_keeps_hunting_as_player_initiated_free_action(tmp_path):
    _, _, _, progress, character, profile, simulation = _state(tmp_path, "high_hunger")
    event = _world_event()
    current = None
    for night in (1, 2, 3):
        candidate = replace(character, chapter=1, segment=2, local_night=night)
        if world_event_situations(candidate, simulation, [event], nights_per_cycle=3):
            current = candidate
            break
    assert current is not None

    selected = choose_night_event(
        current,
        profile,
        simulation,
        year=progress.year,
        world_events=[event],
        nights_per_cycle=3,
    )
    actions = free_action_situations(
        current,
        profile,
        simulation,
        year=progress.year,
        event_id=selected.id,
        world_events=[event],
        nights_per_cycle=3,
    )
    assert not selected.id.startswith("hunt_")
    assert any(item.id.startswith("hunt_") for item in actions)


def test_npc_agenda_progress_has_distinct_persistent_stages(tmp_path):
    _, _, _, _, _, _, simulation = _state(tmp_path)
    npc = simulation.npcs["npc_beatrix"]

    assert agenda_stage(replace(npc, agenda_progress=0)) == "probe"
    assert agenda_stage(replace(npc, agenda_progress=3)) == "recruit"
    assert agenda_stage(replace(npc, agenda_progress=6)) == "commit"
    assert agenda_stage(replace(npc, agenda_progress=9)) == "consolidate"

    probe_effect = agenda_effect(replace(npc, agenda_progress=0), 2)
    recruit_effect = agenda_effect(replace(npc, agenda_progress=3), 2)
    commit_effect = agenda_effect(replace(npc, agenda_progress=6), 2)
    assert probe_effect in {0, 1}
    assert recruit_effect in {0, 1, 2}
    assert commit_effect in {1, 2, 3}
    assert len({probe_effect, recruit_effect, commit_effect}) >= 2


def test_agenda_stage_survives_existing_simulation_json_persistence(tmp_path):
    _, _, _, _, _, _, simulation = _state(tmp_path)
    npcs = dict(simulation.npcs)
    npcs["npc_beatrix"] = replace(npcs["npc_beatrix"], agenda_progress=7)
    simulation = replace(simulation, npcs=npcs)

    restored = simulation_from_dict(simulation_to_dict(simulation))
    assert restored.npcs["npc_beatrix"].agenda_progress == 7
    assert agenda_stage(restored.npcs["npc_beatrix"]) == "commit"


def test_world_store_persists_public_event_without_returning_hidden_intent(tmp_path):
    repo, context, _, progress, _, _, _ = _state(tmp_path)
    store = ChronicleWorldStore(repo)
    store.record_beats(
        progress,
        (
            SimulationBeat(
                actor_id="npc_beatrix",
                actor_name="Béatrix",
                category="alliance_building",
                public_text="Béatrix reçoit plus souvent un ancien allié.",
                hidden_intent="Prendre le contrôle de son réseau sans être vue.",
            ),
        ),
    )

    events = store.list_events(context.game_id)
    assert len(events) == 1
    assert events[0]["public_text"] == "Béatrix reçoit plus souvent un ancien allié."
    assert "hidden_intent" not in events[0]
