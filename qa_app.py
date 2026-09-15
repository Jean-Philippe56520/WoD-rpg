from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from game.chronicle_ui import render_chronicle_app
from game.editable_repository import EditableSQLiteGameRepository
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


def _database_path(scenario_id: str) -> Path:
    override_dir = os.environ.get("WOD_QA_DATA_DIR", "").strip()
    if override_dir:
        return Path(override_dir).expanduser().resolve() / f"{scenario_id}.sqlite3"
    return qa_default_database_path(scenario_id).expanduser().resolve()


st.sidebar.error("ENVIRONNEMENT QA ISOLÉ — aucune écriture Supabase")
scenario_id = st.sidebar.selectbox(
    "Scénario QA",
    options=[scenario.id for scenario in QA_SCENARIOS],
    format_func=lambda value: next(
        scenario.label for scenario in QA_SCENARIOS if scenario.id == value
    ),
    key="qa_scenario_selector",
)
scenario = next(item for item in QA_SCENARIOS if item.id == scenario_id)
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

render_chronicle_app(
    repository,
    player_id=qa_player_id(scenario_id),
    player_name="QA automatisé",
    backend_label="SQLite QA isolée",
)
