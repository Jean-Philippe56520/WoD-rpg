from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from game.editable_repository import EditableSQLiteGameRepository
from game.night_cycle import NightPhase
from game.night_cycle_store import NightCycleStore
from game.qa_scenarios import QA_SCENARIOS, qa_player_id, qa_snapshot


APP_PATH = Path(__file__).resolve().parents[1] / "qa_app.py"


def _scenario_label(scenario_id: str) -> str:
    return next(scenario.label for scenario in QA_SCENARIOS if scenario.id == scenario_id)


def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("WOD_QA_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(APP_PATH), default_timeout=10)
    app.run()
    assert not app.exception
    return app


def _repo(tmp_path, scenario_id: str):
    return EditableSQLiteGameRepository(tmp_path / f"{scenario_id}.sqlite3")


def _select_scenario(app, scenario_id: str):
    app.selectbox(key="qa_scenario_selector").select(_scenario_label(scenario_id)).run()
    assert not app.exception
    return app


def _button_by_label(app, label: str):
    return next(button for button in app.button if button.label == label)


def _buttons_by_label(app, label: str):
    return [button for button in app.button if button.label == label]


def _text_values(elements):
    return [str(item.value) for item in elements]


def _night_state(tmp_path, scenario_id: str):
    repo = _repo(tmp_path, scenario_id)
    snapshot = qa_snapshot(repo, scenario_id)
    state = NightCycleStore(repo).get_state(
        snapshot["scenario"].get("game_id", "") or f"unused:{scenario_id}",
        qa_player_id(scenario_id),
    )
    if state is not None:
        return state
    delegate = getattr(repo, "delegate", repo)
    with delegate._connect() as con:
        row = con.execute(
            "SELECT * FROM wod_character_night_state WHERE player_id = ?",
            (qa_player_id(scenario_id),),
        ).fetchone()
    return NightCycleStore._from_row(dict(row)) if row else None


def _chronicle_time(tmp_path, scenario_id: str):
    repo = _repo(tmp_path, scenario_id)
    delegate = getattr(repo, "delegate", repo)
    with delegate._connect() as con:
        row = con.execute(
            "SELECT month,minimum_cycles_per_chapter,cycle_months FROM wod_chronicle_time LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def test_qa_harness_opens_on_isolated_first_night(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)

    assert app.selectbox(key="qa_scenario_selector").value == _scenario_label("first_night")
    assert any("laboratoire QA" in value for value in _text_values(app.title))
    assert any("Agnès de Chartres" in value for value in _text_values(app.title))
    assert any("aucune écriture Supabase" in value for value in _text_values(app.error))
    assert any("Événement de la nuit" in value for value in _text_values(app.markdown))
    rendered = _text_values(app.markdown) + _text_values(app.caption)
    assert any("Nuit significative" in value for value in rendered)

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["world"]["prince_id"] == "npc_alexandre"
    assert snapshot["character"]["local_night"] == 1
    assert snapshot["character"]["ready_for_convergence"] is False


def test_all_qa_scenarios_boot_without_streamlit_exception(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)

    for scenario in QA_SCENARIOS:
        _select_scenario(app, scenario.id)
        snapshot = qa_snapshot(_repo(tmp_path, scenario.id), scenario.id)
        assert snapshot["scenario"]["id"] == scenario.id
        assert snapshot["character"]["clan"] == scenario.clan_id
        assert snapshot["world"]["prince_id"] == "npc_alexandre"


def test_high_hunger_keeps_hunt_as_player_initiated_action(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "high_hunger")
    snapshot = qa_snapshot(_repo(tmp_path, "high_hunger"), "high_hunger")

    assert snapshot["character"]["hunger"] == 4
    assert snapshot["situations"][0]["id"].startswith("hunt_")
    assert not any("La Faim réclame une décision" in value for value in _text_values(app.markdown))
    assert _buttons_by_label(app, "Résoudre l'événement")


def test_release_candidate_uses_emancipation_as_opening_event(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "release_candidate")
    snapshot = qa_snapshot(_repo(tmp_path, "release_candidate"), "release_candidate")

    assert snapshot["character"]["status"] == 1
    assert snapshot["situations"][0]["id"] == "sire_release"
    assert any("Faire reconnaître votre autonomie" in value for value in _text_values(app.markdown))


def test_resolving_event_keeps_same_night_and_persists_free_action_phase(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    _button_by_label(app, "Résoudre l'événement").click().run()
    assert not app.exception

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["character"]["local_night"] == 1
    state = _night_state(tmp_path, "first_night")
    assert state is not None
    assert state.phase == NightPhase.FREE_ACTIONS
    assert state.remaining_actions in {0, 1, 2}
    assert len(state.log) == 1
    assert _buttons_by_label(app, "Terminer la nuit")


def test_free_action_if_available_stays_inside_same_night(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    _button_by_label(app, "Résoudre l'événement").click().run()
    assert not app.exception
    state = _night_state(tmp_path, "first_night")
    assert state is not None

    action_buttons = _buttons_by_label(app, "Entreprendre cette action")
    if state.remaining_actions > 0:
        assert action_buttons
        action_buttons[0].click().run()
        assert not app.exception
        snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
        assert snapshot["character"]["local_night"] == 1
        next_state = _night_state(tmp_path, "first_night")
        assert next_state is not None
        assert len(next_state.log) == 2
        assert next_state.remaining_actions <= state.remaining_actions
    else:
        assert not action_buttons


def test_finishing_night_advances_real_chronicle(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    _button_by_label(app, "Résoudre l'événement").click().run()
    assert not app.exception
    _button_by_label(app, "Terminer la nuit").click().run()
    assert not app.exception

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["character"]["local_night"] == 2


def test_trusted_and_hostile_sire_change_rendered_difficulty_context(monkeypatch, tmp_path):
    trusted = _select_scenario(_app(monkeypatch, tmp_path), "trusted_sire")
    _button_by_label(trusted, "Résoudre l'événement").click().run()
    assert not trusted.exception
    assert any(
        "confiance acquise" in value.lower()
        for value in _text_values(trusted.success)
    )

    hostile = _select_scenario(_app(monkeypatch, tmp_path), "hostile_sire")
    _button_by_label(hostile, "Résoudre l'événement").click().run()
    assert not hostile.exception
    assert any(
        "passif avec cet interlocuteur" in value.lower()
        for value in _text_values(hostile.success)
    )


def test_prestation_fixture_is_visible_in_relationship_state(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "prestation_due")
    snapshot = qa_snapshot(_repo(tmp_path, "prestation_due"), "prestation_due")

    assert snapshot["world"]["boon_count"] >= 1
    rendered_text = _text_values(app.markdown) + _text_values(app.caption)
    assert any("Prestation" in value for value in rendered_text)


def test_narrative_convergence_offers_continue_or_close(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "convergence_ready")
    before = qa_snapshot(_repo(tmp_path, "convergence_ready"), "convergence_ready")

    assert before["character"]["ready_for_convergence"] is True
    assert before["character"]["goal_progress"] == 5
    assert before["progress"]["segment"] == 2
    assert _buttons_by_label(app, "Continuer le chapitre")
    assert _buttons_by_label(app, "Clore le chapitre")
    assert not _buttons_by_label(app, "Faire avancer le monde")


def test_continuing_chapter_advances_cycle_without_resetting_arc(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "convergence_ready")
    _button_by_label(app, "Continuer le chapitre").click().run()
    assert not app.exception

    after = qa_snapshot(_repo(tmp_path, "convergence_ready"), "convergence_ready")
    assert after["progress"]["chapter"] == 1
    assert after["progress"]["segment"] == 3
    assert after["progress"]["year"] == 1435
    assert after["character"]["local_night"] == 1
    assert after["character"]["goal_progress"] == 5
    assert after["character"]["ready_for_convergence"] is False
    time_state = _chronicle_time(tmp_path, "convergence_ready")
    assert time_state is not None
    assert time_state["month"] == 2


def test_closing_chapter_uses_short_infant_ellipse_and_resets_arc(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "convergence_ready")
    _button_by_label(app, "Clore le chapitre").click().run()
    assert not app.exception

    after = qa_snapshot(_repo(tmp_path, "convergence_ready"), "convergence_ready")
    assert after["progress"]["chapter"] == 2
    assert after["progress"]["segment"] == 1
    assert after["progress"]["year"] == 1435
    assert after["character"]["local_night"] == 1
    assert after["character"]["goal_progress"] == 0
    assert after["character"]["ready_for_convergence"] is False
    time_state = _chronicle_time(tmp_path, "convergence_ready")
    assert time_state is not None
    assert time_state["month"] == 3


def test_reset_button_restores_scenario_fixture_and_night_state(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    _button_by_label(app, "Résoudre l'événement").click().run()
    _button_by_label(app, "Terminer la nuit").click().run()
    assert qa_snapshot(_repo(tmp_path, "first_night"), "first_night")["character"]["local_night"] == 2

    app.sidebar.button(key="qa_reset_scenario").click().run()
    assert not app.exception

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["character"]["local_night"] == 1
    assert snapshot["character"]["hunger"] == 2
    state = _night_state(tmp_path, "first_night")
    assert state is not None
    assert state.phase == NightPhase.EVENT
    assert len(state.log) == 0
