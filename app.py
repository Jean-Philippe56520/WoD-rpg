from __future__ import annotations

import streamlit as st

from game.actions import ACTION_LABELS
from game.config import DEFAULT_RULES
from game.embrace import create_embrace_request, decide_embrace_request
from game.models import (
    ActionType,
    Candidate,
    EmbraceStatus,
    GameAction,
    PrimogenPosition,
    PrimogenVote,
)
from game.politics import determine_opposition_stances
from game.resolution import resolve_night
from game.world import candidates_from_state, create_initial_game_state


st.set_page_config(page_title="WoD RPG - Chronique politique", page_icon="🩸", layout="wide")
st.title("WoD RPG - Chronique politique")
st.caption("V0.3 - Brujah - Toreador - Ventrue - Prince, successions et Etreintes")

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
    st.metric("Stabilite Camarilla", f"{state.camarilla_stability:.0f}%")
    st.metric("Integrite Mascarade", f"{state.masquerade_integrity:.0f}%")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        prince = state.characters[state.prince_id]
        st.write(f"**Prince :** {prince.name}")
        st.metric("Capital politique", f"{state.prince_political_capital:.0f}")
    if st.button("Reinitialiser la chronique", use_container_width=True):
        st.session_state.game_state = create_initial_game_state()
        st.session_state.extra_candidates = []
        st.session_state.last_resolution = None
        st.rerun()

if state.prince_id is None:
    with st.expander("Ajouter un candidat exterieur a la Praxis"):
        candidate_name = st.text_input("Nom du candidat")
        if st.button("Ajouter le candidat", disabled=not candidate_name.strip()):
            candidate_id = f"outsider_{len(st.session_state.extra_candidates) + 1}"
            st.session_state.extra_candidates.append(
                Candidate(id=candidate_id, name=candidate_name.strip(), is_primogen=False)
            )
            st.rerun()

base_candidates = candidates_from_state(state)
candidates = base_candidates + st.session_state.extra_candidates
candidate_labels = {candidate.id: candidate.name for candidate in candidates}
for character in state.characters.values():
    candidate_labels.setdefault(character.id, character.name)

primogen_labels = {
    clan_state.clan.primogen_id: state.characters[clan_state.clan.primogen_id].name
    for clan_state in state.clan_states.values()
}
stances = determine_opposition_stances(state)

night_tab, clans_tab, prince_tab, chronicle_tab = st.tabs(
    ["Nuit politique", "Clans", "Cour du Prince", "Chronique"]
)

with night_tab:
    st.subheader(f"Preparation de la nuit {state.night}")
    st.info(
        f"Chaque clan dispose de {DEFAULT_RULES.actions_per_clan} actions. "
        "L'opposition choisit elle-meme si elle suit son Primogene."
    )
    cols = st.columns(3)
    actions: list[GameAction] = []
    votes: dict[str, PrimogenVote] = {}

    for col, clan_state in zip(cols, state.clan_states.values()):
        clan = clan_state.clan
        primogen = state.characters[clan.primogen_id]
        with col:
            st.markdown(f"### {clan.name}")
            st.write(f"**Primogene :** {primogen.name}")
            st.metric("Influence totale", f"{clan.total_influence:.0f}")
            st.write(
                f"Courant du Primogene : **{clan.dominant_current.influence:.0f}**  \n"
                f"Opposition ({clan.opposition_current.leader_name}) : "
                f"**{clan.opposition_current.influence:.0f}**"
            )
            st.progress(
                clan_state.opposition_loyalty / 100,
                text=f"Loyaute opposition : {clan_state.opposition_loyalty:.0f}/100",
            )
            stance = stances[clan.id]
            if stance.supports_primogen:
                st.success("Opposition : soutien probable")
            else:
                ally_name = primogen_labels.get(
                    clan_state.opposition_ally_id, clan_state.opposition_ally_id
                )
                st.warning(f"Opposition : dissidence probable - allie : {ally_name}")

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
                        "Clan cible",
                        options=targets,
                        format_func=lambda cid: state.clan_states[cid].clan.name,
                        key=f"target_{state.night}_{clan.id}_{index}",
                    )
                actions.append(GameAction(clan.id, action_type, target_clan_id))

            if state.prince_id is None:
                candidate_ids = list(candidate_labels)
                default_vote_index = candidate_ids.index(clan.primogen_id)
                vote_candidate = st.selectbox(
                    "Vote du Primogene pour la Praxis",
                    options=candidate_ids,
                    index=default_vote_index,
                    format_func=lambda cid: candidate_labels[cid],
                    key=f"vote_{state.night}_{clan.id}",
                )
                votes[clan.primogen_id] = PrimogenVote(clan.primogen_id, vote_candidate)
            else:
                st.caption("Un Prince est reconnu : aucun vote de Praxis cette nuit.")

    if st.button(f"Resoudre la nuit {state.night}", type="primary", use_container_width=True):
        resolution = resolve_night(state, actions, votes, candidates)
        st.session_state.game_state = resolution.state
        st.session_state.last_resolution = resolution
        st.rerun()

    last_resolution = st.session_state.last_resolution
    if last_resolution and last_resolution.vote:
        st.divider()
        st.subheader("Derniere resolution de Praxis")
        vote = last_resolution.vote
        for candidate_id, score in sorted(
            vote.candidate_totals.items(), key=lambda item: item[1], reverse=True
        ):
            if score > 0:
                st.write(f"**{candidate_labels.get(candidate_id, candidate_id)}** : {score:.1f}")
        st.caption(
            f"Majorite necessaire : strictement plus de {vote.recognition_threshold:.1f} "
            f"sur {vote.total_cast_influence:.1f}."
        )

