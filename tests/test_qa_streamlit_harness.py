from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from game.editable_repository import EditableSQLiteGameRepository
from game.qa_scenarios import QA_SCENARIOS, qa_snapshot


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


def _text_values(elements):
    return [str(item.value) for item in elements]


def test_qa_harness_opens_on_isolated_first_night(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)

    assert app.selectbox(key="qa_scenario_selector").value == _scenario_label("first_night")
    assert any("laboratoire QA" in value for value in _text_values(app.title))
    assert any("Agnès de Chartres" in value for value in _text_values(app.title))
    assert any("aucune écriture Supabase" in value for value in _text_values(app.error))

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


def test_high_hunger_scenario_prioritizes_hunt(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "high_hunger")
    snapshot = qa_snapshot(_repo(tmp_path, "high_hunger"), "high_hunger")

    assert snapshot["character"]["hunger"] == 4
    assert snapshot["situations"][0]["id"].startswith("hunt_")
    assert any("La Faim réclame une décision" in value for value in _text_values(app.markdown))


def test_release_candidate_exposes_emancipation_situation(monkeypatch, tmp_path):
    _select_scenario(_app(monkeypatch, tmp_path), "release_candidate")
    snapshot = qa_snapshot(_repo(tmp_path, "release_candidate"), "release_candidate")

    assert snapshot["character"]["status"] == 1
    assert snapshot["situations"][0]["id"] == "sire_release"


def test_playing_first_situation_advances_real_chronicle_and_records_memory(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)

    _button_by_label(app, "Jouer cette situation").click().run()
    assert not app.exception

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["character"]["local_night"] == 2
    sire_memory = next(
        memory
        for memory in snapshot["memories"]
        if memory["npc_id"] == snapshot["character"]["sire_id"]
    )
    assert sire_memory["last_interaction_year"] == 1435


def test_trusted_and_hostile_sire_change_rendered_difficulty_context(monkeypatch, tmp_path):
    trusted = _select_scenario(_app(monkeypatch, tmp_path), "trusted_sire")
    _button_by_label(trusted, "Jouer cette situation").click().run()
    assert not trusted.exception
    assert any(
        "confiance acquise" in value.lower()
        for value in _text_values(trusted.success)
    )

    hostile = _select_scenario(_app(monkeypatch, tmp_path), "hostile_sire")
    _button_by_label(hostile, "Jouer cette situation").click().run()
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


def test_convergence_button_advances_world_and_resets_local_night(monkeypatch, tmp_path):
    app = _select_scenario(_app(monkeypatch, tmp_path), "convergence_ready")
    before = qa_snapshot(_repo(tmp_path, "convergence_ready"), "convergence_ready")
    assert before["character"]["ready_for_convergence"] is True
    assert before["progress"]["segment"] == 1

    _button_by_label(app, "Faire avancer le monde").click().run()
    assert not app.exception

    after = qa_snapshot(_repo(tmp_path, "convergence_ready"), "convergence_ready")
    assert after["progress"]["segment"] == 2
    assert after["character"]["local_night"] == 1
    assert after["character"]["ready_for_convergence"] is False


def test_reset_button_restores_scenario_fixture(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    _button_by_label(app, "Jouer cette situation").click().run()
    assert qa_snapshot(_repo(tmp_path, "first_night"), "first_night")["character"]["local_night"] == 2

    app.sidebar.button(key="qa_reset_scenario").click().run()
    assert not app.exception

    snapshot = qa_snapshot(_repo(tmp_path, "first_night"), "first_night")
    assert snapshot["character"]["local_night"] == 1
    assert snapshot["character"]["hunger"] == 2
