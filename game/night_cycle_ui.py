from __future__ import annotations

import streamlit as st

from .chronicle import CLAN_LABELS, OFFICE_LABELS
from .chronicle_politics import primary_office
from .chronicle_service import ChronicleService, chronicle_time_label, ellipse_label
from .chronicle_world_store import ChronicleWorldStore
from .dice import difficulty_band
from .mecaniques_vampiriques import (
    bonus_coup_de_sang,
    recuperer_volonte_fin_nuit,
    usage_discipline,
)
from .night_cycle import (
    NightPhase,
    OptionsResolution,
    available_situations,
    choose_night_event,
    free_action_situations,
    resolve_free_action,
    resolve_night_event,
    time_remaining_text,
)
from .night_cycle_store import NightCycleStore
from .situations import action_risk_preview


ATTRIBUTE_LABELS = {
    "strength": "Force",
    "dexterity": "Dextérité",
    "stamina": "Vigueur",
    "charisma": "Charisme",
    "manipulation": "Manipulation",
    "composure": "Sang-froid",
    "intelligence": "Intelligence",
    "wits": "Astuce",
    "resolve": "Résolution",
}

SKILL_LABELS = {
    "athletics": "Athlétisme",
    "awareness": "Vigilance",
    "brawl": "Bagarre",
    "stealth": "Furtivité",
    "insight": "Perspicacité",
    "persuasion": "Persuasion",
    "subterfuge": "Subterfuge",
    "etiquette": "Étiquette",
    "academics": "Érudition",
    "occult": "Occultisme",
    "politics": "Politique",
    "survival": "Survie",
}


def _label(mapping: dict[str, str], value: str) -> str:
    return mapping.get(value, value.replace("_", " ").title())


def _situation_for_id(
    character,
    profile,
    simulation,
    *,
    year: int,
    situation_id: str,
    world_events=(),
    nights_per_cycle: int = 3,
):
    return next(
        (
            item
            for item in available_situations(
                character,
                profile,
                simulation,
                year=year,
                world_events=world_events,
                nights_per_cycle=nights_per_cycle,
            )
            if item.id == situation_id
        ),
        None,
    )


def _render_choice_form(
    situation,
    character,
    profile,
    simulation,
    *,
    key_prefix: str,
    submit_label: str,
):
    choice_id = st.radio(
        "Votre décision",
        options=[choice.id for choice in situation.choices],
        format_func=lambda value: next(
            choice.label for choice in situation.choices if choice.id == value
        ),
        key=f"{key_prefix}_choice_{situation.id}",
    )
    selected = next(choice for choice in situation.choices if choice.id == choice_id)
    preview = action_risk_preview(character, simulation, situation, selected)
    st.caption(selected.description)
    st.caption(
        f"Approche : {_label(ATTRIBUTE_LABELS, preview.attribute)} + "
        f"{_label(SKILL_LABELS, preview.skill)} · Risque estimé : **{preview.band.title()}**"
    )
    st.caption(preview.hint)

    with st.form(f"{key_prefix}_{situation.id}_{choice_id}"):
        st.markdown("**Leviers vampiriques**")
        usage = usage_discipline(profile, situation, selected)
        if usage is not None:
            utiliser_discipline = st.checkbox(
                f"Utiliser {usage.discipline} — {usage.pouvoir} (+{usage.bonus_des} dé(s))",
                key=f"{key_prefix}_discipline_{situation.id}_{choice_id}",
            )
            st.caption(usage.description)
        else:
            utiliser_discipline = False
            st.caption(
                "Aucun pouvoir de Discipline actuellement modélisé ne s'applique directement à cette approche."
            )

        bonus_sang = bonus_coup_de_sang(profile.blood_potency)
        coup_indisponible = character.hunger >= 5
        coup_de_sang = st.checkbox(
            f"Coup de Sang (+{bonus_sang} dés, avec Test d’Exaltation)",
            disabled=coup_indisponible,
            key=f"{key_prefix}_coup_sang_{situation.id}_{choice_id}",
        )
        if coup_indisponible:
            st.caption("Coup de Sang indisponible : la Faim est déjà à 5.")
        else:
            st.caption("Le Test d’Exaltation peut augmenter la Faim de 1.")

        volonte_indisponible = profile.willpower <= 0
        depenser_volonte = st.checkbox(
            "Dépenser 1 Volonté pour relancer jusqu'à trois dés ordinaires en échec",
            disabled=volonte_indisponible,
            key=f"{key_prefix}_volonte_{situation.id}_{choice_id}",
        )
        if volonte_indisponible:
            st.caption("Aucun point de Volonté disponible.")
        else:
            st.caption("Les dés de Faim ne peuvent jamais être relancés par la Volonté.")

        free_intent = st.text_area(
            "Précision libre",
            placeholder="Votre manière d'agir, ce que vous cachez, ce que vous cherchez vraiment…",
            max_chars=500,
            key=f"{key_prefix}_intent_{situation.id}_{choice_id}",
        )
        submitted = st.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )

    return (
        submitted,
        choice_id,
        free_intent,
        OptionsResolution(
            depenser_volonte=depenser_volonte,
            coup_de_sang=coup_de_sang,
            utiliser_discipline=utiliser_discipline,
        ),
    )


