from __future__ import annotations

import uuid

import streamlit as st

from game.actions import ACTION_LABELS
from game.auth import (
    DEFAULT_SUPABASE_PUBLISHABLE_KEY,
    AuthError,
    AuthSession,
    SupabaseAuthClient,
)
from game.coteries import (
    clan_total_influence,
    coterie_influence,
    effective_relation_to_primogen,
    ideology_relation_modifier,
    initialize_coteries,
)
from game.models import (
    ActionType,
    ClanNightOrders,
    CoterieSide,
    EmbracePetitionOrder,
    GameAction,
    NightStatus,
    PrimogenVote,
)
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.repository_factory import create_repository
from game.supabase_repository import SupabaseRestError
from game.world import candidates_from_state


st.set_page_config(page_title="WoD RPG - Chronique politique", page_icon="🩸", layout="wide")
st.title("WoD RPG - Chronique politique")
st.caption("V0.8 - coteries, relations personnelles et une action par vampire")

AUTH_SESSION_KEY = "wod_auth_session"
LOCAL_PLAYER_KEY = "wod_local_player_id"

BLOOD_RANK_LABELS = {
    "newborn": "Nouveau-né",
    "ancilla": "Ancilla",
    "elder": "Ancien",
}

DISCIPLINE_LABELS = {
    "auspex": "Auspex",
    "celerite": "Célérité",
    "domination": "Domination",
    "force_d_ame": "Force d'âme",
    "presence": "Présence",
    "puissance": "Puissance",
}

COTERIE_LABELS = {
    CoterieSide.PRIMOGEN: "Coterie du Primogène",
    CoterieSide.OPPOSITION: "Opposition",
}

V08_ACTIONS = (
    ActionType.BUILD_INFLUENCE,
    ActionType.DIPLOMACY,
    ActionType.CONSOLIDATE_RELATION,
    ActionType.RECRUIT,
    ActionType.UNDERMINE,
    ActionType.POACH,
    ActionType.INVESTIGATE,
)


@st.cache_resource
def get_repository():
    return create_repository(st.secrets)


@st.cache_resource
def get_auth_client() -> SupabaseAuthClient:
    url = str(st.secrets.get("SUPABASE_URL", "")).strip()
    key = str(
        st.secrets.get("SUPABASE_PUBLISHABLE_KEY", DEFAULT_SUPABASE_PUBLISHABLE_KEY)
    ).strip()
    return SupabaseAuthClient(url, key)


