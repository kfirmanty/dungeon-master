"""
D&D 5e ability checks, skill checks, and saving throws.

Core mechanic: d20 + modifier vs DC (Difficulty Class).
- Ability check: d20 + ability modifier (+ proficiency if proficient)
- Skill check: d20 + ability modifier for governing ability (+ proficiency, or double for expertise)
- Saving throw: d20 + ability modifier (+ proficiency if proficient in that save)

Conditions are checked before each roll and may impose advantage/disadvantage
or auto-failure (e.g., paralyzed auto-fails STR/DEX saves).
"""

from dungeonmaster.models import CheckResult, DiceResult
from dungeonmaster.rules.dice import roll_d20
from dungeonmaster.rules.dnd5e.conditions import get_condition_effects
from dungeonmaster.rules.dnd5e.data import PROFICIENCY_BY_LEVEL, SKILL_ABILITIES


def ability_modifier(score: int) -> int:
    """D&D 5e ability modifier: (score - 10) // 2.

    Examples: 10 → +0, 14 → +2, 8 → -1, 20 → +5, 1 → -5
    """
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    """Proficiency bonus by character level (1-20)."""
    if level < 1:
        return 2
    index = min(level - 1, len(PROFICIENCY_BY_LEVEL) - 1)
    return PROFICIENCY_BY_LEVEL[index]


def _apply_condition_modifiers(
    character: dict,
    check_type: str,
    ability: str,
    advantage: bool,
    disadvantage: bool,
) -> tuple[bool, bool, bool]:
    """Check active conditions and adjust advantage/disadvantage.

    Returns (advantage, disadvantage, auto_fail).
    """
    conditions = character.get("conditions", [])
    if not conditions:
        return advantage, disadvantage, False

    effects = get_condition_effects(conditions)

    # Auto-fail checks
    if check_type == "saving_throw":
        if ability in ("strength",) and effects.auto_fail_str_saves:
            return advantage, disadvantage, True
        if ability in ("dexterity",) and effects.auto_fail_dex_saves:
            return advantage, disadvantage, True

    # Condition-imposed disadvantage
    if check_type in ("ability_check", "skill_check"):
        if effects.disadvantage_on_ability_checks:
            disadvantage = True
    if check_type == "saving_throw":
        if ability == "dexterity" and effects.disadvantage_on_dex_saves:
            disadvantage = True
        if ability == "strength" and effects.disadvantage_on_str_saves:
            disadvantage = True

    return advantage, disadvantage, False


def ability_check(
    character: dict,
    ability: str,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
) -> CheckResult:
    """Roll an ability check: d20 + ability modifier vs DC."""
    score = character.get("abilities", {}).get(ability, 10)
    mod = ability_modifier(score)

    # Apply condition modifiers
    advantage, disadvantage, auto_fail = _apply_condition_modifiers(
        character, "ability_check", ability, advantage, disadvantage
    )

    if auto_fail:
        return CheckResult(
            dice_result=DiceResult(expression="auto-fail", rolls=[0], modifier=0, total=0),
            success=False,
            target_number=dc,
            check_type="ability_check",
            detail=ability,
            actor=character.get("name", "Unknown"),
            description=f"Ability check ({ability.title()}): Auto-fail (condition)",
        )

    dice = roll_d20(modifier=mod, advantage=advantage, disadvantage=disadvantage)
    success = dice.total >= dc

    description = (
        f"Ability check ({ability.title()}): "
        f"{dice.rolls} + {mod} = {dice.total} vs DC {dc} — "
        f"{'Success' if success else 'Failure'}"
    )
    if dice.natural_max:
        description += " (Natural 20!)"
    elif dice.natural_min:
        description += " (Natural 1!)"

    return CheckResult(
        dice_result=dice,
        success=success,
        target_number=dc,
        check_type="ability_check",
        detail=ability,
        actor=character.get("name", "Unknown"),
        description=description,
    )


