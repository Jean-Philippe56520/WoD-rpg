from __future__ import annotations

import uuid

import streamlit as st

from .chronicle import (
    CHRONICLE_NAME,
    CLAN_DISCIPLINES,
    CLAN_LABELS,
    OFFICE_LABELS,
    SUPPORTED_CLANS,
    create_player_character,
    sire_for_id,
)
from .chronicle_instance import ensure_personal_chronicle
from .chronicle_offices import office_eligibility
from .chronicle_politics import political_actor, primary_office, validate_political_state
from .chronicle_service import ChronicleService
from .chronicle_simulation import active_hunting_access, ensure_character_links
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
from .clans import clan_identity
from .creation_rules import (
    CONVICTIONS,
    MORTAL_ORIGINS,
    VENTRUE_FEEDING_PREFERENCES,
    choose_sire_from_creation,
    concept_from_origin,
    conviction as conviction_rule,
)
from .era import era_for_year
from .sire_relations import sire_bond
from .situations import generate_situations, resolve_situation
from .vampire_profile import profile_for_creation
from .vampire_profile_store import VampireProfileStore


ROAD_LABELS = {
    "humanitatis": "Via Humanitas",
    "regalis": "Via Regalis",
    "caeli": "Via Caeli",
    "bestiae": "Via Bestiae",
    "peccati": "Via Peccati",
    "via_mutationis": "Voie de la transformation",
}
SKILL_LABELS = {
    "etiquette": "Étiquette",
    "insight": "Intuition",
    "persuasion": "Persuasion",
    "politics": "Politique",
    "survival": "Survie",
}
CAMARILLA_STAGE_LABELS = {
    "absent": "Aucune Camarilla constituée",
    "project": "Camarilla naissante — coalition annoncée",
    "coalition": "Coalition proto-Camarilla",
    "institutional": "Camarilla institutionnelle",
}


def _render_creation(
    store: ChronicleStore,
    profile_store: VampireProfileStore,
    simulation_store: ChronicleSimulationStore,
    game_id: str,
    player_id: str,
    default_player_name: str,
) -> None:
    st.title("WoD RPG — Les Premières Nuits")
    st.caption("1435 · Révolte, lignages et naissance d'un nouvel ordre")
    st.markdown(
        "Vous êtes un vampire récemment Étreint. Votre sire répond encore de vous, votre droit de chasse dépend "
        "d'autrui et la Camarilla qui vient d'être annoncée reste une coalition contestée, loin de son ordre futur."
    )

    st.subheader("Créer votre vampire")
    player_name = st.text_input("Nom du joueur", value=default_player_name or "Joueur")
    name = st.text_input("Nom du vampire")
    clan_id = st.selectbox(
        "Clan",
        options=SUPPORTED_CLANS,
        format_func=lambda value: CLAN_LABELS[value],
    )

    origin_ids = tuple(item.id for item in MORTAL_ORIGINS)
    origin_id = st.selectbox(
        "Origine mortelle",
        options=origin_ids,
        format_func=lambda value: next(item.label for item in MORTAL_ORIGINS if item.id == value),
    )
    selected_origin = next(item for item in MORTAL_ORIGINS if item.id == origin_id)
    st.caption(selected_origin.description)
    origin_detail = st.text_input(
        "Précision sur votre ancienne vie — facultatif",
        placeholder="Ex. chevalier sans terre, copiste d'un monastère, héritière d'un comptoir…",
    )

    starting_discipline = st.selectbox(
        "Discipline de départ dominante",
        options=CLAN_DISCIPLINES[clan_id],
        key=f"chronicle_starting_discipline_{clan_id}",
    )

    conviction_ids = tuple(item.id for item in CONVICTIONS)
    conviction_id = st.selectbox(
        "Conviction",
        options=conviction_ids,
        format_func=lambda value: next(item.label for item in CONVICTIONS if item.id == value),
    )
    selected_conviction = conviction_rule(conviction_id)
    st.caption(selected_conviction.description)
    st.caption(
        f"Effet mécanique actuel : +1 en {SKILL_LABELS.get(selected_conviction.favored_skill, selected_conviction.favored_skill)}. "
        "Les conséquences morales de respecter ou violer cette Conviction seront reliées à l'Humanité lors de la passe dédiée."
    )

    st.info("Voie des personnages joueurs : Via Humanitas.")

    feeding_preference = None
    if clan_id == "ventrue":
        feeding_preference = st.selectbox(
            "Restriction de chasse Ventrue",
            options=VENTRUE_FEEDING_PREFERENCES,
            key="chronicle_ventrue_feeding_preference",
        )
        st.caption("Votre Sang n'accepte réellement que des proies correspondant à cette catégorie.")

    sire_key = "|".join(
        (
            player_id,
            name.strip().lower(),
            clan_id,
            origin_id,
            conviction_id,
            starting_discipline,
            feeding_preference or "",
        )
    )
    selected_sire = choose_sire_from_creation(
        clan_id=clan_id,
        origin_id=origin_id,
        conviction_id=conviction_id,
        starting_discipline=starting_discipline,
        stable_key=sire_key,
    )
    with st.container(border=True):
        st.markdown(f"### Sire déterminé — {selected_sire.name}")
        st.caption(selected_sire.title)
        st.write(selected_sire.description)
        st.write(f"**Protection initiale :** {selected_sire.protection}")
        st.write(f"**Ce qu'il attend :** {selected_sire.expectation}")
        st.caption(
            "Ce sire est calculé automatiquement à partir du Clan, de l'origine, "
            "de la Conviction et de la Discipline choisis."
        )

    submitted = st.button(
        "Commencer la chronique",
        type="primary",
        use_container_width=True,
    )
    if not submitted:
        return
    if not name.strip():
        st.error("Votre vampire doit avoir un nom.")
        return

    progress = store.get_progress(game_id)
    if progress is None:
        st.error("La chronologie de la chronique est introuvable.")
        return

    character = create_player_character(
        game_id=game_id,
        player_id=player_id,
        player_name=player_name,
        character_id=f"pc_{uuid.uuid4().hex}",
        name=name,
        clan_id=clan_id,
        concept=concept_from_origin(origin_id, origin_detail),
        starting_discipline=starting_discipline,
        # Retained internally only for compatibility with V0.21-V0.39 saves.
        # They are no longer player-facing creation choices.
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="",
        chapter_goal="",
        progress=progress,
        sire_id=selected_sire.id,
        sire_name=selected_sire.name,
    )
    store.create_character(character)

    profile = profile_for_creation(
        character,
        conviction_id=conviction_id,
        feeding_preference=feeding_preference,
    )
    profile_store.save(profile)

    simulation = simulation_store.ensure(game_id, year=progress.year)
    linked = ensure_character_links(simulation, character)
    if linked != simulation:
        simulation_store.save(linked)

    st.session_state["wod_last_chronicle_notice"] = (
        f"{character.name} a été Étreint en {character.embraced_year}. "
        f"{character.sire_name} répond encore de ses actes et lui ouvre un premier accès à la chasse."
    )
    st.rerun()


