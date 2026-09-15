from __future__ import annotations

from dataclasses import dataclass
import hashlib


DIFFICULTY_BANDS: tuple[tuple[int, int | None, str, str], ...] = (
    (1, 1, "facile", "Cette approche paraît favorable dans les circonstances visibles."),
    (2, 3, "standard", "Cette approche paraît accessible, mais une mauvaise exécution peut suffire à la faire échouer."),
    (4, 5, "difficile", "Cette approche paraît exigeante ; un avantage, une préparation ou un bon pool peuvent faire la différence."),
    (6, None, "extrême", "Cette approche paraît hors de portée sans circonstances exceptionnellement favorables."),
)


def difficulty_band(difficulty: int) -> str:
    """Return the player-facing difficulty band without exposing the target number."""

    if difficulty < 1:
        raise ValueError("Difficulty must be positive")
    for minimum, maximum, label, _ in DIFFICULTY_BANDS:
        if difficulty >= minimum and (maximum is None or difficulty <= maximum):
            return label
    raise AssertionError("Unreachable difficulty band")


def difficulty_hint(difficulty: int) -> str:
    """Return a diegetic risk clue while keeping the exact difficulty hidden."""

    band = difficulty_band(difficulty)
    for _, _, label, hint in DIFFICULTY_BANDS:
        if label == band:
            return hint
    raise AssertionError("Unreachable difficulty hint")


@dataclass(frozen=True)
class DiceResult:
    pool: int
    difficulty: int
    hunger: int
    normal_dice: tuple[int, ...]
    hunger_dice: tuple[int, ...]
    successes: int
    margin: int
    critical: bool
    messy_critical: bool
    bestial_failure: bool
    relances_volonte: int = 0

    @property
    def success(self) -> bool:
        return self.successes >= self.difficulty

    @property
    def label(self) -> str:
        if self.messy_critical:
            return "réussite critique bestiale"
        if self.critical:
            return "réussite critique"
        if self.bestial_failure:
            return "échec bestial"
        return "réussite" if self.success else "échec"


def _die(seed: str, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
    return digest[0] % 10 + 1


def _relancer_par_volonte(normal: tuple[int, ...], seed: str) -> tuple[tuple[int, ...], int]:
    """Relance jusqu'à trois dés ordinaires en échec, jamais les dés de Faim."""

    indices = tuple(index for index, value in enumerate(normal) if value < 6)[:3]
    if not indices:
        return normal, 0
    updated = list(normal)
    for rang, index in enumerate(indices):
        updated[index] = _die(seed + ":volonte", rang)
    return tuple(updated), len(indices)


def _resultat_des(
    *,
    pool: int,
    difficulty: int,
    hunger_count: int,
    normal: tuple[int, ...],
    hungry: tuple[int, ...],
    relances_volonte: int = 0,
) -> DiceResult:
    all_dice = normal + hungry
    base_successes = sum(1 for value in all_dice if value >= 6)
    tens = sum(1 for value in all_dice if value == 10)
    critical_pairs = tens // 2
    successes = base_successes + critical_pairs * 2
    critical = critical_pairs > 0
    messy = critical and any(value == 10 for value in hungry)
    failed = successes < difficulty
    bestial = failed and any(value == 1 for value in hungry)
    return DiceResult(
        pool=pool,
        difficulty=difficulty,
        hunger=hunger_count,
        normal_dice=normal,
        hunger_dice=hungry,
        successes=successes,
        margin=successes - difficulty,
        critical=critical,
        messy_critical=messy,
        bestial_failure=bestial,
        relances_volonte=relances_volonte,
    )


def roll_pool(*, pool: int, hunger: int, difficulty: int, seed: str) -> DiceResult:
    if pool < 1:
        pool = 1
    if difficulty < 1:
        raise ValueError("Difficulty must be positive")
    hunger = max(0, min(5, hunger))
    hunger_count = min(pool, hunger)
    normal_count = pool - hunger_count

    utiliser_volonte = "@volonte" in seed
    base_seed = seed.replace("@volonte", "")
    normal = tuple(_die(base_seed + ":normal", index) for index in range(normal_count))
    hungry = tuple(_die(base_seed + ":hunger", index) for index in range(hunger_count))
    relances = 0
    if utiliser_volonte:
        normal, relances = _relancer_par_volonte(normal, base_seed)

    return _resultat_des(
        pool=pool,
        difficulty=difficulty,
        hunger_count=hunger_count,
        normal=normal,
        hungry=hungry,
        relances_volonte=relances,
    )


def rouse_check(*, hunger: int, seed: str) -> tuple[int, int]:
    """Return the rouse die and resulting Hunger.

    A result of 6+ succeeds and leaves Hunger unchanged. A failure increases
    Hunger by one, capped at 5. This deterministic implementation preserves
    asynchronous retry safety while using the V5-style risk structure.
    """

    die = _die(seed + ":rouse", 0)
    next_hunger = hunger if die >= 6 else min(5, hunger + 1)
    return die, next_hunger
