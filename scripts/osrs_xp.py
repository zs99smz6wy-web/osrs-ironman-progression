"""Pure helpers for canonical Old School RuneScape skill experience."""

from bisect import bisect_right
from functools import lru_cache


MAX_LEVEL = 99
MAX_XP = 200_000_000
SKILLS = (
    "Agility", "Attack", "Construction", "Cooking", "Crafting", "Defence",
    "Farming", "Firemaking", "Fishing", "Fletching", "Herblore", "Hitpoints",
    "Hunter", "Magic", "Mining", "Prayer", "Ranged", "Runecraft", "Sailing",
    "Slayer", "Smithing", "Strength", "Thieving", "Woodcutting",
)


def _require_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@lru_cache(maxsize=1)
def _minimum_xp_by_level() -> tuple[int, ...]:
    """Return indexed XP thresholds for levels 1 through 99.

    The OSRS threshold for each next level is derived from the game's canonical
    cumulative-points formula, floored after division by four.
    """
    thresholds = [0]
    points = 0
    for level in range(1, MAX_LEVEL):
        points += int(level + 300 * 2 ** (level / 7))
        thresholds.append(points // 4)
    return tuple(thresholds)


def minimum_xp_for_level(level: int) -> int:
    """Return the minimum cumulative XP required for an OSRS level (1..99)."""
    _require_int(level, "level")
    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(f"level must be between 1 and {MAX_LEVEL}")
    return _minimum_xp_by_level()[level - 1]


def level_from_xp(xp: int) -> int:
    """Return the displayed OSRS level for XP in the inclusive 0..200M range."""
    _require_int(xp, "xp")
    if not 0 <= xp <= MAX_XP:
        raise ValueError(f"xp must be between 0 and {MAX_XP}")
    return min(bisect_right(_minimum_xp_by_level(), xp), MAX_LEVEL)


def add_xp(current_xp: int, amount: int, *, cap: int = MAX_XP) -> int:
    """Add non-negative XP, returning the total capped at ``cap``.

    ``cap`` defaults to OSRS's 200M-XP skill cap and may be lowered for
    deterministic simulations. Inputs must be integers, and the existing XP
    total cannot already exceed the selected cap.
    """
    _require_int(current_xp, "current_xp")
    _require_int(amount, "amount")
    _require_int(cap, "cap")
    if not 0 <= cap <= MAX_XP:
        raise ValueError(f"cap must be between 0 and {MAX_XP}")
    if not 0 <= current_xp <= cap:
        raise ValueError("current_xp must be between 0 and cap")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return min(current_xp + amount, cap)
