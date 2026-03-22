"""
D&D 5e constants and reference data.

All the lookup tables the rules engine needs: skill-to-ability mappings,
class hit dice, proficiency bonus by level, race traits, etc.
"""

# ---------------------------------------------------------------------------
# Skills → Governing Ability
# ---------------------------------------------------------------------------

SKILL_ABILITIES: dict[str, str] = {
    "athletics": "strength",
    "acrobatics": "dexterity",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "arcana": "intelligence",
    "history": "intelligence",
    "investigation": "intelligence",
    "nature": "intelligence",
    "religion": "intelligence",
    "animal_handling": "wisdom",
    "insight": "wisdom",
    "medicine": "wisdom",
    "perception": "wisdom",
    "survival": "wisdom",
    "deception": "charisma",
    "intimidation": "charisma",
    "performance": "charisma",
    "persuasion": "charisma",
}

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

# ---------------------------------------------------------------------------
# Class Data
# ---------------------------------------------------------------------------

CLASS_HIT_DICE: dict[str, int] = {
    "barbarian": 12,
    "bard": 8,
    "cleric": 8,
    "druid": 8,
    "fighter": 10,
    "monk": 8,
    "paladin": 10,
    "ranger": 10,
    "rogue": 8,
    "sorcerer": 6,
    "warlock": 8,
    "wizard": 6,
}

# Proficiency bonus by character level (index 0 = level 1)
PROFICIENCY_BY_LEVEL: list[int] = [
    2, 2, 2, 2,   # levels 1-4
    3, 3, 3, 3,   # levels 5-8
    4, 4, 4, 4,   # levels 9-12
    5, 5, 5, 5,   # levels 13-16
    6, 6, 6, 6,   # levels 17-20
]

# Saving throw proficiencies by class
CLASS_SAVE_PROFICIENCIES: dict[str, list[str]] = {
    "barbarian": ["strength", "constitution"],
    "bard": ["dexterity", "charisma"],
    "cleric": ["wisdom", "charisma"],
    "druid": ["intelligence", "wisdom"],
    "fighter": ["strength", "constitution"],
    "monk": ["strength", "dexterity"],
    "paladin": ["wisdom", "charisma"],
    "ranger": ["strength", "dexterity"],
    "rogue": ["dexterity", "intelligence"],
    "sorcerer": ["constitution", "charisma"],
    "warlock": ["wisdom", "charisma"],
    "wizard": ["intelligence", "wisdom"],
}

# Starting skill proficiency count by class
CLASS_SKILL_COUNT: dict[str, int] = {
    "barbarian": 2,
    "bard": 3,
    "cleric": 2,
    "druid": 2,
    "fighter": 2,
    "monk": 2,
    "paladin": 2,
    "ranger": 3,
    "rogue": 4,
    "sorcerer": 2,
    "warlock": 2,
    "wizard": 2,
}

# ---------------------------------------------------------------------------
# Race Data
# ---------------------------------------------------------------------------

# Ability score increases by race
RACE_ABILITY_BONUSES: dict[str, dict[str, int]] = {
    "human": {"strength": 1, "dexterity": 1, "constitution": 1, "intelligence": 1, "wisdom": 1, "charisma": 1},
    "elf": {"dexterity": 2},
    "dwarf": {"constitution": 2},
    "halfling": {"dexterity": 2},
    "half_orc": {"strength": 2, "constitution": 1},
    "tiefling": {"intelligence": 1, "charisma": 2},
    "dragonborn": {"strength": 2, "charisma": 1},
    "gnome": {"intelligence": 2},
    "half_elf": {"charisma": 2},  # +1 to two others chosen at creation
}

RACE_SPEED: dict[str, int] = {
    "human": 30,
    "elf": 30,
    "high_elf": 30,
    "wood_elf": 35,
    "dwarf": 25,
    "hill_dwarf": 25,
    "mountain_dwarf": 25,
    "halfling": 25,
    "lightfoot_halfling": 25,
    "stout_halfling": 25,
    "half_orc": 30,
    "tiefling": 30,
    "dragonborn": 30,
    "gnome": 25,
    "half_elf": 30,
}