with clans_tab:
    st.subheader("Equilibres internes")
    for clan_state in state.clan_states.values():
        clan = clan_state.clan
        primogen = state.characters[clan.primogen_id]
        with st.expander(f"{clan.name} - Primogene : {primogen.name}", expanded=True):
            members = [
                character
                for character in state.characters.values()
                if character.clan_id == clan.id
            ]
            for member in sorted(members, key=lambda char: char.personal_influence, reverse=True):
                role = "Primogene" if member.is_primogen else "Membre"
                current = (
                    "courant du Primogene"
                    if member.current_id == clan.dominant_current.id
                    else "opposition"
                )
                st.write(
                    f"**{member.name}** - {role} - {current} - "
                    f"influence {member.personal_influence:.0f} - Humanite {member.humanity} - "
                    f"ambition {member.ambition:.0f}"
                )
            st.caption(
                f"Allie politique de l'opposition : "
                f"{primogen_labels.get(clan_state.opposition_ally_id, clan_state.opposition_ally_id)}"
            )

with prince_tab:
    if state.prince_id is None:
        st.info("Aucun Prince n'est reconnu. La Cour du Prince est inactive.")
    else:
        prince = state.characters[state.prince_id]
        st.subheader(f"Cour de {prince.name}")
        metrics = st.columns(2)
        metrics[0].metric("Capital politique", f"{state.prince_political_capital:.0f}")
        metrics[1].metric("Demandes d'Etreinte", len(state.embrace_requests))

        st.markdown("#### Relations du Prince avec les clans")
        for clan_id, relation in state.prince_relations.items():
            st.write(f"**{state.clan_states[clan_id].clan.name}** : {relation:+.0f}")

        st.markdown("#### Nouvelle demande d'Etreinte")
        requester_ids = [
            char.id
            for char in state.characters.values()
            if char.clan_id in state.clan_states and char.id != state.prince_id
        ]
        requester_id = st.selectbox(
            "Vampire demandeur",
            options=requester_ids,
            format_func=lambda cid: state.characters[cid].name,
            key="embrace_requester",
        )
        childe_name = st.text_input("Nom du futur infant", key="embrace_childe")
        position = st.selectbox(
            "Position du Primogene du clan",
            options=list(PrimogenPosition),
            format_func=lambda item: {
                PrimogenPosition.SUPPORT: "Soutient la demande",
                PrimogenPosition.NEUTRAL: "Neutre",
                PrimogenPosition.OPPOSE: "S'oppose a la demande",
            }[item],
        )
        if st.button("Soumettre la demande", disabled=not childe_name.strip()):
            try:
                st.session_state.game_state = create_embrace_request(
                    state, requester_id, childe_name, position
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        st.markdown("#### Dossiers")
        if not state.embrace_requests:
            st.caption("Aucune demande enregistree.")
        for request in reversed(list(state.embrace_requests.values())):
            requester = state.characters[request.requester_id]
            status_label = {
                EmbraceStatus.PENDING: "EN ATTENTE",
                EmbraceStatus.APPROVED: "AUTORISEE",
                EmbraceStatus.REFUSED: "REFUSEE",
            }[request.status]
            with st.container(border=True):
                st.write(
                    f"**{requester.name} -> {request.proposed_childe_name}**  \n"
                    f"Clan : {state.clan_states[requester.clan_id].clan.name} - "
                    f"cout : **{request.political_cost:.0f}** - statut : **{status_label}**"
                )
                st.caption(f"Position du Primogene : {request.primogen_position.value}")
                if request.status == EmbraceStatus.PENDING:
                    approve_col, refuse_col = st.columns(2)
                    if approve_col.button("Autoriser", key=f"approve_{request.id}", use_container_width=True):
                        try:
                            st.session_state.game_state = decide_embrace_request(
                                state, request.id, True
                            )
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                    if refuse_col.button("Refuser", key=f"refuse_{request.id}", use_container_width=True):
                        st.session_state.game_state = decide_embrace_request(
                            state, request.id, False
                        )
                        st.rerun()

with chronicle_tab:
    st.subheader("Chronique des evenements")
    if not state.events:
        st.caption("Aucun evenement resolu pour le moment.")
    else:
        for event in reversed(state.events[-30:]):
            st.write(f"**Nuit {event.night} - {event.category.capitalize()}** - {event.message}")

st.caption(
    "V0.3 : etat conserve dans la session Streamlit. La persistance multijoueur distante viendra dans une version ulterieure."
)