def _render_header(character, profile, progress, simulation) -> None:
    current_office = primary_office(simulation, character.character_id)
    st.title(character.name)
    st.caption(
        f"{CLAN_LABELS[character.clan_id]} · {character.concept} · "
        f"{profile.generation}e génération · Étreint en {character.embraced_year} · "
        f"{OFFICE_LABELS.get(current_office, current_office)}"
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


def _render_convergence(repo, character, progress) -> None:
    st.subheader("Le monde avance")
    st.write(
        "Vos nuits personnelles de ce segment sont terminées. Vous pouvez maintenant laisser la cité, "
        "les lignages et les autres Caïnites poursuivre leurs propres affaires."
    )
    st.success("Votre trajectoire est prête. Aucun autre joueur n'est attendu.")
    if st.button("Faire avancer le monde", type="primary", use_container_width=True):
        result = ChronicleService(repo).resolve_convergence(character.game_id)
        beats = " ".join(beat.public_text for beat in result.world_beats[:2])
        if result.next_progress.chapter > progress.chapter:
            notice = (
                f"Le chapitre {progress.chapter} s'achève. Une ellipse de "
                f"{result.next_progress.year - progress.year} an(s) conduit la chronique en "
                f"{result.next_progress.year}."
            )
        else:
            notice = f"Le monde a avancé. Le segment {result.next_progress.segment} commence."
        if beats:
            notice += f" Pendant ce temps : {beats}"
        st.session_state["wod_last_chronicle_notice"] = notice
        st.rerun()


def _render_profile(character, profile) -> None:
    identity = clan_identity(character.clan_id)
    st.markdown("### Votre Sang")
    st.write(identity.medieval_position)
    st.write(f"**Fléau — {identity.bane_name} :** {identity.bane_text}")
    st.write(f"**Génération :** {profile.generation}e")
    st.write(f"**Puissance du Sang :** {profile.blood_potency}")
    st.write(f"**Voie :** {ROAD_LABELS.get(profile.road_affinity, profile.road_affinity)}")
    conviction_value = profile.convictions[0] if profile.convictions else ""
    try:
        selected_conviction = conviction_rule(conviction_value)
    except ValueError:
        st.write(f"**Conviction :** {conviction_value or 'Non renseignée'}")
    else:
        st.write(f"**Conviction :** {selected_conviction.label}")
        st.caption(
            f"Effet actuel : +1 en {SKILL_LABELS.get(selected_conviction.favored_skill, selected_conviction.favored_skill)}."
        )
    if profile.feeding_preference:
        st.write(f"**Restriction de chasse :** {profile.feeding_preference}")


def _render_domain_and_debts(character, simulation, year: int, characters) -> None:
    st.subheader("Chasse et Domaine")
    rights = active_hunting_access(simulation, character.character_id, year)
    if not rights:
        st.warning("Vous ne disposez actuellement d'aucun droit de chasse reconnu.")
    for right in rights:
        domain = simulation.domains[right.domain_id]
        holder_name = "sans détenteur reconnu"
        if domain.holder_id:
            holder_name = political_actor(simulation, characters, domain.holder_id).name
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
        other_name = political_actor(simulation, characters, other_id).name
        st.write(f"- **{direction}** une faveur {boon.level} — {other_name} · {boon.status} · {boon.origin}")


def _render_world(repo, character, simulation, progress, characters) -> None:
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
    if prince_id:
        prince = political_actor(simulation, characters, prince_id)
        st.write(f"**Prince local :** {prince.name} — {prince.clan_id.title()}")
    st.write(
        f"**Caïnites persistants :** {len(simulation.npcs) + 1} "
        "vampires suivis par cette chronique"
    )

    eligibilities = office_eligibility(character, simulation, era)
    with st.expander("Votre accès aux fonctions politiques"):
        for item in eligibilities:
            state = "accessible" if item.available else "non institutionnalisé"
            readiness = "éligible" if item.eligible else "pas encore éligible"
            st.write(f"**{OFFICE_LABELS.get(item.office, item.office)}** — {state}, {readiness}")
            st.caption(item.reason)

    events = ChronicleWorldStore(repo).list_events(character.game_id, limit=20)
    if events:
        st.markdown("### Ce qui a changé autour de vous")
        for event in events:
            with st.container(border=True):
                st.write(event["public_text"])
                st.caption(f"{event['year']} · Chapitre {event['chapter']} · Segment {event['segment']}")
    else:
        st.caption("Le monde n'a pas encore connu de convergence depuis votre Étreinte.")


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
    st.caption(
        "Les propositions ci-dessous sont des situations, pas une liste d'actions abstraites : "
        "choisissez celle que votre vampire décide réellement d'affronter."
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
    try:
        context = ensure_personal_chronicle(repo, player_id=player_id)
    except ValueError as exc:
        st.error(f"Chronique personnelle incohérente : {exc}")
        return

    game_id = context.game_id
    store = ChronicleStore(repo)
    profile_store = VampireProfileStore(repo)
    simulation_store = ChronicleSimulationStore(repo)
    progress = store.get_progress(game_id)
    if progress is None:
        st.error("Impossible d'initialiser la chronique.")
        return

    character = store.get_character(game_id, player_id)
    if character is None:
        _render_creation(
            store,
            profile_store,
            simulation_store,
            game_id,
            player_id,
            player_name,
        )
        return

    profile = profile_store.ensure_for_character(character)
    simulation = simulation_store.ensure(game_id, year=progress.year)
    linked = ensure_character_links(simulation, character)
    if linked != simulation:
        simulation = simulation_store.save(linked)

    characters = store.list_characters(game_id)
    if len(characters) != 1 or characters[0].player_id != player_id:
        st.error("Cette Chronique personnelle contient un personnage étranger. Aucun état n'a été modifié.")
        return
    validate_political_state(simulation, characters, era_for_year(progress.year))
    current_office = primary_office(simulation, character.character_id)

    notice = st.session_state.pop("wod_last_chronicle_notice", None)
    if context.migrated_legacy and not notice:
        notice = "Votre ancienne Chronique partagée a été isolée dans une sauvegarde personnelle."
    if notice:
        st.success(notice)

    with st.sidebar:
        st.header("Chronique")
        st.write(f"**{CHRONICLE_NAME}**")
        st.caption(f"Persistance : {backend_label} · partie personnelle")
        st.write(f"**Année :** {progress.year}")
        st.write(f"**Chapitre :** {progress.chapter}")
        st.write(f"**Segment :** {progress.segment}/{progress.segments_per_chapter}")
        st.divider()
        st.write(f"**Personnage :** {character.name}")
        st.write(f"**Clan :** {CLAN_LABELS[character.clan_id]}")
        st.write(f"**Sire :** {character.sire_name}")
        st.write(f"**Fonction :** {OFFICE_LABELS.get(current_office, current_office)}")

    _render_header(character, profile, progress, simulation)

    night_tab, relations_tab, domain_tab, journal_tab, world_tab = st.tabs(
        ["Cette nuit", "Mes liens", "Domaine & dettes", "Journal", "Le monde"]
    )

    with night_tab:
        if character.ready_for_convergence:
            _render_convergence(repo, character, progress)
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

    with relations_tab:
        _render_sire(character, profile, era_for_year(progress.year))
        _render_profile(character, profile)
        st.markdown("### Votre position")
        st.write(f"**Réputation :** {character.reputation:+d}")
        st.write(f"**Expérience accumulée :** {character.experience}")

    with domain_tab:
        _render_domain_and_debts(character, simulation, progress.year, characters)

    with journal_tab:
        _render_journal(store, character)

    with world_tab:
        _render_world(repo, character, simulation, progress, characters)
