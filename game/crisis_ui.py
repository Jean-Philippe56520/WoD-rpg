from __future__ import annotations

from dataclasses import replace

import streamlit as st

from .crises import (
    CRISIS_ACTION_LABELS,
    active_crises,
    current_crisis_intel,
    crisis_clues,
    crisis_public_description,
    crisis_response_score,
    crisis_stage_label,
    crisis_title,
)
from .models import ActionType, ClanNightOrders, GameAction, GameState


CRISIS_OVERRIDE_KEY = "wod_crisis_action_override"


def _available_action_types(state: GameState, clan_id: str, crisis_id: str) -> list[ActionType]:
    crisis = next((item for item in active_crises(state) if item.id == crisis_id), None)
    if crisis is None:
        return []
    choices = [
        ActionType.CRISIS_INVESTIGATE,
        ActionType.CRISIS_INFILTRATE,
        ActionType.CRISIS_NEGOTIATE,
        ActionType.CRISIS_CONTAIN,
    ]
    domain = state.domains[crisis.domain_id]
    holder = state.characters.get(domain.holder_id or "")
    if holder is not None and holder.clan_id != clan_id:
        choices.append(ActionType.CRISIS_EXPLOIT)
    return choices


def build_crisis_action(
    state: GameState,
    clan_id: str,
    actor_id: str,
    crisis_id: str,
    action_type: ActionType,
) -> GameAction:
    crises = {crisis.id: crisis for crisis in active_crises(state)}
    crisis = crises.get(crisis_id)
    if crisis is None:
        raise ValueError("La crise sélectionnée n'est plus active")
    actor = state.characters.get(actor_id)
    if actor is None or actor.clan_id != clan_id or actor.id == state.prince_id:
        raise ValueError("Le vampire sélectionné n'est pas un membre actif de ce clan")
    if action_type not in _available_action_types(state, clan_id, crisis_id):
        raise ValueError("Cette approche n'est pas disponible pour cette crise")
    return GameAction(
        clan_id=clan_id,
        action_type=action_type,
        actor_character_id=actor_id,
        target_domain_id=crisis.domain_id,
    )


def apply_crisis_override(
    state: GameState,
    orders: ClanNightOrders,
    payload: dict | None,
) -> ClanNightOrders:
    """Remplace exactement une mission du formulaire principal par une réponse de crise."""

    if not payload:
        return orders
    if int(payload.get("night", -1)) != state.night or payload.get("clan_id") != orders.clan_id:
        raise ValueError("La sélection de crise est périmée ; choisissez à nouveau votre intervention")

    replacement = build_crisis_action(
        state,
        orders.clan_id,
        str(payload.get("actor_id", "")),
        str(payload.get("crisis_id", "")),
        ActionType(str(payload.get("action_type", ""))),
    )

    replaced = False
    actions: list[GameAction] = []
    for action in orders.actions:
        if action.actor_character_id == replacement.actor_character_id:
            actions.append(replacement)
            replaced = True
        else:
            actions.append(action)
    if not replaced:
        raise ValueError("Le vampire affecté à la crise n'a pas d'action dans ces ordres")
    return replace(orders, actions=tuple(actions))


def render_crises_panel(state: GameState, clan_id: str) -> None:
    st.markdown("### Crises en cours")
    crises = active_crises(state)
    if not crises:
        st.session_state.pop(CRISIS_OVERRIDE_KEY, None)
        st.caption(
            "Aucune crise active. Les pressions extérieures peuvent faire apparaître une situation "
            "concrète si la ville reste vulnérable."
        )
        return

    for crisis in crises:
        intel = current_crisis_intel(state, crisis.id, clan_id)
        domain = state.domains[crisis.domain_id]
        with st.container(border=True):
            st.markdown(f"#### {crisis_title(state, crisis)}")
            stage_col, domain_col, deadline_col = st.columns(3)
            stage_col.metric("Stade", crisis_stage_label(crisis.stage))
            domain_col.metric("Domaine", domain.name)
            deadline_col.metric("Escalade", f"Nuit {crisis.next_escalation_night}")
            st.write(crisis_public_description(crisis))
            st.write(f"**Renseignement de votre clan : {intel}/2**")
            for clue in crisis_clues(crisis, intel):
                st.write(f"- {clue}")
            if crisis.stage >= 3:
                st.error(
                    "Menace imminente : sans progrès suffisant à la prochaine échéance, "
                    "la crise produit une conséquence majeure."
                )

    st.divider()
    st.caption(
        "Répondre à une crise consomme l'action nocturne du vampire choisi : sa mission sélectionnée "
        "dans « Une action par vampire » sera remplacée lors de la validation."
    )
    enabled = st.checkbox(
        "Affecter un vampire à une crise cette nuit",
        key=f"crisis_override_enabled_{state.night}_{clan_id}",
    )
    if not enabled:
        st.session_state.pop(CRISIS_OVERRIDE_KEY, None)
        return

    actor_ids = [
        character.id
        for character in state.characters.values()
        if character.clan_id == clan_id and character.id != state.prince_id
    ]
    actor_id = st.selectbox(
        "Vampire mobilisé",
        options=actor_ids,
        format_func=lambda character_id: state.characters[character_id].name,
        key=f"crisis_actor_{state.night}_{clan_id}",
    )
    crisis_id = st.selectbox(
        "Crise ciblée",
        options=[crisis.id for crisis in crises],
        format_func=lambda selected: crisis_title(
            state, next(item for item in crises if item.id == selected)
        ),
        key=f"crisis_target_{state.night}_{clan_id}",
    )
    action_types = _available_action_types(state, clan_id, crisis_id)
    action_type = st.selectbox(
        "Approche",
        options=action_types,
        format_func=lambda item: CRISIS_ACTION_LABELS[item],
        key=f"crisis_approach_{state.night}_{clan_id}",
    )

    action = build_crisis_action(state, clan_id, actor_id, crisis_id, action_type)
    crisis = next(item for item in crises if item.id == crisis_id)
    score, difficulty = crisis_response_score(state, crisis, action)
    st.info(
        f"Aperçu moteur : score {score} / difficulté {difficulty}. "
        "Un succès fort fournit deux points de progrès ou de renseignement."
    )
    if action_type == ActionType.CRISIS_INVESTIGATE:
        st.caption("Enquêter fournit du renseignement mais ne fait pas reculer directement la crise.")
    elif action_type == ActionType.CRISIS_EXPLOIT:
        st.warning(
            "Exploiter peut affaiblir le détenteur rival du Domaine, mais ne réduit pas la menace "
            "et peut créer un grief si la manipulation est découverte."
        )

    st.session_state[CRISIS_OVERRIDE_KEY] = {
        "night": state.night,
        "clan_id": clan_id,
        "actor_id": actor_id,
        "crisis_id": crisis_id,
        "action_type": action_type.value,
    }
