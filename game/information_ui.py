from __future__ import annotations

import streamlit as st

from .information import rumor_views
from .models import GameState


_STATUS_LABELS = {
    "unverified": "NON VÉRIFIÉE",
    "confirmed": "CONFIRMÉE",
    "disproved": "DÉMENTIE",
}


def render_information_panel(state: GameState, player_clan: str) -> None:
    rumors = rumor_views(state, player_clan)
    st.divider()
    st.subheader("Rumeurs et renseignements")
    st.caption(
        "Une première source n'est pas une vérité. Une enquête ultérieure sur le même clan peut "
        "corroborer ou démentir une rumeur. La vérité interne n'est jamais affichée avant vérification."
    )

    if not rumors:
        st.caption("Aucune rumeur exploitable n'a encore été recueillie par votre clan.")
        return

    for rumor in rumors:
        subject = state.characters.get(rumor.subject_id)
        subject_name = subject.name if subject else rumor.subject_id
        status = _STATUS_LABELS[rumor.status]
        with st.container(border=True):
            st.write(f"**{subject_name}** — {status}")
            st.write(rumor.claim)
            st.caption(
                f"Première source : nuit {rumor.created_night} · confiance {rumor.confidence}/2"
            )
            if rumor.status == "confirmed":
                st.success("La seconde source confirme cette information.")
            elif rumor.status == "disproved":
                st.warning("La seconde source indique que cette information était fausse ou trompeuse.")
