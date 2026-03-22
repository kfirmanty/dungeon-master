"""Tests for D&D 5e character creation and management."""

import random

import pytest

from dungeonmaster.rules.dnd5e.characters import (
    calculate_ac,
    calculate_hp,
    create_character,
    get_character_summary,
    roll_ability_scores,
    standard_array,
)


class TestAbilityScoreGeneration:
    def test_standard_array_values(self):
        array = standard_array()
        assert sorted(array.values(), reverse=True) == [15, 14, 13, 12, 10, 8]
        assert set(array.keys()) == {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}

    def test_rolled_scores_in_valid_range(self):
        """4d6 drop lowest: min=3, max=18."""
        random.seed(42)
        scores = roll_ability_scores()
        assert len(scores) == 6
        for score in scores.values():
            assert 3 <= score <= 18


class TestCalculateHP:
    def test_fighter_level_1(self):
        # Fighter (d10), CON 14 (+2): 10 + 2 = 12
        assert calculate_hp("fighter", 14, 1) == 12

    def test_wizard_level_1(self):
        # Wizard (d6), CON 10 (+0): 6 + 0 = 6
        assert calculate_hp("wizard", 10, 1) == 6

    def test_fighter_level_5(self):
        # Fighter (d10), CON 14 (+2):
        # Level 1: 10 + 2 = 12
        # Levels 2-5: (6 + 2) * 4 = 32
        # Total: 44
        assert calculate_hp("fighter", 14, 5) == 44

    def test_low_con_minimum_1hp(self):
        # Even with very low CON, minimum is 1 HP
        hp = calculate_hp("wizard", 1, 1)
        assert hp >= 1

    def test_barbarian_has_most_hp(self):
        # Barbarian (d12) should have more HP than wizard (d6) at same level/CON
        barb_hp = calculate_hp("barbarian", 14, 5)
        wiz_hp = calculate_hp("wizard", 14, 5)
        assert barb_hp > wiz_hp


class TestCalculateAC:
    def test_unarmored(self):
        char = {"abilities": {"dexterity": 14}, "inventory": []}
        # 10 + DEX mod (+2) = 12
        assert calculate_ac(char) == 12

    def test_light_armor(self):
        char = {
            "abilities": {"dexterity": 16},
            "inventory": [
                {"name": "Leather Armor", "equipped": True, "properties": {"ac": "11", "type": "light"}},
            ],
        }
        # Light: 11 + DEX mod (+3) = 14
        assert calculate_ac(char) == 14

    def test_medium_armor_caps_dex(self):
        char = {
            "abilities": {"dexterity": 20},
            "inventory": [
                {"name": "Scale Mail", "equipped": True, "properties": {"ac": "14", "type": "medium"}},
            ],
        }
        # Medium: 14 + min(DEX +5, 2) = 16
        assert calculate_ac(char) == 16

    def test_heavy_armor_ignores_dex(self):
        char = {
            "abilities": {"dexterity": 8},
            "inventory": [
                {"name": "Chain Mail", "equipped": True, "properties": {"ac": "16", "type": "heavy"}},
            ],
        }
        # Heavy: just 16, no DEX
        assert calculate_ac(char) == 16

    def test_shield_bonus(self):
        char = {
            "abilities": {"dexterity": 14},
            "inventory": [
                {"name": "Chain Mail", "equipped": True, "properties": {"ac": "16", "type": "heavy"}},
                {"name": "Shield", "equipped": True, "properties": {"ac_bonus": "2"}},
            ],
        }
        # 16 + 2 (shield) = 18
        assert calculate_ac(char) == 18

    def test_unequipped_armor_ignored(self):
        char = {
            "abilities": {"dexterity": 14},
            "inventory": [
                {"name": "Chain Mail", "equipped": False, "properties": {"ac": "16", "type": "heavy"}},
            ],
        }
        # Unequipped → unarmored: 10 + 2 = 12
        assert calculate_ac(char) == 12


