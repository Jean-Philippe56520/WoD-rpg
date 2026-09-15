from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .chronicle import PlayerCharacter


ATTRIBUTE_NAMES = (
    "strength",
    "dexterity",
    "stamina",
    "charisma",
    "manipulation",
    "composure",
    "intelligence",
    "wits",
    "resolve",
)

SKILL_NAMES = (
    "athletics",
    "awareness",
    "brawl",
    "stealth",
    "insight",
    "persuasion",
    "subterfuge",
    "etiquette",
    "academics",
    "occult",
    "politics",
    "survival",
)

SIRE_GENERATIONS = {
    "sire_ventrue_aymon": 8,
    "sire_ventrue_heloise": 9,
    "sire_toreador_isabeau": 8,
    "sire_toreador_matteo": 9,
    "sire_brujah_guilhem": 8,
    "sire_brujah_ysabeau": 9,
}


@dataclass(frozen=True)
class VampireProfile:
    game_id: str
    character_id: str
    generation: int
    blood_potency: int
    willpower: int
    attributes: dict[str, int] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)
    disciplines: dict[str, int] = field(default_factory=dict)
    backgrounds: dict[str, int] = field(default_factory=dict)
    convictions: tuple[str, ...] = ()
    touchstones: tuple[str, ...] = ()
    road_affinity: str = "humanitatis"
    current_desire: str = "Trouver ma place sans devenir l'instrument d'un ancien"
    feeding_preference: str | None = None
    released_from_sire: bool = False
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not 4 <= self.generation <= 16:
            raise ValueError("Generation must be between 4 and 16")
        if not 0 <= self.blood_potency <= 10:
            raise ValueError("Blood Potency must be between 0 and 10")
        if not 0 <= self.willpower <= 10:
            raise ValueError("Willpower must be between 0 and 10")
        _validate_scores("attribute", self.attributes, ATTRIBUTE_NAMES, 1, 5)
        _validate_scores("skill", self.skills, SKILL_NAMES, 0, 5)
        for name, score in self.disciplines.items():
            if not name.strip() or not 0 <= int(score) <= 5:
                raise ValueError("Discipline scores must be between 0 and 5")
        for name, score in self.backgrounds.items():
            if not name.strip() or not 0 <= int(score) <= 5:
                raise ValueError("Background scores must be between 0 and 5")
        if not self.convictions:
            raise ValueError("At least one Conviction is required")
        if not self.touchstones:
            raise ValueError("At least one Touchstone is required")

    def pool(self, attribute: str, skill: str, *, bonus: int = 0) -> int:
        if attribute not in self.attributes:
            raise ValueError(f"Unknown attribute: {attribute}")
        if skill not in self.skills:
            raise ValueError(f"Unknown skill: {skill}")
        return max(1, self.attributes[attribute] + self.skills[skill] + bonus)


def _validate_scores(
    label: str,
    scores: Mapping[str, int],
    allowed: tuple[str, ...],
    minimum: int,
    maximum: int,
) -> None:
    missing = set(allowed) - set(scores)
    extra = set(scores) - set(allowed)
    if missing or extra:
        raise ValueError(f"Invalid {label} set; missing={sorted(missing)}, extra={sorted(extra)}")
    for name, score in scores.items():
        if not isinstance(score, int) or isinstance(score, bool) or not minimum <= score <= maximum:
            raise ValueError(f"{label.title()} {name} must be between {minimum} and {maximum}")


def _base_attributes(clan_id: str) -> dict[str, int]:
    values = {name: 1 for name in ATTRIBUTE_NAMES}
    values.update({"composure": 2, "resolve": 2, "wits": 2})
    if clan_id == "brujah":
        values.update({"strength": 2, "charisma": 2})
    elif clan_id == "toreador":
        values.update({"dexterity": 2, "charisma": 3})
    elif clan_id == "ventrue":
        values.update({"manipulation": 2, "composure": 3})
    return values


