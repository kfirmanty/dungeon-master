"""
Universal dice rolling module — shared across all RPG rules systems.

Every tabletop RPG uses dice. This module provides a notation parser and
roller that handles standard RPG dice expressions like "2d6+3", "1d20",
"4d8-1", "d100", "3d6".

All randomness goes through Python's random module, which can be seeded
in tests for deterministic verification.
"""

import random
import re

from dungeonmaster.models import DiceResult


# Pattern: optional count, "d", sides, optional modifier
# Matches: "2d6+3", "d20", "1d8-1", "4d6", "d100", "2d10+5"
_DICE_RE = re.compile(
    r"^(\d+)?d(\d+)([+-]\d+)?$",
    re.IGNORECASE,
)


def roll(expression: str) -> DiceResult:
    """Parse and roll a dice expression like '2d6+3', '1d20', 'd8'.

    Supports:
        - NdM: roll N dice with M sides (e.g. 2d6)
        - dM: shorthand for 1dM (e.g. d20)
        - NdM+K / NdM-K: add/subtract a flat modifier (e.g. 1d20+5)

    Returns a DiceResult with individual rolls, modifier, total, and
    natural max/min flags (based on the first die for d20-style checks).
    """
    expression = expression.strip().replace(" ", "")
    match = _DICE_RE.match(expression)
    if not match:
        raise ValueError(f"Invalid dice expression: '{expression}'")

    count = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if count < 1:
        raise ValueError(f"Dice count must be >= 1, got {count}")
    if sides < 2:
        raise ValueError(f"Dice sides must be >= 2, got {sides}")

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    # Natural max/min is meaningful for single-die rolls (like d20 checks)
    natural_max = len(rolls) == 1 and rolls[0] == sides
    natural_min = len(rolls) == 1 and rolls[0] == 1

    return DiceResult(
        expression=expression,
        rolls=rolls,
        modifier=modifier,
        total=total,
        natural_max=natural_max,
        natural_min=natural_min,
    )


def roll_d20(modifier: int = 0, advantage: bool = False, disadvantage: bool = False) -> DiceResult:
    """Roll a d20 with optional advantage/disadvantage.

    Advantage: roll 2d20, take the higher.
    Disadvantage: roll 2d20, take the lower.
    If both are True, they cancel out (roll normally).
    """
    if advantage and disadvantage:
        # Cancel out
        advantage = False
        disadvantage = False

    if advantage or disadvantage:
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        chosen = max(roll1, roll2) if advantage else min(roll1, roll2)
        total = chosen + modifier

        return DiceResult(
            expression=f"2d20{'kh1' if advantage else 'kl1'}{'+' if modifier >= 0 else ''}{modifier}" if modifier else f"2d20{'kh1' if advantage else 'kl1'}",
            rolls=[roll1, roll2],
            modifier=modifier,
            total=total,
            natural_max=chosen == 20,
            natural_min=chosen == 1,
        )
    else:
        die = random.randint(1, 20)
        total = die + modifier

        expr = f"1d20{'+' if modifier > 0 else ''}{modifier}" if modifier else "1d20"
        return DiceResult(
            expression=expr,
            rolls=[die],
            modifier=modifier,
            total=total,
            natural_max=die == 20,
            natural_min=die == 1,
        )


def roll_d100() -> DiceResult:
    """Roll percentile dice (d100). Used by WFRP, Call of Cthulhu, etc."""
    die = random.randint(1, 100)
    return DiceResult(
        expression="1d100",
        rolls=[die],
        modifier=0,
        total=die,
        natural_max=die == 100,
        natural_min=die == 1,
    )


def roll_multiple(expression: str, count: int) -> list[DiceResult]:
    """Roll the same expression multiple times. Useful for ability score generation."""
    return [roll(expression) for _ in range(count)]
