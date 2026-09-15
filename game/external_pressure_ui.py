from __future__ import annotations

import streamlit as st

from .external_pressures import current_external_pressures
from .models import GameState


def _label(value: int) -> str:
    if value <= 0:
        return "CALME"
    if value <= 2:
        return "FAIBLE"
    if value <= 4:
        return "ÉLEVÉE"
    return "CRITIQUE"


def render_external_pressure_panel(state: GameState, player_clan_id: str) -> None:
    """Affiche des signaux publics de menace, sans information clanique privée."""

    pressure = current_external_pressures(state)
    with st.expander("Pressions extérieures", expanded=False):
        st.caption(
            "Une Camarilla instable ouvre de l'espace aux Anarchs. Une Mascarade fragilisée "
            "attire l'attention des chasseurs mortels. Ces pressions persistent d'une nuit à l'autre."
        )
        anarch_col, hunters_col = st.columns(2)
        anarch_col.metric(
            "Agitation anarch",
            _label(pressure.anarch_pressure),
            help=f"Pression interne du moteur : {pressure.anarch_pressure}/10",
        )
        hunters_col.metric(
            "Attention des chasseurs",
            _label(pressure.hunter_attention),
            help=f"Attention interne du moteur : {pressure.hunter_attention}/10",
        )
        if pressure.anarch_pressure >= 3:
            st.warning("Les Anarchs disposent d'une fenêtre politique exploitable dans la ville.")
        if pressure.hunter_attention >= 3:
            st.warning("La surveillance mortelle approche d'un niveau susceptible de produire un incident.")