class TestCreateCharacter:
    def test_basic_creation(self):
        random.seed(42)
        char = create_character({
            "name": "Aelindra",
            "race": "elf",
            "character_class": "ranger",
            "abilities": {"strength": 12, "dexterity": 16, "constitution": 14, "intelligence": 10, "wisdom": 14, "charisma": 8},
            "proficiencies": ["stealth", "perception", "survival"],
        })

        assert char["name"] == "Aelindra"
        assert char["race"] == "elf"
        assert char["character_class"] == "ranger"
        assert char["level"] == 1
        # Elf gets +2 DEX
        assert char["abilities"]["dexterity"] == 18
        assert char["hp"]["current"] == char["hp"]["max"]
        assert char["hp"]["current"] > 0
        assert char["proficiency_bonus"] == 2
        assert char["speed"] == 30  # elf speed
        assert "stealth" in char["proficiencies"]
        assert len(char["inventory"]) > 0  # starting equipment
        assert char["gold"] == 50
        assert char["is_player"] is True

    def test_racial_ability_bonuses(self):
        char = create_character({
            "name": "Bruenor",
            "race": "dwarf",
            "character_class": "fighter",
            "abilities": {"strength": 15, "dexterity": 10, "constitution": 14, "intelligence": 10, "wisdom": 12, "charisma": 8},
        })
        # Dwarf gets +2 CON
        assert char["abilities"]["constitution"] == 16

    def test_human_gets_all_bonuses(self):
        char = create_character({
            "name": "Joe",
            "race": "human",
            "character_class": "fighter",
            "abilities": {"strength": 14, "dexterity": 14, "constitution": 14, "intelligence": 14, "wisdom": 14, "charisma": 14},
        })
        # Human gets +1 to all abilities
        for ability in char["abilities"].values():
            assert ability == 15

    def test_save_proficiencies_match_class(self):
        char = create_character({
            "name": "Test",
            "race": "human",
            "character_class": "wizard",
        })
        assert "intelligence" in char["save_proficiencies"]
        assert "wisdom" in char["save_proficiencies"]

    def test_starting_equipment_is_equipped(self):
        char = create_character({
            "name": "Test",
            "race": "human",
            "character_class": "fighter",
        })
        for item in char["inventory"]:
            assert item["equipped"] is True

    def test_ac_calculated_from_equipment(self):
        char = create_character({
            "name": "Test",
            "race": "human",
            "character_class": "fighter",
            "abilities": {"strength": 14, "dexterity": 10, "constitution": 14, "intelligence": 10, "wisdom": 10, "charisma": 10},
        })
        # Fighter starts with Chain Mail (AC 16) + Shield (+2) = 18
        assert char["ac"] == 18

    def test_companion_creation(self):
        char = create_character({
            "name": "Lyra",
            "race": "half_elf",
            "character_class": "bard",
            "is_player": False,
            "personality": "Cheerful and quick-witted, always ready with a song.",
        })
        assert char["is_player"] is False
        assert "Cheerful" in char["personality"]

    def test_auto_roll_abilities_when_not_provided(self):
        random.seed(42)
        char = create_character({
            "name": "Random",
            "race": "human",
            "character_class": "fighter",
        })
        # Abilities should be populated (3-18 + racial)
        for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
            assert ability in char["abilities"]
            assert char["abilities"][ability] >= 4  # 3 (min roll) + 1 (human)


class TestGetCharacterSummary:
    def test_summary_format(self):
        char = {
            "name": "Aelindra",
            "race": "elf",
            "character_class": "ranger",
            "level": 3,
            "abilities": {"strength": 12, "dexterity": 18, "constitution": 14, "intelligence": 10, "wisdom": 14, "charisma": 8},
            "hp": {"current": 24, "max": 28},
            "ac": 15,
            "conditions": [],
        }
        summary = get_character_summary(char)
        assert "Aelindra" in summary
        assert "Level 3" in summary
        assert "Elf" in summary
        assert "Ranger" in summary
        assert "HP 24/28" in summary
        assert "AC 15" in summary

    def test_summary_with_conditions(self):
        char = {
            "name": "Hurt",
            "race": "human",
            "character_class": "fighter",
            "level": 1,
            "abilities": {"strength": 10, "dexterity": 10, "constitution": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
            "hp": {"current": 5, "max": 10},
            "ac": 16,
            "conditions": ["poisoned", "prone"],
        }
        summary = get_character_summary(char)
        assert "poisoned" in summary
        assert "prone" in summary
