from __future__ import annotations

import streamlit as st

from game.actions import ACTION_LABELS
from game.config import DEFAULT_RULES
from game.models import ActionType, Candidate, GameAction, PrimogenVote
from game.politics import determine_opposition_stances
from game.resolution import resolve_night
from game.world import create_initial_game_state, seed_candidates, seed_characters


st.set_page_config(page_title="WoD RPG — Chronique politique", page_icon="🩸", layout="wide")

st.title("WoD RPG — Chronique politique")
st.caption("V0.2 · Brujah · Toreador · Ventrue · nuits politiques asynchrones")

characters = seed_characters()

if "game_state" not in st.session_state:
    st.session_state.game_state = create_initial_game_state()
if "extra_candidates" not in st.session_state:
    st.session_state.extra_candidates = []
if "last_resolution" not in st.session_state:
    st.session_state.last_resolution = None

state = st.session_state.game_state

with st.sidebar:
    st.header("Chronique")
    st.metric("Nuit", state.night)
    st.metric("Stabilité Camarilla", f"{state.camarilla_stability:.0f}%")
    st.metric("Intégrité Mascarade", f"{state.masquerade_integrity:.0f}%")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        prince_name = next(
            (
                candidate.name
                for candidate in seed_candidates() + st.session_state.extra_candidates
                if candidate.id == state.prince_id
            ),
            state.prince_id,
        )
        st.write(f"**Prince :** {prince_name}")
    if st.button("Réinitialiser la chronique", use_container_width=True):
        st.session_state.game_state = create_initial_game_state()
        st.session_state.extra_candidates = []
        st.session_state.last_resolution = None
        st.rerun()

with st.expander("Ajouter un candidat non-Primogène à la Praxis"):
    candidate_name = st.text_input("Nom du candidat")
    if st.button("Ajouter le candidat", disabled=not candidate_name.strip()):
        candidate_id = f"outsider_{len(st.session_state.extra_candidates) + 1}"
        st.session_state.extra_candidates.append(
            Candidate(id=candidate_id, name=candidate_name.strip(), is_primogen=False)
        )
        st.rerun()

candidates = seed_candidates() + st.session_state.extra_candidates
candidate_labels = {candidate.id: candidate.name for candidate in candidates}
primogen_labels = {
    clan_state.clan.primogen_id: characters[clan_state.clan.primogen_id].name
    for clan_state in state.clan_states.values()
}
stances = determine_opposition_stances(state)

st.subheader(f"Préparation de la nuit {state.night}")
st.info(
    f"Chaque clan dispose de {DEFAULT_RULES.actions_per_clan} actions. "
    "L'opposition décide elle-même si elle suit son Primogène ; le joueur peut seulement agir sur l'équilibre politique."
)

cols = st.columns(3)
actions: list[GameAction] = []
votes: dict[str, PrimogenVote] = {}

for col, clan_state in zip(cols, state.clan_states.values()):
    clan = clan_state.clan
    with col:
        primogen = characters[clan.primogen_id]
        st.markdown(f"### {clan.name}")
        st.write(f"**Primogène :** {primogen.name}")
        st.metric("Influence totale", f"{clan.total_influence:.0f}")
        st.write(
            f"Courant du Primogène : **{clan.dominant_current.influence:.0f}**  \n"
            f"Opposition ({clan.opposition_current.leader_name}) : **{clan.opposition_current.influence:.0f}**"
        )
        st.progress(
            clan_state.opposition_loyalty / 100,
            text=f"Loyauté opposition : {clan_state.opposition_loyalty:.0f}/100",
        )

        stance = stances[clan.id]
        if stance.supports_primogen:
            st.success("Opposition : soutien probable au Primogène")
        else:
            ally_name = primogen_labels.get(
                clan_state.opposition_ally_id, clan_state.opposition_ally_id
            )
            st.warning(f"Opposition : dissidence probable · allié : {ally_name}")

        st.markdown("**Relations**")
        for target_id, score in clan_state.relations.items():
            target_name = state.clan_states[target_id].clan.name
            st.caption(f"{target_name} : {score:+.0f}")

        st.markdown("**Actions**")
        action_options = list(ActionType)
        for index in range(DEFAULT_RULES.actions_per_clan):
            action_type = st.selectbox(
                f"Action {index + 1}",
                options=action_options,
                format_func=lambda action: ACTION_LABELS[action],
                key=f"action_{state.night}_{clan.id}_{index}",
            )
            target_clan_id = None
            if action_type == ActionType.DIPLOMACY:
                targets = [cid for cid in state.clan_states if cid != clan.id]
                target_clan_id = st.selectbox(
                    "Clan ciblé",
                    options=targets,
                    format_func=lambda cid: state.clan_states[cid].clan.name,
                    key=f"target_{state.night}_{clan.id}_{index}",
                )
            actions.append(
                GameAction(
                    clan_id=clan.id,
                    action_type=action_type,
                    target_clan_id=target_clan_id,
                )
            )

        if state.prince_id is None:
            candidate_ids = list(candidate_labels)
            default_vote_index = (
                candidate_ids.index(clan.primogen_id)
                if clan.primogen_id in candidate_ids
                else 0
            )
            vote_candidate = st.selectbox(
                "Vote du Primogène pour la Praxis",
                options=candidate_ids,
                index=default_vote_index,
                format_func=lambda cid: candidate_labels[cid],
                key=f"vote_{state.night}_{clan.id}",
            )
            votes[clan.primogen_id] = PrimogenVote(
                primogen_id=clan.primogen_id,
                candidate_id=vote_candidate,
            )
        else:
            st.caption("Un Prince est reconnu : aucun vote de Praxis n'est ouvert cette nuit.")

st.divider()
if st.button(
    f"Résoudre la nuit {state.night}", type="primary", use_container_width=True
):
    resolution = resolve_night(
        state=state,
        actions=actions,
        votes=votes,
        candidates=candidates,
    )
    st.session_state.game_state = resolution.state
    st.session_state.last_resolution = resolution
    st.rerun()

last_resolution = st.session_state.last_resolution
if last_resolution and last_resolution.vote:
    st.subheader("Dernière résolution de Praxis")
    vote = last_resolution.vote
    for candidate_id, score in sorted(
        vote.candidate_totals.items(), key=lambda item: item[1], reverse=True
    ):
        st.write(f"**{candidate_labels.get(candidate_id, candidate_id)}** : {score:.1f}")
    st.caption(
        f"Majorité nécessaire : strictement plus de {vote.recognition_threshold:.1f} "
        f"sur {vote.total_cast_influence:.1f} influence exprimée."
    )
    if vote.disputed:
        st.error("Praxis contestée : aucune majorité politique suffisante.")
    else:
        winner_name = candidate_labels.get(vote.winner_id, vote.winner_id)
        st.success(f"{winner_name} obtient une majorité de reconnaissance.")

st.subheader("Chronique des événements")
if not state.events:
    st.caption("Aucun événement résolu pour le moment.")
else:
    for event in reversed(state.events[-18:]):
        st.write(
            f"**Nuit {event.night} · {event.category.capitalize()}** — {event.message}"
        )

st.caption(
    "V0.2 : l'état est conservé dans la session Streamlit. Une base persistante distante viendra plus tard pour le multijoueur réel."
)