def _step_notice(result) -> str:
    dice = result.resolution.dice
    return (
        f"{result.resolution.outcome.summary} {result.resolution.outcome.detail} "
        f"{result.consequence} [{dice.successes} succès · risque {difficulty_band(dice.difficulty)}]"
    )


def render_chronicle_header(character, profile, progress, simulation) -> None:
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
    col3.metric("Cycle", progress.segment)
    current_night = progress.nights_per_segment if character.ready_for_convergence else character.local_night
    col4.metric("Nuit significative", f"{current_night}/{progress.nights_per_segment}")

    vital1, vital2, vital3, vital4, vital5, vital6 = st.columns(6)
    vital1.metric("Faim", f"{character.hunger}/5")
    vital2.metric("Humanité", f"{character.humanity}/10")
    vital3.metric("Volonté", f"{profile.willpower}/{profile.volonte_maximale}")
    vital4.metric("Statut", character.status)
    vital5.metric("Influence", f"{character.personal_influence:.1f}")
    vital6.metric("Expérience", character.experience)


def render_chronicle_journal(store, character) -> None:
    history = store.list_history(character.game_id, character.character_id, limit=30)
    if not history:
        st.caption("Aucune nuit n'a encore été jouée.")
        return
    for item in history:
        outcome = item.get("outcome_json") or {}
        with st.container(border=True):
            st.markdown(
                f"**Chapitre {item['chapter']} · Cycle {item['segment']} · Nuit {item['night_number']}**"
            )
            st.write(outcome.get("summary", item["action"]))
            detail = outcome.get("detail")
            if detail:
                st.caption(detail)


def _convergence_notice(result) -> str:
    beats = " ".join(beat.public_text for beat in result.world_beats[:2])
    if result.chapter_closed:
        notice = (
            f"Le chapitre {result.previous_progress.chapter} s'achève. "
            f"Après {ellipse_label(result.ellipse_months)}, la chronique reprend en "
            f"{chronicle_time_label(result.next_progress.year, result.next_time.month)}."
        )
    else:
        notice = (
            f"Le monde avance et le Cycle {result.next_progress.segment} commence en "
            f"{chronicle_time_label(result.next_progress.year, result.next_time.month)}."
        )
    if beats:
        notice += f" Pendant ce temps : {beats}"
    return notice


