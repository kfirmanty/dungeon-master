"""Tests for D&D 5e ability checks, skill checks, and saving throws."""

import random

import pytest

from dungeonmaster.rules.dnd5e.abilities import (
    ability_check,
    ability_modifier,
    proficiency_bonus,
    saving_throw,
    skill_check,
)


# --- Ability Modifier ---

class TestAbilityModifier:
    def test_standard_scores(self):
        assert ability_modifier(10) == 0
        assert ability_modifier(11) == 0
        assert ability_modifier(12) == 1
        assert ability_modifier(14) == 2
        assert ability_modifier(16) == 3
        assert ability_modifier(18) == 4
        assert ability_modifier(20) == 5

    def test_low_scores(self):
        assert ability_modifier(8) == -1
        assert ability_modifier(6) == -2
        assert ability_modifier(1) == -5

    def test_odd_vs_even(self):
        """Odd scores round down (e.g. 13 → +1, not +1.5)."""
        assert ability_modifier(13) == 1
        assert ability_modifier(15) == 2
        assert ability_modifier(9) == -1


# --- Proficiency Bonus ---

class TestProficiencyBonus:
    def test_level_1_through_4(self):
        for level in range(1, 5):
            assert proficiency_bonus(level) == 2

    def test_level_5_through_8(self):
        for level in range(5, 9):
            assert proficiency_bonus(level) == 3

    def test_level_17_through_20(self):
        for level in range(17, 21):
            assert proficiency_bonus(level) == 6

    def test_level_below_1(self):
        assert proficiency_bonus(0) == 2


# --- Ability Check ---

class TestAbilityCheck:
    @pytest.fixture
    def fighter(self):
        return {
            "name": "Conan",
            "abilities": {
                "strength": 18,
                "dexterity": 14,
                "constitution": 16,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 12,
            },
            "level": 5,
        }

    def test_basic_strength_check(self, fighter):
        random.seed(42)
        result = ability_check(fighter, "strength", dc=15)
        assert result.check_type == "ability_check"
        assert result.detail == "strength"
        assert result.actor == "Conan"
        assert result.dice_result.modifier == 4  # STR 18 → +4
        assert result.target_number == 15

    def test_success_vs_failure(self, fighter):
        """Verify success is correctly determined by comparing total to DC."""
        # With STR 18 (+4), we need the d20 to roll >= 11 to beat DC 15
        for seed in range(100):
            random.seed(seed)
            result = ability_check(fighter, "strength", dc=15)
            expected_success = result.dice_result.total >= 15
            assert result.success == expected_success

    def test_missing_ability_defaults_to_10(self):
        character = {"name": "Test", "abilities": {}}
        random.seed(42)
        result = ability_check(character, "strength", dc=10)
        assert result.dice_result.modifier == 0  # default 10 → +0


# --- Skill Check ---

class TestSkillCheck:
    @pytest.fixture
    def rogue(self):
        return {
            "name": "Shadow",
            "abilities": {
                "strength": 10,
                "dexterity": 18,
                "constitution": 12,
                "intelligence": 14,
                "wisdom": 12,
                "charisma": 10,
            },
            "level": 3,
            "proficiencies": ["stealth", "sleight_of_hand", "perception"],
        }

    def test_proficient_skill(self, rogue):
        """Proficient skill should add proficiency bonus."""
        random.seed(42)
        result = skill_check(rogue, "stealth", dc=15)
        # DEX 18 → +4, level 3 → prof +2, total mod = +6
        assert result.dice_result.modifier == 6
        assert result.check_type == "skill_check"
        assert result.detail == "stealth"

    def test_non_proficient_skill(self, rogue):
        """Non-proficient skill uses only ability modifier."""
        random.seed(42)
        result = skill_check(rogue, "athletics", dc=15)
        # STR 10 → +0, no proficiency
        assert result.dice_result.modifier == 0

    def test_skill_case_insensitive(self, rogue):
        random.seed(42)
        r1 = skill_check(rogue, "Stealth", dc=15)
        random.seed(42)
        r2 = skill_check(rogue, "stealth", dc=15)
        assert r1.dice_result.total == r2.dice_result.total

    def test_invalid_skill(self, rogue):
        with pytest.raises(ValueError, match="Unknown skill"):
            skill_check(rogue, "hacking", dc=15)

    def test_description_contains_result(self, rogue):
        random.seed(42)
        result = skill_check(rogue, "stealth", dc=15)
        assert "Stealth" in result.description
        assert "DC 15" in result.description


# --- Saving Throw ---

class TestSavingThrow:
    @pytest.fixture
    def wizard(self):
        return {
            "name": "Gandalf",
            "abilities": {
                "strength": 8,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 20,
                "wisdom": 16,
                "charisma": 10,
            },
            "level": 5,
            "save_proficiencies": ["intelligence", "wisdom"],
        }

    def test_proficient_save(self, wizard):
        """Wizard with INT save proficiency should add prof bonus."""
        random.seed(42)
        result = saving_throw(wizard, "intelligence", dc=15)
        # INT 20 → +5, level 5 → prof +3, total = +8
        assert result.dice_result.modifier == 8
        assert result.check_type == "saving_throw"

    def test_non_proficient_save(self, wizard):
        """Non-proficient save uses only ability modifier."""
        random.seed(42)
        result = saving_throw(wizard, "strength", dc=15)
        # STR 8 → -1
        assert result.dice_result.modifier == -1

    def test_advantage_on_save(self, wizard):
        random.seed(42)
        result = saving_throw(wizard, "wisdom", dc=15, advantage=True)
        assert len(result.dice_result.rolls) == 2  # advantage = 2 d20s
