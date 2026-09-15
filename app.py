from __future__ import annotations

from pathlib import Path
import uuid

import streamlit as st

import game.repository_factory as repository_factory
from game.agency_ui import render_agency_panel
from game.auth import (
    DEFAULT_SUPABASE_PUBLISHABLE_KEY,
    AuthError,
    AuthSession,
    SupabaseAuthClient,
)
from game.browser_session import (
    clear_device_refresh_token,
    persist_device_refresh_token,
    read_device_refresh_token,
)
from game.chronicle_ui import render_chronicle_app
from game.coterie_ui import render_coteries_panel
from game.court_ui import render_court_panel
from game.crisis_ui import render_crises_panel
from game.diplomatic_pact_ui import render_diplomatic_pacts_panel
from game.external_pressure_ui import render_external_pressure_panel
from game.hunger_ui import render_hunger_panel
from game.information_ui import render_information_panel
from game.runtime import (
    PRODUCTION_GAME_ID,
    PRODUCTION_MODE,
    WORKSHOP_GAME_NAME,
    WORKSHOP_MODE,
    WORKSHOP_PLAYERS,
    RuntimeBackendLabel,
    RuntimeGameRepository,
    set_runtime_mode,
)
from game.world import REQUIRED_CLANS, create_initial_game_state


AUTH_SESSION_KEY = "wod_auth_session"
AUTH_SEEN_KEY = "wod_auth_seen_in_streamlit_session"
LOCAL_PLAYER_KEY = "wod_local_player_id"
LOCAL_CHRONICLE_PLAYER_KEY = "wod_local_chronicle_player_id"

