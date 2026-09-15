from __future__ import annotations

import streamlit as st

from .diplomatic_pacts import ACTIVE, BROKEN, EXPIRED, list_diplomatic_pacts
from .models import GameState


STATUS_LABELS = {
    ACTIVE: "ACTIF",
    BROKEN: "ROMPU",
    EXPIRED: "ÉCHU",
}


def render_diplomatic_pacts_panel(state: GameState, player_clan_id: str) -> None:
    """Affiche les pactes publics sans exposer d'information privée supplémentaire."""

    pacts = list_diplomatic_pacts(state)
    with st.expander("Accords diplomatiques", expanded=False):
        st.caption(
            "Deux Primogènes qui choisissent réciproquement Diplomatie la même nuit "
            "formalisent un pacte de coopération. Une manœuvre hostile exécutée entre "
            "leurs clans le rompt automatiquement."
        )
        if not pacts:
            st.caption("Aucun pacte diplomatique n'a encore été formalisé.")
            return

        for pact in pacts:
            clan_a = state.clan_states[pact.clan_a_id].clan.name
            clan_b = state.clan_states[pact.clan_b_id].clan.name
            own_marker = " · votre clan" if pact.involves(player_clan_id) else ""
            st.write(
                f"**{clan_a} ↔ {clan_b}** · {STATUS_LABELS[pact.status]}{own_marker}"
            )
            if pact.status == ACTIVE:
                st.caption(
                    f"Conclu nuit {pact.created_night} · valable jusqu'à la fin de la nuit "
                    f"{pact.expires_night}."
                )
            elif pact.status == BROKEN:
                breaking_name = state.clan_states[pact.broken_by_clan_id].clan.name
                st.caption(
                    f"Conclu nuit {pact.created_night} · rompu nuit {pact.resolved_night} "
                    f"par {breaking_name}."
                )
            else:
                st.caption(
                    f"Conclu nuit {pact.created_night} · arrivé à échéance après la nuit "
                    f"{pact.expires_night}."
                )
