from __future__ import annotations

import uuid

import streamlit as st

from .chronicle import (
    ACTION_LABELS,
    CHRONICLE_GAME_ID,
    CHRONICLE_NAME,
    CLAN_DISCIPLINES,
    CLAN_LABELS,
    ChronicleProgress,
    PersonalAction,
    SUPPORTED_CLANS,
    create_player_character,
    nightly_hook,
    resolve_personal_night,
    sire_for_id,
)
from .chronicle_store import ChronicleStore
from .models import GameState


MORTAL_STANCE_LABELS = {
    "humanist": "Humaniste",
    "predatory": "Prédateur",
}
ORDER_STANCE_LABELS = {
    "orthodox": "Attaché aux anciens usages",
    "reformist": "Réformateur",
}


def _ensure_chronicle(repo) -> ChronicleStore:
    repo.ensure_game(
        CHRONICLE_GAME_ID,
        CHRONICLE_NAME,
        GameState(),
        SUPPORTED_CLANS,
    )
    store = ChronicleStore(repo)
    store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    return store


def _render_creation(store: ChronicleStore, player_id: str, default_player_name: str) -> None:
    st.title("WoD RPG — Les Premières Nuits")
    st.caption("1435 · La société caïnite se cherche encore un ordre commun")
    st.markdown(
        "Vous n'êtes pas un clan. Vous êtes un vampire récemment Étreint, encore dépendant de votre sire, "
        "avec peu de Statut et presque aucun poids politique. Ce que vous deviendrez dépendra des nuits à venir."
    )

    with st.form("create_player_character"):
        st.subheader("Créer votre vampire")
        player_name = st.text_input("Nom du joueur", value=default_player_name or "Joueur")
        name = st.text_input("Nom du vampire")
        clan_id = st.selectbox(
            "Clan",
            options=SUPPORTED_CLANS,
            format_func=lambda value: CLAN_LABELS[value],
        )
        concept = st.text_input(
            "Concept",
            placeholder="Ex. chevalier déchu, copiste monastique, héritière marchande…",
        )
        mortal_stance = st.selectbox(
            "Rapport aux mortels",
            options=("humanist", "predatory"),
            format_func=lambda value: MORTAL_STANCE_LABELS[value],
        )
        order_stance = st.selectbox(
            "Rapport à l'ordre caïnite",
            options=("orthodox", "reformist"),
            format_func=lambda value: ORDER_STANCE_LABELS[value],
        )
        starting_discipline = st.selectbox(
            "Discipline de départ dominante",
            options=CLAN_DISCIPLINES[clan_id],
        )
        long_term_goal = st.text_input(
            "Ambition à long terme",
            placeholder="Ex. obtenir un domaine, devenir indispensable à la Cour…",
        )
        chapter_goal = st.text_input(
            "Objectif du premier chapitre",
            placeholder="Ex. comprendre les attentes de mon sire, gagner mon indépendance…",
        )
        submitted = st.form_submit_button(
            "Commencer la chronique",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return
    if not name.strip():
        st.error("Votre vampire doit avoir un nom.")
        return

    progress = store.get_progress(CHRONICLE_GAME_ID)
    if progress is None:
        st.error("La chronologie de la chronique est introuvable.")
        return

    character = create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=player_id,
        player_name=player_name,
        character_id=f"pc_{uuid.uuid4().hex}",
        name=name,
        clan_id=clan_id,
        concept=concept,
        starting_discipline=starting_discipline,
        mortal_stance=mortal_stance,
        order_stance=order_stance,
        long_term_goal=long_term_goal,
        chapter_goal=chapter_goal,
        progress=progress,
    )
    store.create_character(character)
    st.session_state["wod_last_chronicle_notice"] = (
        f"{character.name} a été Étreint en {character.embraced_year}. "
        f"Son sire, {character.sire_name}, répond encore de lui devant les autres Caïnites."
    )
    st.rerun()