st.set_page_config(
    page_title="WoD RPG - Chronique vampirique",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

_ORIGINAL_CREATE_REPOSITORY = repository_factory.create_repository


@st.cache_resource
def _base_repository():
    return _ORIGINAL_CREATE_REPOSITORY(st.secrets)


@st.cache_resource
def _launcher_auth_client() -> SupabaseAuthClient:
    url = str(st.secrets.get("SUPABASE_URL", "")).strip()
    key = str(
        st.secrets.get("SUPABASE_PUBLISHABLE_KEY", DEFAULT_SUPABASE_PUBLISHABLE_KEY)
    ).strip()
    return SupabaseAuthClient(url, key)


def _restore_persistent_session(backend: str) -> None:
    if backend != "Supabase":
        return

    auth = _launcher_auth_client()
    session = st.session_state.get(AUTH_SESSION_KEY)
    if session is not None and not isinstance(session, AuthSession):
        st.session_state.pop(AUTH_SESSION_KEY, None)
        session = None

    if session is None and st.session_state.get(AUTH_SEEN_KEY):
        st.session_state[AUTH_SEEN_KEY] = False
        clear_device_refresh_token()
        return

    if isinstance(session, AuthSession):
        try:
            session = auth.validate(session)
            st.session_state[AUTH_SESSION_KEY] = session
            st.session_state[AUTH_SEEN_KEY] = True
            persist_device_refresh_token(session.refresh_token)
            return
        except AuthError:
            st.session_state.pop(AUTH_SESSION_KEY, None)
            st.session_state[AUTH_SEEN_KEY] = False
            clear_device_refresh_token()
            return

    stored = read_device_refresh_token()
    if not stored.loaded:
        st.info("Recherche d'une session enregistrée sur cet appareil…")
        st.stop()
    if stored.error:
        st.sidebar.caption("La mémorisation de session n'est pas disponible sur ce navigateur.")
        return
    if not stored.value:
        return

    try:
        session = auth.refresh(stored.value)
        session = auth.validate(session)
        st.session_state[AUTH_SESSION_KEY] = session
        st.session_state[AUTH_SEEN_KEY] = True
        persist_device_refresh_token(session.refresh_token)
    except AuthError:
        st.session_state.pop(AUTH_SESSION_KEY, None)
        st.session_state[AUTH_SEEN_KEY] = False
        clear_device_refresh_token()


def _render_authentication(auth: SupabaseAuthClient) -> None:
    st.title("WoD RPG — Les Premières Nuits")
    st.subheader("Connexion à la chronique")
    st.write(
        "Votre compte retrouve automatiquement votre vampire sur cet appareil. "
        "La connexion est distincte de votre personnage : celui-ci sera créé après authentification."
    )
    login_tab, signup_tab = st.tabs(["Connexion", "Créer un compte"])

    with login_tab:
        with st.form("launcher_login_form"):
            email = st.text_input("Email", key="launcher_login_email")
            password = st.text_input(
                "Mot de passe", type="password", key="launcher_login_password"
            )
            submitted = st.form_submit_button(
                "Se connecter", type="primary", use_container_width=True
            )
        if submitted:
            try:
                session = auth.sign_in(email, password)
                st.session_state[AUTH_SESSION_KEY] = session
                st.session_state[AUTH_SEEN_KEY] = True
                persist_device_refresh_token(session.refresh_token)
                st.rerun()
            except (AuthError, ValueError) as exc:
                st.error(str(exc))

    with signup_tab:
        with st.form("launcher_signup_form"):
            email = st.text_input("Email", key="launcher_signup_email")
            password = st.text_input(
                "Mot de passe", type="password", key="launcher_signup_password"
            )
            password_confirm = st.text_input(
                "Confirmer le mot de passe",
                type="password",
                key="launcher_signup_password_confirm",
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
                        st.session_state[AUTH_SEEN_KEY] = True
                        persist_device_refresh_token(session.refresh_token)
                        st.rerun()
                    st.success(
                        "Compte créé. Si un email de confirmation a été envoyé, validez-le puis connectez-vous."
                    )
                except (AuthError, ValueError) as exc:
                    st.error(str(exc))
    st.stop()


def _assign_workshop_players(repo: RuntimeGameRepository) -> None:
    repo.ensure_game(
        PRODUCTION_GAME_ID,
        WORKSHOP_GAME_NAME,
        create_initial_game_state(),
        REQUIRED_CLANS,
    )
    for clan_id, (player_id, player_name) in WORKSHOP_PLAYERS.items():
        repo.claim_clan(PRODUCTION_GAME_ID, player_id, player_name, clan_id)


mode = st.sidebar.radio(
    "Mode d'accès",
    options=(PRODUCTION_MODE, WORKSHOP_MODE),
    format_func=lambda value: "Chronique" if value == PRODUCTION_MODE else "Atelier legacy (test/dev)",
    key="wod_runtime_mode_selector",
)
st.sidebar.caption("Moteur V0.43 — Paris 1435, société caïnite autonome")
set_runtime_mode(mode)

try:
    base_repo, backend = _base_repository()
except (RuntimeError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

runtime_repo = RuntimeGameRepository(base_repo)
backend_label = RuntimeBackendLabel(backend)


def _runtime_create_repository(*args, **kwargs):
    return runtime_repo, backend_label


if mode == PRODUCTION_MODE:
    _restore_persistent_session(backend)
    if backend == "Supabase":
        auth = _launcher_auth_client()
        session = st.session_state.get(AUTH_SESSION_KEY)
        if not isinstance(session, AuthSession):
            _render_authentication(auth)
        player_id = session.user_id
        player_name = session.email.split("@", 1)[0] if session.email else "Joueur"
        with st.sidebar:
            if session.email:
                st.caption(f"Compte : {session.email}")
            if st.button("Se déconnecter", use_container_width=True):
                try:
                    auth.sign_out(session.access_token)
                except AuthError:
                    pass
                st.session_state.pop(AUTH_SESSION_KEY, None)
                st.session_state[AUTH_SEEN_KEY] = False
                clear_device_refresh_token()
                st.rerun()
    else:
        if LOCAL_CHRONICLE_PLAYER_KEY not in st.session_state:
            st.session_state[LOCAL_CHRONICLE_PLAYER_KEY] = f"local:{uuid.uuid4().hex}"
        player_id = st.session_state[LOCAL_CHRONICLE_PLAYER_KEY]
        player_name = "Joueur local"

    render_chronicle_app(
        runtime_repo,
        player_id=player_id,
        player_name=player_name,
        backend_label=str(backend_label),
    )
    st.stop()


# L'Atelier conserve volontairement le moteur V0.20.1 comme banc de test et de
# comparaison pendant la migration. Il ne touche jamais aux Chroniques personnelles.
st.sidebar.warning("MODE ATELIER — moteur politique V0.20.1 isolé")
try:
    _assign_workshop_players(runtime_repo)
except ValueError as exc:
    st.error(f"Atelier incohérent : {exc}")
    st.stop()

selected_clan = st.sidebar.selectbox(
    "Incarner le clan",
    options=REQUIRED_CLANS,
    format_func=lambda clan_id: clan_id.capitalize(),
    key="wod_workshop_clan",
)
st.session_state[LOCAL_PLAYER_KEY] = WORKSHOP_PLAYERS[selected_clan][0]

if st.sidebar.button("Réinitialiser l'Atelier", use_container_width=True):
    runtime_repo.reset_workshop_game(
        WORKSHOP_GAME_NAME,
        create_initial_game_state(),
        REQUIRED_CLANS,
    )
    _assign_workshop_players(runtime_repo)
    st.rerun()

ui_path = Path(__file__).with_name("game_ui.py")
repository_factory.create_repository = _runtime_create_repository
try:
    exec(compile(ui_path.read_text(encoding="utf-8"), str(ui_path), "exec"), globals(), globals())
finally:
    repository_factory.create_repository = _ORIGINAL_CREATE_REPOSITORY

if "state" in globals() and "player_clan" in globals() and player_clan:
    render_coteries_panel(state, player_clan)
    render_court_panel(state, player_clan)
    render_hunger_panel(state, player_clan)
    render_information_panel(state, player_clan)
    render_agency_panel(state, player_clan)
    render_diplomatic_pacts_panel(state, player_clan)
    render_crises_panel(state, player_clan)
    render_external_pressure_panel(state, player_clan)