def skill_check(
    character: dict,
    skill: str,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
) -> CheckResult:
    """Roll a skill check: d20 + ability modifier + proficiency/expertise.

    Supports:
    - Proficiency: character["proficiencies"] list
    - Expertise (Rogue/Bard): character["expertise"] list — doubles proficiency bonus
    - Jack of All Trades (Bard): character["jack_of_all_trades"] — half proficiency on non-proficient checks
    - Condition modifiers: poisoned/frightened impose disadvantage
    """
    skill_lower = skill.lower()
    governing_ability = SKILL_ABILITIES.get(skill_lower)
    if governing_ability is None:
        raise ValueError(
            f"Unknown skill '{skill}'. Valid skills: {', '.join(sorted(SKILL_ABILITIES))}"
        )

    score = character.get("abilities", {}).get(governing_ability, 10)
    mod = ability_modifier(score)
    prof = proficiency_bonus(character.get("level", 1))

    # Check expertise (double proficiency) → proficiency → jack of all trades (half)
    is_expert = skill_lower in [e.lower() for e in character.get("expertise", [])]
    is_proficient = skill_lower in [p.lower() for p in character.get("proficiencies", [])]
    has_jack = character.get("jack_of_all_trades", False)

    if is_expert:
        skill_bonus = prof * 2
        bonus_label = f" + {prof * 2} expertise"
    elif is_proficient:
        skill_bonus = prof
        bonus_label = f" + {prof} prof"
    elif has_jack:
        skill_bonus = prof // 2
        bonus_label = f" + {prof // 2} jack"
    else:
        skill_bonus = 0
        bonus_label = ""

    total_mod = mod + skill_bonus

    # Apply condition modifiers
    advantage, disadvantage, auto_fail = _apply_condition_modifiers(
        character, "skill_check", governing_ability, advantage, disadvantage
    )

    if auto_fail:
        return CheckResult(
            dice_result=DiceResult(expression="auto-fail", rolls=[0], modifier=0, total=0),
            success=False,
            target_number=dc,
            check_type="skill_check",
            detail=skill_lower,
            actor=character.get("name", "Unknown"),
            description=f"Skill check ({skill.title()}): Auto-fail (condition)",
        )

    dice = roll_d20(modifier=total_mod, advantage=advantage, disadvantage=disadvantage)
    success = dice.total >= dc

    description = (
        f"Skill check ({skill.title()}): "
        f"{dice.rolls} + {mod}{bonus_label} = {dice.total} vs DC {dc} — "
        f"{'Success' if success else 'Failure'}"
    )
    if dice.natural_max:
        description += " (Natural 20!)"
    elif dice.natural_min:
        description += " (Natural 1!)"

    return CheckResult(
        dice_result=dice,
        success=success,
        target_number=dc,
        check_type="skill_check",
        detail=skill_lower,
        actor=character.get("name", "Unknown"),
        description=description,
    )


def saving_throw(
    character: dict,
    ability: str,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
) -> CheckResult:
    """Roll a saving throw: d20 + ability modifier + proficiency (if proficient).

    Conditions may impose auto-fail (paralyzed/stunned/unconscious auto-fail STR/DEX).
    """
    ability_lower = ability.lower()
    score = character.get("abilities", {}).get(ability_lower, 10)
    mod = ability_modifier(score)

    is_proficient = ability_lower in [p.lower() for p in character.get("save_proficiencies", [])]
    prof = proficiency_bonus(character.get("level", 1)) if is_proficient else 0
    total_mod = mod + prof

    # Apply condition modifiers
    advantage, disadvantage, auto_fail = _apply_condition_modifiers(
        character, "saving_throw", ability_lower, advantage, disadvantage
    )

    if auto_fail:
        return CheckResult(
            dice_result=DiceResult(expression="auto-fail", rolls=[0], modifier=0, total=0),
            success=False,
            target_number=dc,
            check_type="saving_throw",
            detail=ability_lower,
            actor=character.get("name", "Unknown"),
            description=f"Saving throw ({ability.title()}): Auto-fail (paralyzed/stunned/unconscious)",
        )

    dice = roll_d20(modifier=total_mod, advantage=advantage, disadvantage=disadvantage)
    success = dice.total >= dc

    prof_str = f" + {prof} prof" if prof else ""
    description = (
        f"Saving throw ({ability.title()}): "
        f"{dice.rolls} + {mod}{prof_str} = {dice.total} vs DC {dc} — "
        f"{'Success' if success else 'Failure'}"
    )
    if dice.natural_max:
        description += " (Natural 20!)"
    elif dice.natural_min:
        description += " (Natural 1!)"

    return CheckResult(
        dice_result=dice,
        success=success,
        target_number=dc,
        check_type="saving_throw",
        detail=ability_lower,
        actor=character.get("name", "Unknown"),
        description=description,
    )


def concentration_save(character: dict, damage: int) -> CheckResult:
    """Roll a concentration save: CON save vs max(10, damage // 2)."""
    dc = max(10, damage // 2)
    return saving_throw(character, "constitution", dc)
