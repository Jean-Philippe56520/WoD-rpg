from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from game.chronicle_ui import render_chronicle_app
from game.editable_repository import EditableSQLiteGameRepository
from game.night_cycle_ui import install_night_cycle_ui
from game.qa_scenarios import (
    QA_SCENARIOS,
    ensure_qa_scenario,
    qa_default_database_path,
    qa_player_id,
    qa_snapshot,
    reset_sqlite_database,
)


st.set_page_config(
    page_title="WoD RPG — QA",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
install_night_cycle_ui()


def _database_path(scenario_id: str) -> Path:
    override_dir = os.environ.get("WOD_QA_DATA_DIR", "").strip()
    if override_dir:
        return Path(override_dir).expanduser().resolve() / f"{scenario_id}.sqlite3"
    return qa_default_database_path(scenario_id).expanduser().resolve()


def _apptest_safe_radio(original_radio):
    """Adapt formatted radios for Streamlit AppTest without changing engine values.

    AppTest serializes rendered option labels. The production view intentionally
    returns stable choice ids through ``format_func``. In QA, expose the labels
    as the widget values and map the selected label back to the original id.
    """

    def radio(label, options, *args, format_func=None, **kwargs):
        raw_options = list(options)
        if format_func is None:
            return original_radio(label, raw_options, *args, **kwargs)
        rendered_options = [format_func(value) for value in raw_options]
        selected_label = original_radio(label, rendered_options, *args, **kwargs)
        return raw_options[rendered_options.index(selected_label)]

    return radio


st.sidebar.error("ENVIRONNEMENT QA ISOLÉ — aucune écriture Supabase")
scenario_by_label = {scenario.label: scenario for scenario in QA_SCENARIOS}
scenario_label = st.sidebar.selectbox(
    "Scénario QA",
    options=list(scenario_by_label),
    key="qa_scenario_selector",
)
scenario = scenario_by_label[scenario_label]
scenario_id = scenario.id
database_path = _database_path(scenario_id)

st.sidebar.caption(scenario.description)
st.sidebar.caption(f"Base locale : {database_path.name}")

if st.sidebar.button(
    "Réinitialiser ce scénario",
    key="qa_reset_scenario",
    use_container_width=True,
):
    reset_sqlite_database(database_path)
    st.rerun()

repository = EditableSQLiteGameRepository(database_path)
ensure_qa_scenario(repository, scenario_id)

st.title("WoD RPG — laboratoire QA")
st.caption(
    "Cette application utilise le même moteur et les mêmes vues de Chronique que la production, "
    "mais uniquement sur une base SQLite dédiée au scénario sélectionné."
)

with st.expander("État QA brut", expanded=False):
    st.json(qa_snapshot(repository, scenario_id))

_original_radio = st.radio
st.radio = _apptest_safe_radio(_original_radio)
try:
    render_chronicle_app(
        repository,
        player_id=qa_player_id(scenario_id),
        player_name="QA automatisé",
        backend_label="SQLite QA isolée",
    )
finally:
    st.radio = _original_radio
