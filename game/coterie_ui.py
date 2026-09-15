from __future__ import annotations

import streamlit as st

from .coteries import canonical_coteries, coterie_clans, effective_coterie_cohesion
from .models import GameState


def render_coteries_panel(state: GameState, player_clan: str) -> None:
    """Affiche uniquement les informations qu'un clan membre connaît naturellement."""

    visible = [
        coterie
        for coterie in canonical_coteries()
        if player_clan in coterie_clans(state, coterie)
    ]
    if not visible:
        return

    st.divider()
    st.subheader("Coteries transclaniques")
    st.caption(
        "Une coterie n'est pas une faction de clan. Elle crée des loyautés personnelles qui peuvent "
        "faciliter la coopération ou entrer en conflit avec les ordres du Primogène."
    )

    for coterie in visible:
        leader = state.characters.get(coterie.leader_id)
        own_members = [
            state.characters[member_id]
            for member_id in coterie.member_ids
            if member_id in state.characters and state.characters[member_id].clan_id == player_clan
        ]
        cohesion = effective_coterie_cohesion(state, coterie)
        with st.expander(f"{coterie.name} — cohésion {cohesion}/3"):
            st.write(coterie.purpose)
            if leader:
                st.write(f"**Chef :** {leader.name}")
            if own_members:
                st.write(
                    "**Votre clan :** " + ", ".join(character.name for character in own_members)
                )
            st.markdown("**Membres connus**")
            for member_id in coterie.member_ids:
                character = state.characters.get(member_id)
                if character is None:
                    continue
                clan_name = (
                    state.clan_states[character.clan_id].clan.name
                    if character.clan_id in state.clan_states
                    else character.clan_id or "Sans clan"
                )
                role = " — chef" if member_id == coterie.leader_id else ""
                st.write(f"- {character.name} · {clan_name}{role}")

    st.caption(
        "La cohésion est une estimation issue des relations et griefs persistants. Les factions internes, "
        "ambitions et griefs étrangers restent cachés par le brouillard de guerre."
    )
