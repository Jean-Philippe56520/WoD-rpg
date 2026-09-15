from __future__ import annotations

from types import SimpleNamespace

import game.night_cycle as night_cycle
from game.chronicle_simulation_store import ChronicleSimulationStore
from game.chronicle_store import ChronicleStore
from game.editable_repository import EditableSQLiteGameRepository
from game.night_cycle import (
    NightPhase,
    _event_budget,
    choose_night_event,
    free_action_situations,
    resolve_free_action,
    resolve_night_event,
)
from game.night_cycle_store import NightCycleStore
from game.qa_scenarios import ensure_qa_scenario
from game.vampire_profile_store import VampireProfileStore


def _state(tmp_path, scenario_id: str):
    repo = EditableSQLiteGameRepository(tmp_path / f"{scenario_id}.sqlite3")
    context = ensure_qa_scenario(repo, scenario_id)
    store = ChronicleStore(repo)
    progress = store.get_progress(context.game_id)
    character = store.get_character(context.game_id, context.player_id)
    assert progress is not None and character is not None
    profile = VampireProfileStore(repo).ensure_for_character(character)
    simulation = ChronicleSimulationStore(repo).ensure(context.game_id, year=progress.year)
    return repo, context, store, progress, character, profile, simulation


def test_event_step_is_persistent_and_does_not_advance_the_night(tmp_path):
    repo, context, store, progress, character, profile, simulation = _state(tmp_path, "first_night")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    assert not event.id.startswith("hunt_")

    night_store = NightCycleStore(repo)
    state = night_store.ensure(character, event_id=event.id)
    assert state.phase == NightPhase.EVENT

    result = resolve_night_event(
        character,
        profile,
        simulation,
        event,
        event.choices[0].id,
        nights_per_segment=progress.nights_per_segment,
    )
    assert result.resolution.outcome.updated_character.local_night == 1
    assert result.resolution.outcome.updated_character.ready_for_convergence is False
    assert result.remaining_actions in {0, 1, 2}

    night_store.apply_event(character, state, result)
    refreshed = store.get_character(context.game_id, context.player_id)
    persisted = night_store.get_state(context.game_id, context.player_id)
    assert refreshed is not None and persisted is not None
    assert refreshed.local_night == 1
    assert persisted.phase == NightPhase.FREE_ACTIONS
    assert persisted.remaining_actions == result.remaining_actions
    assert len(persisted.log) == 1


def test_finishing_the_night_is_the_only_step_that_advances_local_night(tmp_path):
    repo, context, store, progress, character, profile, simulation = _state(tmp_path, "first_night")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    night_store = NightCycleStore(repo)
    state = night_store.ensure(character, event_id=event.id)
    result = resolve_night_event(
        character,
        profile,
        simulation,
        event,
        event.choices[0].id,
        nights_per_segment=progress.nights_per_segment,
    )
    night_store.apply_event(character, state, result)

    before_finish = store.get_character(context.game_id, context.player_id)
    state = night_store.get_state(context.game_id, context.player_id)
    assert before_finish is not None and state is not None
    assert before_finish.local_night == 1

    finished = night_store.finish_night(
        before_finish,
        state,
        nights_per_segment=progress.nights_per_segment,
    )
    assert finished.local_night == 2
    assert finished.ready_for_convergence is False
    history = store.list_history(context.game_id, character.character_id)
    assert len(history) == 1
    assert history[0]["outcome_json"]["tags"] == ["night_cycle", "event_then_free_actions"]


def test_hunting_is_a_free_action_not_an_imposed_high_hunger_event(tmp_path):
    _, _, _, progress, character, profile, simulation = _state(tmp_path, "high_hunger")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    actions = free_action_situations(
        character,
        profile,
        simulation,
        year=progress.year,
        event_id=event.id,
    )
    assert not event.id.startswith("hunt_")
    assert any(item.id.startswith("hunt_") for item in actions)
    assert all(item.id != event.id for item in actions)


