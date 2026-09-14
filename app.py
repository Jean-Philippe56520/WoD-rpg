from __future__ import annotations

import uuid

import streamlit as st

from game.actions import ACTION_LABELS
from game.config import DEFAULT_RULES
from game.ideology import build_currents, clan_total_influence, primogen_current_id
from game.models import (
    ActionType,
    ClanNightOrders,
    EmbracePetitionOrder,
    GameAction,
    PrimogenVote,
)
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.repository_factory import create_repository
from game.supabase_repository import SupabaseRestError
from game.world import candidates_from_state


st.set_page_config(page_title="WoD RPG - Chronique politique", page_icon="🩸", layout="wide")
st.title("WoD RPG - Chronique politique")
st.caption("V0.5 - partie multijoueur asynchrone - un joueur, un clan, une nuit commune")


@st.cache_resource
def get_repository():
    return create_repository(st.secrets)


try:
    repo, persistence_backend = get_repository()
except (RuntimeError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

service = MultiplayerGameService(repo)
try:
    service.ensure_default_game()
except SupabaseRestError as exc:
    st.error(
        f"Connexion Supabase refusee (HTTP {exc.status_code}). "
        "Verifiez que SUPABASE_URL cible bien le projet WoD-rpg et que "
        "SUPABASE_SECRET_KEY est une cle serveur sb_secret_ (ou l'ancienne cle service_role), "
        "jamais une cle publishable/anon."
    )
    st.stop()
except RuntimeError as exc:
    st.error(f"Supabase est temporairement inaccessible : {exc}")
    st.stop()

player_id = st.query_params.get("player")
if not player_id:
    player_id = uuid.uuid4().hex
    st.query_params["player"] = player_id

try:
    state = repo.get_game_state(DEFAULT_GAME_ID)
    game_info = repo.get_game_info(DEFAULT_GAME_ID)
    assignments = repo.list_assignments(DEFAULT_GAME_ID)
    player_clan = repo.get_player_clan(DEFAULT_GAME_ID, player_id)
except SupabaseRestError as exc:
    st.error(f"Lecture Supabase impossible (HTTP {exc.status_code}).")
    st.stop()

clan_names = {clan_id: clan_state.clan.name for clan_id, clan_state in state.clan_states.items()}

with st.sidebar:
    st.header("Ville")
    st.caption(f"Persistance : {persistence_backend}")
    st.metric("Nuit", game_info["current_night"])
    st.write(f"**Statut :** {game_info['night_status'].value.upper()}")
    st.metric("Stabilite Camarilla", f"{state.camarilla_stability:.0f}%")
    st.metric("Integrite Mascarade", f"{state.masquerade_integrity:.0f}%")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        st.write(f"**Prince :** {state.characters[state.prince_id].name}")
    if st.button("Actualiser", use_container_width=True):
        st.rerun()

if player_clan is None:
    st.subheader("Rejoindre la chronique")
    st.write(
        "Chaque joueur controle un seul clan et incarne son Primogene. "
        "Une fois le clan choisi, la session n'affichera plus les informations internes des autres clans."
    )
    player_name = st.text_input("Nom du joueur", value="Joueur")
    available = [
        clan_id
        for clan_id in game_info["required_clans"]
        if clan_id not in assignments
    ]
    if not available:
        st.warning("Les trois clans sont deja attribues dans cette chronique.")
        st.stop()
    selected_clan = st.selectbox(
        "Clan",
        options=available,
        format_func=lambda cid: clan_names[cid],
    )
    if st.button("Prendre ce clan", type="primary"):
        try:
            service.claim_clan(player_id, player_name, selected_clan)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.stop()

own_clan_state = state.clan_states[player_clan]
own_clan = own_clan_state.clan
own_primogen = state.characters[own_clan.primogen_id]

st.success(f"Vous controlez le clan {own_clan.name} et incarnez {own_primogen.name}, son Primogene.")

submission_statuses = repo.submission_statuses(DEFAULT_GAME_ID)
status_cols = st.columns(len(game_info["required_clans"]))
for col, clan_id in zip(status_cols, game_info["required_clans"]):
    label = "VALIDE" if submission_statuses[clan_id] else "EN PREPARATION"
    controller = assignments.get(clan_id, "non attribue")
    col.metric(clan_names[clan_id], label)
    col.caption(controller)

night_tab, clan_tab, city_tab, elysium_tab, reports_tab = st.tabs(
    ["Ma nuit", "Mon clan", "Ville", "Elysium", "Mes rapports"]
)

with night_tab:
    st.subheader(f"Ordres du clan {own_clan.name} - Nuit {state.night}")
    already_submitted = submission_statuses.get(player_clan, False)
    if already_submitted:
        st.info(
            "Vos ordres sont verrouilles pour cette nuit. La resolution globale aura lieu des que "
            "les autres clans auront egalement valide leurs choix."
        )
    else:
        currents = build_currents(state, player_clan)
        primary_id = primogen_current_id(state, player_clan)
        rival_current_ids = [cid for cid in currents if cid != primary_id]
        candidates = candidates_from_state(state)
        candidate_labels = {candidate.id: candidate.name for candidate in candidates}

        with st.form("night_orders"):
            st.markdown("#### Actions politiques")
            actions: list[GameAction] = []
            options = list(ActionType)
            if not rival_current_ids:
                options.remove(ActionType.RALLY_OPPOSITION)

            for index in range(DEFAULT_RULES.actions_per_clan):
                action_type = st.selectbox(
                    f"Action {index + 1}",
                    options=options,
                    format_func=lambda action: ACTION_LABELS[action],
                    key=f"action_{state.night}_{player_clan}_{index}",
                )
                target_clan_id = None
                target_current_id = None
                if action_type == ActionType.DIPLOMACY:
                    target_clan_id = st.selectbox(
                        "Clan cible",
                        options=[cid for cid in state.clan_states if cid != player_clan],
                        format_func=lambda cid: clan_names[cid],
                        key=f"target_clan_{state.night}_{index}",
                    )
                elif action_type == ActionType.RALLY_OPPOSITION:
                    target_current_id = st.selectbox(
                        "Courant rival a rallier",
                        options=rival_current_ids,
                        format_func=lambda cid: currents[cid].name,
                        key=f"target_current_{state.night}_{index}",
                    )
                actions.append(
                    GameAction(
                        clan_id=player_clan,
                        action_type=action_type,
                        target_clan_id=target_clan_id,
                        target_current_id=target_current_id,
                    )
                )

            vote = None
            if state.prince_id is None:
                st.markdown("#### Praxis")
                candidate_id = st.selectbox(
                    "Vote de votre Primogene",
                    options=list(candidate_labels),
                    index=(
                        list(candidate_labels).index(own_clan.primogen_id)
                        if own_clan.primogen_id in candidate_labels
                        else 0
                    ),
                    format_func=lambda cid: candidate_labels[cid],
                )
                vote = PrimogenVote(own_clan.primogen_id, candidate_id)

            petitions: list[EmbracePetitionOrder] = []
            if state.prince_id is not None:
                st.markdown("#### Demande au Prince")
                st.caption(
                    "Le Primogene ne demande jamais une Etreinte en son nom institutionnel : "
                    "il porte officiellement la demande d'un membre de son clan."
                )
                send_petition = st.checkbox("Porter une demande d'Etreinte cette nuit")
                if send_petition:
                    member_ids = [
                        char.id
                        for char in state.characters.values()
                        if char.clan_id == player_clan
                        and char.id != own_clan.primogen_id
                        and char.id != state.prince_id
                    ]
                    member_id = st.selectbox(
                        "Membre represente",
                        options=member_ids,
                        format_func=lambda cid: state.characters[cid].name,
                    )
                    childe_name = st.text_input("Nom du futur infant")
                    if childe_name.strip():
                        petitions.append(EmbracePetitionOrder(member_id, childe_name.strip()))

            submitted = st.form_submit_button("VALIDER MA NUIT", type="primary", use_container_width=True)
            if submitted:
                try:
                    orders = ClanNightOrders(
                        clan_id=player_clan,
                        actions=tuple(actions),
                        vote=vote,
                        embrace_petitions=tuple(petitions),
                    )
                    resolved = service.submit_orders(player_id, orders)
                    if resolved:
                        st.success("Les trois clans ont valide : la nuit a ete resolue.")
                    else:
                        st.success("Vos ordres sont enregistres. En attente des autres clans.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

with clan_tab:
    st.subheader(f"Clan {own_clan.name}")
    st.metric("Influence totale", f"{clan_total_influence(state, player_clan):.0f}")
    st.write(f"**Primogene :** {own_primogen.name}")
    currents = build_currents(state, player_clan)
    primary_id = primogen_current_id(state, player_clan)
    for current_id, current in sorted(currents.items(), key=lambda item: item[1].influence, reverse=True):
        leader = state.characters[current.leader_id] if current.leader_id else None
        label = "courant du Primogene" if current_id == primary_id else "courant rival"
        with st.container(border=True):
            st.write(
                f"**{current.name}** - {label} - influence **{current.influence:.0f}** - "
                f"chef : **{leader.name if leader else 'aucun'}**"
            )
            if current_id != primary_id:
                st.caption(
                    f"Loyaute : {own_clan_state.current_loyalties.get(current_id, 50):.0f}/100"
                )
            for member_id in current.member_ids:
                member = state.characters[member_id]
                role = "Primogene" if member.is_primogen else "Membre"
                st.caption(
                    f"{member.name} - {role} - influence {member.personal_influence:.0f} - "
                    f"Humanite {member.humanity} - Humanisme {member.humanism:+.0f} - "
                    f"Tradition {member.tradition:+.0f}"
                )

with city_tab:
    st.subheader("Informations publiques")
    st.write(f"**Nuit :** {state.night}")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        st.write(f"**Prince :** {state.characters[state.prince_id].name}")
    st.markdown("#### Conseil des Primogenes")
    for clan_id, clan_state in state.clan_states.items():
        primogen = state.characters[clan_state.clan.primogen_id]
        st.write(f"**{clan_state.clan.name}** : {primogen.name}")
    st.caption("Les membres, courants, loyautes et ordres des autres clans ne sont pas exposes.")

with elysium_tab:
    st.subheader("Elysium")
    st.caption("L'Elysium reste accessible meme apres validation de vos ordres de nuit.")
    messages = repo.list_elysium_messages(DEFAULT_GAME_ID)
    for message in messages:
        st.write(
            f"**{clan_names[message['clan_id']]} - {message['player_name']}** : {message['body']}"
        )
        st.caption(message["created_at"])
    with st.form("elysium_message", clear_on_submit=True):
        body = st.text_input("Message")
        post = st.form_submit_button("Parler a l'Elysium")
        if post:
            try:
                repo.post_elysium_message(DEFAULT_GAME_ID, player_id, player_clan, body)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with reports_tab:
    st.subheader("Rapports de votre clan")
    reports = repo.list_reports(DEFAULT_GAME_ID, player_clan)
    if not reports:
        st.caption("Aucune nuit resolue pour votre clan pour le moment.")
    for report in reports:
        with st.expander(f"Nuit {report.night}", expanded=(report == reports[0])):
            if not report.items:
                st.caption("Aucun evenement dont votre clan ait connaissance.")
            for item in report.items:
                st.write(f"- {item}")

st.caption(
    "V0.5 : les ordres sont persistants dans Supabase en production et resolus globalement "
    "lorsque les trois clans ont valide. SQLite reste disponible pour le developpement local."
)