# ---------------------------------------------------------------------------
# Subraces
# ---------------------------------------------------------------------------

# Maps subrace → (parent_race, additional_ability_bonuses, additional_traits)
SUBRACES: dict[str, dict] = {
    "high_elf": {
        "parent": "elf",
        "ability_bonuses": {"intelligence": 1},
        "traits": ["darkvision_60", "keen_senses", "fey_ancestry", "trance", "elf_weapon_training", "cantrip"],
    },
    "wood_elf": {
        "parent": "elf",
        "ability_bonuses": {"wisdom": 1},
        "traits": ["darkvision_60", "keen_senses", "fey_ancestry", "trance", "elf_weapon_training", "fleet_of_foot", "mask_of_the_wild"],
    },
    "hill_dwarf": {
        "parent": "dwarf",
        "ability_bonuses": {"wisdom": 1},
        "traits": ["darkvision_60", "dwarven_resilience", "dwarven_combat_training", "stonecunning", "dwarven_toughness"],
        "extra_hp_per_level": 1,
    },
    "mountain_dwarf": {
        "parent": "dwarf",
        "ability_bonuses": {"strength": 2},
        "traits": ["darkvision_60", "dwarven_resilience", "dwarven_combat_training", "stonecunning", "dwarven_armor_training"],
    },
    "lightfoot_halfling": {
        "parent": "halfling",
        "ability_bonuses": {"charisma": 1},
        "traits": ["lucky", "brave", "halfling_nimbleness", "naturally_stealthy"],
    },
    "stout_halfling": {
        "parent": "halfling",
        "ability_bonuses": {"constitution": 1},
        "traits": ["lucky", "brave", "halfling_nimbleness", "stout_resilience"],
    },
}

# ---------------------------------------------------------------------------
# Racial Traits
# ---------------------------------------------------------------------------

RACE_TRAITS: dict[str, list[str]] = {
    "human": [],
    "elf": ["darkvision_60", "keen_senses", "fey_ancestry", "trance"],
    "dwarf": ["darkvision_60", "dwarven_resilience", "dwarven_combat_training", "stonecunning"],
    "halfling": ["lucky", "brave", "halfling_nimbleness"],
    "half_orc": ["darkvision_60", "menacing", "relentless_endurance", "savage_attacks"],
    "tiefling": ["darkvision_60", "hellish_resistance", "infernal_legacy"],
    "dragonborn": ["breath_weapon", "damage_resistance"],
    "gnome": ["darkvision_60", "gnome_cunning"],
    "half_elf": ["darkvision_60", "fey_ancestry", "skill_versatility"],
}

# Racial resistances (for damage type resistance checks)
RACE_RESISTANCES: dict[str, list[str]] = {
    "dwarf": ["poison"],
    "stout_halfling": ["poison"],
    "tiefling": ["fire"],
    "half_orc": [],
    "dragonborn": [],  # depends on ancestry choice
}

