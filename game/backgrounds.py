from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackgroundDefinition:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class BackgroundLeverage:
    id: str
    label: str
    rating: int
    difficulty_adjustment: int
    reason: str


BACKGROUND_DEFINITIONS: dict[str, BackgroundDefinition] = {
    "sire": BackgroundDefinition(
        "sire",
        "Sire",
        "Protection, accès et obligations issus du lien avec le sire. WoD-rpg traite surtout ce levier par la relation, le droit de chasse et les scènes dédiées.",
    ),
    "contacts": BackgroundDefinition(
        "contacts",
        "Contacts",
        "Réseau mortel ou intermédiaire capable de faire circuler une question, une rumeur ou un renseignement.",
    ),
    "resources": BackgroundDefinition(
        "resources",
        "Ressources",
        "Biens, revenus et capacité matérielle à financer une solution sans transformer l'argent en compétence personnelle.",
    ),
    "status": BackgroundDefinition(
        "status",
        "Statut",
        "Reconnaissance sociale ou vampirique qui permet d'être reçu, entendu ou traité selon son rang.",
    ),
}

# Un Historique pertinent modifie les circonstances, pas la compétence du vampire.
# Pour le MVP, un seul Historique principal peut réduire la difficulté d'une même
# approche. Cette limite évite l'empilement automatique Contacts + Ressources + Statut.
BACKGROUND_DIFFICULTY_ADJUSTMENT = {
    "contacts": -1,
    "resources": -1,
    "status": -1,
    "sire": 0,
}


def background_rating(character, profile, background_id: str) -> int:
    """Retourne la valeur canonique utilisée par le moteur.

    `status` vit déjà sur PlayerCharacter et progresse avec la chronique ; l'ancien
    champ `backgrounds['status']` est donc ignoré pour éviter deux vérités concurrentes.
    Les autres Historiques restent dans le profil JSON.
    """

    if background_id not in BACKGROUND_DEFINITIONS:
        raise ValueError(f"Historique inconnu : {background_id}")
    if background_id == "status":
        return max(0, int(character.status))
    return max(0, int(profile.backgrounds.get(background_id, 0)))


def background_unlocked(character, profile, background_id: str, minimum: int = 1) -> bool:
    if minimum < 1:
        raise ValueError("Le minimum d'un Historique doit être positif")
    return background_rating(character, profile, background_id) >= minimum


def background_leverage(character, profile, allowed: tuple[str, ...]) -> BackgroundLeverage | None:
    """Choisit le meilleur Historique explicitement autorisé par une approche.

    L'approche déclare les Historiques qui ont du sens dans son contenu. Le moteur
    ne déduit jamais qu'un Contact ou des Ressources s'appliquent à toutes les scènes.
    """

    candidates: list[BackgroundLeverage] = []
    for background_id in allowed:
        definition = BACKGROUND_DEFINITIONS.get(background_id)
        if definition is None:
            raise ValueError(f"Historique non déclaré : {background_id}")
        rating = background_rating(character, profile, background_id)
        if rating <= 0:
            continue
        adjustment = BACKGROUND_DIFFICULTY_ADJUSTMENT[background_id]
        candidates.append(
            BackgroundLeverage(
                id=background_id,
                label=definition.label,
                rating=rating,
                difficulty_adjustment=adjustment,
                reason=(
                    f"{definition.label} {rating} fournit un levier extérieur adapté à cette approche."
                    if adjustment < 0
                    else f"{definition.label} {rating} donne accès à cette approche sans modifier votre compétence."
                ),
            )
        )
    if not candidates:
        return None
    # D'abord le levier qui améliore le plus le contexte, puis le plus haut rating,
    # enfin un ordre stable pour assurer la déterminisme asynchrone.
    return sorted(
        candidates,
        key=lambda item: (item.difficulty_adjustment, -item.rating, item.id),
    )[0]
