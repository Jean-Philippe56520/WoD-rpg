from __future__ import annotations

from dataclasses import dataclass

from .chronicle import PlayerCharacter, PoliticalOffice
from .chronicle_politics import actor_offices
from .chronicle_simulation import SimulationState
from .era import EraRules


@dataclass(frozen=True)
class OfficeEligibility:
    office: str
    available: bool
    eligible: bool
    reason: str


def office_eligibility(
    character: PlayerCharacter,
    simulation: SimulationState,
    era: EraRules,
) -> tuple[OfficeEligibility, ...]:
    current_offices = set(actor_offices(simulation, character.character_id))
    held_domain = PoliticalOffice.DOMAIN_HOLDER.value in current_offices
    rows: list[OfficeEligibility] = []

    rows.append(
        OfficeEligibility(
            office=PoliticalOffice.DOMAIN_HOLDER.value,
            available=True,
            eligible=held_domain,
            reason=(
                "Vous détenez déjà un Domaine reconnu."
                if held_domain
                else "Un Domaine doit d'abord vous être accordé, transmis ou obtenu politiquement."
            ),
        )
    )

    envoy_available = PoliticalOffice.CLAN_ENVOY.value in era.available_offices
    rows.append(
        OfficeEligibility(
            office=PoliticalOffice.CLAN_ENVOY.value,
            available=envoy_available,
            eligible=envoy_available and character.status >= 1 and character.personal_influence >= 2.0,
            reason=(
                "Le rôle de représentant est une pratique locale accessible à un vampire déjà reconnu."
                if envoy_available
                else "Cette forme de représentation n'est pas disponible dans cette période."
            ),
        )
    )

    primogen_available = (
        era.primogen_council_standardized
        and PoliticalOffice.PRIMOGEN.value in era.available_offices
    )
    blocked_by_prince = PoliticalOffice.PRINCE.value in current_offices
    rows.append(
        OfficeEligibility(
            office=PoliticalOffice.PRIMOGEN.value,
            available=primogen_available,
            eligible=(
                primogen_available
                and not blocked_by_prince
                and character.status >= 3
                and character.personal_influence >= 5.0
            ),
            reason=(
                "Un Prince reconnu ne peut pas être simultanément Primogène."
                if blocked_by_prince
                else (
                    "Le Primogénat est désormais une institution reconnue, mais il exige un poids politique réel."
                    if primogen_available
                    else "En cette période, le Primogénat n'est pas traité comme une institution standardisée de la cité."
                )
            ),
        )
    )

    prince_available = PoliticalOffice.PRINCE.value in era.available_offices
    blocked_by_primogen = PoliticalOffice.PRIMOGEN.value in current_offices
    rows.append(
        OfficeEligibility(
            office=PoliticalOffice.PRINCE.value,
            available=prince_available,
            eligible=(
                prince_available
                and not blocked_by_primogen
                and character.status >= 3
                and character.personal_influence >= 6.0
            ),
            reason=(
                "Un Primogène reconnu doit quitter cette fonction avant de pouvoir tenir la Praxis."
                if blocked_by_primogen
                else (
                    "Un Prince doit imposer ou faire reconnaître sa Praxis ; ce n'est jamais une promotion automatique."
                    if prince_available
                    else "La fonction princière n'est pas disponible dans cette configuration."
                )
            ),
        )
    )
    return tuple(rows)


def validate_office_assignment(character: PlayerCharacter, office: str, era: EraRules) -> None:
    """Compatibility validator for callers that do not yet own world state.

    New Chronicle code should use ``chronicle_politics.assign_office`` because
    it also validates the canonical office registry and Prince/Primogen
    exclusivity.
    """

    resolved = PoliticalOffice(office).value
    if resolved not in era.available_offices:
        raise ValueError(f"Office {resolved} is not available in year {era.year}")
    if resolved == PoliticalOffice.PRIMOGEN.value and not era.primogen_council_standardized:
        raise ValueError("Primogen cannot be treated as a standardized office in this era")
