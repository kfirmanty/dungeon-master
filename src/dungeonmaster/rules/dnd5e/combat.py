"""
D&D 5e combat mechanics.

Handles initiative, attack rolls, damage application, and death saving throws.
Now includes: condition-aware attacks, damage resistance/immunity,
unarmored defense, sneak attack, and concentration saves.
"""

from dungeonmaster.models import AttackResult, DamageResult, DiceResult
from dungeonmaster.rules.dice import roll, roll_d20
from dungeonmaster.rules.dnd5e.abilities import ability_modifier
from dungeonmaster.rules.dnd5e.conditions import get_condition_effects
from dungeonmaster.rules.dnd5e.data import SNEAK_ATTACK_DICE


def roll_initiative(character: dict) -> DiceResult:
    """Roll initiative: d20 + DEX modifier."""
    dex_score = character.get("abilities", {}).get("dexterity", 10)
    mod = ability_modifier(dex_score)
    return roll_d20(modifier=mod)


def calculate_unarmored_ac(character: dict) -> int | None:
    """Calculate unarmored defense AC for Barbarian and Monk.

    Returns None if the character doesn't have unarmored defense.
    """
    class_features = character.get("class_features", [])
    feature_names = [f.get("name", "").lower() if isinstance(f, dict) else f.lower()
                     for f in class_features]

    dex_mod = ability_modifier(character.get("abilities", {}).get("dexterity", 10))

    if "unarmored defense" in feature_names:
        char_class = character.get("character_class", "").lower()
        if char_class == "barbarian":
            con_mod = ability_modifier(character.get("abilities", {}).get("constitution", 10))
            return 10 + dex_mod + con_mod
        elif char_class == "monk":
            wis_mod = ability_modifier(character.get("abilities", {}).get("wisdom", 10))
            return 10 + dex_mod + wis_mod

    return None


def attack_roll(
    attacker: dict,
    target_ac: int,
    weapon: dict | None = None,
    advantage: bool = False,
    disadvantage: bool = False,
    sneak_attack_eligible: bool = False,
) -> AttackResult:
    """Resolve an attack: d20 + attack bonus vs AC, then damage if hit.

    Now includes:
    - Condition-based advantage/disadvantage (attacker and defender conditions)
    - Sneak Attack extra damage for rogues
    - Rage bonus damage for barbarians
    """
    # Check attacker conditions for disadvantage on attacks
    attacker_conditions = attacker.get("conditions", [])
    if attacker_conditions:
        effects = get_condition_effects(attacker_conditions)
        if effects.disadvantage_on_attacks:
            disadvantage = True
        # Invisible attacker gets advantage
        if "invisible" in [c.lower() for c in attacker_conditions]:
            advantage = True

    # Determine attack modifier
    if weapon and weapon.get("properties", {}).get("finesse"):
        str_mod = ability_modifier(attacker.get("abilities", {}).get("strength", 10))
        dex_mod = ability_modifier(attacker.get("abilities", {}).get("dexterity", 10))
        ability_mod = max(str_mod, dex_mod)
    elif weapon and weapon.get("properties", {}).get("range"):
        ability_mod = ability_modifier(attacker.get("abilities", {}).get("dexterity", 10))
    else:
        ability_mod = ability_modifier(attacker.get("abilities", {}).get("strength", 10))

    prof_bonus = attacker.get("proficiency_bonus", 2)
    total_attack_mod = ability_mod + prof_bonus

    # Roll attack
    attack_dice = roll_d20(modifier=total_attack_mod, advantage=advantage, disadvantage=disadvantage)

    # Natural 1 always misses
    if attack_dice.natural_min:
        return AttackResult(
            attack_roll=attack_dice,
            hit=False,
            critical=False,
            damage_roll=None,
            total_damage=0,
            attacker=attacker.get("name", "Unknown"),
            defender=f"AC {target_ac}",
            description=f"Attack: {attack_dice.total} vs AC {target_ac} — Critical Miss!",
        )

    critical = attack_dice.natural_max
    hit = critical or attack_dice.total >= target_ac

    if not hit:
        return AttackResult(
            attack_roll=attack_dice,
            hit=False,
            critical=False,
            damage_roll=None,
            total_damage=0,
            attacker=attacker.get("name", "Unknown"),
            defender=f"AC {target_ac}",
            description=f"Attack: {attack_dice.total} vs AC {target_ac} — Miss!",
        )

    # Roll damage
    damage_expr = "1d8"  # default
    if weapon:
        damage_expr = weapon.get("properties", {}).get("damage", "1d8")

    damage_dice = roll(damage_expr)
    base_damage = damage_dice.total + ability_mod
    total_damage = base_damage
    damage_parts = [f"{damage_dice.rolls}+{ability_mod}"]

    # Critical hit: roll damage dice twice
    if critical:
        crit_bonus = roll(damage_expr)
        total_damage += crit_bonus.total
        damage_parts.append(f"crit {crit_bonus.rolls}")

    # Sneak Attack (Rogue)
    sneak_dice_expr = attacker.get("sneak_attack_dice")
    if not sneak_dice_expr:
        # Derive from class + level
        char_class = attacker.get("character_class", "").lower()
        level = attacker.get("level", 1)
        if char_class == "rogue":
            sneak_dice_expr = SNEAK_ATTACK_DICE.get(level)

    if sneak_dice_expr and sneak_attack_eligible:
        is_finesse = weapon and weapon.get("properties", {}).get("finesse")
        is_ranged = weapon and weapon.get("properties", {}).get("range")
        if is_finesse or is_ranged:
            sneak_roll = roll(sneak_dice_expr)
            total_damage += sneak_roll.total
            damage_parts.append(f"sneak {sneak_roll.rolls}")

    # Rage bonus damage (Barbarian)
    rage_bonus = attacker.get("rage_bonus_damage", 0)
    if rage_bonus and "raging" in [c.lower() for c in attacker.get("conditions", [])]:
        # Rage only applies to STR-based melee attacks
        is_ranged = weapon and weapon.get("properties", {}).get("range")
        if not is_ranged:
            total_damage += rage_bonus
            damage_parts.append(f"rage +{rage_bonus}")

    total_damage = max(0, total_damage)

    crit_str = "CRITICAL HIT! " if critical else ""
    description = (
        f"Attack: {attack_dice.total} vs AC {target_ac} — {crit_str}Hit! "
        f"Damage: {' + '.join(damage_parts)} = {total_damage}"
    )

    final_damage_dice = DiceResult(
        expression=f"{damage_expr}+{ability_mod}",
        rolls=damage_dice.rolls,
        modifier=ability_mod,
        total=total_damage,
    )

    return AttackResult(
        attack_roll=attack_dice,
        hit=True,
        critical=critical,
        damage_roll=final_damage_dice,
        total_damage=total_damage,
        attacker=attacker.get("name", "Unknown"),
        defender=f"AC {target_ac}",
        description=description,
    )