# Starting equipment templates by class (simplified)
CLASS_STARTING_EQUIPMENT: dict[str, list[dict]] = {
    "fighter": [
        {"name": "Longsword", "properties": {"damage": "1d8", "type": "slashing", "versatile": "1d10"}},
        {"name": "Shield", "properties": {"ac_bonus": "2"}},
        {"name": "Chain Mail", "properties": {"ac": "16", "type": "heavy"}},
    ],
    "wizard": [
        {"name": "Quarterstaff", "properties": {"damage": "1d6", "type": "bludgeoning", "versatile": "1d8"}},
        {"name": "Spellbook", "properties": {}},
        {"name": "Robes", "properties": {"ac": "11", "type": "none"}},
    ],
    "rogue": [
        {"name": "Shortsword", "properties": {"damage": "1d6", "type": "piercing", "finesse": "true"}},
        {"name": "Shortbow", "properties": {"damage": "1d6", "type": "piercing", "range": "80/320"}},
        {"name": "Leather Armor", "properties": {"ac": "11", "type": "light"}},
        {"name": "Thieves' Tools", "properties": {}},
    ],
    "cleric": [
        {"name": "Mace", "properties": {"damage": "1d6", "type": "bludgeoning"}},
        {"name": "Shield", "properties": {"ac_bonus": "2"}},
        {"name": "Scale Mail", "properties": {"ac": "14", "type": "medium"}},
        {"name": "Holy Symbol", "properties": {}},
    ],
    "ranger": [
        {"name": "Longbow", "properties": {"damage": "1d8", "type": "piercing", "range": "150/600"}},
        {"name": "Shortsword", "properties": {"damage": "1d6", "type": "piercing", "finesse": "true"}},
        {"name": "Leather Armor", "properties": {"ac": "11", "type": "light"}},
    ],
    "bard": [
        {"name": "Rapier", "properties": {"damage": "1d8", "type": "piercing", "finesse": "true"}},
        {"name": "Lute", "properties": {}},
        {"name": "Leather Armor", "properties": {"ac": "11", "type": "light"}},
    ],
    "paladin": [
        {"name": "Longsword", "properties": {"damage": "1d8", "type": "slashing", "versatile": "1d10"}},
        {"name": "Shield", "properties": {"ac_bonus": "2"}},
        {"name": "Chain Mail", "properties": {"ac": "16", "type": "heavy"}},
        {"name": "Holy Symbol", "properties": {}},
    ],
    "barbarian": [
        {"name": "Greataxe", "properties": {"damage": "1d12", "type": "slashing", "two_handed": "true"}},
        {"name": "Handaxe", "properties": {"damage": "1d6", "type": "slashing", "thrown": "20/60"}, "quantity": 2},
        {"name": "Hide Armor", "properties": {"ac": "12", "type": "medium"}},
    ],
    "druid": [
        {"name": "Scimitar", "properties": {"damage": "1d6", "type": "slashing", "finesse": "true"}},
        {"name": "Wooden Shield", "properties": {"ac_bonus": "2"}},
        {"name": "Leather Armor", "properties": {"ac": "11", "type": "light"}},
        {"name": "Druidic Focus", "properties": {}},
    ],
    "monk": [
        {"name": "Shortsword", "properties": {"damage": "1d6", "type": "piercing", "finesse": "true"}},
        {"name": "Dart", "properties": {"damage": "1d4", "type": "piercing", "thrown": "20/60"}, "quantity": 10},
    ],
    "sorcerer": [
        {"name": "Dagger", "properties": {"damage": "1d4", "type": "piercing", "finesse": "true", "thrown": "20/60"}},
        {"name": "Arcane Focus", "properties": {}},
    ],
    "warlock": [
        {"name": "Light Crossbow", "properties": {"damage": "1d8", "type": "piercing", "range": "80/320"}},
        {"name": "Dagger", "properties": {"damage": "1d4", "type": "piercing", "finesse": "true", "thrown": "20/60"}},
        {"name": "Leather Armor", "properties": {"ac": "11", "type": "light"}},
        {"name": "Arcane Focus", "properties": {}},
    ],
}

# ---------------------------------------------------------------------------
# Class Features (levels 1-5, key defining features)
# ---------------------------------------------------------------------------

