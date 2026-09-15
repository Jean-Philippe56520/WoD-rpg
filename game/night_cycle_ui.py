from __future__ import annotations

import streamlit as st

from .night_cycle import (
    NightPhase,
    choose_night_event,
    free_action_situations,
    resolve_free_action,
    resolve_night_event,
    time_remaining_text,
)
from .night_cycle_store import NightCycleStore
from .situations import generate_situations


def _situation_for_id(character, profile, simulation, *, year: int, situation_id: str):
    return next(
        (
            item
            for item in generate_situations(character, profile, simulation, year=year)
            if item.id == situation_id
        ),
        None,
    )


def _render_choice_form(situation, *, key_prefix: str, submit_label: str):
    with st.form(f"{key_prefix}_{situation.id}"):
        choice_id = st.radio(
            "Votre décision",
            options=[choice.id for choice in situation.choices],
            format_func=lambda value: next(
                choice.label for choice in situation.choices if choice.id == value
            ),
            key=f"{key_prefix}_choice_{situation.id}",
        )
        selected = next(choice for choice in situation.choices if choice.id == choice_id)
        st.caption(selected.description)
        free_intent = st.text_area(
            "Précision libre",
            placeholder="Votre manière d'agir, ce que vous cachez, ce que vous cherchez vraiment…",
            max_chars=500,
            key=f"{key_prefix}_intent_{situation.id}",
        )
        submitted = st.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )
    return submitted, choice_id, free_intent


def _step_notice(result) -> str:
    dice = result.resolution.dice
    return (
        f"{result.resolution.outcome.summary} {result.resolution.outcome.detail} "
        f"{result.consequence} [{dice.successes} succès sur difficulté {dice.difficulty}]"
    )


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
    proposed_event = choose_night_event(character, profile, simulation, year=progress.year)
    night_state = night_store.ensure(character, event_id=proposed_event.id)

    st.subheader(f"Nuit {character.local_night}")

    if night_state.phase == NightPhase.EVENT:
        event = _situation_for_id(
            character,
            profile,
            simulation,
            year=progress.year,
            situation_id=night_state.event_id,
        )
        if event is None:
            st.error("L'événement persistant de cette nuit n'est plus disponible dans le moteur.")
            return

        st.caption(
            "Le monde vient à vous. Résolvez d'abord cet événement ; son issue déterminera le temps qui restera avant l'aube."
        )
        with st.container(border=True):
            st.markdown("### Événement de la nuit")
            st.markdown(f"#### {event.title}")
            st.write(event.body)
            play, choice_id, free_intent = _render_choice_form(
                event,
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
        )
        if not actions:
            st.warning("Aucune entreprise pertinente n'est actuellement disponible.")
        for index, situation in enumerate(actions):
            with st.container(border=True):
                st.markdown(f"#### {situation.title}")
                st.write(situation.body)
                play, choice_id, free_intent = _render_choice_form(
                    situation,
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
        st.session_state["wod_last_chronicle_notice"] = (
            f"La nuit {character.local_night} s'achève. Ses conséquences sont désormais inscrites dans la Chronique."
        )
        st.rerun()


def install_night_cycle_ui() -> None:
    """Install the V0.45 night renderer without modifying the other Chronicle tabs."""

    from . import chronicle_ui

    chronicle_ui._render_night = render_night_cycle