def render_authentication(auth: SupabaseAuthClient) -> None:
    st.subheader("Connexion à la chronique")
    st.write(
        "Votre compte identifie durablement votre joueur. En vous reconnectant avec le même "
        "compte, vous retrouverez automatiquement votre clan."
    )
    login_tab, signup_tab = st.tabs(["Connexion", "Créer un compte"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Mot de passe", type="password", key="login_password")
            submitted = st.form_submit_button(
                "Se connecter", type="primary", use_container_width=True
            )
        if submitted:
            try:
                session = auth.sign_in(email, password)
                st.session_state[AUTH_SESSION_KEY] = session
                st.rerun()
            except (AuthError, ValueError) as exc:
                st.error(str(exc))

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Mot de passe", type="password", key="signup_password")
            password_confirm = st.text_input(
                "Confirmer le mot de passe",
                type="password",
                key="signup_password_confirm",
            )
            submitted = st.form_submit_button("Créer mon compte", use_container_width=True)
        if submitted:
            if password != password_confirm:
                st.error("Les deux mots de passe ne correspondent pas.")
            else:
                try:
                    session = auth.sign_up(email, password)
                    if session:
                        st.session_state[AUTH_SESSION_KEY] = session
                        st.rerun()
                    st.success(
                        "Compte créé. Si Supabase vous a envoyé un email de confirmation, "
                        "validez-le puis revenez ici pour vous connecter."
                    )
                except (AuthError, ValueError) as exc:
                    st.error(str(exc))
    st.stop()


def describe_orders(orders: ClanNightOrders, state) -> list[str]:
    lines: list[str] = []
    for index, action in enumerate(orders.actions, start=1):
        actor_id = action.actor_character_id or state.clan_states[orders.clan_id].clan.primogen_id
        actor = state.characters.get(actor_id)
        text = f"Action {index} : {actor.name if actor else actor_id} — {ACTION_LABELS[action.action_type]}"
        if action.target_character_id:
            target = state.characters.get(action.target_character_id)
            text += f" → {target.name if target else action.target_character_id}"
        elif action.target_clan_id:
            text += f" → {state.clan_states[action.target_clan_id].clan.name}"
        lines.append(text)
    if orders.vote:
        candidate = state.characters.get(orders.vote.candidate_id)
        lines.append(f"Vote de Praxis : {candidate.name if candidate else orders.vote.candidate_id}")
    for petition in orders.embrace_petitions:
        member = state.characters[petition.member_id]
        lines.append(
            f"Demande d'Étreinte : {member.name} souhaite Étreindre {petition.proposed_childe_name}"
        )
    return lines


def format_score_map(values: dict[str, int], labels: dict[str, str] | None = None) -> str:
    labels = labels or {}
    if not values:
        return "Aucun"
    return " · ".join(f"{labels.get(name, name)} {score}" for name, score in values.items())


def known_foreign_members(state, clan_id: str, minimum_level: int = 1) -> list[str]:
    intel = state.clan_states[clan_id].known_character_intel
    return [
        character_id
        for character_id, level in intel.items()
        if level >= minimum_level
        and character_id in state.characters
        and state.characters[character_id].clan_id != clan_id
        and character_id != state.prince_id
    ]


def foreign_primogens(state, clan_id: str) -> list[str]:
    return [
        clan_state.clan.primogen_id
        for other_clan_id, clan_state in state.clan_states.items()
        if other_clan_id != clan_id
    ]


try:
    repo, persistence_backend = get_repository()
except (RuntimeError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

service = MultiplayerGameService(repo)
try:
    service.ensure_default_game()
except SupabaseRestError as exc:
    st.error(f"Connexion Supabase refusée (HTTP {exc.status_code}) : {exc.api_message}")
    st.stop()
except RuntimeError as exc:
    st.error(f"Supabase est temporairement inaccessible : {exc}")
    st.stop()

auth: SupabaseAuthClient | None = None
account_email: str | None = None
if persistence_backend == "Supabase":
    try:
        auth = get_auth_client()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    session = st.session_state.get(AUTH_SESSION_KEY)
    if session is not None and not isinstance(session, AuthSession):
        st.session_state.pop(AUTH_SESSION_KEY, None)
        session = None
    if session is not None:
        try:
            session = auth.validate(session)
            st.session_state[AUTH_SESSION_KEY] = session
        except AuthError:
            st.session_state.pop(AUTH_SESSION_KEY, None)
            session = None
    if session is None:
        render_authentication(auth)
    player_id = session.user_id
    account_email = session.email
else:
    if LOCAL_PLAYER_KEY not in st.session_state:
        st.session_state[LOCAL_PLAYER_KEY] = uuid.uuid4().hex
    player_id = st.session_state[LOCAL_PLAYER_KEY]

try:
    state = repo.get_game_state(DEFAULT_GAME_ID)
    initialize_coteries(state)
    game_info = repo.get_game_info(DEFAULT_GAME_ID)
    assignments = repo.list_assignments(DEFAULT_GAME_ID)
    player_clan = repo.get_player_clan(DEFAULT_GAME_ID, player_id)
except SupabaseRestError as exc:
    st.error(f"Lecture Supabase impossible (HTTP {exc.status_code}) : {exc.api_message}")
    st.stop()

clan_names = {clan_id: clan_state.clan.name for clan_id, clan_state in state.clan_states.items()}

with st.sidebar:
    st.header("Ville")
    st.caption(f"Persistance : {persistence_backend}")
    if account_email:
        st.caption(f"Compte : {account_email}")
    st.metric("Nuit", game_info["current_night"])
    st.write(f"**Statut :** {game_info['night_status'].value.upper()}")
    st.metric("Stabilité Camarilla", f"{state.camarilla_stability:.0f}%")
    st.metric("Intégrité Mascarade", f"{state.masquerade_integrity:.0f}%")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        st.write(f"**Prince :** {state.characters[state.prince_id].name}")
    if st.button("Actualiser", use_container_width=True):
        st.rerun()
    if auth is not None and st.button("Se déconnecter", use_container_width=True):
        current_session = st.session_state.get(AUTH_SESSION_KEY)
        try:
            if isinstance(current_session, AuthSession):
                auth.sign_out(current_session.access_token)
        except AuthError:
            pass
        st.session_state.pop(AUTH_SESSION_KEY, None)
        st.rerun()

if player_clan is None:
    st.subheader("Lobby de la chronique")
    st.write(
        "Chaque compte contrôle un seul clan et incarne son Primogène actuel. "
        "Le choix est persistant : après reconnexion, vous retrouverez automatiquement votre clan."
    )
    lobby_cols = st.columns(len(game_info["required_clans"]))
    for col, clan_id in zip(lobby_cols, game_info["required_clans"]):
        controller = assignments.get(clan_id)
        col.metric(clan_names[clan_id], "Occupé" if controller else "Disponible")
        col.caption(controller or "Aucun joueur")

    default_name = account_email.split("@", 1)[0] if account_email else "Joueur"
    player_name = st.text_input("Nom affiché", value=default_name)
    available = [cid for cid in game_info["required_clans"] if cid not in assignments]
    if not available:
        st.warning("Les trois clans sont déjà attribués dans cette chronique.")
        st.stop()
    selected_clan = st.selectbox("Clan", options=available, format_func=lambda cid: clan_names[cid])
    if st.button("Prendre ce clan", type="primary", use_container_width=True):
        try:
            service.claim_clan(player_id, player_name, selected_clan)
            st.rerun()
        except (ValueError, SupabaseRestError) as exc:
            st.error(str(exc))
    st.stop()

own_clan_state = state.clan_states[player_clan]
own_clan = own_clan_state.clan
own_primogen = state.characters[own_clan.primogen_id]

st.success(f"Vous contrôlez le clan {own_clan.name} et incarnez {own_primogen.name}, son Primogène.")

submission_statuses = repo.submission_statuses(DEFAULT_GAME_ID)
status_cols = st.columns(len(game_info["required_clans"]))
for col, clan_id in zip(status_cols, game_info["required_clans"]):
    label = "VALIDÉ" if submission_statuses[clan_id] else "EN PRÉPARATION"
    controller = assignments.get(clan_id, "non attribué")
    col.metric(clan_names[clan_id], label)
    col.caption(controller)

night_tab, clan_tab, city_tab, elysium_tab, reports_tab = st.tabs(
    ["Ma nuit", "Mon clan", "Ville", "Elysium", "Mes rapports"]
)

with night_tab:
    st.subheader(f"Ordres du clan {own_clan.name} - Nuit {state.night}")
    already_submitted = submission_statuses.get(player_clan, False)
    if already_submitted:
        st.info("Vos ordres sont persistants et verrouillés. Ils seront résolus avec ceux des autres clans.")
        submitted_orders = repo.get_submitted_orders(DEFAULT_GAME_ID, player_clan)
        if submitted_orders:
            with st.container(border=True):
                st.markdown("#### Ordres validés")
                for line in describe_orders(submitted_orders, state):
                    st.write(f"- {line}")
        if game_info["night_status"] == NightStatus.OPEN:
            st.caption(
                "Tant que tous les clans n'ont pas validé et que la résolution n'a pas commencé, "
                "vous pouvez reprendre vos ordres."
            )
            if st.button("Annuler ma validation", use_container_width=True):
                try:
                    service.withdraw_orders(player_id)
                    st.success("Vos ordres ont été retirés. Vous pouvez les préparer à nouveau.")
                    st.rerun()
                except (ValueError, SupabaseRestError) as exc:
                    st.error(str(exc))
        else:
            st.caption("La résolution de cette nuit a commencé : les ordres ne sont plus modifiables.")
    else:
        candidates = candidates_from_state(state)
        candidate_labels = {candidate.id: candidate.name for candidate in candidates}
        active_members = sorted(
            [
                character
                for character in state.characters.values()
                if character.clan_id == player_clan and character.id != state.prince_id
            ],
            key=lambda character: (
                character.id != own_clan.primogen_id,
                own_clan_state.coterie_memberships.get(character.id) == CoterieSide.OPPOSITION,
                -character.personal_influence,
            ),
        )

        with st.form("night_orders"):
            st.markdown("#### Une action par vampire")
            st.caption(
                "Vous choisissez une mission pour chaque membre actif. Un opposant peut refuser une "
                "mission si sa relation au Primogène est faible ; une diplomatie compatible avec son "
                "idéologie est plus facilement acceptée."
            )
            actions: list[GameAction] = []

            for actor in active_members:
                side = own_clan_state.coterie_memberships.get(actor.id, CoterieSide.PRIMOGEN)
                effective = effective_relation_to_primogen(state, actor.id)
                with st.container(border=True):
                    st.markdown(f"##### {actor.name} — {COTERIE_LABELS[side]}")
                    st.caption(
                        f"Humanité {actor.humanity_axis.value} · Traditions {actor.tradition_axis.value} · "
                        f"relation au Primogène {actor.relation_to_primogen}/2 · effective {effective:+d}"
                    )

                    own_targets = [
                        character.id
                        for character in active_members
                        if character.id not in {actor.id, own_clan.primogen_id}
                    ]
                    recruit_targets = [
                        character_id
                        for character_id in own_targets
                        if own_clan_state.coterie_memberships.get(character_id) != side
                    ]
                    known_foreign = known_foreign_members(state, player_clan, 1)
                    known_foreign_non_primogens = [
                        character_id
                        for character_id in known_foreign
                        if character_id
                        != state.clan_states[state.characters[character_id].clan_id].clan.primogen_id
                    ]
                    poach_targets = [
                        character_id
                        for character_id in known_foreign_members(state, player_clan, 2)
                        if character_id in known_foreign_non_primogens
                        and state.clan_states[state.characters[character_id].clan_id].coterie_memberships.get(
                            character_id
                        )
                        == CoterieSide.PRIMOGEN
                        and effective_relation_to_primogen(state, character_id) <= 0
                    ]

                    options = [ActionType.BUILD_INFLUENCE, ActionType.DIPLOMACY, ActionType.INVESTIGATE]
                    if own_targets:
                        options.append(ActionType.CONSOLIDATE_RELATION)
                    if recruit_targets:
                        options.append(ActionType.RECRUIT)
                    if known_foreign_non_primogens:
                        options.append(ActionType.UNDERMINE)
                    if poach_targets:
                        options.append(ActionType.POACH)

                    action_type = st.selectbox(
                        "Action",
                        options=options,
                        format_func=lambda action: ACTION_LABELS[action],
                        key=f"action_{state.night}_{actor.id}",
                    )
                    target_character_id = None
                    target_clan_id = None

                    if action_type == ActionType.DIPLOMACY:
                        target_ids = list(dict.fromkeys(foreign_primogens(state, player_clan) + known_foreign))
                        target_character_id = st.selectbox(
                            "Interlocuteur",
                            options=target_ids,
                            format_func=lambda cid: (
                                f"{state.characters[cid].name} — "
                                f"{clan_names[state.characters[cid].clan_id]} — affinité "
                                f"{ideology_relation_modifier(actor, state.characters[cid]):+d}"
                            ),
                            key=f"target_diplomacy_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.CONSOLIDATE_RELATION:
                        target_character_id = st.selectbox(
                            "Membre à rapprocher",
                            options=own_targets,
                            format_func=lambda cid: state.characters[cid].name,
                            key=f"target_relation_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.RECRUIT:
                        target_character_id = st.selectbox(
                            "Membre de l'autre coterie",
                            options=recruit_targets,
                            format_func=lambda cid: state.characters[cid].name,
                            key=f"target_recruit_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.UNDERMINE:
                        target_character_id = st.selectbox(
                            "Membre étranger connu",
                            options=known_foreign_non_primogens,
                            format_func=lambda cid: (
                                f"{state.characters[cid].name} — {clan_names[state.characters[cid].clan_id]}"
                            ),
                            key=f"target_undermine_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.POACH:
                        target_character_id = st.selectbox(
                            "Cible fragile",
                            options=poach_targets,
                            format_func=lambda cid: (
                                f"{state.characters[cid].name} — {clan_names[state.characters[cid].clan_id]}"
                            ),
                            key=f"target_poach_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.INVESTIGATE:
                        target_clan_id = st.selectbox(
                            "Clan à infiltrer",
                            options=[cid for cid in state.clan_states if cid != player_clan],
                            format_func=lambda cid: clan_names[cid],
                            key=f"target_investigate_{state.night}_{actor.id}",
                        )

                    actions.append(
                        GameAction(
                            clan_id=player_clan,
                            action_type=action_type,
                            target_clan_id=target_clan_id,
                            actor_character_id=actor.id,
                            target_character_id=target_character_id,
                        )
                    )

            vote = None
            if state.prince_id is None:
                st.markdown("#### Praxis")
                candidate_id = st.selectbox(
                    "Vote de votre Primogène",
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
                st.caption("Le Primogène porte officiellement la demande d'un membre précis de son clan.")
                send_petition = st.checkbox("Porter une demande d'Étreinte cette nuit")
                if send_petition:
                    member_ids = [
                        char.id
                        for char in state.characters.values()
                        if char.clan_id == player_clan
                        and char.id != own_clan.primogen_id
                        and char.id != state.prince_id
                    ]
                    member_id = st.selectbox(
                        "Membre représenté",
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
                        version=2,
                    )
                    resolved = service.submit_orders(player_id, orders)
                    if resolved:
                        st.success("Les trois clans ont validé : la nuit a été résolue.")
                    else:
                        st.success("Vos ordres sont enregistrés. En attente des autres clans.")
                    st.rerun()
                except (ValueError, SupabaseRestError) as exc:
                    st.error(str(exc))

with clan_tab:
    st.subheader(f"Clan {own_clan.name}")
    total_col, primogen_col, opposition_col = st.columns(3)
    total_col.metric("Influence totale", f"{clan_total_influence(state, player_clan):.0f}")
    primogen_col.metric(
        "Coterie du Primogène",
        f"{coterie_influence(state, player_clan, CoterieSide.PRIMOGEN):.0f}",
    )
    opposition_col.metric(
        "Opposition",
        f"{coterie_influence(state, player_clan, CoterieSide.OPPOSITION):.0f}",
    )
    opposition_leader = state.characters[own_clan_state.opposition_leader_id]
    ally_id = own_clan_state.opposition_allied_primogen_id
    st.write(f"**Primogène :** {own_primogen.name}")
    st.write(f"**Chef d'opposition :** {opposition_leader.name}")
    if ally_id:
        st.caption(f"Allié extérieur actuel de l'opposition : {state.characters[ally_id].name}")

    for side in (CoterieSide.PRIMOGEN, CoterieSide.OPPOSITION):
        st.markdown(f"### {COTERIE_LABELS[side]}")
        members = sorted(
            [
                character
                for character in state.characters.values()
                if character.clan_id == player_clan
                and character.id != state.prince_id
                and own_clan_state.coterie_memberships.get(character.id) == side
            ],
            key=lambda character: character.personal_influence,
            reverse=True,
        )
        for member in members:
            roles = []
            if member.id == own_clan.primogen_id:
                roles.append("Primogène")
            if member.id == own_clan_state.opposition_leader_id:
                roles.append("Chef d'opposition")
            role = " · ".join(roles) if roles else "Membre"
            modifier = ideology_relation_modifier(member, own_primogen)
            effective = effective_relation_to_primogen(state, member.id)
            with st.expander(f"{member.name} — {role} — influence {member.personal_influence:.0f}"):
                st.caption(
                    f"Humanité {member.humanity_axis.value} · Traditions {member.tradition_axis.value} · "
                    f"Rang de Sang : {BLOOD_RANK_LABELS[member.blood_rank.value]}"
                )
                relation_col, ideology_col, effective_col = st.columns(3)
                relation_col.metric("Relation personnelle", f"{member.relation_to_primogen}/2")
                ideology_col.metric("Mod. idéologique", f"{modifier:+d}")
                effective_col.metric("Relation effective", f"{effective:+d}")
                physical_col, social_col, mental_col = st.columns(3)
                physical_col.metric("Physique", member.physical)
                social_col.metric("Social", member.social)
                mental_col.metric("Mental", member.mental)
                st.write("**Expertises :** " + (" · ".join(member.expertises) if member.expertises else "Aucune"))
                st.write("**Disciplines :** " + format_score_map(member.disciplines, DISCIPLINE_LABELS))
                st.write("**Historiques :** " + format_score_map(member.backgrounds))

with city_tab:
    st.subheader("Informations publiques")
    st.write(f"**Nuit :** {state.night}")
    st.write(f"**Praxis :** {state.praxis_status}")
    if state.prince_id:
        st.write(f"**Prince :** {state.characters[state.prince_id].name}")
    st.markdown("#### Conseil des Primogènes")
    for clan_id, clan_state in state.clan_states.items():
        primogen = state.characters[clan_state.clan.primogen_id]
        st.write(
            f"**{clan_state.clan.name}** : {primogen.name} — "
            f"Humanité {primogen.humanity_axis.value} / Traditions {primogen.tradition_axis.value}"
        )

    st.markdown("#### Renseignements de votre clan")
    known = sorted(
        own_clan_state.known_character_intel.items(),
        key=lambda item: (state.characters[item[0]].clan_id, state.characters[item[0]].name),
    )
    if not known:
        st.caption("Aucun membre étranger n'a encore été identifié. Utilisez l'action Enquêter.")
    for character_id, level in known:
        character = state.characters.get(character_id)
        if not character or character.clan_id == player_clan:
            continue
        line = f"**{character.name} — {clan_names[character.clan_id]}** · renseignement {level}/2"
        st.write(line)
        if level >= 2:
            target_state = state.clan_states[character.clan_id]
            side = target_state.coterie_memberships.get(character.id, CoterieSide.PRIMOGEN)
            st.caption(
                f"Coterie : {COTERIE_LABELS[side]} · relation effective au Primogène : "
                f"{effective_relation_to_primogen(state, character.id):+d} · influence {character.personal_influence:.0f}"
            )
    st.caption("Les autres membres, relations, coteries et ordres restent privés tant qu'ils ne sont pas découverts.")

with elysium_tab:
    st.subheader("Elysium")
    st.caption("L'Elysium reste accessible même après validation de vos ordres de nuit.")
    messages = repo.list_elysium_messages(DEFAULT_GAME_ID)
    for message in messages:
        st.write(f"**{clan_names[message['clan_id']]} - {message['player_name']}** : {message['body']}")
        st.caption(message["created_at"])
    with st.form("elysium_message", clear_on_submit=True):
        body = st.text_input("Message")
        post = st.form_submit_button("Parler à l'Elysium")
        if post:
            try:
                repo.post_elysium_message(DEFAULT_GAME_ID, player_id, player_clan, body)
                st.rerun()
            except (ValueError, SupabaseRestError) as exc:
                st.error(str(exc))

with reports_tab:
    st.subheader("Rapports de votre clan")
    reports = repo.list_reports(DEFAULT_GAME_ID, player_clan)
    if not reports:
        st.caption("Aucune nuit résolue pour votre clan pour le moment.")
    for report in reports:
        with st.expander(f"Nuit {report.night} - rapport du clan", expanded=(report == reports[0])):
            if not report.items:
                st.caption("Aucun événement dont votre clan ait connaissance.")
            for item in report.items:
                st.write(f"- {item}")

st.caption(
    "V0.8 : deux coteries par clan, relation personnelle au Primogène, une action par vampire, "
    "diplomatie idéologique, recrutement, débauchage et renseignement progressif."
)
