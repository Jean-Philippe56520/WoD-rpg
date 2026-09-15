from __future__ import annotations

import streamlit as st

from .hunger import active_hunting_access_domains, hunger_penalty
from .models import GameState


def render_hunger_panel(state: GameState, player_clan: str) -> None:
    members = sorted(
        (
            character
            for character in state.characters.values()
            if character.clan_id == player_clan and character.id != state.prince_id
        ),
        key=lambda character: (-character.hunger, character.name),
    )
    if not members:
        return

    st.divider()
    st.subheader("Faim et chasse")
    st.caption(
        "Un droit de chasse ou un Domaine personnel permet une alimentation de routine. "
        "Sans accès légal, la Faim monte chaque nuit ; le braconnage peut servir d'urgence."
    )

    for character in members:
        domains = active_hunting_access_domains(state, character.id)
        domain_names = [state.domains[domain_id].name for domain_id in domains]
        penalty = hunger_penalty(character.hunger)
        with st.container(border=True):
            cols = st.columns(2)
            cols[0].write(f"**{character.name}**")
            cols[1].metric("Faim", f"{character.hunger}/5")
            if domain_names:
                st.caption("Chasse légale : " + " · ".join(domain_names))
            else:
                st.warning("Aucun accès de chasse légal connu pour cette nuit.")
            if penalty:
                st.caption(
                    f"Pression de la Bête : -{penalty} aux caractéristiques effectives Sociales et Mentales."
                )
