from __future__ import annotations

from dataclasses import replace

from game.chronicle_simulation_store import ChronicleSimulationStore
from game.chronicle_store import ChronicleStore
from game.dice import DiceResult
from game.editable_repository import EditableSQLiteGameRepository
from game.night_cycle import resolve_night_event
from game.paris_simulation import parisify_simulation
from game.praxis import assess_praxis_pressure, praxis_pressure_beat
from game.qa_scenarios import ensure_qa_scenario
from game.vampire_profile_store import VampireProfileStore
from game.world_situations import world_event_situations


def _state(tmp_path):
    repo = EditableSQLiteGameRepository(tmp_path / "praxis.sqlite3")
    context = ensure_qa_scenario(repo, "first_night")
    store = ChronicleStore(repo)
    progress = store.get_progress(context.game_id)
    character = store.get_character(context.game_id, context.player_id)
    assert progress is not None and character is not None
    profile = VampireProfileStore(repo).ensure_for_character(character)
    simulation = ChronicleSimulationStore(repo).ensure(context.game_id, year=progress.year)
    simulation = parisify_simulation(simulation)
    return progress, character, profile, simulation


def _critical_state(simulation, character):
    prince_id = simulation.offices["prince"]
    npcs = dict(simulation.npcs)
    for npc_id, npc in npcs.items():
        if npc_id == prince_id:
            continue
        relations = dict(npc.relations)
        relations[prince_id] = -3
        npcs[npc_id] = replace(npc, relations=relations)

    domains = dict(simulation.domains)
    citadel = domains["domain_citadelle"]
    domains[citadel.id] = replace(citadel, pressure=6, masquerade_risk=3)
    critical = replace(simulation, npcs=npcs, domains=domains)
    claimant = replace(character, status=3, personal_influence=6.0, chapter=1, segment=2)
    return critical, claimant


def _praxis_event():
    return {
        "id": "praxis_crisis",
        "game_id": "game",
        "year": 1435,
        "chapter": 1,
        "segment": 1,
        "actor_id": "npc_alexandre",
        "actor_name": "Alexandre",
        "category": "praxis_pressure",
        "public_text": "L'autorité d'Alexandre est désormais discutée dans plusieurs cercles de la Cour.",
    }


def _assigned_praxis_situation(character, simulation):
    event = _praxis_event()
    for night in (1, 2, 3):
        current = replace(character, local_night=night)
        situations = world_event_situations(current, simulation, [event], nights_per_cycle=3)
        if situations:
            return current, situations[0]
    raise AssertionError("Praxis hook was not assigned to a significant night")


def test_initial_alexandre_praxis_is_not_automatically_a_crisis(tmp_path):
    _, character, _, simulation = _state(tmp_path)
    assessment = assess_praxis_pressure(simulation, (character,))
    assert assessment.prince_id == "npc_alexandre"
    assert assessment.level in {"stable", "strained"}
    assert praxis_pressure_beat(simulation, (character,)) is None


def test_persistent_hostility_domain_pressure_and_debts_can_make_praxis_critical(tmp_path):
    _, character, _, simulation = _state(tmp_path)
    critical, claimant = _critical_state(simulation, character)

    assessment = assess_praxis_pressure(critical, (claimant,))
    beat = praxis_pressure_beat(critical, (claimant,))

    assert assessment.is_critical
    assert claimant.character_id in assessment.player_candidate_ids
    assert assessment.credible_challenger_ids
    assert beat is not None
    assert beat.category == "praxis_pressure"
    assert "score" not in beat.public_text.lower()
    assert claimant.character_id not in beat.public_text


def test_praxis_claim_choice_only_appears_for_credible_player_during_critical_crisis(tmp_path):
    _, character, _, simulation = _state(tmp_path)
    critical, claimant = _critical_state(simulation, character)
    current, situation = _assigned_praxis_situation(claimant, critical)
    choice_ids = {choice.id for choice in situation.choices}
    assert "claim_praxis" in choice_ids

    weak = replace(current, status=0, personal_influence=0.0)
    _, weak_situation = _assigned_praxis_situation(weak, critical)
    assert "claim_praxis" not in {choice.id for choice in weak_situation.choices}


def test_clean_critical_claim_can_transfer_praxis_but_normal_button_is_never_exposed(tmp_path, monkeypatch):
    progress, character, profile, simulation = _state(tmp_path)
    critical, claimant = _critical_state(simulation, character)
    claimant, situation = _assigned_praxis_situation(claimant, critical)

    def clean_critical(*, pool, hunger, difficulty, seed):
        successes = max(difficulty + 2, 4)
        return DiceResult(
            pool=pool,
            difficulty=difficulty,
            hunger=0,
            normal_dice=(10, 10, 8, 8),
            hunger_dice=(),
            successes=successes,
            margin=successes - difficulty,
            critical=True,
            messy_critical=False,
            bestial_failure=False,
        )

    monkeypatch.setattr("game.situations.roll_pool", clean_critical)
    result = resolve_night_event(
        claimant,
        profile,
        critical,
        situation,
        "claim_praxis",
        nights_per_segment=progress.nights_per_segment,
    )

    assert result.resolution.simulation.offices["prince"] == claimant.character_id
    assert result.resolution.outcome.updated_character.status >= 4
    assert result.resolution.outcome.updated_character.personal_influence >= 8.0
    assert "praxis_taken" in result.resolution.outcome.tags
    assert "Praxis reconnue" in result.resolution.outcome.detail


def test_claim_is_not_available_while_world_state_is_only_strained(tmp_path):
    _, character, _, simulation = _state(tmp_path)
    claimant = replace(character, status=3, personal_influence=6.0, chapter=1, segment=2)
    assessment = assess_praxis_pressure(simulation, (claimant,))
    assert not assessment.is_critical

    event = _praxis_event()
    for night in (1, 2, 3):
        current = replace(claimant, local_night=night)
        situations = world_event_situations(current, simulation, [event], nights_per_cycle=3)
        if situations:
            assert "claim_praxis" not in {choice.id for choice in situations[0].choices}
