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
from game.crises import (
    CRISIS_ACTION_LABELS,
    CRISIS_ACTION_TYPES,
    active_crises,
    crisis_stage_label,
    crisis_title,
)
from game.domains import active_hunting_rights, has_hunting_access, initialize_domains
from game.factions import (
    clan_total_influence,
    effective_relation_to_primogen,
    faction_influence,
    ideology_relation_modifier,
    initialize_factions,
)
from game.models import (
    ActionType,
    BoonLevel,
    BoonStatus,
    ClanFactionSide,
    ClanNightOrders,
    DomainDecisionOrder,
    DomainDecisionType,
    DomainDisputeStatus,
    EmbracePetitionOrder,
    GameAction,
    HuntingRightStatus,
    NightStatus,
    PoliticalRequestDecisionOrder,
    PoliticalRequestStatus,
    PrimogenVote,
    PromiseStatus,
    RequestDecision,
)
from game.multiplayer import DEFAULT_GAME_ID, MultiplayerGameService
from game.repository_factory import create_repository
from game.supabase_repository import SupabaseRestError
from game.world import candidates_from_state


st.set_page_config(page_title="WoD RPG - Chronique politique", page_icon="🩸", layout="wide")
st.title("WoD RPG - Chronique politique")
st.caption("V0.20 — crises jouables, Praxis contestable, Faim et politique territoriale")

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

FACTION_LABELS = {
    ClanFactionSide.PRIMOGEN: "Faction du Primogène",
    ClanFactionSide.OPPOSITION: "Faction d'opposition",
}

MORTAL_STANCE_LABELS = {
    "humanist": "Humaniste",
    "predatory": "Prédateur",
}

ORDER_STANCE_LABELS = {
    "orthodox": "Orthodoxe",
    "reformist": "Réformateur",
}

REQUEST_DECISION_LABELS = {
    RequestDecision.ACCEPT: "Accepter",
    RequestDecision.REFUSE: "Refuser",
    RequestDecision.NEGOTIATE: "Négocier",
    RequestDecision.PROMISE: "Promettre",
}

DOMAIN_DECISION_LABELS = {
    DomainDecisionType.GRANT_HUNTING_RIGHT: "Accorder un droit de chasse",
    DomainDecisionType.REVOKE_HUNTING_RIGHT: "Révoquer un droit de chasse",
}

BOON_LEVEL_LABELS = {
    BoonLevel.MINOR: "Faveur mineure",
    BoonLevel.MAJOR: "Faveur majeure",
    BoonLevel.LIFE: "Dette de vie",
}

# Les actions récentes sont ajoutées à la table centrale historique sans modifier
# le comportement des anciennes vues/actions.
ACTION_LABELS[ActionType.CHALLENGE_PRAXIS] = "Contester la Praxis"
ACTION_LABELS.update(CRISIS_ACTION_LABELS)


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


def political_profile(character) -> str:
    return (
        f"{MORTAL_STANCE_LABELS[character.mortal_stance.value]} · "
        f"{ORDER_STANCE_LABELS[character.order_stance.value]}"
    )


def holder_label(state, domain) -> str:
    if not domain.holder_id:
        return "Non attribué"
    holder = state.characters.get(domain.holder_id)
    if not holder:
        return domain.holder_id
    clan_name = state.clan_states[holder.clan_id].clan.name if holder.clan_id else "Sans clan"
    return f"{holder.name} — {clan_name}"


