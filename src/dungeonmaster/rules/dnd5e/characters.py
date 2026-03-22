"""
D&D 5e character creation, management, and lifecycle.

Creates a complete character dict from player choices (race, class, abilities, name).
Now includes: subrace support, racial traits, class features at creation,
rest mechanics (short/long), and level-up with ASI.
"""

import random

from dungeonmaster.rules.dnd5e.abilities import ability_modifier, proficiency_bonus
from dungeonmaster.rules.dnd5e.combat import calculate_unarmored_ac
from dungeonmaster.rules.dnd5e.data import (
    ABILITIES,
    ASI_LEVELS,
    CLASS_CASTER_TYPE,
    CLASS_FEATURES,
    CLASS_HIT_DICE,
    CLASS_SAVE_PROFICIENCIES,
    CLASS_STARTING_EQUIPMENT,
    FULL_CASTER_SLOTS,
    HALF_CASTER_SLOTS,
    RACE_ABILITY_BONUSES,
    RACE_RESISTANCES,
    RACE_SPEED,
    RACE_TRAITS,
    RAGE_DATA,
    SNEAK_ATTACK_DICE,
    SUBRACES,
    WARLOCK_PACT_SLOTS,
)


def roll_ability_scores() -> dict[str, int]:
    """Roll ability scores using the 4d6-drop-lowest method."""
    scores = {}
    for ability in ABILITIES:
        rolls = sorted([random.randint(1, 6) for _ in range(4)])
        scores[ability] = sum(rolls[1:])  # drop lowest
    return scores


def standard_array() -> dict[str, int]:
    """Return the D&D 5e standard ability score array."""
    values = [15, 14, 13, 12, 10, 8]
    return dict(zip(ABILITIES, values))


