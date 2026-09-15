from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

from .chronicle import PlayerCharacter
from .creation_rules import conviction


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

# Identifiants V5 canoniques. Les libellés visibles sont adaptés à Paris 1435.
SKILL_NAMES = (
    "athletics", "brawl", "craft", "drive", "firearms", "larceny", "melee", "stealth", "survival",
    "animal_ken", "etiquette", "insight", "intimidation", "leadership", "performance", "persuasion",
    "streetwise", "subterfuge", "academics", "awareness", "finance", "investigation", "medicine",
    "occult", "politics", "science", "technology",
)

SKILL_LABELS_1435 = {
    "athletics": "Athlétisme", "brawl": "Bagarre", "craft": "Artisanat",
    "drive": "Conduite & monte", "firearms": "Tir", "larceny": "Larcin",
    "melee": "Mêlée", "stealth": "Furtivité", "survival": "Survie",
    "animal_ken": "Animaux", "etiquette": "Étiquette", "insight": "Intuition",
    "intimidation": "Intimidation", "leadership": "Commandement", "performance": "Représentation",
    "persuasion": "Persuasion", "streetwise": "Bas-fonds", "subterfuge": "Subterfuge",
    "academics": "Érudition", "awareness": "Vigilance", "finance": "Commerce & comptes",
    "investigation": "Investigation", "medicine": "Médecine", "occult": "Occultisme",
    "politics": "Politique", "science": "Sciences naturelles", "technology": "Techniques",
}

PHYSICAL_ATTRIBUTES = {"strength", "dexterity", "stamina"}

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
    specialties: dict[str, tuple[str, ...]] = field(default_factory=dict)
    disciplines: dict[str, int] = field(default_factory=dict)
    backgrounds: dict[str, int] = field(default_factory=dict)
    convictions: tuple[str, ...] = ()
    # Conservé uniquement pour lire les anciennes sauvegardes V0.31-V0.39.
    touchstones: tuple[str, ...] = ()
    road_affinity: str = "humanitatis"
    current_desire: str = ""
    feeding_preference: str | None = None
    released_from_sire: bool = False
    health_superficial: int = 0
    health_aggravated: int = 0
    humanity_stains: int = 0
    current_compulsion: str | None = None
    compulsion_focus: str = ""
    compulsion_scope: str = ""
    schema_version: int = 5
    # Bonus transitoire, jamais sérialisé. Il peut être négatif lorsqu'une
    # Compulsion pénalise une action sans rapport avec l'impulsion de la Bête.
    bonus_resolution: int = 0

    def __post_init__(self) -> None:
        if not 4 <= self.generation <= 16:
            raise ValueError("Generation must be between 4 and 16")
        if not 0 <= self.blood_potency <= 10:
            raise ValueError("Blood Potency must be between 0 and 10")
        if not 0 <= self.willpower <= 10:
            raise ValueError("Willpower must be between 0 and 10")
        if not 0 <= self.humanity_stains <= 10:
            raise ValueError("Humanity Stains must be between 0 and 10")
        if not -10 <= self.bonus_resolution <= 10:
            raise ValueError("Le modificateur temporaire de résolution doit être compris entre -10 et 10")
        _validate_scores("attribute", self.attributes, ATTRIBUTE_NAMES, 1, 5)
        _validate_scores("skill", self.skills, SKILL_NAMES, 0, 5)
        for skill, items in self.specialties.items():
            if skill not in SKILL_NAMES:
                raise ValueError(f"Unknown specialty skill: {skill}")
            if self.skills[skill] < 1:
                raise ValueError("A specialty requires at least one dot in its skill")
            if not items or any(not item.strip() for item in items):
                raise ValueError("Specialties must contain non-empty labels")
            normalized = tuple(item.strip().casefold() for item in items)
            if len(normalized) != len(set(normalized)):
                raise ValueError("Specialties must be unique within a skill")
        for name, score in self.disciplines.items():
            if not name.strip() or not 0 <= int(score) <= 5:
                raise ValueError("Discipline scores must be between 0 and 5")
        for name, score in self.backgrounds.items():
            if not name.strip() or not 0 <= int(score) <= 5:
                raise ValueError("Background scores must be between 0 and 5")
        if not self.convictions:
            raise ValueError("At least one Conviction is required")
        if self.health_superficial < 0 or self.health_aggravated < 0:
            raise ValueError("Health damage cannot be negative")
        if self.health_superficial + self.health_aggravated > self.sante_maximale:
            raise ValueError("Health damage cannot exceed the Health tracker")
        if self.current_compulsion is None and (self.compulsion_focus or self.compulsion_scope):
            raise ValueError("Compulsion metadata requires an active Compulsion")

    @property
    def volonte_maximale(self) -> int:
        return min(10, self.attributes["resolve"] + self.attributes["composure"])

    @property
    def sante_maximale(self) -> int:
        return self.attributes["stamina"] + 3

    @property
    def degats_sante(self) -> int:
        return self.health_superficial + self.health_aggravated

    @property
    def sante_restante(self) -> int:
        return max(0, self.sante_maximale - self.degats_sante)

    @property
    def est_diminue(self) -> bool:
        return self.degats_sante >= self.sante_maximale

    @property
    def en_torpeur_par_degats(self) -> bool:
        return self.health_aggravated >= self.sante_maximale

    def has_specialty(self, skill: str, specialty: str | None) -> bool:
        if not specialty:
            return False
        target = specialty.strip().casefold()
        return any(item.casefold() == target for item in self.specialties.get(skill, ()))

    def pool(self, attribute: str, skill: str, *, bonus: int = 0, specialty: str | None = None) -> int:
        if attribute not in self.attributes:
            raise ValueError(f"Unknown attribute: {attribute}")
        if skill not in self.skills:
            raise ValueError(f"Unknown skill: {skill}")
        impairment = 2 if self.est_diminue and attribute in PHYSICAL_ATTRIBUTES else 0
        specialty_bonus = 1 if self.has_specialty(skill, specialty) else 0
        return max(
            1,
            self.attributes[attribute] + self.skills[skill] + specialty_bonus + bonus
            + self.bonus_resolution - impairment,
        )


