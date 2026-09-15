from __future__ import annotations

import streamlit as st

from .crises import (
    ANARCHS,
    active_crises,
    crisis_clues,
    crisis_public_description,
    crisis_stage_label,
    crisis_title,
    current_crisis_intel,
)
from .models import GameState


def render_crises_panel(state: GameState, clan_id: str) -> None:
    st.markdown("### Crises en cours")
    crises = active_crises(state)
    if not crises:
        st.caption(
            "Aucune crise active. Les pressions extérieures peuvent faire apparaître une situation "
            "concrète si la ville reste vulnérable."
        )
        return

    for crisis in crises:
        faction_label = "Anarchs" if crisis.faction == ANARCHS else "Chasseurs mortels"
        intel = current_crisis_intel(state, crisis.id, clan_id)
        with st.container(border=True):
            st.markdown(f"#### {crisis_title(state, crisis)}")
            stage_col, faction_col, deadline_col = st.columns(3)
            stage_col.metric("Stade", crisis_stage_label(crisis.stage))
            faction_col.metric("Menace", faction_label)
            deadline_col.metric("Escalade", f"Nuit {crisis.next_escalation_night}")
            st.write(crisis_public_description(crisis))
            st.caption(
                "Sans progrès suffisant avant l'échéance, la crise monte d'un stade. "
                "Au stade III, l'échec produit une conséquence majeure."
            )
            st.write(f"**Renseignement de votre clan : {intel}/2**")
            clues = crisis_clues(crisis, intel)
            if not clues:
                st.caption(
                    "Aucun détail fiable. Utilisez `Enquêter sur la crise` dans « Une action par vampire » "
                    "pour obtenir des informations et faciliter les interventions suivantes."
                )
            for clue in clues:
                st.write(f"- {clue}")

            if crisis.faction == ANARCHS:
                st.caption(
                    "Approches généralement efficaces : infiltration ou négociation. La contenir par les "
                    "réseaux d'autorité est possible, mais plus difficile."
                )
            else:
                st.caption(
                    "Approche généralement efficace : contenir/étouffer les traces. Infiltrer ou négocier "
                    "avec les chasseurs est nettement plus difficile."
                )
