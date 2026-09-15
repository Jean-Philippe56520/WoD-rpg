from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_starts_without_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    assert not app.exception
