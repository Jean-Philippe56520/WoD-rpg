from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_starts_without_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    assert not app.exception


def test_streamlit_workshop_mode_opens_without_auth_and_can_switch_clan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    app.radio(key="wod_runtime_mode_selector").set_value("workshop").run()
    assert not app.exception
    assert any("MODE ATELIER" in item.value for item in app.warning)

    clan_selector = app.selectbox(key="wod_workshop_clan")
    clan_selector.set_value("toreador").run()
    assert not app.exception
    assert any("Toreador" in item.value for item in app.success)