# Maps class → level → list of feature dicts
# Each feature: {"name": str, "description": str, ...mechanic-specific keys}
CLASS_FEATURES: dict[str, dict[int, list[dict]]] = {
    "barbarian": {
        1: [
            {"name": "Rage", "uses_per_rest": 2, "bonus_damage": 2,
             "description": "Bonus action: advantage on STR checks/saves, +2 melee damage, resistance to bludgeoning/piercing/slashing. Lasts 1 minute."},
            {"name": "Unarmored Defense", "ac_formula": "10+dex+con",
             "description": "While not wearing armor, AC = 10 + DEX modifier + CON modifier."},
        ],
        2: [{"name": "Reckless Attack", "description": "Advantage on STR melee attacks this turn; attacks against you have advantage until next turn."},
            {"name": "Danger Sense", "description": "Advantage on DEX saving throws against effects you can see."}],
        3: [{"name": "Rage Uses", "uses_per_rest": 3}],
        5: [{"name": "Extra Attack", "attacks_per_action": 2, "description": "Attack twice when you take the Attack action."},
            {"name": "Fast Movement", "speed_bonus": 10, "description": "+10 ft speed when not wearing heavy armor."}],
    },
    "bard": {
        1: [{"name": "Spellcasting", "ability": "charisma"},
            {"name": "Bardic Inspiration", "die": "d6", "uses": "charisma_mod",
             "description": "Bonus action: give an ally a d6 to add to one ability check, attack roll, or saving throw."}],
        2: [{"name": "Jack of All Trades", "description": "Add half proficiency bonus to ability checks you're not proficient in."},
            {"name": "Song of Rest", "die": "d6", "description": "During short rest, allies regain extra 1d6 HP."}],
        3: [{"name": "Expertise", "count": 2, "description": "Double proficiency bonus on 2 skill proficiencies."}],
        5: [{"name": "Bardic Inspiration", "die": "d8"},
            {"name": "Font of Inspiration", "description": "Bardic Inspiration recharges on short or long rest."}],
    },
    "cleric": {
        1: [{"name": "Spellcasting", "ability": "wisdom"},
            {"name": "Channel Divinity", "uses": 1, "description": "Turn Undead: undead within 30 ft must make WIS save or flee."}],
        2: [{"name": "Channel Divinity", "uses": 1}],
        5: [{"name": "Destroy Undead", "cr": "1/2", "description": "Turned undead of CR 1/2 or lower are destroyed."}],
    },
    "druid": {
        1: [{"name": "Spellcasting", "ability": "wisdom"},
            {"name": "Druidic", "description": "Secret language of druids."}],
        2: [{"name": "Wild Shape", "uses": 2, "max_cr": "1/4",
             "description": "Transform into a beast you've seen. Max CR 1/4, no flying/swimming."}],
        4: [{"name": "Wild Shape", "max_cr": "1/2", "description": "Max CR 1/2, no flying."}],
    },
    "fighter": {
        1: [{"name": "Fighting Style", "description": "Choose one: Archery (+2 ranged attack), Defense (+1 AC), Dueling (+2 damage one-handed), Great Weapon Fighting (reroll 1-2 on damage), Protection, Two-Weapon Fighting."},
            {"name": "Second Wind", "uses": 1, "healing": "1d10+level",
             "description": "Bonus action: regain 1d10 + fighter level HP. Recharges on short rest."}],
        2: [{"name": "Action Surge", "uses": 1, "description": "Take one additional action. Recharges on short rest."}],
        3: [],  # subclass choice
        5: [{"name": "Extra Attack", "attacks_per_action": 2, "description": "Attack twice when you take the Attack action."}],
    },
    "monk": {
        1: [{"name": "Unarmored Defense", "ac_formula": "10+dex+wis",
             "description": "While not wearing armor or shield, AC = 10 + DEX modifier + WIS modifier."},
            {"name": "Martial Arts", "die": "d4",
             "description": "Use DEX for unarmed/monk weapons. Bonus action unarmed strike. Damage die d4."}],
        2: [{"name": "Ki", "points": "monk_level", "description": "Ki points = monk level. Flurry of Blows, Patient Defense, Step of the Wind."}],
        3: [{"name": "Deflect Missiles", "description": "Reduce ranged attack damage by 1d10 + DEX + monk level."}],
        5: [{"name": "Extra Attack", "attacks_per_action": 2},
            {"name": "Stunning Strike", "description": "Spend 1 ki: target must CON save or be stunned until end of your next turn."},
            {"name": "Martial Arts", "die": "d6"}],
    },
    "paladin": {
        1: [{"name": "Divine Sense", "uses": "1+charisma_mod", "description": "Detect celestials, fiends, undead within 60 ft."},
            {"name": "Lay on Hands", "pool": "5*paladin_level", "description": "Heal up to 5 x paladin level HP total per long rest."}],
        2: [{"name": "Spellcasting", "ability": "charisma"},
            {"name": "Fighting Style", "description": "Choose one fighting style."},
            {"name": "Divine Smite", "description": "On hit, expend spell slot for +2d8 radiant (+1d8 per slot above 1st, max 5d8). +1d8 vs undead/fiend."}],
        5: [{"name": "Extra Attack", "attacks_per_action": 2}],
    },
    "ranger": {
        1: [{"name": "Favored Enemy", "description": "Advantage on Survival checks to track, INT checks to recall info about chosen enemy type."},
            {"name": "Natural Explorer", "description": "Expertise-like benefits in favored terrain."}],
        2: [{"name": "Spellcasting", "ability": "wisdom"},
            {"name": "Fighting Style", "description": "Choose one fighting style."}],
        3: [],  # subclass
        5: [{"name": "Extra Attack", "attacks_per_action": 2}],
    },
    "rogue": {
        1: [{"name": "Expertise", "count": 2, "description": "Double proficiency bonus on 2 skill proficiencies."},
            {"name": "Sneak Attack", "dice": "1d6",
             "description": "Once per turn, +1d6 damage with finesse/ranged weapon when you have advantage or ally within 5ft of target."},
            {"name": "Thieves' Cant", "description": "Secret language of rogues."}],
        2: [{"name": "Cunning Action", "description": "Bonus action: Dash, Disengage, or Hide."}],
        3: [{"name": "Sneak Attack", "dice": "2d6"}],
        5: [{"name": "Sneak Attack", "dice": "3d6"},
            {"name": "Uncanny Dodge", "description": "Reaction: halve damage from an attack you can see."}],
    },
    "sorcerer": {
        1: [{"name": "Spellcasting", "ability": "charisma"}],
        2: [{"name": "Sorcery Points", "points": "sorcerer_level", "description": "Create bonus spell slots or fuel metamagic."}],
        3: [{"name": "Metamagic", "count": 2, "description": "Choose 2 metamagic options."}],
    },
    "warlock": {
        1: [{"name": "Pact Magic", "ability": "charisma",
             "description": "Spell slots recharge on short rest. All slots cast at highest available level."}],
        2: [{"name": "Eldritch Invocations", "count": 2, "description": "Choose 2 invocations."}],
        3: [{"name": "Pact Boon", "description": "Choose Pact of the Chain, Blade, or Tome."}],
    },
    "wizard": {
        1: [{"name": "Spellcasting", "ability": "intelligence"},
            {"name": "Arcane Recovery", "description": "Once per day during short rest, recover spell slots totaling up to half wizard level (rounded up)."}],
        2: [],  # subclass
    },
}