def _validate_scores(label: str, scores: Mapping[str, int], allowed: tuple[str, ...], minimum: int, maximum: int) -> None:
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


def _migrate_skills(raw: Mapping) -> dict[str, int]:
    values = {name: 0 for name in SKILL_NAMES}
    for key, value in dict(raw).items():
        key = str(key)
        if key in values:
            values[key] = int(value)
    return values


def _migrate_specialties(raw: Mapping | None) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for skill, items in dict(raw or {}).items():
        if str(skill) not in SKILL_NAMES:
            continue
        values = (items,) if isinstance(items, str) else tuple(str(item) for item in items)
        cleaned = tuple(item.strip() for item in values if item.strip())
        if cleaned:
            result[str(skill)] = cleaned
    return result


def default_profile(character: PlayerCharacter) -> VampireProfile:
    sire_generation = SIRE_GENERATIONS.get(character.sire_id, 10)
    generation = min(16, sire_generation + 1)
    discipline_key = character.starting_discipline.strip().lower()
    feeding = None
    if character.clan_id == "ventrue":
        feeding = "Mortels appartenant à une condition sociale liée à votre ancienne vie"
    attributes = _base_attributes(character.clan_id)
    willpower = min(10, attributes["resolve"] + attributes["composure"])
    return VampireProfile(
        game_id=character.game_id,
        character_id=character.character_id,
        generation=generation,
        blood_potency=1,
        willpower=willpower,
        attributes=attributes,
        skills=_base_skills(character.clan_id),
        specialties={},
        disciplines={discipline_key: 1},
        backgrounds={"sire": 1, "contacts": 1, "resources": 0, "status": 0},
        convictions=("keep_word",),
        touchstones=(),
        road_affinity="humanitatis",
        current_desire="",
        feeding_preference=feeding,
        health_superficial=0,
        health_aggravated=0,
        humanity_stains=0,
        current_compulsion=None,
        compulsion_focus="",
        compulsion_scope="",
    )


def profile_for_creation(
    character: PlayerCharacter,
    *,
    conviction_id: str,
    feeding_preference: str | None = None,
) -> VampireProfile:
    """Construit une fiche neuve sans l'ancienne règle maison +1 Compétence."""

    conviction(conviction_id)
    profile = default_profile(character)
    return replace(
        profile,
        convictions=(conviction_id,),
        touchstones=(),
        road_affinity="humanitatis",
        current_desire="",
        feeding_preference=feeding_preference if character.clan_id == "ventrue" else None,
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
        "specialties": {key: list(value) for key, value in profile.specialties.items()},
        "disciplines": dict(profile.disciplines),
        "backgrounds": dict(profile.backgrounds),
        "convictions": list(profile.convictions),
        "touchstones": list(profile.touchstones),
        "road_affinity": profile.road_affinity,
        "current_desire": profile.current_desire,
        "feeding_preference": profile.feeding_preference,
        "released_from_sire": profile.released_from_sire,
        "health_superficial": profile.health_superficial,
        "health_aggravated": profile.health_aggravated,
        "humanity_stains": profile.humanity_stains,
        "current_compulsion": profile.current_compulsion,
        "compulsion_focus": profile.compulsion_focus,
        "compulsion_scope": profile.compulsion_scope,
        "schema_version": profile.schema_version,
    }


def profile_from_dict(data: Mapping) -> VampireProfile:
    compulsion = str(data["current_compulsion"]) if data.get("current_compulsion") else None
    return VampireProfile(
        game_id=str(data["game_id"]),
        character_id=str(data["character_id"]),
        generation=int(data.get("generation", 11)),
        blood_potency=int(data.get("blood_potency", 1)),
        willpower=int(data.get("willpower", 4)),
        attributes={str(k): int(v) for k, v in dict(data["attributes"]).items()},
        skills=_migrate_skills(data.get("skills", {})),
        specialties=_migrate_specialties(data.get("specialties")),
        disciplines={str(k): int(v) for k, v in dict(data.get("disciplines", {})).items()},
        backgrounds={str(k): int(v) for k, v in dict(data.get("backgrounds", {})).items()},
        convictions=tuple(str(item) for item in data.get("convictions", ("keep_word",))),
        touchstones=tuple(str(item) for item in data.get("touchstones", ())),
        road_affinity=str(data.get("road_affinity", "humanitatis")),
        current_desire=str(data.get("current_desire", "")),
        feeding_preference=(str(data["feeding_preference"]) if data.get("feeding_preference") is not None else None),
        released_from_sire=bool(data.get("released_from_sire", False)),
        health_superficial=int(data.get("health_superficial", 0)),
        health_aggravated=int(data.get("health_aggravated", 0)),
        humanity_stains=int(data.get("humanity_stains", 0)),
        current_compulsion=compulsion,
        compulsion_focus=str(data.get("compulsion_focus", "")) if compulsion else "",
        compulsion_scope=str(data.get("compulsion_scope", "")) if compulsion else "",
        schema_version=max(5, int(data.get("schema_version", 1))),
    )