def describe_orders(orders: ClanNightOrders, state) -> list[str]:
    lines: list[str] = []
    for decision in orders.request_decisions:
        request = state.political_requests.get(decision.request_id)
        if request:
            requester = state.characters[request.requester_id]
            lines.append(
                f"Requête de {requester.name} : {REQUEST_DECISION_LABELS[decision.decision]}"
            )
    for promise_id in orders.promise_fulfillments:
        promise = state.promises.get(promise_id)
        if promise:
            beneficiary = state.characters[promise.beneficiary_id]
            lines.append(f"Promesse honorée envers {beneficiary.name}")
    for item in orders.domain_decisions:
        domain = state.domains.get(item.domain_id)
        domain_name = domain.name if domain else item.domain_id
        if item.decision == DomainDecisionType.GRANT_HUNTING_RIGHT:
            beneficiary = state.characters.get(item.beneficiary_id or "")
            text = (
                f"Domaine : droit de chasse sur {domain_name} accordé à "
                f"{beneficiary.name if beneficiary else item.beneficiary_id} pour {item.duration_nights} nuits"
            )
            if item.boon_level:
                text += f" contre {BOON_LEVEL_LABELS[item.boon_level].lower()}"
            lines.append(text)
        else:
            right = state.hunting_rights.get(item.right_id or "")
            beneficiary = state.characters.get(right.beneficiary_id) if right else None
            lines.append(
                f"Domaine : droit de chasse sur {domain_name} révoqué"
                + (f" pour {beneficiary.name}" if beneficiary else "")
            )
    for index, action in enumerate(orders.actions, start=1):
        actor_id = action.actor_character_id or state.clan_states[orders.clan_id].clan.primogen_id
        actor = state.characters.get(actor_id)
        text = f"Action {index} : {actor.name if actor else actor_id} — {ACTION_LABELS[action.action_type]}"
        if action.target_character_id:
            target = state.characters.get(action.target_character_id)
            text += f" → {target.name if target else action.target_character_id}"
        elif action.target_domain_id:
            domain = state.domains.get(action.target_domain_id)
            text += f" → {domain.name if domain else action.target_domain_id}"
        elif action.target_clan_id:
            text += f" → {state.clan_states[action.target_clan_id].clan.name}"
        lines.append(text)
    if orders.vote:
        candidate = state.characters.get(orders.vote.candidate_id)
        lines.append(f"Reconnaissance de Praxis : {candidate.name if candidate else orders.vote.candidate_id}")
    for petition in orders.embrace_petitions:
        member = state.characters[petition.member_id]
        lines.append(
            f"Demande d'Étreinte : {member.name} souhaite Étreindre {petition.proposed_childe_name}"
        )
    return lines


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
    initialize_factions(state)
    initialize_domains(state)
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

night_tab, clan_tab, domains_tab, prestation_tab, city_tab, elysium_tab, reports_tab = st.tabs(
    ["Ma nuit", "Mon clan", "Domaines", "Prestation", "Ville", "Elysium", "Mes rapports"]
)