# Sneak Attack dice by rogue level
SNEAK_ATTACK_DICE: dict[int, str] = {
    1: "1d6", 2: "1d6", 3: "2d6", 4: "2d6", 5: "3d6", 6: "3d6",
    7: "4d6", 8: "4d6", 9: "5d6", 10: "5d6", 11: "6d6", 12: "6d6",
    13: "7d6", 14: "7d6", 15: "8d6", 16: "8d6", 17: "9d6", 18: "9d6",
    19: "10d6", 20: "10d6",
}

# Rage bonus damage and uses by barbarian level
RAGE_DATA: dict[int, dict] = {
    1: {"uses": 2, "bonus": 2}, 2: {"uses": 2, "bonus": 2},
    3: {"uses": 3, "bonus": 2}, 4: {"uses": 3, "bonus": 2},
    5: {"uses": 3, "bonus": 2}, 6: {"uses": 4, "bonus": 2},
    7: {"uses": 4, "bonus": 2}, 8: {"uses": 4, "bonus": 2},
    9: {"uses": 4, "bonus": 3}, 10: {"uses": 4, "bonus": 3},
    11: {"uses": 4, "bonus": 3}, 12: {"uses": 5, "bonus": 3},
    13: {"uses": 5, "bonus": 3}, 14: {"uses": 5, "bonus": 3},
    15: {"uses": 5, "bonus": 3}, 16: {"uses": 5, "bonus": 4},
    17: {"uses": 6, "bonus": 4}, 18: {"uses": 6, "bonus": 4},
    19: {"uses": 6, "bonus": 4}, 20: {"uses": -1, "bonus": 4},  # -1 = unlimited
}

