from __future__ import annotations

import streamlit as st

from .agency import member_reliability
from .factions import effective_relation_to_primogen
from .models import ClanFactionSide, GameState
from .social_politics import active_grievance_score


_LABELS = {
    "direct": "DIRECTE",
    "forte": "FORTE",
    "conditionnelle": "CONDITIONNELLE",
    "faible": "FAIBLE",
    "hors_clan": "—",
}


def render_agency_panel(state: GameState, player_clan: str) -> None:
    clan_state = state.clan_states[player_clan]
    primogen_id = clan_state.clan.primogen_id
    members = sorted(
        (
            character
            for character in state.characters.values()
            if character.clan_id == player_clan and character.id != state.prince_id
        ),
        key=lambda character: (character.id != primogen_id, character.name),
    )

    st.divider()
    st.subheader("Autorité du Primogène")
    st.caption(
        "Une faction indique un camp politique, pas une obéissance absolue. La fiabilité d'une mission "
        "dépend de la relation effective, des griefs et de l'ambition propre du vampire."
    )

    for member in members:
        reliability = member_reliability(state, member.id)
        side = clan_state.faction_memberships.get(member.id, ClanFactionSide.PRIMOGEN)
        grievance = (
            0 if member.id == primogen_id else active_grievance_score(state, member.id, primogen_id)
        )
        relation = 2 if member.id == primogen_id else effective_relation_to_primogen(state, member.id)
        with st.container(border=True):
            st.write(f"**{member.name}** — fiabilité {_LABELS[reliability]}")
            st.caption(
                f"Faction {side.value} · relation effective {relation:+d} · griefs envers le Primogène {grievance} "
                f"· ambition : {member.political_ambition.value}"
            )