def _base_skills(clan_id: str) -> dict[str, int]:
    values = {name: 0 for name in SKILL_NAMES}
    values.update({"awareness": 1, "insight": 1, "survival": 1})
    if clan_id == "brujah":
        values.update({"brawl": 2, "politics": 1, "academics": 1})
    elif clan_id == "toreador":
        values.update({"etiquette": 2, "persuasion": 2, "academics": 1})
    elif clan_id == "ventrue":
        values.update({"politics": 2, "persuasion": 1, "subterfuge": 1, "etiquette": 1})
    return values


def _default_conviction(character: PlayerCharacter) -> str:
    if character.mortal_stance == "humanist":
        return "Ne pas sacrifier un innocent pour faciliter ma propre survie"
    return "Ne jamais gaspiller une vie ou une dette qui pourrait servir ma lignée"


def _default_road(character: PlayerCharacter) -> str:
    if character.mortal_stance == "humanist":
        return "humanitatis"
    if character.order_stance == "orthodox":
        return "regalis"
    return "bestiae"


def default_profile(character: PlayerCharacter) -> VampireProfile:
    sire_generation = SIRE_GENERATIONS.get(character.sire_id, 10)
    generation = min(16, sire_generation + 1)
    discipline_key = character.starting_discipline.strip().lower()
    feeding = None
    if character.clan_id == "ventrue":
        feeding = "Mortels appartenant à une condition sociale liée à votre ancienne vie"
    return VampireProfile(
        game_id=character.game_id,
        character_id=character.character_id,
        generation=generation,
        blood_potency=1,
        willpower=4,
        attributes=_base_attributes(character.clan_id),
        skills=_base_skills(character.clan_id),
        disciplines={discipline_key: 1},
        backgrounds={"sire": 1, "contacts": 1, "resources": 0, "status": 0},
        convictions=(_default_conviction(character),),
        touchstones=("Un mortel encore lié à votre ancienne existence",),
        road_affinity=_default_road(character),
        current_desire="Obtenir assez d'autonomie pour choisir moi-même ma prochaine nuit",
        feeding_preference=feeding,
    )


def profile_to_dict(profile: VampireProfile) -> dict:
    return {
        "game_id": profile.game_id,
        "character_id": profile.character_id,
        "generation": profile.generation,
        "blood_potency": profile.blood_potency,
        "willpower": profile.willpower,
        "attributes": dict(profile.attributes),
        "skills": dict(profile.skills),
        "disciplines": dict(profile.disciplines),
        "backgrounds": dict(profile.backgrounds),
        "convictions": list(profile.convictions),
        "touchstones": list(profile.touchstones),
        "road_affinity": profile.road_affinity,
        "current_desire": profile.current_desire,
        "feeding_preference": profile.feeding_preference,
        "released_from_sire": profile.released_from_sire,
        "schema_version": profile.schema_version,
    }


def profile_from_dict(data: Mapping) -> VampireProfile:
    return VampireProfile(
        game_id=str(data["game_id"]),
        character_id=str(data["character_id"]),
        generation=int(data.get("generation", 11)),
        blood_potency=int(data.get("blood_potency", 1)),
        willpower=int(data.get("willpower", 4)),
        attributes={str(k): int(v) for k, v in dict(data["attributes"]).items()},
        skills={str(k): int(v) for k, v in dict(data["skills"]).items()},
        disciplines={str(k): int(v) for k, v in dict(data.get("disciplines", {})).items()},
        backgrounds={str(k): int(v) for k, v in dict(data.get("backgrounds", {})).items()},
        convictions=tuple(str(item) for item in data.get("convictions", ())),
        touchstones=tuple(str(item) for item in data.get("touchstones", ())),
        road_affinity=str(data.get("road_affinity", "humanitatis")),
        current_desire=str(data.get("current_desire", "")),
        feeding_preference=(
            str(data["feeding_preference"]) if data.get("feeding_preference") is not None else None
        ),
        released_from_sire=bool(data.get("released_from_sire", False)),
        schema_version=int(data.get("schema_version", 1)),
    )
