from __future__ import annotations

import streamlit as st

from .relationship_memory import (
    events_from_history,
    memories_for_character,
    prestation_balance,
    qualitative_confidence,
    qualitative_relation,
    qualitative_respect,
)


def _prestation_text(balance: int) -> str:
    if balance > 0:
        return f"Vous lui devez un poids de Prestation de {balance}."
    if balance < 0:
        return f"Il ou elle vous doit un poids de Prestation de {-balance}."
    return "Aucune Prestation active entre vous."


def render_relationship_memories(store, character, simulation) -> None:
    st.markdown("### Ceux qui se souviennent de vous")
    st.caption(
        "Ces appréciations appartiennent aux PNJ : elles évoluent selon vos actes. "
        "Elles ne révèlent pas leurs ambitions ou leurs secrets."
    )
    memories = memories_for_character(simulation, character)
    if not memories:
        st.caption("Vous n'avez pas encore laissé de trace relationnelle durable hors de votre lien de sire.")
        return

    history = store.list_history(character.game_id, character.character_id, limit=100)
    for memory in memories:
        npc = simulation.npcs.get(memory.npc_id)
        if npc is None:
            continue
        with st.container(border=True):
            st.markdown(f"**{npc.name}** — {npc.role}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Disposition", qualitative_relation(memory.disposition))
            col2.metric("Confiance", qualitative_confidence(memory.trust))
            col3.metric("Respect", qualitative_respect(memory.respect))
            col4.metric("Crainte", f"{memory.fear}/3")

            st.write(_prestation_text(prestation_balance(simulation, npc.id, character.character_id)))
            if memory.grievance_count:
                st.warning(f"Griefs persistants : {memory.grievance_count}")
            if memory.last_interaction_year:
                st.caption(f"Dernière interaction mémorisée : {memory.last_interaction_year}")

            with st.expander("Ce que cette relation a retenu"):
                for fact in memory.known_facts:
                    st.write(f"- {fact}")
                events = events_from_history(history, npc.id)
                if events:
                    st.markdown("**Interactions récentes**")
                    for event in events[:6]:
                        sign = "+" if event.valence > 0 else "−" if event.valence < 0 else "±"
                        st.write(
                            f"- {sign} Chapitre {event.chapter} · Segment {event.segment} · Nuit {event.night} — "
                            f"{event.summary}"
                        )
                else:
                    st.caption("Aucun souvenir détaillé archivé dans l'historique des nuits.")