def render_chronicle_convergence(repo, character, progress) -> None:
    service = ChronicleService(repo)
    time_state = service.get_time_state(character.game_id)
    assessment = service.assess_chapter_closure(character.game_id)

    st.subheader("Convergence")
    st.write(
        "Les trois Nuits significatives de ce Cycle sont terminées. Elles représentent les moments joués "
        "qui comptent pour la chronique et ne sont pas nécessairement trois nuits civiles consécutives."
    )
    st.caption(
        f"Repère temporel actuel : {chronicle_time_label(progress.year, time_state.month)}. "
        "La Convergence laisse Paris, les lignages et les autres Caïnites agir avant le prochain Cycle."
    )

    if assessment.closable:
        st.success(assessment.reason)
        st.write(
            "Vous pouvez continuer à jouer le même enjeu de chapitre, ou considérer que ce tournant clôt l'arc actuel. "
            "Clore le chapitre déclenche une ellipse adaptée à l'âge et au statut du vampire."
        )
        left, right = st.columns(2)
        if left.button(
            "Continuer le chapitre",
            type="secondary",
            use_container_width=True,
            key=f"continue_chapter_{progress.chapter}_{progress.segment}",
        ):
            result = service.resolve_convergence(character.game_id, close_chapter=False)
            st.session_state["wod_last_chronicle_notice"] = _convergence_notice(result)
            st.rerun()
        if right.button(
            "Clore le chapitre",
            type="primary",
            use_container_width=True,
            key=f"close_chapter_{progress.chapter}_{progress.segment}",
        ):
            result = service.resolve_convergence(character.game_id, close_chapter=True)
            st.session_state["wod_last_chronicle_notice"] = _convergence_notice(result)
            st.rerun()
        return

    st.info(assessment.reason)
    if st.button(
        "Faire avancer le monde",
        type="primary",
        use_container_width=True,
        key=f"advance_cycle_{progress.chapter}_{progress.segment}",
    ):
        result = service.resolve_convergence(character.game_id, close_chapter=False)
        st.session_state["wod_last_chronicle_notice"] = _convergence_notice(result)
        st.rerun()