def calculate_hp(character_class: str, constitution_score: int, level: int, extra_hp_per_level: int = 0) -> int:
    """Calculate max HP for a given class, CON, and level.

    extra_hp_per_level: for Hill Dwarf (+1 HP per level).
    """
    hit_die = CLASS_HIT_DICE.get(character_class, 8)
    con_mod = ability_modifier(constitution_score)

    # Level 1: max hit die + CON modifier
    hp = hit_die + con_mod + extra_hp_per_level

    # Levels 2+: average roll (rounded up) + CON modifier per level
    avg_roll = (hit_die // 2) + 1
    hp += (avg_roll + con_mod + extra_hp_per_level) * (level - 1)

    return max(1, hp)


def calculate_ac(character: dict) -> int:
    """Calculate Armor Class from equipped armor, DEX, and class features.

    Checks for Unarmored Defense (Barbarian: 10+DEX+CON, Monk: 10+DEX+WIS).
    """
    dex_mod = ability_modifier(character.get("abilities", {}).get("dexterity", 10))

    # Check if wearing armor
    wearing_armor = False
    base_ac = 10 + dex_mod  # unarmored default
    shield_bonus = 0

    inventory = character.get("inventory", [])
    for item in inventory:
        if not item.get("equipped", False):
            continue
        props = item.get("properties", {})

        if "ac_bonus" in props:
            shield_bonus = int(props["ac_bonus"])
        elif "ac" in props:
            wearing_armor = True
            armor_ac = int(props["ac"])
            armor_type = props.get("type", "light")

            if armor_type == "heavy":
                base_ac = armor_ac
            elif armor_type == "medium":
                base_ac = armor_ac + min(dex_mod, 2)
            elif armor_type == "light":
                base_ac = armor_ac + dex_mod

    # If not wearing armor, check for Unarmored Defense
    if not wearing_armor:
        unarmored_ac = calculate_unarmored_ac(character)
        if unarmored_ac is not None:
            base_ac = max(base_ac, unarmored_ac)

    return base_ac + shield_bonus


def _get_spell_slots(character_class: str, level: int) -> list[int]:
    """Get spell slot array for a class at a given level."""
    caster_type = CLASS_CASTER_TYPE.get(character_class)
    if caster_type == "full":
        return list(FULL_CASTER_SLOTS.get(level, [0] * 10))
    elif caster_type == "half":
        return list(HALF_CASTER_SLOTS.get(level, [0] * 10))
    elif caster_type == "pact":
        pact = WARLOCK_PACT_SLOTS.get(level, {"slots": 0, "level": 1})
        slots = [0] * 10
        if pact["slots"] > 0:
            slots[pact["level"]] = pact["slots"]
        return slots
    return [0] * 10


def _get_class_features_at_level(character_class: str, level: int) -> list[dict]:
    """Collect all class features from level 1 up to the given level."""
    features = []
    class_data = CLASS_FEATURES.get(character_class, {})
    for lvl in range(1, level + 1):
        lvl_features = class_data.get(lvl, [])
        for feat in lvl_features:
            # Later levels may override earlier features (e.g., Sneak Attack dice)
            # Remove older version of the same feature
            features = [f for f in features if f.get("name") != feat.get("name")]
            features.append(feat)
    return features


def create_character(choices: dict) -> dict:
    """Create a full D&D 5e character dict from player choices.

    Now supports subraces, racial traits, class features, and spell slots.
    """
    name = choices.get("name", "Unnamed Hero")
    race = choices.get("race", "human").lower()
    subrace = choices.get("subrace", "").lower()
    char_class = choices.get("character_class", "fighter").lower()
    level = choices.get("level", 1)

    # Ability scores: use provided, or roll
    if "abilities" in choices:
        abilities = dict(choices["abilities"])
    else:
        abilities = roll_ability_scores()

    # Apply racial bonuses (base race)
    race_bonuses = RACE_ABILITY_BONUSES.get(race, {})
    for ability, bonus in race_bonuses.items():
        abilities[ability] = abilities.get(ability, 10) + bonus

    # Apply subrace bonuses
    extra_hp_per_level = 0
    traits = list(RACE_TRAITS.get(race, []))
    resistances = list(RACE_RESISTANCES.get(race, []))

    if subrace and subrace in SUBRACES:
        sub_data = SUBRACES[subrace]
        for ability, bonus in sub_data.get("ability_bonuses", {}).items():
            abilities[ability] = abilities.get(ability, 10) + bonus
        traits = sub_data.get("traits", traits)
        extra_hp_per_level = sub_data.get("extra_hp_per_level", 0)
        # Add subrace resistances if any
        resistances.extend(RACE_RESISTANCES.get(subrace, []))

    # Derived stats
    hp = calculate_hp(char_class, abilities.get("constitution", 10), level, extra_hp_per_level)
    prof_bonus = proficiency_bonus(level)
    speed = RACE_SPEED.get(subrace, RACE_SPEED.get(race, 30))
    save_profs = CLASS_SAVE_PROFICIENCIES.get(char_class, [])

    # Skill proficiencies
    skill_profs = choices.get("proficiencies", [])

    # Class features
    class_features = _get_class_features_at_level(char_class, level)

    # Expertise (Rogue level 1 gets 2, Bard level 3 gets 2)
    expertise = list(choices.get("expertise", []))

    # Sneak attack dice (Rogue)
    sneak_dice = SNEAK_ATTACK_DICE.get(level) if char_class == "rogue" else None

    # Rage data (Barbarian)
    rage_data = RAGE_DATA.get(level) if char_class == "barbarian" else None

    # Spell slots
    max_slots = _get_spell_slots(char_class, level)

    # Starting equipment
    equipment = []
    for item_template in CLASS_STARTING_EQUIPMENT.get(char_class, []):
        item = {
            "name": item_template["name"],
            "description": "",
            "weight": 0.0,
            "quantity": item_template.get("quantity", 1),
            "equipped": True,
            "properties": dict(item_template.get("properties", {})),
        }
        equipment.append(item)

    # Hit dice for short rest
    hit_die = CLASS_HIT_DICE.get(char_class, 8)

    character = {
        "name": name,
        "race": race,
        "subrace": subrace,
        "character_class": char_class,
        "level": level,
        "abilities": abilities,
        "hp": {"current": hp, "max": hp, "temp": 0},
        "ac": 10,  # calculated after equipment
        "proficiency_bonus": prof_bonus,
        "speed": speed,
        "proficiencies": skill_profs,
        "save_proficiencies": save_profs,
        "expertise": expertise,
        "traits": traits,
        "resistances": resistances,
        "class_features": class_features,
        "inventory": equipment,
        "spells_known": [],
        "spell_slots": {"max": max_slots, "current": list(max_slots)},
        "conditions": [],
        "death_saves": {"successes": 0, "failures": 0},
        "hit_dice": {"size": hit_die, "total": level, "current": level},
        "is_player": choices.get("is_player", True),
        "personality": choices.get("personality", ""),
        "backstory": choices.get("backstory", ""),
        "gold": 50,
        "xp": 0,
    }

    # Rogue-specific
    if sneak_dice:
        character["sneak_attack_dice"] = sneak_dice

    # Barbarian-specific
    if rage_data:
        character["rage_uses"] = {"max": rage_data["uses"], "current": rage_data["uses"]}
        character["rage_bonus_damage"] = rage_data["bonus"]

    # Bard: Jack of All Trades at level 2+
    if char_class == "bard" and level >= 2:
        character["jack_of_all_trades"] = True

    # Calculate AC (after equipment and class features are set)
    character["ac"] = calculate_ac(character)

    return character


def take_short_rest(character: dict) -> dict:
    """Process a short rest: spend hit dice to recover HP.

    Returns dict describing what was restored.
    """
    hit_dice = character.get("hit_dice", {})
    available = hit_dice.get("current", 0)
    die_size = hit_dice.get("size", 8)
    hp = character.get("hp", {})
    current_hp = hp.get("current", 0)
    max_hp = hp.get("max", 0)

    if available <= 0 or current_hp >= max_hp:
        return {"hp_restored": 0, "hit_dice_spent": 0}

    # Spend up to all available hit dice
    con_mod = ability_modifier(character.get("abilities", {}).get("constitution", 10))
    total_healed = 0
    dice_spent = 0

    while available > 0 and current_hp < max_hp:
        roll_result = random.randint(1, die_size) + con_mod
        heal = max(0, roll_result)
        current_hp = min(max_hp, current_hp + heal)
        total_healed += heal
        available -= 1
        dice_spent += 1

    hp["current"] = current_hp
    character["hp"] = hp
    hit_dice["current"] = available
    character["hit_dice"] = hit_dice

    # Warlock: recover pact magic slots on short rest
    char_class = character.get("character_class", "").lower()
    slots_restored = []
    if char_class == "warlock":
        spell_slots = character.get("spell_slots", {})
        max_slots = spell_slots.get("max", [0] * 10)
        spell_slots["current"] = list(max_slots)
        character["spell_slots"] = spell_slots
        slots_restored = max_slots

    return {
        "hp_restored": total_healed,
        "hit_dice_spent": dice_spent,
        "slots_restored": slots_restored,
    }


def take_long_rest(character: dict) -> dict:
    """Process a long rest: restore all HP, regain half hit dice, reset spell slots."""
    hp = character.get("hp", {})
    max_hp = hp.get("max", 0)
    old_hp = hp.get("current", 0)
    hp["current"] = max_hp
    character["hp"] = hp

    # Regain spent hit dice (up to half total, minimum 1)
    hit_dice = character.get("hit_dice", {})
    total_dice = hit_dice.get("total", 1)
    regain = max(1, total_dice // 2)
    hit_dice["current"] = min(total_dice, hit_dice.get("current", 0) + regain)
    character["hit_dice"] = hit_dice

    # Reset spell slots to max
    spell_slots = character.get("spell_slots", {})
    max_slots = spell_slots.get("max", [0] * 10)
    spell_slots["current"] = list(max_slots)
    character["spell_slots"] = spell_slots

    # Reset rage uses (Barbarian)
    if "rage_uses" in character:
        character["rage_uses"]["current"] = character["rage_uses"]["max"]

    # Clear temporary conditions
    character["conditions"] = [
        c for c in character.get("conditions", [])
        if c.lower() not in ("frightened", "charmed", "raging")
    ]

    return {
        "hp_restored": max_hp - old_hp,
        "hit_dice_regained": regain,
        "spell_slots_reset": True,
    }


def level_up(character: dict, choices: dict) -> dict:
    """Apply a level-up to a character.

    choices may include:
    - ability_increase: {ability: str, amount: int} (for ASI levels)
    - new_spells: [str, ...] (spells learned)
    """
    old_level = character.get("level", 1)
    new_level = old_level + 1
    char_class = character.get("character_class", "fighter").lower()

    character["level"] = new_level
    character["proficiency_bonus"] = proficiency_bonus(new_level)

    # HP increase: average hit die + CON modifier
    hit_die = CLASS_HIT_DICE.get(char_class, 8)
    con_mod = ability_modifier(character.get("abilities", {}).get("constitution", 10))
    extra_hp_per_level = 1 if character.get("subrace") == "hill_dwarf" else 0
    hp_gain = (hit_die // 2) + 1 + con_mod + extra_hp_per_level
    hp_gain = max(1, hp_gain)

    hp = character.get("hp", {})
    hp["max"] = hp.get("max", 0) + hp_gain
    hp["current"] = hp.get("current", 0) + hp_gain
    character["hp"] = hp

    # Hit dice increase
    hit_dice = character.get("hit_dice", {})
    hit_dice["total"] = new_level
    hit_dice["current"] = hit_dice.get("current", 0) + 1
    character["hit_dice"] = hit_dice

    # Update class features
    character["class_features"] = _get_class_features_at_level(char_class, new_level)

    # Update sneak attack (Rogue)
    if char_class == "rogue":
        character["sneak_attack_dice"] = SNEAK_ATTACK_DICE.get(new_level)

    # Update rage (Barbarian)
    if char_class == "barbarian":
        rage = RAGE_DATA.get(new_level)
        if rage:
            character["rage_uses"] = {"max": rage["uses"], "current": rage["uses"]}
            character["rage_bonus_damage"] = rage["bonus"]

    # Update spell slots
    max_slots = _get_spell_slots(char_class, new_level)
    character["spell_slots"] = {"max": max_slots, "current": list(max_slots)}

    # Ability Score Improvement at ASI levels
    if new_level in ASI_LEVELS and "ability_increase" in choices:
        inc = choices["ability_increase"]
        ability = inc.get("ability", "")
        amount = inc.get("amount", 2)
        if ability in character.get("abilities", {}):
            character["abilities"][ability] = min(20, character["abilities"][ability] + amount)

    # Recalculate AC (CON/DEX may have changed)
    character["ac"] = calculate_ac(character)

    features_gained = [f.get("name", "") for f in CLASS_FEATURES.get(char_class, {}).get(new_level, [])]

    return {
        "new_level": new_level,
        "hp_gained": hp_gain,
        "features": features_gained,
    }


def get_character_summary(character: dict) -> str:
    """Return a concise human-readable character summary for prompts."""
    name = character.get("name", "Unknown")
    race = character.get("subrace") or character.get("race", "unknown")
    char_class = character.get("character_class", "unknown").title()
    level = character.get("level", 1)
    hp = character.get("hp", {})
    current_hp = hp.get("current", 0)
    max_hp = hp.get("max", 0)
    ac = character.get("ac", 10)
    abilities = character.get("abilities", {})

    ability_str = ", ".join(
        f"{a[:3].upper()} {abilities.get(a, 10)}"
        for a in ABILITIES
    )

    conditions = character.get("conditions", [])
    cond_str = f" [{', '.join(conditions)}]" if conditions else ""

    return (
        f"{name} — Level {level} {race.replace('_', ' ').title()} {char_class} | "
        f"HP {current_hp}/{max_hp} | AC {ac} | "
        f"{ability_str}{cond_str}"
    )
