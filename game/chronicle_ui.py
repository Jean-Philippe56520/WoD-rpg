from __future__ import annotations

import uuid

import streamlit as st

from .chronicle import (
    ACTION_LABELS,
    CHRONICLE_GAME_ID,
    CHRONICLE_NAME,
    CLAN_DISCIPLINES,
    CLAN_LABELS,
    OFFICE_LABELS,
    ChronicleProgress,
    PersonalAction,
    SUPPORTED_CLANS,
    create_player_character,
    nightly_hook,
    resolve_personal_night,
    sire_for_id,
)
from .chronicle_scenes import ChronicleSceneStore
from .chronicle_service import ChronicleService
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
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
        "avec peu de Statut et presque aucun poids politique. Votre place se gagnera nuit après nuit."
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
            placeholder="Ex. obtenir un Domaine, devenir indispensable à la Cour…",
        )
        chapter_goal = st.text_input(
            "Objectif du premier chapitre",
            placeholder="Ex. comprendre mon sire, obtenir une autonomie de chasse…",
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
        f"Étreint en {character.embraced_year} · {OFFICE_LABELS.get(character.office, character.office)}"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Année", progress.year)
    col2.metric("Chapitre", progress.chapter)
    col3.metric("Segment", f"{progress.segment}/{progress.segments_per_chapter}")
    current_night = progress.nights_per_segment if character.ready_for_convergence else character.local_night
    col4.metric("Nuit", f"{current_night}/{progress.nights_per_segment}")

    vital1, vital2, vital3, vital4, vital5 = st.columns(5)
    vital1.metric("Faim", f"{character.hunger}/5")
    vital2.metric("Humanité", f"{character.humanity}/10")
    vital3.metric("Statut", character.status)
    vital4.metric("Influence", f"{character.personal_influence:.1f}")
    vital5.metric("Expérience", character.experience)


def _render_sire(character) -> None:
    with st.container(border=True):
        try:
            sire = sire_for_id(character.sire_id)
        except ValueError:
            st.markdown(f"### Votre sire — {character.sire_name}")
            st.write(f"**Relation :** {character.sire_relation}/3")
            st.caption("Votre sire appartient à votre lignée persistante.")
            return
        st.markdown(f"### Votre sire — {sire.name}")
        st.caption(sire.title)
        st.write(sire.description)
        st.write(f"**Protection :** {sire.protection}")
        st.write(f"**Attente :** {sire.expectation}")
        st.write(f"**Relation :** {character.sire_relation}/3")


def _render_journal(store: ChronicleStore, character) -> None:
    history = store.list_history(character.game_id, character.character_id, limit=30)
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


def _render_convergence(repo, store: ChronicleStore, character, progress) -> None:
    st.subheader("Convergence")
    st.write(
        "Vos nuits personnelles de ce segment sont terminées. Le monde peut continuer à discuter et à "
        "échanger, mais le prochain segment ne devient canonique qu'après la convergence."
    )
    characters = [pc for pc in store.list_characters(character.game_id) if pc.is_active]
    current_characters = [
        pc
        for pc in characters
        if pc.chapter == progress.chapter and pc.segment == progress.segment
    ]
    ready = [pc for pc in current_characters if pc.ready_for_convergence]
    st.progress(len(ready) / max(1, len(current_characters)))
    st.caption(f"{len(ready)}/{len(current_characters)} personnage(s) prêt(s).")
    for pc in current_characters:
        marker = "Prêt" if pc.ready_for_convergence else f"Nuit {pc.local_night}/{progress.nights_per_segment}"
        st.write(f"- {pc.name} — {CLAN_LABELS[pc.clan_id]} — {marker}")

    if store.all_ready_for_convergence(character.game_id):
        st.success("Toutes les trajectoires ont rejoint le point de convergence.")
        if st.button("Résoudre la convergence", type="primary", use_container_width=True):
            result = ChronicleService(repo).resolve_convergence(character.game_id)
            beats = " ".join(beat.public_text for beat in result.world_beats[:2])
            if result.next_progress.chapter > progress.chapter:
                notice = (
                    f"Le chapitre {progress.chapter} s'achève. Une ellipse de "
                    f"{result.next_progress.year - progress.year} an(s) conduit la chronique en "
                    f"{result.next_progress.year}."
                )
            else:
                notice = f"La convergence est résolue. Le segment {result.next_progress.segment} commence."
            if beats:
                notice += f" Pendant ce temps : {beats}"
            st.session_state["wod_last_chronicle_notice"] = notice
            st.rerun()


def _character_names(store: ChronicleStore, game_id: str) -> dict[str, str]:
    return {character.character_id: character.name for character in store.list_characters(game_id)}


def _render_scenes(repo, store: ChronicleStore, character, progress) -> None:
    scenes = ChronicleSceneStore(repo)
    characters = [
        pc
        for pc in store.list_characters(character.game_id)
        if pc.is_active and pc.character_id != character.character_id
    ]
    names = _character_names(store, character.game_id)

    st.subheader("Scènes entre personnages")
    st.caption(
        "Ces échanges sont asynchrones : vous pouvez ouvrir une scène puis continuer vos nuits. "
        "L'autre joueur répondra lorsqu'il se reconnectera."
    )

    if characters:
        with st.form(f"open_scene_{character.chapter}_{character.segment}_{character.local_night}"):
            target_id = st.selectbox(
                "Personnage à contacter",
                options=[pc.character_id for pc in characters],
                format_func=lambda value: names[value],
            )
            title = st.text_input("Objet de la scène", max_chars=160)
            opening = st.text_area("Votre approche", max_chars=2000)
            opened = st.form_submit_button("Ouvrir la scène", use_container_width=True)
        if opened:
            try:
                scenes.create_scene(
                    game_id=character.game_id,
                    from_character_id=character.character_id,
                    to_character_id=target_id,
                    chapter=character.chapter,
                    segment=character.segment,
                    night_number=character.local_night,
                    title=title,
                    opening_text=opening,
                )
                st.success("La scène a été transmise. Elle ne bloque pas votre progression personnelle.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("Aucun autre personnage joueur n'a encore rejoint cette chronique.")

    st.markdown("### Reçues")
    incoming = scenes.list_incoming(character.game_id, character.character_id)
    if not incoming:
        st.caption("Aucune scène reçue.")
    for scene in incoming:
        with st.container(border=True):
            sender = names.get(scene.from_character_id, scene.from_character_id)
            st.markdown(f"**{scene.title}** — {sender}")
            st.caption(
                f"Chapitre {scene.chapter} · Segment {scene.segment} · Nuit {scene.night_number} · {scene.status}"
            )
            st.write(scene.opening_text)
            if scene.response_text:
                st.write(f"**Votre réponse :** {scene.response_text}")
            elif scene.status == "open":
                with st.form(f"respond_scene_{scene.id}"):
                    response = st.text_area("Répondre", max_chars=2000, key=f"response_{scene.id}")
                    respond = st.form_submit_button("Envoyer la réponse", use_container_width=True)
                if respond:
                    try:
                        scenes.respond(
                            scene,
                            character_id=character.character_id,
                            response_text=response,
                        )
                        st.success("Réponse transmise.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    st.markdown("### Envoyées")
    outgoing = scenes.list_outgoing(character.game_id, character.character_id)
    if not outgoing:
        st.caption("Aucune scène envoyée.")
    for scene in outgoing:
        with st.container(border=True):
            target = names.get(scene.to_character_id, scene.to_character_id)
            st.markdown(f"**{scene.title}** — à {target}")
            st.caption(f"Statut : {scene.status}")
            st.write(scene.opening_text)
            if scene.response_text:
                st.write(f"**Réponse :** {scene.response_text}")


def _render_world(repo, progress) -> None:
    st.subheader(f"{progress.year} — un ordre encore incertain")
    st.write(
        "Les anciens, les sires et les institutions poursuivent leurs propres intérêts. Ils n'attendent pas "
        "les ordres des joueurs : leurs décisions deviennent visibles aux points de convergence."
    )
    events = ChronicleWorldStore(repo).list_events(CHRONICLE_GAME_ID, limit=20)
    if events:
        st.markdown("### Ce qui a changé autour de vous")
        for event in events:
            with st.container(border=True):
                st.write(event["public_text"])
                st.caption(
                    f"{event['year']} · Chapitre {event['chapter']} · Segment {event['segment']}"
                )
    else:
        st.caption("La première convergence n'a pas encore produit d'événement partagé.")

    st.markdown("### Rythme de la chronique")
    st.write(
        f"Vous pouvez jouer jusqu'à **{progress.nights_per_segment} nuits personnelles** sans attendre les "
        "autres. Les scènes PJ restent asynchrones. Une convergence rassemble ensuite les conséquences "
        "avant le segment suivant."
    )


def render_chronicle_app(
    repo,
    *,
    player_id: str,
    player_name: str = "Joueur",
    backend_label: str = "",
) -> None:
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
        st.write(f"**Fonction :** {OFFICE_LABELS.get(character.office, character.office)}")

    _render_header(character, progress)

    night_tab, scenes_tab, relations_tab, journal_tab, world_tab = st.tabs(
        ["Cette nuit", "Scènes", "Mes liens", "Journal", "Le monde"]
    )

    with night_tab:
        if character.ready_for_convergence:
            _render_convergence(repo, store, character, progress)
        else:
            st.subheader(f"Nuit {character.local_night}")
            st.info(nightly_hook(character))
            st.write(f"**Objectif du chapitre :** {character.chapter_goal}")
            st.caption(
                f"Progression actuelle : {character.goal_progress}. Ce score sert au bilan du chapitre ; "
                "il ne remplace pas les conséquences narratives."
            )
            with st.form(f"personal_night_{character.chapter}_{character.segment}_{character.local_night}"):
                action = st.selectbox(
                    "Votre engagement principal cette nuit",
                    options=list(PersonalAction),
                    format_func=lambda value: ACTION_LABELS[value],
                )
                free_intent = st.text_area(
                    "Précision libre",
                    placeholder="Ex. je cherche le copiste aperçu hier et veux savoir qui l'emploie…",
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

    with scenes_tab:
        _render_scenes(repo, store, character, progress)

    with relations_tab:
        _render_sire(character)
        st.markdown("### Votre position")
        st.write(f"**Ambition :** {character.long_term_goal}")
        st.write(f"**Réputation :** {character.reputation:+d}")
        st.write(f"**Discipline dominante :** {character.starting_discipline}")
        st.write(f"**Expérience accumulée :** {character.experience}")
        st.write(f"**Fonction :** {OFFICE_LABELS.get(character.office, character.office)}")
        st.caption(
            "Le Primogénat, un Domaine ou la Praxis seront des positions politiques à obtenir. "
            "Aucune fonction ne vous donne le contrôle direct des autres vampires."
        )

    with journal_tab:
        _render_journal(store, character)

    with world_tab:
        _render_world(repo, progress)