def render_night_cycle(
    store,
    profile_store,
    simulation_store,
    character,
    profile,
    simulation,
    progress,
) -> None:
    night_store = NightCycleStore(store.repository)
    world_events = ChronicleWorldStore(store.repository).list_events(character.game_id, limit=12)
    proposed_event = choose_night_event(
        character,
        profile,
        simulation,
        year=progress.year,
        world_events=world_events,
        nights_per_cycle=progress.nights_per_segment,
    )
    night_state = night_store.ensure(character, event_id=proposed_event.id)

    st.subheader(f"Nuit significative {character.local_night}")
    st.caption(
        "Cette Nuit représente un moment important de la chronique. Du temps ordinaire peut s'écouler entre deux Nuits jouées."
    )

    if night_state.phase == NightPhase.EVENT:
        event = _situation_for_id(
            character,
            profile,
            simulation,
            year=progress.year,
            situation_id=night_state.event_id,
            world_events=world_events,
            nights_per_cycle=progress.nights_per_segment,
        )
        if event is None:
            st.error("L'événement persistant de cette nuit n'est plus disponible dans le moteur.")
            return

        st.caption(
            "Le monde vient à vous. Résolvez d'abord cet événement ; son issue déterminera le temps qui restera avant l'aube."
        )
        with st.container(border=True):
            st.markdown("### Événement de la nuit")
            if event.id.startswith("world_event_"):
                st.caption("Écho du Cycle précédent — information imparfaite, issue d'un changement réel du monde.")
            st.markdown(f"#### {event.title}")
            st.write(event.body)
            play, choice_id, free_intent, options = _render_choice_form(
                event,
                character,
                profile,
                simulation,
                key_prefix=(
                    f"night_event_{character.chapter}_{character.segment}_{character.local_night}"
                ),
                submit_label="Résoudre l'événement",
            )
        if play:
            result = resolve_night_event(
                character,
                profile,
                simulation,
                event,
                choice_id,
                nights_per_segment=progress.nights_per_segment,
                free_intent=free_intent,
                options=options,
            )
            night_store.apply_event(character, night_state, result)
            simulation_store.save(result.resolution.simulation)
            profile_store.save(result.resolution.profile)
            st.session_state["wod_last_chronicle_notice"] = _step_notice(result)
            st.rerun()
        return

    if night_state.log:
        event_log = night_state.log[0]
        with st.container(border=True):
            st.markdown("### Événement résolu")
            st.write(event_log.get("summary", "L'événement de la nuit est résolu."))
            detail = str(event_log.get("detail", "")).strip()
            if detail:
                st.caption(detail)
            consequence = str(event_log.get("consequence", "")).strip()
            if consequence:
                st.info(consequence)

    st.markdown("### Le reste de votre nuit")
    st.info(time_remaining_text(night_state.remaining_actions))

    free_action_count = sum(
        1 for item in night_state.log if item.get("kind") == "free_action"
    )
    if night_state.remaining_actions > 0:
        st.caption(
            "Ces actions viennent de votre vampire : vous choisissez maintenant ce qu'il veut entreprendre avec le temps qui lui reste."
        )
        actions = free_action_situations(
            character,
            profile,
            simulation,
            year=progress.year,
            event_id=night_state.event_id,
            world_events=world_events,
            nights_per_cycle=progress.nights_per_segment,
        )
        if not actions:
            st.warning("Aucune entreprise pertinente n'est actuellement disponible.")
        for index, situation in enumerate(actions):
            with st.container(border=True):
                st.markdown(f"#### {situation.title}")
                st.write(situation.body)
                play, choice_id, free_intent, options = _render_choice_form(
                    situation,
                    character,
                    profile,
                    simulation,
                    key_prefix=(
                        f"free_action_{character.chapter}_{character.segment}_"
                        f"{character.local_night}_{len(night_state.log)}_{index}"
                    ),
                    submit_label="Entreprendre cette action",
                )
            if play:
                result = resolve_free_action(
                    character,
                    profile,
                    simulation,
                    situation,
                    choice_id,
                    nights_per_segment=progress.nights_per_segment,
                    remaining_actions=night_state.remaining_actions,
                    action_index=free_action_count + 1,
                    free_intent=free_intent,
                    options=options,
                )
                night_store.apply_free_action(character, night_state, result)
                simulation_store.save(result.resolution.simulation)
                profile_store.save(result.resolution.profile)
                st.session_state["wod_last_chronicle_notice"] = _step_notice(result)
                st.rerun()

    if night_state.remaining_actions == 0:
        st.caption("Il ne reste plus qu'à laisser venir l'aube et retenir les conséquences de cette nuit.")
    elif free_action_count == 0:
        st.caption("Vous pouvez aussi renoncer à agir davantage et laisser la nuit s'achever.")

    if st.button(
        "Terminer la nuit",
        type="primary" if night_state.remaining_actions == 0 else "secondary",
        use_container_width=True,
        key=(
            f"finish_night_{character.chapter}_{character.segment}_{character.local_night}"
        ),
    ):
        night_store.finish_night(
            character,
            night_state,
            nights_per_segment=progress.nights_per_segment,
        )
        profil_recupere, recuperation = recuperer_volonte_fin_nuit(profile)
        if recuperation > 0:
            profile_store.save(profil_recupere)
        notice = (
            f"La nuit {character.local_night} s'achève. Ses conséquences sont désormais inscrites dans la Chronique."
        )
        if recuperation > 0:
            notice += f" Vous récupérez {recuperation} point(s) de Volonté."
        st.session_state["wod_last_chronicle_notice"] = notice
        st.rerun()


def install_night_cycle_ui() -> None:
    """Installe l'interface de Chronique V0.48c et ses leviers vampiriques."""

    from . import chronicle_ui

    chronicle_ui._render_header = render_chronicle_header
    chronicle_ui._render_journal = render_chronicle_journal
    chronicle_ui._render_convergence = render_chronicle_convergence
    chronicle_ui._render_night = render_night_cycle
