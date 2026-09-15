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
    """Return the player-facing difficulty band without exposing the target number.

    WoD-rpg keeps the exact target inside the engine. The UI only exposes a
    coarse estimate: 2-3 standard, 4-5 difficult, 6+ extreme. Difficulty 1 is
    treated as easy for completeness.
    """

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


def roll_pool(*, pool: int, hunger: int, difficulty: int, seed: str) -> DiceResult:
    if pool < 1:
        pool = 1
    if difficulty < 1:
        raise ValueError("Difficulty must be positive")
    hunger = max(0, min(5, hunger))
    hunger_count = min(pool, hunger)
    normal_count = pool - hunger_count
    normal = tuple(_die(seed + ":normal", index) for index in range(normal_count))
    hungry = tuple(_die(seed + ":hunger", index) for index in range(hunger_count))
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