def _render_header(character, progress) -> None:
    st.title(character.name)
    st.caption(
        f"{CLAN_LABELS[character.clan_id]} · {character.concept} · "
        f"Étreint en {character.embraced_year}"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Année", progress.year)
    col2.metric("Chapitre", progress.chapter)
    col3.metric("Segment", f"{progress.segment}/{progress.segments_per_chapter}")
    if character.ready_for_convergence:
        col4.metric("Nuit", f"{progress.nights_per_segment}/{progress.nights_per_segment}")
    else:
        col4.metric("Nuit", f"{character.local_night}/{progress.nights_per_segment}")

    vital1, vital2, vital3, vital4 = st.columns(4)
    vital1.metric("Faim", f"{character.hunger}/5")
    vital2.metric("Humanité", f"{character.humanity}/10")
    vital3.metric("Statut", character.status)
    vital4.metric("Influence", f"{character.personal_influence:.1f}")


def _render_sire(character) -> None:
    sire = sire_for_id(character.sire_id)
    with st.container(border=True):
        st.markdown(f"### Votre sire — {sire.name}")
        st.caption(sire.title)
        st.write(sire.description)
        st.write(f"**Protection :** {sire.protection}")
        st.write(f"**Attente :** {sire.expectation}")
        st.write(f"**Relation :** {character.sire_relation}/3")


def _render_journal(store: ChronicleStore, character) -> None:
    history = store.list_history(character.game_id, character.character_id, limit=20)
    if not history:
        st.caption("Aucune nuit n'a encore été jouée.")
        return
    for item in history:
        outcome = item.get("outcome_json") or {}
        with st.container(border=True):
            st.markdown(
                f"**Chapitre {item['chapter']} · Segment {item['segment']} · Nuit {item['night_number']}**"
            )
            st.write(outcome.get("summary", item["action"]))
            detail = outcome.get("detail")
            if detail:
                st.caption(detail)


def _render_convergence(store: ChronicleStore, character, progress) -> None:
    st.subheader("Convergence")
    st.write(
        "Vous avez terminé vos nuits personnelles de ce segment. Vous pouvez encore consulter votre journal "
        "et vos relations, mais le prochain segment ne commencera qu'une fois les trajectoires réunies."
    )
    characters = [pc for pc in store.list_characters(character.game_id) if pc.is_active]
    ready = [pc for pc in characters if pc.ready_for_convergence]
    st.progress(len(ready) / max(1, len(characters)))
    st.caption(f"{len(ready)}/{len(characters)} personnage(s) prêt(s).")
    for pc in characters:
        marker = "Prêt" if pc.ready_for_convergence else f"Nuit {pc.local_night}/{progress.nights_per_segment}"
        st.write(f"- {pc.name} — {CLAN_LABELS[pc.clan_id]} — {marker}")

    if store.all_ready_for_convergence(character.game_id):
        st.success("Toutes les trajectoires ont rejoint le point de convergence.")
        if st.button("Résoudre la convergence", type="primary", use_container_width=True):
            next_progress = store.resolve_convergence(character.game_id)
            if next_progress.chapter > progress.chapter:
                st.session_state["wod_last_chronicle_notice"] = (
                    f"Le chapitre {progress.chapter} s'achève. Une ellipse de "
                    f"{next_progress.year - progress.year} an(s) conduit la chronique en {next_progress.year}."
                )
            else:
                st.session_state["wod_last_chronicle_notice"] = (
                    f"La convergence est résolue. Le segment {next_progress.segment} commence."
                )
            st.rerun()


def render_chronicle_app(repo, *, player_id: str, player_name: str = "Joueur", backend_label: str = "") -> None:
    store = _ensure_chronicle(repo)
    progress = store.get_progress(CHRONICLE_GAME_ID)
    if progress is None:
        st.error("Impossible d'initialiser la chronique.")
        return

    character = store.get_character(CHRONICLE_GAME_ID, player_id)
    if character is None:
        _render_creation(store, player_id, player_name)
        return

    notice = st.session_state.pop("wod_last_chronicle_notice", None)
    if notice:
        st.success(notice)

    with st.sidebar:
        st.header("Chronique")
        st.write(f"**{CHRONICLE_NAME}**")
        st.caption(f"Persistance : {backend_label}")
        st.write(f"**Année :** {progress.year}")
        st.write(f"**Chapitre :** {progress.chapter}")
        st.write(f"**Segment :** {progress.segment}/{progress.segments_per_chapter}")
        st.divider()
        st.write(f"**Personnage :** {character.name}")
        st.write(f"**Clan :** {CLAN_LABELS[character.clan_id]}")
        st.write(f"**Sire :** {character.sire_name}")

    _render_header(character, progress)

    night_tab, relations_tab, journal_tab, world_tab = st.tabs(
        ["Cette nuit", "Mes liens", "Journal", "Le monde"]
    )

    with night_tab:
        if character.ready_for_convergence:
            _render_convergence(store, character, progress)
        else:
            st.subheader(f"Nuit {character.local_night}")
            st.info(nightly_hook(character))
            st.write(f"**Objectif du chapitre :** {character.chapter_goal}")
            st.caption(
                f"Progression actuelle : {character.goal_progress}. Il ne s'agit pas d'une quête linéaire : "
                "ce score mesure simplement ce que votre vampire a réellement réussi à construire."
            )
            with st.form(f"personal_night_{character.chapter}_{character.segment}_{character.local_night}"):
                action = st.selectbox(
                    "Votre engagement principal cette nuit",
                    options=list(PersonalAction),
                    format_func=lambda value: ACTION_LABELS[value],
                )
                free_intent = st.text_area(
                    "Précision libre",
                    placeholder="Ex. je cherche le copiste aperçu hier, je veux savoir qui l'emploie…",
                    max_chars=500,
                )
                play = st.form_submit_button(
                    "Jouer cette nuit",
                    type="primary",
                    use_container_width=True,
                )
            if play:
                outcome = resolve_personal_night(
                    character,
                    action,
                    nights_per_segment=progress.nights_per_segment,
                    free_intent=free_intent,
                )
                store.advance_personal_night(character, outcome, free_intent=free_intent)
                st.session_state["wod_last_chronicle_notice"] = (
                    f"{outcome.summary} {outcome.detail}"
                )
                st.rerun()

    with relations_tab:
        _render_sire(character)
        st.markdown("### Votre position")
        st.write(f"**Ambition :** {character.long_term_goal}")
        st.write(f"**Réputation :** {character.reputation:+d}")
        st.write(f"**Discipline dominante :** {character.starting_discipline}")
        st.caption(
            "Les autres membres du clan, la Cour et les coteries ne sont pas vos unités. Ils agiront pour leurs "
            "propres intérêts au fur et à mesure de la refonte du moteur autonome."
        )

    with journal_tab:
        _render_journal(store, character)

    with world_tab:
        st.subheader("1435 — un ordre encore incertain")
        st.write(
            "Les anciens cherchent à contenir les révoltes, les menaces mortelles et leurs propres rivalités. "
            "Les institutions qui deviendront centrales dans les siècles suivants ne constituent pas encore un "
            "cadre uniforme. Votre vampire entre dans l'histoire avant d'en connaître l'issue."
        )
        st.markdown("### Rythme de la chronique")
        st.write(
            f"Vous pouvez jouer jusqu'à **{progress.nights_per_segment} nuits personnelles** sans attendre les "
            "autres. Ensuite, une convergence rassemble les trajectoires avant le segment suivant."
        )
