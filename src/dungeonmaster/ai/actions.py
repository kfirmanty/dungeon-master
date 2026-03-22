"""
Action parser — extracts [ROLL:...] tags from LLM output and executes
them through the rules engine.

The AI DM embeds roll requests in its narrative:
    "The rogue attempts to pick the lock with nimble fingers.
    [ROLL:skill_check:sleight_of_hand:DC15:Lyra]"

This module parses those tags into structured GameAction objects and
routes them to the appropriate RulesEngine method.
"""

import re
from dataclasses import dataclass

from dungeonmaster.models import AttackResult, CheckResult
from dungeonmaster.rules.base import RulesEngine


# Strict 4-field: [ROLL:check_type:detail:DC_or_AC_value:actor_name]
# Allows optional spaces around colons
_ROLL_TAG_4 = re.compile(
    r"\[ROLL\s*:\s*(\w+)\s*:\s*(\w+)\s*:\s*(?:DC|AC)?\s*(\d+)\s*:\s*([^\]]+?)\s*\]",
    re.IGNORECASE,
)

# Loose 3-field (LLM sometimes skips check_type): [ROLL: detail: DC value: actor]
_ROLL_TAG_3 = re.compile(
    r"\[ROLL\s*:\s*(\w+)\s*:\s*(?:DC|AC)\s*(\d+)\s*:\s*([^\]]+?)\s*\]",
    re.IGNORECASE,
)

# Skill name → check_type mapping for the 3-field fallback
_SKILL_TO_CHECK_TYPE = {
    "perception": "skill_check", "stealth": "skill_check", "athletics": "skill_check",
    "acrobatics": "skill_check", "arcana": "skill_check", "history": "skill_check",
    "investigation": "skill_check", "nature": "skill_check", "religion": "skill_check",
    "animal_handling": "skill_check", "insight": "skill_check", "medicine": "skill_check",
    "survival": "skill_check", "deception": "skill_check", "intimidation": "skill_check",
    "performance": "skill_check", "persuasion": "skill_check", "sleight_of_hand": "skill_check",
    "strength": "saving_throw", "dexterity": "saving_throw", "constitution": "saving_throw",
    "intelligence": "saving_throw", "wisdom": "saving_throw", "charisma": "saving_throw",
}


@dataclass
class GameAction:
    """A structured action extracted from AI output."""

    action_type: str  # "skill_check", "saving_throw", "attack", "ability_check"
    detail: str  # "stealth", "dexterity", "longsword"
    target_value: int  # DC or AC
    actor: str  # character name
    raw_tag: str  # the original tag string for reference


@dataclass
class ActionResult:
    """Result of executing a GameAction through the rules engine."""

    action: GameAction
    check_result: CheckResult | None = None
    attack_result: AttackResult | None = None
    description: str = ""  # human-readable summary


def parse_actions(text: str) -> tuple[str, list[GameAction]]:
    """Extract roll tags from AI output and return clean narrative + actions.

    Handles both strict 4-field format [ROLL:type:detail:DC:actor] and
    loose 3-field format [ROLL:skill:DC value:actor] that LLMs often produce.

    Returns:
        (narrative_text, list_of_actions)
        narrative_text has the [ROLL:...] tags stripped out.
    """
    actions = []
    matched_spans = []

    # Try strict 4-field format first
    for match in _ROLL_TAG_4.finditer(text):
        actions.append(GameAction(
            action_type=match.group(1).lower().replace(" ", "_"),
            detail=match.group(2).lower().replace(" ", "_"),
            target_value=int(match.group(3)),
            actor=match.group(4).strip(),
            raw_tag=match.group(0),
        ))
        matched_spans.append(match.span())

    # Then try loose 3-field format for any remaining unmatched tags
    for match in _ROLL_TAG_3.finditer(text):
        # Skip if this span was already matched by the 4-field regex
        if any(s[0] <= match.start() < s[1] for s in matched_spans):
            continue
        detail = match.group(1).lower().replace(" ", "_")
        # Infer check_type from the detail name
        check_type = _SKILL_TO_CHECK_TYPE.get(detail, "skill_check")
        actions.append(GameAction(
            action_type=check_type,
            detail=detail,
            target_value=int(match.group(2)),
            actor=match.group(3).strip(),
            raw_tag=match.group(0),
        ))

    # Strip all [ROLL...] tags from narrative (catch any format)
    clean_text = re.sub(r"\[ROLL[^\]]*\]", "", text, flags=re.IGNORECASE).strip()
    # Clean up double blank lines left by tag removal
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

    return clean_text, actions


def execute_action(
    action: GameAction,
    engine: RulesEngine,
    characters: dict[str, dict],
) -> ActionResult:
    """Execute a parsed action through the rules engine.

    Args:
        action: The parsed GameAction
        engine: The active RulesEngine
        characters: Dict mapping character names to their character dicts
            (includes player, companions, and enemies)

    Returns:
        ActionResult with the mechanical outcome
    """
    actor_char = characters.get(action.actor)
    if actor_char is None:
        return ActionResult(
            action=action,
            description=f"Unknown character '{action.actor}' — skipping roll.",
        )

    if action.action_type == "attack":
        # For attacks, we need a defender. Use the target_value as AC directly.
        # Build a minimal defender dict with just AC.
        defender = {"name": "target", "ac": action.target_value}

        # Try to find a weapon matching the detail
        weapon = None
        for item in actor_char.get("inventory", []):
            if item.get("equipped") and action.detail in item.get("name", "").lower():
                weapon = item
                break

        result = engine.resolve_attack(actor_char, defender, weapon=weapon)
        return ActionResult(
            action=action,
            attack_result=result,
            description=result.description,
        )
    else:
        # All other types route through roll_check
        result = engine.roll_check(
            character=actor_char,
            check_type=action.action_type,
            detail=action.detail,
            target=action.target_value,
        )
        return ActionResult(
            action=action,
            check_result=result,
            description=result.description,
        )


def format_result_for_llm(result: ActionResult) -> str:
    """Format an action result as context for the LLM's follow-up narration."""
    if result.attack_result:
        ar = result.attack_result
        parts = [f"Attack by {result.action.actor}: {ar.attack_roll.expression} = {ar.attack_roll.total}"]
        if ar.critical:
            parts.append("CRITICAL HIT!")
        elif ar.hit:
            parts.append(f"Hit! (vs AC {result.action.target_value})")
            parts.append(f"Damage: {ar.total_damage}")
        else:
            parts.append(f"Miss! (vs AC {result.action.target_value})")
        return " | ".join(parts)

    if result.check_result:
        cr = result.check_result
        return (
            f"{cr.check_type.replace('_', ' ').title()} ({cr.detail}) by {cr.actor}: "
            f"{cr.dice_result.expression} = {cr.dice_result.total} vs DC {cr.target_number} — "
            f"{'SUCCESS' if cr.success else 'FAILURE'}"
        )

    return result.description