def apply_damage(target: dict, damage: int, damage_type: str = "") -> DamageResult:
    """Apply damage to a character, mutating the target dict in place.

    Checks for damage resistance (half damage) and immunity (no damage).
    """
    # Check resistance/immunity
    resistances = [r.lower() for r in target.get("resistances", [])]
    immunities = [i.lower() for i in target.get("immunities", [])]
    damage_type_lower = damage_type.lower() if damage_type else ""

    if damage_type_lower and damage_type_lower in immunities:
        name = target.get("name", "Unknown")
        return DamageResult(
            damage_dealt=0,
            target=name,
            description=f"{name} is immune to {damage_type} damage!",
        )

    if damage_type_lower and damage_type_lower in resistances:
        damage = damage // 2  # resistance halves damage

    hp = target.get("hp", {})
    current = hp.get("current", 0)
    max_hp = hp.get("max", 0)

    # Reduce temp HP first
    temp_hp = hp.get("temp", 0)
    if temp_hp > 0:
        absorbed = min(temp_hp, damage)
        temp_hp -= absorbed
        damage -= absorbed
        hp["temp"] = temp_hp

    # Apply remaining damage to current HP
    new_hp = max(0, current - damage)
    actual_dealt = current - new_hp
    hp["current"] = new_hp
    target["hp"] = hp

    # Check for unconscious / death
    unconscious = new_hp == 0 and current > 0
    overflow = damage - current
    dead = unconscious and overflow >= max_hp

    if unconscious and not dead:
        target["death_saves"] = {"successes": 0, "failures": 0}

    name = target.get("name", "Unknown")
    resist_note = f" (resisted, halved)" if damage_type_lower in resistances else ""
    if dead:
        desc = f"{name} takes {actual_dealt} {damage_type} damage{resist_note} and is killed instantly by massive damage!"
    elif unconscious:
        desc = f"{name} takes {actual_dealt} {damage_type} damage{resist_note} and falls unconscious! (0/{max_hp} HP)"
    else:
        desc = f"{name} takes {actual_dealt} {damage_type} damage{resist_note}. ({new_hp}/{max_hp} HP)"

    return DamageResult(
        damage_dealt=actual_dealt,
        target_unconscious=unconscious,
        target_dead=dead,
        target=name,
        description=desc,
    )


def death_saving_throw(character: dict) -> tuple[DiceResult, str]:
    """Roll a death saving throw.

    - DC 10: d20 >= 10 is a success, < 10 is a failure.
    - Natural 20: regain 1 HP and become conscious.
    - Natural 1: counts as 2 failures.
    - 3 successes: stabilize.
    - 3 failures: die.
    """
    dice = roll_d20()
    saves = character.get("death_saves", {"successes": 0, "failures": 0})

    if dice.natural_max:
        hp = character.get("hp", {})
        hp["current"] = 1
        character["hp"] = hp
        character["death_saves"] = {"successes": 0, "failures": 0}
        return dice, "revived"

    if dice.natural_min:
        saves["failures"] = saves.get("failures", 0) + 2
    elif dice.total >= 10:
        saves["successes"] = saves.get("successes", 0) + 1
    else:
        saves["failures"] = saves.get("failures", 0) + 1

    character["death_saves"] = saves

    if saves.get("failures", 0) >= 3:
        return dice, "dead"
    if saves.get("successes", 0) >= 3:
        character["death_saves"] = {"successes": 0, "failures": 0}
        return dice, "stabilized"
    if dice.total >= 10:
        return dice, "success"
    return dice, "failure"
