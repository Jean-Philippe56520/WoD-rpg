from __future__ import annotations

import streamlit as st

from game.models import Candidate, OppositionStance, PrimogenVote
from game.politics import resolve_praxis_vote
from game.world import seed_candidates, seed_characters, seed_clans


st.set_page_config(page_title="WoD RPG — Praxis", page_icon="🩸", layout="wide")

st.title("WoD RPG — Prototype politique")
st.caption("V0.1 · Brujah · Toreador · Ventrue · vote de Praxis et dissidence interne")

characters = seed_characters()
clans = seed_clans()
base_candidates = seed_candidates()

if "extra_candidates" not in st.session_state:
    st.session_state.extra_candidates = []

with st.expander("Ajouter un candidat non-Primogène"):
    candidate_name = st.text_input("Nom du candidat")
    if st.button("Ajouter le candidat", disabled=not candidate_name.strip()):
        candidate_id = f"outsider_{len(st.session_state.extra_candidates) + 1}"
        st.session_state.extra_candidates.append(
            Candidate(id=candidate_id, name=candidate_name.strip(), is_primogen=False)
        )
        st.rerun()

candidates = base_candidates + st.session_state.extra_candidates
candidate_labels = {candidate.id: candidate.name for candidate in candidates}
primogen_labels = {
    clan.primogen_id: characters[clan.primogen_id].name for clan in clans
}

st.subheader("Conseil des Primogènes")
cols = st.columns(3)
stances: dict[str, OppositionStance] = {}
votes: dict[str, PrimogenVote] = {}

for col, clan in zip(cols, clans):
    with col:
        primogen = characters[clan.primogen_id]
        st.markdown(f"### {clan.name}")
        st.write(f"**Primogène :** {primogen.name}")
        st.metric("Influence totale du clan", f"{clan.total_influence:.0f}")
        st.write(
            f"Courant du Primogène : **{clan.dominant_current.influence:.0f}**  \n"
            f"Opposition ({clan.opposition_current.leader_name}) : **{clan.opposition_current.influence:.0f}**"
        )

        support = st.toggle(
            "L'opposition soutient le vote du Primogène",
            value=True,
            key=f"support_{clan.id}",
        )

        ally_id = None
        if not support:
            eligible_allies = {
                pid: label
                for pid, label in primogen_labels.items()
                if pid != clan.primogen_id
            }
            ally_id = st.selectbox(
                "Primogène allié de l'opposition",
                options=list(eligible_allies),
                format_func=lambda pid: eligible_allies[pid],
                key=f"ally_{clan.id}",
            )

        vote_candidate = st.selectbox(
            "Vote du Primogène pour la Praxis",
            options=list(candidate_labels),
            format_func=lambda cid: candidate_labels[cid],
            key=f"vote_{clan.id}",
        )

        stances[clan.id] = OppositionStance(
            clan_id=clan.id,
            supports_primogen=support,
            allied_primogen_id=ally_id,
        )
        votes[clan.primogen_id] = PrimogenVote(
            primogen_id=clan.primogen_id,
            candidate_id=vote_candidate,
        )

st.divider()

if st.button("Résoudre le vote de Praxis", type="primary", use_container_width=True):
    result = resolve_praxis_vote(
        clans=clans,
        stances=stances,
        votes=votes,
        candidates=candidates,
        opposition_transfer_ratio=0.5,
    )

    st.subheader("Résolution")
    weight_cols = st.columns(3)
    for col, clan in zip(weight_cols, clans):
        with col:
            st.metric(
                primogen_labels[clan.primogen_id],
                f"{result.primogen_weights[clan.primogen_id]:.1f}",
                help="Poids politique du vote après éventuelle dissidence interne.",
            )

    if result.opposition_transfers:
        st.markdown("#### Transferts d'influence")
        for transfer in result.opposition_transfers:
            from_clan = next(c for c in clans if c.id == transfer["from_clan_id"])
            st.write(
                f"- Opposition **{from_clan.name}** : **{transfer['amount']:.1f}** d'influence "
                f"renforce le vote de **{primogen_labels[str(transfer['to_primogen_id'])]}**."
            )

    st.markdown("#### Poids reçu par candidat")
    for candidate_id, score in sorted(
        result.candidate_totals.items(), key=lambda item: item[1], reverse=True
    ):
        st.write(f"**{candidate_labels[candidate_id]}** : {score:.1f}")

    if result.disputed:
        st.error("Praxis contestée : aucun candidat ne dispose d'une victoire nette.")
    else:
        winner = next(c for c in candidates if c.id == result.winner_id)
        st.success(f"Praxis attribuée à **{winner.name}** dans cette version du moteur.")
        if winner.is_primogen:
            st.warning(
                "Le vainqueur est Primogène : s'il devient Prince, son siège de Primogène doit devenir vacant. "
                "La succession interne du clan sera gérée dans une prochaine version."
            )

st.info(
    "Règle V0.1 : en cas de dissidence, 50 % de l'influence du courant d'opposition reste dans le poids "
    "du Primogène du clan et 50 % renforce le poids du vote du Primogène allié choisi préalablement."
)