def test_careful_hunt_can_consume_all_remaining_free_time(tmp_path):
    _, _, _, progress, character, profile, simulation = _state(tmp_path, "high_hunger")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    hunt = next(
        item
        for item in free_action_situations(
            character, profile, simulation, year=progress.year, event_id=event.id
        )
        if item.id.startswith("hunt_")
    )
    result = resolve_free_action(
        character,
        profile,
        simulation,
        hunt,
        "careful_hunt",
        nights_per_segment=progress.nights_per_segment,
        remaining_actions=2,
    )
    assert result.action_cost == 2
    assert result.remaining_actions == 0
    assert result.resolution.outcome.updated_character.local_night == character.local_night


def test_free_actions_use_distinct_deterministic_step_nonces(monkeypatch, tmp_path):
    _, _, _, progress, character, profile, simulation = _state(tmp_path, "high_hunger")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    action = next(
        item
        for item in free_action_situations(
            character, profile, simulation, year=progress.year, event_id=event.id
        )
        if item.id.startswith("hunt_")
    )
    choice_id = action.choices[0].id
    seen_choice_ids: list[str] = []
    original = night_cycle.resolve_situation

    def capture(character_arg, profile_arg, simulation_arg, situation_arg, seeded_choice_id, **kwargs):
        seen_choice_ids.append(seeded_choice_id)
        return original(
            character_arg,
            profile_arg,
            simulation_arg,
            situation_arg,
            seeded_choice_id,
            **kwargs,
        )

    monkeypatch.setattr(night_cycle, "resolve_situation", capture)
    first = resolve_free_action(
        character,
        profile,
        simulation,
        action,
        choice_id,
        nights_per_segment=progress.nights_per_segment,
        remaining_actions=2,
        action_index=1,
    )
    second = resolve_free_action(
        character,
        profile,
        simulation,
        action,
        choice_id,
        nights_per_segment=progress.nights_per_segment,
        remaining_actions=2,
        action_index=2,
    )

    assert seen_choice_ids == [f"{choice_id}@free:1", f"{choice_id}@free:2"]
    assert first.resolution.choice.id == choice_id
    assert second.resolution.choice.id == choice_id


def test_unresolved_obsolete_event_is_rebound_without_blocking_the_night(tmp_path):
    repo, context, _, progress, character, profile, simulation = _state(tmp_path, "first_night")
    event = choose_night_event(character, profile, simulation, year=progress.year)
    night_store = NightCycleStore(repo)
    state = night_store.ensure(character, event_id=event.id)
    assert state.phase == NightPhase.EVENT and not state.log

    with repo._connect() as con:
        con.execute(
            "UPDATE wod_character_night_state SET event_id=? WHERE game_id=? AND player_id=?",
            ("obsolete_event", context.game_id, context.player_id),
        )

    recovered = night_store.ensure(character, event_id=event.id)
    assert recovered.event_id == event.id
    assert recovered.phase == NightPhase.EVENT
    assert recovered.log == ()


def test_intense_sire_relationship_makes_sire_event_relevant(tmp_path):
    for scenario_id in ("trusted_sire", "hostile_sire"):
        _, _, _, progress, character, profile, simulation = _state(tmp_path, scenario_id)
        event = choose_night_event(character, profile, simulation, year=progress.year)
        assert event.id == "sire_accounting"


def test_failed_refusal_by_dependent_infant_can_end_the_night_with_sire_sanction():
    character = SimpleNamespace(sire_relation=0)
    resolution = SimpleNamespace(
        dice=SimpleNamespace(success=False, bestial_failure=False, critical=False, messy_critical=False),
        choice=SimpleNamespace(effect="sire_refuse"),
        simulation=SimpleNamespace(npcs={}),
        situation=SimpleNamespace(source_actor_id="sire"),
        outcome=SimpleNamespace(updated_character=SimpleNamespace(sire_relation=0)),
    )
    remaining, consequence = _event_budget(character, resolution)
    assert remaining == 0
    assert "sanction" in consequence
    assert "aube" in consequence