# ---------------------------------------------------------------------------
# Spellcasting
# ---------------------------------------------------------------------------

# Which ability governs spellcasting for each class
CLASS_SPELLCASTING_ABILITY: dict[str, str] = {
    "bard": "charisma",
    "cleric": "wisdom",
    "druid": "wisdom",
    "paladin": "charisma",
    "ranger": "wisdom",
    "sorcerer": "charisma",
    "warlock": "charisma",
    "wizard": "intelligence",
}

# Full caster spell slots by level (bard, cleric, druid, sorcerer, wizard)
# Index 0 = cantrips (not tracked as slots), indices 1-9 = spell levels
FULL_CASTER_SLOTS: dict[int, list[int]] = {
    1:  [0, 2, 0, 0, 0, 0, 0, 0, 0, 0],
    2:  [0, 3, 0, 0, 0, 0, 0, 0, 0, 0],
    3:  [0, 4, 2, 0, 0, 0, 0, 0, 0, 0],
    4:  [0, 4, 3, 0, 0, 0, 0, 0, 0, 0],
    5:  [0, 4, 3, 2, 0, 0, 0, 0, 0, 0],
    6:  [0, 4, 3, 3, 0, 0, 0, 0, 0, 0],
    7:  [0, 4, 3, 3, 1, 0, 0, 0, 0, 0],
    8:  [0, 4, 3, 3, 2, 0, 0, 0, 0, 0],
    9:  [0, 4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [0, 4, 3, 3, 3, 2, 0, 0, 0, 0],
}

# Half caster spell slots (paladin, ranger) — start at level 2
HALF_CASTER_SLOTS: dict[int, list[int]] = {
    1:  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    2:  [0, 2, 0, 0, 0, 0, 0, 0, 0, 0],
    3:  [0, 3, 0, 0, 0, 0, 0, 0, 0, 0],
    4:  [0, 3, 0, 0, 0, 0, 0, 0, 0, 0],
    5:  [0, 4, 2, 0, 0, 0, 0, 0, 0, 0],
    6:  [0, 4, 2, 0, 0, 0, 0, 0, 0, 0],
    7:  [0, 4, 3, 0, 0, 0, 0, 0, 0, 0],
    8:  [0, 4, 3, 0, 0, 0, 0, 0, 0, 0],
    9:  [0, 4, 3, 2, 0, 0, 0, 0, 0, 0],
    10: [0, 4, 3, 2, 0, 0, 0, 0, 0, 0],
}

# Warlock pact magic slots (all slots same level, recharge on short rest)
WARLOCK_PACT_SLOTS: dict[int, dict] = {
    1: {"slots": 1, "level": 1}, 2: {"slots": 2, "level": 1},
    3: {"slots": 2, "level": 2}, 4: {"slots": 2, "level": 2},
    5: {"slots": 2, "level": 3}, 6: {"slots": 2, "level": 3},
    7: {"slots": 2, "level": 4}, 8: {"slots": 2, "level": 4},
    9: {"slots": 2, "level": 5}, 10: {"slots": 2, "level": 5},
}

# Caster type by class
CLASS_CASTER_TYPE: dict[str, str] = {
    "bard": "full",
    "cleric": "full",
    "druid": "full",
    "sorcerer": "full",
    "wizard": "full",
    "paladin": "half",
    "ranger": "half",
    "warlock": "pact",
    # fighter, barbarian, rogue, monk: not casters (no entry)
}

# Levels that grant Ability Score Improvement (all classes)
ASI_LEVELS = [4, 8, 12, 16, 19]
