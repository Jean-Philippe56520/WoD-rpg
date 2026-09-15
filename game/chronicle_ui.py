from __future__ import annotations

from dataclasses import replace
import uuid

import streamlit as st

from .chronicle import (
    CHRONICLE_GAME_ID,
    CHRONICLE_NAME,
    CLAN_DISCIPLINES,
    CLAN_LABELS,
    OFFICE_LABELS,
    ChronicleProgress,
    SUPPORTED_CLANS,
    create_player_character,
    sire_for_id,
)
from .chronicle_offices import office_eligibility
from .chronicle_scenes import ChronicleSceneStore
from .chronicle_service import ChronicleService
from .chronicle_simulation import active_hunting_access, ensure_character_links
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
from .clans import clan_identity
from .era import era_for_year
from .models import GameState
from .sire_relations import sire_bond
from .situations import generate_situations, resolve_situation
from .vampire_profile import default_profile
from .vampire_profile_store import VampireProfileStore


MORTAL_STANCE_LABELS = {
    "humanist": "Humaniste",
    "predatory": "Prédateur",
}
ORDER_STANCE_LABELS = {
    "orthodox": "Attaché aux anciens usages",
    "reformist": "Réformateur",
}
ROAD_LABELS = {
    "humanitatis": "Via Humanitatis",
    "regalis": "Via Regalis",
    "caeli": "Via Caeli",
    "bestiae": "Via Bestiae",
    "peccati": "Via Peccati",
    "via_mutationis": "Voie de la transformation",
}
CAMARILLA_STAGE_LABELS = {
    "absent": "Aucune Camarilla constituée",
    "project": "Camarilla naissante — coalition annoncée",
    "coalition": "Coalition proto-Camarilla",
    "institutional": "Camarilla institutionnelle",
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


def _render_creation(
    store: ChronicleStore,
    profile_store: VampireProfileStore,
    simulation_store: ChronicleSimulationStore,
    player_id: str,
    default_player_name: str,
) -> None:
    st.title("WoD RPG — Les Premières Nuits")
    st.caption("1435 · Révolte, lignages et naissance d'un nouvel ordre")
    st.markdown(
        "Vous êtes un vampire récemment Étreint. Votre sire répond encore de vous, votre droit de chasse dépend "
        "d'autrui et la Camarilla qui vient d'être annoncée reste une coalition contestée, loin de son ordre futur."
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
            "Concept mortel / social",
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
        conviction = st.text_input(
            "Conviction",
            placeholder="Ex. Je ne sacrifierai pas un innocent pour ma propre sécurité.",
        )
        touchstone = st.text_input(
            "Pierre de touche mortelle",
            placeholder="Ex. ma sœur restée humaine, mon ancien apprenti, un village protégé…",
        )
        road_affinity = st.selectbox(
            "Affinité de Voie",
            options=("humanitatis", "regalis", "caeli", "bestiae", "peccati"),
            format_func=lambda value: ROAD_LABELS[value],
        )
        feeding_preference = st.text_input(
            "Préférence de chasse",
            placeholder="Particulièrement importante pour un Ventrue ; sinon facultative.",
        )
        current_desire = st.text_input(
            "Désir immédiat",
            placeholder="Ex. obtenir une nuit sans ordre de mon sire.",
        )
        long_term_goal = st.text_input(
            "Ambition à long terme",
            placeholder="Ex. obtenir un Domaine, devenir indispensable à la Cour…",
        )
        chapter_goal = st.text_input(
            "Objectif du premier chapitre",
            placeholder="Ex. obtenir une autonomie de chasse, comprendre mon sire…",
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
    if not conviction.strip() or not touchstone.strip():
        st.error("Une Conviction et une Pierre de touche sont nécessaires pour commencer.")
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

    profile = default_profile(character)
    profile = replace(
        profile,
        convictions=(conviction.strip(),),
        touchstones=(touchstone.strip(),),
        road_affinity=road_affinity,
        current_desire=(current_desire.strip() or profile.current_desire),
        feeding_preference=(feeding_preference.strip() or profile.feeding_preference),
    )
    profile_store.save(profile)

    simulation = simulation_store.ensure(CHRONICLE_GAME_ID, year=progress.year)
    linked = ensure_character_links(simulation, character)
    if linked != simulation:
        simulation_store.save(linked)

    st.session_state["wod_last_chronicle_notice"] = (
        f"{character.name} a été Étreint en {character.embraced_year}. "
        f"{character.sire_name} répond encore de ses actes et lui ouvre un premier accès à la chasse."
    )
    st.rerun()


def _render_header(character, profile, progress) -> None:
    st.title(character.name)
    st.caption(
        f"{CLAN_LABELS[character.clan_id]} · {character.concept} · "
        f"{profile.generation}e génération · Étreint en {character.embraced_year} · "
        f"{OFFICE_LABELS.get(character.office, character.office)}"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Année", progress.year)
    col2.metric("Chapitre", progress.chapter)
    col3.metric("Segment", f"{progress.segment}/{progress.segments_per_chapter}")
    current_night = progress.nights_per_segment if character.ready_for_convergence else character.local_night
    col4.metric("Nuit", f"{current_night}/{progress.nights_per_segment}")

    vital1, vital2, vital3, vital4, vital5, vital6 = st.columns(6)
    vital1.metric("Faim", f"{character.hunger}/5")
    vital2.metric("Humanité", f"{character.humanity}/10")
    vital3.metric("Volonté", profile.willpower)
    vital4.metric("Statut", character.status)
    vital5.metric("Influence", f"{character.personal_influence:.1f}")
    vital6.metric("Expérience", character.experience)


def _render_sire(character, profile, era) -> None:
    bond = sire_bond(character, profile, era)
    with st.container(border=True):
        try:
            sire = sire_for_id(character.sire_id)
        except ValueError:
            st.markdown(f"### Votre sire — {character.sire_name}")
            st.write(f"**Relation :** {character.sire_relation}/3")
        else:
            st.markdown(f"### Votre sire — {sire.name}")
            st.caption(sire.title)
            st.write(sire.description)
            st.write(f"**Protection :** {sire.protection}")
            st.write(f"**Attente :** {sire.expectation}")
            st.write(f"**Relation :** {character.sire_relation}/3")
        st.write(bond.authority_text)
        st.caption(bond.protection_text)
        if bond.can_seek_release:
            st.info("Votre position permet désormais d'envisager une négociation formelle d'autonomie.")


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
        "Vos nuits personnelles de ce segment sont terminées. Les messages et scènes restent accessibles, "
        "mais le prochain état canonique de la cité sera fixé lors de cette convergence."
    )
    characters = [pc for pc in store.list_characters(character.game_id) if pc.is_active]
    current_characters = [
        pc for pc in characters if pc.chapter == progress.chapter and pc.segment == progress.segment
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


def _render_scenes(repo, store: ChronicleStore, character) -> None:
    scenes = ChronicleSceneStore(repo)
    characters = [
        pc
        for pc in store.list_characters(character.game_id)
        if pc.is_active and pc.character_id != character.character_id
    ]
    names = _character_names(store, character.game_id)

    st.subheader("Scènes entre personnages")
    st.caption(
        "Ces échanges sont asynchrones. Une demande peut rester ouverte pendant que chacun poursuit ses autres affaires."
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
                st.success("La scène a été transmise.")
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
            st.caption(f"Chapitre {scene.chapter} · Segment {scene.segment} · Nuit {scene.night_number}")
            st.write(scene.opening_text)
            if scene.response_text:
                st.write(f"**Votre réponse :** {scene.response_text}")
            elif scene.status == "open":
                with st.form(f"respond_scene_{scene.id}"):
                    response = st.text_area("Répondre", max_chars=2000, key=f"response_{scene.id}")
                    respond = st.form_submit_button("Envoyer la réponse", use_container_width=True)
                if respond:
                    try:
                        scenes.respond(scene, character_id=character.character_id, response_text=response)
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


def _render_profile(character, profile) -> None:
    identity = clan_identity(character.clan_id)
    st.markdown("### Votre Sang")
    st.write(identity.medieval_position)
    st.write(f"**Fléau — {identity.bane_name} :** {identity.bane_text}")
    st.write(f"**Génération :** {profile.generation}e")
    st.write(f"**Puissance du Sang :** {profile.blood_potency}")
    st.write(f"**Affinité de Voie :** {ROAD_LABELS.get(profile.road_affinity, profile.road_affinity)}")
    st.write(f"**Conviction :** {profile.convictions[0]}")
    st.write(f"**Pierre de touche :** {profile.touchstones[0]}")
    st.write(f"**Désir actuel :** {profile.current_desire}")
    if profile.feeding_preference:
        st.write(f"**Préférence de chasse :** {profile.feeding_preference}")


def _render_domain_and_debts(character, simulation, year: int) -> None:
    st.subheader("Chasse et Domaine")
    rights = active_hunting_access(simulation, character.character_id, year)
    if not rights:
        st.warning("Vous ne disposez actuellement d'aucun droit de chasse reconnu.")
    for right in rights:
        domain = simulation.domains[right.domain_id]
        holder = simulation.npcs.get(domain.holder_id or "")
        holder_name = holder.name if holder else (domain.holder_id or "sans détenteur reconnu")
        with st.container(border=True):
            st.markdown(f"**{domain.name}**")
            st.write(domain.description)
            st.write(f"Détenteur : **{holder_name}**")
            st.write(
                f"Viandis **{domain.viandis}/3** · Servage **{domain.servage}/3** · Rempart **{domain.rempart}/3**"
            )
            st.caption(f"Accès : {right.source} · Pression {domain.pressure} · Risque {domain.masquerade_risk}/3")

    st.subheader("Faveurs et dettes")
    relevant = [
        boon for boon in simulation.boons.values()
        if boon.creditor_id == character.character_id or boon.debtor_id == character.character_id
    ]
    if not relevant:
        st.caption("Aucune faveur formalisée ne vous lie encore.")
    for boon in relevant:
        if boon.creditor_id == character.character_id:
            direction = "On vous doit"
            other_id = boon.debtor_id
        else:
            direction = "Vous devez"
            other_id = boon.creditor_id
        other = simulation.npcs.get(other_id)
        other_name = other.name if other else other_id
        st.write(f"- **{direction}** une faveur {boon.level} — {other_name} · {boon.status} · {boon.origin}")


def _render_world(repo, character, simulation, progress) -> None:
    era = era_for_year(progress.year)
    st.subheader(f"{progress.year} — {era.label}")
    st.write(era.public_context)
    st.info(CAMARILLA_STAGE_LABELS.get(era.camarilla_stage.value, era.camarilla_stage.value))
    if not era.primogen_council_standardized:
        st.caption(
            "Le Prince et des conseils locaux peuvent exister, mais le jeu ne suppose pas encore un Conseil des Primogènes standardisé."
        )

    st.markdown("### Pouvoirs visibles")
    prince_id = simulation.offices.get("prince")
    prince = simulation.npcs.get(prince_id or "")
    if prince:
        st.write(f"**Prince local :** {prince.name} — {prince.clan_id.title()}")
    st.write(f"**Caïnites connus du moteur :** {len(simulation.npcs)} PNJ actifs ou persistants")

    eligibilities = office_eligibility(character, simulation, era)
    with st.expander("Votre accès aux fonctions politiques"):
        for item in eligibilities:
            state = "accessible" if item.available else "non institutionnalisé"
            readiness = "éligible" if item.eligible else "pas encore éligible"
            st.write(f"**{OFFICE_LABELS.get(item.office, item.office)}** — {state}, {readiness}")
            st.caption(item.reason)

    events = ChronicleWorldStore(repo).list_events(CHRONICLE_GAME_ID, limit=20)
    if events:
        st.markdown("### Ce qui a changé autour de vous")
        for event in events:
            with st.container(border=True):
                st.write(event["public_text"])
                st.caption(f"{event['year']} · Chapitre {event['chapter']} · Segment {event['segment']}")
    else:
        st.caption("La première convergence n'a pas encore produit d'événement partagé.")


def _render_night(
    store,
    profile_store,
    simulation_store,
    character,
    profile,
    simulation,
    progress,
) -> None:
    st.subheader(f"Nuit {character.local_night}")
    st.write(f"**Objectif du chapitre :** {character.chapter_goal}")
    st.caption(
        f"Progression actuelle : {character.goal_progress}. Les propositions ci-dessous sont des situations, "
        "pas une liste d'actions abstraites : choisissez celle que votre vampire décide réellement d'affronter."
    )

    situations = generate_situations(character, profile, simulation, year=progress.year)
    for situation in situations:
        with st.container(border=True):
            st.markdown(f"### {situation.title}")
            st.write(situation.body)
            with st.form(
                f"situation_{character.chapter}_{character.segment}_{character.local_night}_{situation.id}"
            ):
                choice_id = st.radio(
                    "Votre décision",
                    options=[choice.id for choice in situation.choices],
                    format_func=lambda value: next(
                        choice.label for choice in situation.choices if choice.id == value
                    ),
                )
                selected = next(choice for choice in situation.choices if choice.id == choice_id)
                st.caption(selected.description)
                free_intent = st.text_area(
                    "Précision libre",
                    placeholder="Votre manière d'agir, ce que vous cachez, ce que vous cherchez vraiment…",
                    max_chars=500,
                    key=f"intent_{situation.id}",
                )
                play = st.form_submit_button(
                    "Jouer cette situation",
                    type="primary",
                    use_container_width=True,
                )
            if play:
                resolution = resolve_situation(
                    character,
                    profile,
                    simulation,
                    situation,
                    choice_id,
                    nights_per_segment=progress.nights_per_segment,
                    free_intent=free_intent,
                )
                store.advance_personal_night(
                    character,
                    resolution.outcome,
                    free_intent=free_intent,
                )
                simulation_store.save(resolution.simulation)
                profile_store.save(resolution.profile)
                dice = resolution.dice
                st.session_state["wod_last_chronicle_notice"] = (
                    f"{resolution.outcome.summary} {resolution.outcome.detail} "
                    f"[{dice.successes} succès sur difficulté {dice.difficulty}]"
                )
                st.rerun()


def render_chronicle_app(
    repo,
    *,
    player_id: str,
    player_name: str = "Joueur",
    backend_label: str = "",
) -> None:
    store = _ensure_chronicle(repo)
    profile_store = VampireProfileStore(repo)
    simulation_store = ChronicleSimulationStore(repo)
    progress = store.get_progress(CHRONICLE_GAME_ID)
    if progress is None:
        st.error("Impossible d'initialiser la chronique.")
        return

    character = store.get_character(CHRONICLE_GAME_ID, player_id)
    if character is None:
        _render_creation(
            store,
            profile_store,
            simulation_store,
            player_id,
            player_name,
        )
        return

    profile = profile_store.ensure_for_character(character)
    simulation = simulation_store.ensure(CHRONICLE_GAME_ID, year=progress.year)
    linked = ensure_character_links(simulation, character)
    if linked != simulation:
        simulation = simulation_store.save(linked)

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

    _render_header(character, profile, progress)

    night_tab, scenes_tab, relations_tab, domain_tab, journal_tab, world_tab = st.tabs(
        ["Cette nuit", "Scènes", "Mes liens", "Domaine & dettes", "Journal", "Le monde"]
    )

    with night_tab:
        if character.ready_for_convergence:
            _render_convergence(repo, store, character, progress)
        else:
            _render_night(
                store,
                profile_store,
                simulation_store,
                character,
                profile,
                simulation,
                progress,
            )

    with scenes_tab:
        _render_scenes(repo, store, character)

    with relations_tab:
        _render_sire(character, profile, era_for_year(progress.year))
        _render_profile(character, profile)
        st.markdown("### Votre position")
        st.write(f"**Ambition :** {character.long_term_goal}")
        st.write(f"**Réputation :** {character.reputation:+d}")
        st.write(f"**Expérience accumulée :** {character.experience}")

    with domain_tab:
        _render_domain_and_debts(character, simulation, progress.year)

    with journal_tab:
        _render_journal(store, character)

    with world_tab:
        _render_world(repo, character, simulation, progress)