with night_tab:
    st.subheader(f"Ordres du clan {own_clan.name} - Nuit {state.night}")
    current_crises = active_crises(state)
    if current_crises:
        st.markdown("#### Crises pouvant mobiliser vos vampires")
        for crisis in current_crises:
            st.write(
                f"**{crisis_title(state, crisis)}** · {crisis_stage_label(crisis.stage)} · "
                f"escalade nuit {crisis.next_escalation_night}"
            )
        st.caption(
            "Répondre à une crise consomme l'action nocturne du vampire choisi. Plusieurs vampires et "
            "plusieurs clans peuvent contribuer à la même crise."
        )

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
                own_clan_state.faction_memberships.get(character.id) == ClanFactionSide.OPPOSITION,
                -character.personal_influence,
            ),
        )
        open_requests = sorted(
            [
                request
                for request in state.political_requests.values()
                if request.clan_id == player_clan and request.status == PoliticalRequestStatus.OPEN
            ],
            key=lambda request: (request.created_night, request.id),
        )
        pending_promises = sorted(
            [
                promise
                for promise in state.promises.values()
                if promise.promisor_id == own_primogen.id
                and promise.status == PromiseStatus.PENDING
                and state.night <= promise.due_night
            ],
            key=lambda promise: (promise.due_night, promise.id),
        )
        primogen_domains = sorted(
            [domain for domain in state.domains.values() if domain.holder_id == own_primogen.id],
            key=lambda domain: domain.name,
        )

        with st.form("night_orders"):
            request_decisions: list[PoliticalRequestDecisionOrder] = []
            if open_requests:
                st.markdown("#### Requêtes adressées au Primogène")
                st.caption(
                    "Ces demandes sont personnelles. Refuser peut créer un grief ; promettre engage "
                    "votre réputation ; négocier peut créer une dette de Prestation."
                )
                for request in open_requests:
                    requester = state.characters[request.requester_id]
                    with st.container(border=True):
                        st.write(f"**{requester.name}** — {request.description}")
                        st.caption(
                            f"Faction : {FACTION_LABELS[own_clan_state.faction_memberships.get(requester.id, ClanFactionSide.PRIMOGEN)]} · "
                            f"relation effective {effective_relation_to_primogen(state, requester.id):+d}"
                        )
                        if request.offered_boon_level:
                            st.caption(
                                f"Contrepartie proposée : {BOON_LEVEL_LABELS[request.offered_boon_level].lower()}."
                            )
                        decision = st.selectbox(
                            "Réponse",
                            options=list(RequestDecision),
                            format_func=lambda item: REQUEST_DECISION_LABELS[item],
                            key=f"request_decision_{request.id}_{state.night}",
                        )
                        request_decisions.append(
                            PoliticalRequestDecisionOrder(request.id, decision)
                        )

            promise_fulfillments: list[str] = []
            if pending_promises:
                st.markdown("#### Promesses à honorer")
                st.caption(
                    "Honorer une promesse intervient avant les missions. Une promesse territoriale peut donc "
                    "ouvrir immédiatement un droit de chasse cette nuit."
                )
                for promise in pending_promises:
                    beneficiary = state.characters[promise.beneficiary_id]
                    if st.checkbox(
                        f"Honorer la promesse faite à {beneficiary.name} — échéance nuit {promise.due_night}",
                        key=f"fulfill_promise_{promise.id}_{state.night}",
                    ):
                        promise_fulfillments.append(promise.id)
                    st.caption(promise.description)

            domain_decisions: list[DomainDecisionOrder] = []
            if primogen_domains:
                st.markdown("#### Administration territoriale du Primogène")
                st.caption(
                    "Le Primogène ne peut administrer ici que les Domaines qu'il détient personnellement. "
                    "Les Domaines de l'opposition restent hors de son contrôle direct."
                )
                domain_decision = st.selectbox(
                    "Décision territoriale",
                    options=[None, *list(DomainDecisionType)],
                    format_func=lambda item: "Aucune" if item is None else DOMAIN_DECISION_LABELS[item],
                    key=f"domain_decision_{state.night}",
                )
                if domain_decision is not None:
                    domain_id = st.selectbox(
                        "Domaine concerné",
                        options=[domain.id for domain in primogen_domains],
                        format_func=lambda did: state.domains[did].name,
                        key=f"domain_decision_target_{state.night}",
                    )
                    if domain_decision == DomainDecisionType.GRANT_HUNTING_RIGHT:
                        visible_foreign = list(
                            dict.fromkeys(
                                foreign_primogens(state, player_clan)
                                + known_foreign_members(state, player_clan, 1)
                            )
                        )
                        beneficiary_ids = [
                            member.id
                            for member in active_members
                            if member.id != own_primogen.id
                            and not has_hunting_access(state, member.id, domain_id)
                        ]
                        beneficiary_ids.extend(
                            character_id
                            for character_id in visible_foreign
                            if character_id in state.characters
                            and character_id != state.prince_id
                            and not has_hunting_access(state, character_id, domain_id)
                        )
                        beneficiary_ids = list(dict.fromkeys(beneficiary_ids))
                        if beneficiary_ids:
                            beneficiary_id = st.selectbox(
                                "Bénéficiaire",
                                options=beneficiary_ids,
                                format_func=lambda cid: state.characters[cid].name,
                                key=f"domain_beneficiary_{state.night}",
                            )
                            duration_nights = int(
                                st.number_input(
                                    "Durée du droit de chasse (nuits)",
                                    min_value=1,
                                    max_value=10,
                                    value=3,
                                    step=1,
                                    key=f"domain_duration_{state.night}",
                                )
                            )
                            boon_level = st.selectbox(
                                "Contrepartie de Prestation",
                                options=[None, *list(BoonLevel)],
                                format_func=lambda level: "Aucune" if level is None else BOON_LEVEL_LABELS[level],
                                key=f"domain_boon_{state.night}",
                            )
                            domain_decisions.append(
                                DomainDecisionOrder(
                                    decision=domain_decision,
                                    domain_id=domain_id,
                                    beneficiary_id=beneficiary_id,
                                    duration_nights=duration_nights,
                                    boon_level=boon_level,
                                )
                            )
                        else:
                            st.caption("Aucun bénéficiaire visible ne peut recevoir un nouveau droit sur ce Domaine.")
                    else:
                        rights = active_hunting_rights(state, domain_id=domain_id)
                        if rights:
                            right_id = st.selectbox(
                                "Droit à révoquer",
                                options=[right.id for right in rights],
                                format_func=lambda rid: (
                                    f"{state.characters[state.hunting_rights[rid].beneficiary_id].name} — "
                                    f"échéance nuit {state.hunting_rights[rid].expires_night}"
                                ),
                                key=f"domain_revoke_{state.night}",
                            )
                            domain_decisions.append(
                                DomainDecisionOrder(
                                    decision=domain_decision,
                                    domain_id=domain_id,
                                    right_id=right_id,
                                )
                            )
                        else:
                            st.caption("Aucun droit de chasse actif n'est révocable sur ce Domaine.")

            st.markdown("#### Une action par vampire")
            st.caption(
                "Vous attribuez une mission à chaque membre actif. Un opposant conserve ses intérêts "
                "propres et peut refuser une mission qui sert mal sa position."
            )
            actions: list[GameAction] = []

            for actor in active_members:
                side = own_clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN)
                effective = effective_relation_to_primogen(state, actor.id)
                with st.container(border=True):
                    st.markdown(f"##### {actor.name} — {FACTION_LABELS[side]}")
                    st.caption(
                        f"{political_profile(actor)} · Humanité {actor.humanity}/10 · Statut {actor.status}/5 · "
                        f"réputation {actor.reputation:+d} · relation au Primogène {actor.relation_to_primogen}/2 · "
                        f"effective {effective:+d}"
                    )

                    own_targets = [
                        character.id
                        for character in active_members
                        if character.id not in {actor.id, own_clan.primogen_id}
                    ]
                    recruit_targets = [
                        character_id
                        for character_id in own_targets
                        if own_clan_state.faction_memberships.get(character_id) != side
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
                        and state.clan_states[state.characters[character_id].clan_id].faction_memberships.get(
                            character_id
                        )
                        == ClanFactionSide.PRIMOGEN
                        and effective_relation_to_primogen(state, character_id) <= 0
                    ]
                    boon_targets = sorted(
                        {
                            boon.debtor_id
                            for boon in state.boons.values()
                            if boon.creditor_id == actor.id and boon.status == BoonStatus.DUE
                        }
                    )
                    actor_domains = [
                        domain.id for domain in state.domains.values() if domain.holder_id == actor.id
                    ]
                    intrusion_domains = [
                        domain.id for domain in state.domains.values() if domain.holder_id != actor.id
                    ]
                    braconnage_domains = [
                        domain.id
                        for domain in state.domains.values()
                        if not has_hunting_access(state, actor.id, domain.id)
                    ]
                    exploitable_crises = [
                        crisis
                        for crisis in current_crises
                        if state.domains[crisis.domain_id].holder_id
                        and state.characters[state.domains[crisis.domain_id].holder_id].clan_id
                        != player_clan
                    ]

                    options = [ActionType.BUILD_INFLUENCE, ActionType.DIPLOMACY, ActionType.INVESTIGATE]
                    if actor.id == own_clan.primogen_id and state.prince_id is not None:
                        options.append(ActionType.CHALLENGE_PRAXIS)
                    if own_targets:
                        options.append(ActionType.CONSOLIDATE_RELATION)
                    if recruit_targets:
                        options.append(ActionType.RECRUIT)
                    if known_foreign_non_primogens:
                        options.append(ActionType.UNDERMINE)
                    if poach_targets:
                        options.append(ActionType.POACH)
                    if boon_targets:
                        options.append(ActionType.CALL_BOON)
                    if actor_domains:
                        options.append(ActionType.DOMAIN_STEWARD)
                    if intrusion_domains:
                        options.append(ActionType.DOMAIN_INTRUSION)
                    if braconnage_domains:
                        options.append(ActionType.BRACONNAGE)
                    if current_crises:
                        options.extend(
                            [
                                ActionType.CRISIS_INVESTIGATE,
                                ActionType.CRISIS_INFILTRATE,
                                ActionType.CRISIS_NEGOTIATE,
                                ActionType.CRISIS_CONTAIN,
                            ]
                        )
                    if exploitable_crises:
                        options.append(ActionType.CRISIS_EXPLOIT)

                    action_type = st.selectbox(
                        "Action",
                        options=options,
                        format_func=lambda action: ACTION_LABELS[action],
                        key=f"action_{state.night}_{actor.id}",
                    )
                    target_character_id = None
                    target_clan_id = None
                    target_domain_id = None

                    if action_type in CRISIS_ACTION_TYPES:
                        crisis_choices = (
                            exploitable_crises
                            if action_type == ActionType.CRISIS_EXPLOIT
                            else current_crises
                        )
                        crisis_by_domain = {crisis.domain_id: crisis for crisis in crisis_choices}
                        target_domain_id = st.selectbox(
                            "Crise ciblée",
                            options=list(crisis_by_domain),
                            format_func=lambda did: (
                                f"{crisis_title(state, crisis_by_domain[did])} — "
                                f"{crisis_stage_label(crisis_by_domain[did].stage)}"
                            ),
                            key=f"target_crisis_{state.night}_{actor.id}_{action_type.value}",
                        )
                        selected_crisis = crisis_by_domain[target_domain_id]
                        if action_type == ActionType.CRISIS_INVESTIGATE:
                            st.caption(
                                "Cette action cherche des informations : elle facilite les interventions futures "
                                "mais ne réduit pas directement la menace."
                            )
                        elif action_type == ActionType.CRISIS_EXPLOIT:
                            st.warning(
                                "Cette action ne résout pas la crise. Elle cherche à convertir la faiblesse du "
                                "détenteur étranger en influence politique ; une manipulation découverte peut "
                                "créer un grief."
                            )
                        else:
                            st.caption(
                                f"Intervention sur une crise {crisis_stage_label(selected_crisis.stage)}. "
                                "Les progrès de tous les vampires engagés cette nuit se cumulent."
                            )
                    elif action_type == ActionType.CHALLENGE_PRAXIS:
                        st.warning(
                            "Action publique : votre Primogène engage le poids politique de son clan contre "
                            "la Praxis reconnue. Si la coalition est insuffisante, le Prince conservera le "
                            "pouvoir et se souviendra de la contestation."
                        )
                    elif action_type == ActionType.DIPLOMACY:
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
                            "Membre de l'autre faction",
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
                    elif action_type == ActionType.CALL_BOON:
                        target_character_id = st.selectbox(
                            "Débiteur",
                            options=boon_targets,
                            format_func=lambda cid: state.characters[cid].name,
                            key=f"target_boon_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.DOMAIN_STEWARD:
                        target_domain_id = st.selectbox(
                            "Domaine à administrer",
                            options=actor_domains,
                            format_func=lambda did: state.domains[did].name,
                            key=f"target_domain_steward_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.DOMAIN_INTRUSION:
                        target_domain_id = st.selectbox(
                            "Domaine à infiltrer",
                            options=intrusion_domains,
                            format_func=lambda did: f"{state.domains[did].name} — {holder_label(state, state.domains[did])}",
                            key=f"target_domain_intrusion_{state.night}_{actor.id}",
                        )
                    elif action_type == ActionType.BRACONNAGE:
                        target_domain_id = st.selectbox(
                            "Domaine à braconner",
                            options=braconnage_domains,
                            format_func=lambda did: f"{state.domains[did].name} — {holder_label(state, state.domains[did])}",
                            key=f"target_braconnage_{state.night}_{actor.id}",
                        )

                    actions.append(
                        GameAction(
                            clan_id=player_clan,
                            action_type=action_type,
                            target_clan_id=target_clan_id,
                            actor_character_id=actor.id,
                            target_character_id=target_character_id,
                            target_domain_id=target_domain_id,
                        )
                    )

            vote = None
            if state.prince_id is None:
                st.markdown("#### Reconnaissance de la Praxis")
                st.caption(
                    "Dans cette chronique, le Conseil des Primogènes sert de mécanisme local de reconnaissance "
                    "d'une Praxis ; ce n'est pas une procédure universelle de la Camarilla."
                )
                candidate_id = st.selectbox(
                    "Candidat reconnu par votre Primogène",
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
                        request_decisions=tuple(request_decisions),
                        domain_decisions=tuple(domain_decisions),
                        promise_fulfillments=tuple(promise_fulfillments),
                        version=4,
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
        "Faction du Primogène",
        f"{faction_influence(state, player_clan, ClanFactionSide.PRIMOGEN):.0f}",
    )
    opposition_col.metric(
        "Faction d'opposition",
        f"{faction_influence(state, player_clan, ClanFactionSide.OPPOSITION):.0f}",
    )
    opposition_leader = state.characters[own_clan_state.opposition_leader_id]
    ally_id = own_clan_state.opposition_allied_primogen_id
    st.write(f"**Primogène :** {own_primogen.name}")
    st.write(f"**Chef d'opposition :** {opposition_leader.name}")
    if ally_id:
        st.caption(f"Allié extérieur actuel de l'opposition : {state.characters[ally_id].name}")

    for side in (ClanFactionSide.PRIMOGEN, ClanFactionSide.OPPOSITION):
        st.markdown(f"### {FACTION_LABELS[side]}")
        members = sorted(
            [
                character
                for character in state.characters.values()
                if character.clan_id == player_clan
                and character.id != state.prince_id
                and own_clan_state.faction_memberships.get(character.id) == side
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
                    f"{political_profile(member)} · Humanité réelle {member.humanity}/10 · "
                    f"Rang de Sang : {BLOOD_RANK_LABELS[member.blood_rank.value]}"
                )
                relation_col, ideology_col, effective_col, status_col = st.columns(4)
                relation_col.metric("Relation personnelle", f"{member.relation_to_primogen}/2")
                ideology_col.metric("Affinité politique", f"{modifier:+d}")
                effective_col.metric("Relation effective", f"{effective:+d}")
                status_col.metric("Statut", f"{member.status}/5")
                st.write(f"**Réputation :** {member.reputation:+d}")
                st.write(f"**Ambition actuelle :** {member.political_ambition.value}")
                physical_col, social_col, mental_col = st.columns(3)
                physical_col.metric("Physique", member.physical)
                social_col.metric("Social", member.social)
                mental_col.metric("Mental", member.mental)
                st.write("**Expertises :** " + (" · ".join(member.expertises) if member.expertises else "Aucune"))
                st.write("**Disciplines :** " + format_score_map(member.disciplines, DISCIPLINE_LABELS))
                st.write("**Historiques :** " + format_score_map(member.backgrounds))

    st.markdown("### Griefs connus dans votre clan")
    own_grievances = [
        grievance
        for grievance in state.grievances.values()
        if not grievance.resolved
        and state.characters[grievance.owner_id].clan_id == player_clan
    ]
    if not own_grievances:
        st.caption("Aucun grief explicite actuellement enregistré.")
    for grievance in own_grievances:
        owner = state.characters[grievance.owner_id]
        target = state.characters[grievance.target_id]
        st.write(
            f"**{owner.name} → {target.name}** · gravité {grievance.severity}/3 — {grievance.reason}"
        )

    st.markdown("### Promesses")
    own_promises = [
        promise
        for promise in state.promises.values()
        if state.characters[promise.promisor_id].clan_id == player_clan
        or state.characters[promise.beneficiary_id].clan_id == player_clan
    ]
    if not own_promises:
        st.caption("Aucune promesse politique enregistrée.")
    for promise in own_promises:
        st.write(
            f"**{state.characters[promise.promisor_id].name} → {state.characters[promise.beneficiary_id].name}** "
            f"· {promise.status.value} · échéance nuit {promise.due_night} — {promise.description}"
        )

with domains_tab:
    st.subheader("Domaines et droits de chasse")
    st.caption(
        "Le détenteur officiel d'un Domaine est public. Viandis, Servage, Rempart, pression réelle, "
        "droits privés et litiges dépendent de votre implication ou de votre renseignement."
    )

    for domain in sorted(state.domains.values(), key=lambda item: item.name):
        holder = state.characters.get(domain.holder_id or "")
        holder_clan = holder.clan_id if holder else None
        own_involvement = holder_clan == player_clan
        intel_level = own_clan_state.known_domain_intel.get(domain.id, 0)
        with st.expander(f"{domain.name} — {holder_label(state, domain)}"):
            st.write(domain.description)
            if own_involvement or intel_level >= 2:
                viandis_col, servage_col, rempart_col, pressure_col = st.columns(4)
                viandis_col.metric("Viandis", f"{domain.viandis}/3")
                servage_col.metric("Servage", f"{domain.servage}/3")
                rempart_col.metric("Rempart", f"{domain.rempart}/3")
                pressure_col.metric("Pression", domain.pressure)
                if not own_involvement:
                    st.caption("Ces informations détaillées proviennent du renseignement territorial de votre clan.")
            elif intel_level == 1:
                st.caption("Votre clan dispose d'indices partiels sur l'organisation de ce Domaine.")
            else:
                st.caption("Les caractéristiques internes de ce Domaine ne sont pas connues de votre clan.")

            visible_rights = [
                right
                for right in active_hunting_rights(state, domain_id=domain.id)
                if own_involvement
                or state.characters[right.beneficiary_id].clan_id == player_clan
                or state.characters[right.granted_by_id].clan_id == player_clan
            ]
            if visible_rights:
                st.markdown("**Droits de chasse connus**")
                for right in visible_rights:
                    beneficiary = state.characters[right.beneficiary_id]
                    grantor = state.characters[right.granted_by_id]
                    st.write(
                        f"- {beneficiary.name} · accordé par {grantor.name} · échéance nuit {right.expires_night}"
                    )

    st.markdown("### Droits détenus par votre clan")
    own_rights = [
        right
        for right in state.hunting_rights.values()
        if right.status == HuntingRightStatus.ACTIVE
        and state.characters[right.beneficiary_id].clan_id == player_clan
    ]
    if not own_rights:
        st.caption("Aucun membre de votre clan ne dispose actuellement d'un droit de chasse concédé.")
    for right in own_rights:
        beneficiary = state.characters[right.beneficiary_id]
        domain = state.domains[right.domain_id]
        st.write(
            f"**{beneficiary.name}** → {domain.name} · échéance nuit {right.expires_night}"
            + (f" · {right.conditions}" if right.conditions else "")
        )

    st.markdown("### Litiges territoriaux connus")
    visible_disputes = []
    for dispute in state.domain_disputes.values():
        if dispute.status != DomainDisputeStatus.OPEN:
            continue
        claimant = state.characters[dispute.claimant_id]
        respondent = state.characters[dispute.respondent_id]
        if dispute.public or claimant.clan_id == player_clan or respondent.clan_id == player_clan:
            visible_disputes.append(dispute)
    if not visible_disputes:
        st.caption("Aucun litige territorial connu de votre clan.")
    for dispute in visible_disputes:
        st.write(
            f"**{state.domains[dispute.domain_id].name}** · "
            f"{state.characters[dispute.claimant_id].name} ↔ {state.characters[dispute.respondent_id].name} "
            f"· gravité {dispute.severity}/3 — {dispute.reason}"
        )

with prestation_tab:
    st.subheader("Prestation — faveurs et dettes")
    st.caption(
        "Les faveurs sont des obligations personnelles. Les honorer renforce la réputation ; les refuser "
        "peut créer un grief et coûter lourdement en crédibilité."
    )
    relevant_boons = [
        boon
        for boon in state.boons.values()
        if state.characters[boon.creditor_id].clan_id == player_clan
        or state.characters[boon.debtor_id].clan_id == player_clan
    ]
    if not relevant_boons:
        st.caption("Aucune faveur enregistrée pour votre clan.")
    for boon in relevant_boons:
        creditor = state.characters[boon.creditor_id]
        debtor = state.characters[boon.debtor_id]
        with st.container(border=True):
            st.write(
                f"**{creditor.name} ← {debtor.name}** · {BOON_LEVEL_LABELS[boon.level]} · {boon.status.value}"
            )
            st.caption(f"Origine : {boon.origin} · créée nuit {boon.created_night}")

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
            f"**{clan_state.clan.name}** : {primogen.name} — {political_profile(primogen)} — "
            f"Statut {primogen.status}/5"
        )

    st.markdown("#### Détenteurs officiels des Domaines")
    for domain in sorted(state.domains.values(), key=lambda item: item.name):
        st.write(f"**{domain.name}** : {holder_label(state, domain)}")

    st.markdown("#### Renseignements sur les vampires")
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
            side = target_state.faction_memberships.get(character.id, ClanFactionSide.PRIMOGEN)
            st.caption(
                f"Faction : {FACTION_LABELS[side]} · relation effective au Primogène : "
                f"{effective_relation_to_primogen(state, character.id):+d} · influence {character.personal_influence:.0f}"
            )
    st.caption(
        "Les relations, griefs, ambitions, droits privés, pression territoriale et ordres restent cachés "
        "tant qu'ils ne sont pas découverts."
    )

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
    "V0.20 : politique vampirique persistante — crises Anarchs/chasseurs jouables, Praxis contestable, "
    "pactes diplomatiques, Étreintes, factions, coteries, Faim, Domaines, Viandis, Servage, Rempart, "
    "Prestation et conséquences."
)
