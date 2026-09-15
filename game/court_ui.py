from __future__ import annotations

import streamlit as st

from .court import current_court_issue, prince_policy_summary
from .models import GameState


def render_court_panel(state: GameState, player_clan: str) -> None:
    """Expose la ligne politique du Prince et le dossier actuellement prioritaire."""

    if not state.prince_id or state.prince_id not in state.characters:
        return

    prince = state.characters[state.prince_id]
    st.divider()
    st.subheader("Cour du Prince")
    st.write(f"**Prince :** {prince.name}")
    policy = prince_policy_summary(state)
    if policy:
        st.caption(f"Ligne politique lisible : {policy}")

    relation = state.prince_relations.get(player_clan, 0.0)
    capital_col, relation_col = st.columns(2)
    capital_col.metric("Capital politique du Prince", f"{state.prince_political_capital:.0f}")
    relation_col.metric("Relation avec votre clan", f"{relation:+.0f}")

    issue = current_court_issue(state)
    if issue is None:
        st.caption("Aucun dossier de Cour prioritaire n'exige actuellement d'arbitrage.")
        return

    with st.container(border=True):
        st.markdown(f"### {issue.title}")
        st.write(issue.description)
        st.caption(
            "Ce dossier sera arbitré pendant la résolution de nuit selon les relations, le Statut, "
            "la réputation, les précédents et la ligne politique du Prince. Un litige territorial "
            "n'est traité qu'à partir de la nuit suivant son apparition, afin de laisser une fenêtre diplomatique."
        )
