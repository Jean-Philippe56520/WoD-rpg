from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .chronicle import ChronicleProgress, PlayerCharacter, SIRES


@dataclass(frozen=True)
class WorldBeat:
    actor_id: str
    actor_name: str
    category: str
    public_text: str
    hidden_intent: str


NPC_AGENDAS = {
    "sire_ventrue_aymon": (
        "Renforcer un ordre hiérarchique entre Caïnites",
        "Identifier les révoltés avant qu'ils ne gagnent des alliés",
    ),
    "sire_ventrue_heloise": (
        "Étendre les relais marchands qui échappent aux vieilles maisons",
        "Faire reconnaître la valeur politique des nouveaux réseaux urbains",
    ),
    "sire_toreador_isabeau": (
        "Préserver les usages de Cour et les protections culturelles",
        "Isoler ceux qui menacent les équilibres sociaux",
    ),
    "sire_toreador_matteo": (
        "Acquérir de l'influence dans les cités et ateliers émergents",
        "Créer des alliances qui ne dépendent pas des anciens titres",
    ),
    "sire_brujah_guilhem": (
        "Maintenir le dialogue entre érudits, guerriers et seigneurs",
        "Empêcher les disputes doctrinales de devenir une guerre ouverte",
    ),
    "sire_brujah_ysabeau": (
        "Protéger les jeunes Caïnites contre les abus des anciens",
        "Relier entre eux les foyers de contestation",
    ),
}


PUBLIC_BEATS = {
    "ventrue": (
        "fait circuler des garanties de protection auprès de plusieurs notables nocturnes",
        "réunit discrètement des détenteurs de terres et de relais marchands",
        "demande que certaines dettes anciennes soient reconnues publiquement",
    ),
    "toreador": (
        "organise une rencontre où artistes, messagers et diplomates se croisent",
        "fait sonder les opinions avant une réunion de Cour encore officieuse",
        "protège un mortel dont le talent attire déjà plusieurs prédateurs",
    ),
    "brujah": (
        "cherche des témoins sur les exactions commises par un ancien",
        "réunit des voix opposées pour éviter qu'une dispute ne dégénère",
        "fait passer des messages entre jeunes Caïnites mécontents",
    ),
}


def _choice(seed: str, values: tuple[str, ...]) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return values[digest[0] % len(values)]


def autonomous_world_beats(
    progress: ChronicleProgress,
    characters: list[PlayerCharacter],
) -> tuple[WorldBeat, ...]:
    """Produce deterministic shared-world movement for a convergence.

    These beats deliberately describe what NPCs do, not what player characters do.
    Their agendas can later become richer persistent state without changing the UI
    contract introduced in V0.21.
    """

    represented_sires = {character.sire_id for character in characters if character.is_active}
    candidates = [sire for sire in SIRES if sire.id in represented_sires]
    if not candidates:
        candidates = list(SIRES[:3])

    beats: list[WorldBeat] = []
    for sire in sorted(candidates, key=lambda item: item.id)[:3]:
        agenda = _choice(
            f"agenda:{progress.year}:{progress.chapter}:{progress.segment}:{sire.id}",
            NPC_AGENDAS[sire.id],
        )
        public_action = _choice(
            f"beat:{progress.year}:{progress.chapter}:{progress.segment}:{sire.id}",
            PUBLIC_BEATS[sire.clan_id],
        )
        beats.append(
            WorldBeat(
                actor_id=sire.id,
                actor_name=sire.name,
                category="npc_agenda",
                public_text=f"{sire.name} {public_action}.",
                hidden_intent=agenda,
            )
        )
    return tuple(beats)
