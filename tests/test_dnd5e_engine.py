"""Tests for the D&D 5e engine — Protocol compliance and integration."""

import random

import pytest

from dungeonmaster.rules.base import RulesEngine, get_engine, register_engine
from dungeonmaster.rules.dnd5e.engine import DnD5eEngine


class TestProtocolCompliance:
    """Verify that DnD5eEngine satisfies the RulesEngine Protocol."""

    def test_engine_has_system_name(self):
        engine = DnD5eEngine()
        assert isinstance(engine.system_name, str)
        assert "5" in engine.system_name  # should mention "5th Edition" or "5e"

    def test_engine_has_all_protocol_methods(self):
        """Check that all Protocol methods exist and are callable."""
        engine = DnD5eEngine()
        assert callable(engine.roll_check)
        assert callable(engine.roll_initiative)
        assert callable(engine.resolve_attack)
        assert callable(engine.apply_damage)
        assert callable(engine.create_character)
        assert callable(engine.get_character_summary)
        assert callable(engine.get_available_actions)
        assert callable(engine.get_rules_summary)
        assert callable(engine.get_check_types)

    def test_engine_registered_as_dnd5e(self):
        """Engine should be retrievable via the 'dnd5e' system ID."""
        engine = get_engine("dnd5e")
        assert isinstance(engine, DnD5eEngine)

    def test_unknown_system_raises(self):
        with pytest.raises(KeyError, match="Unknown rules system"):
            get_engine("gurps_4e")


class TestEngineRollCheck:
    """Test the engine's roll_check dispatcher."""

    @pytest.fixture
    def engine(self):
        return DnD5eEngine()

    @pytest.fixture
    def character(self):
        return {
            "name": "Test",
            "abilities": {
                "strength": 16, "dexterity": 14, "constitution": 12,
                "intelligence": 10, "wisdom": 14, "charisma": 8,
            },
            "level": 3,
            "proficiencies": ["athletics", "perception"],
            "save_proficiencies": ["strength", "constitution"],
        }

    def test_ability_check(self, engine, character):
        random.seed(42)
        result = engine.roll_check(character, "ability_check", "strength", 15)
        assert result.check_type == "ability_check"
        assert result.detail == "strength"

    def test_skill_check(self, engine, character):
        random.seed(42)
        result = engine.roll_check(character, "skill_check", "athletics", 15)
        assert result.check_type == "skill_check"
        assert result.detail == "athletics"

    def test_saving_throw(self, engine, character):
        random.seed(42)
        result = engine.roll_check(character, "saving_throw", "constitution", 15)
        assert result.check_type == "saving_throw"

    def test_invalid_check_type(self, engine, character):
        with pytest.raises(ValueError, match="Unknown check type"):
            engine.roll_check(character, "percentile_test", "luck", 50)

    def test_advantage_kwarg(self, engine, character):
        random.seed(42)
        result = engine.roll_check(character, "skill_check", "stealth", 15, advantage=True)
        assert len(result.dice_result.rolls) == 2  # advantage = 2 dice


class TestEngineResolveAttack:
    @pytest.fixture
    def engine(self):
        return DnD5eEngine()

    def test_attack_resolution(self, engine):
        random.seed(42)
        attacker = {
            "name": "Fighter",
            "abilities": {"strength": 16, "dexterity": 12},
            "proficiency_bonus": 2,
        }
        defender = {"name": "Goblin", "ac": 13}
        weapon = {"name": "Longsword", "properties": {"damage": "1d8", "type": "slashing"}}

        result = engine.resolve_attack(attacker, defender, weapon=weapon)
        assert result.attacker == "Fighter"
        assert isinstance(result.hit, bool)


class TestEngineCreateCharacter:
    @pytest.fixture
    def engine(self):
        return DnD5eEngine()

    def test_create_and_summarize(self, engine):
        random.seed(42)
        char = engine.create_character({
            "name": "Gandalf",
            "race": "human",
            "character_class": "wizard",
        })
        assert char["name"] == "Gandalf"

        summary = engine.get_character_summary(char)
        assert "Gandalf" in summary
        assert "Wizard" in summary


class TestEngineSystemInfo:
    @pytest.fixture
    def engine(self):
        return DnD5eEngine()

    def test_rules_summary_mentions_d20(self, engine):
        summary = engine.get_rules_summary()
        assert "d20" in summary.lower()

    def test_check_types_include_core(self, engine):
        types = engine.get_check_types()
        assert "ability_check" in types
        assert "skill_check" in types
        assert "saving_throw" in types
        assert "attack" in types

    def test_available_actions_combat(self, engine):
        char = {"name": "Test"}
        actions = engine.get_available_actions(char, "combat")
        assert "attack" in actions
        assert "dodge" in actions
        assert "dash" in actions

    def test_available_actions_exploration(self, engine):
        char = {"name": "Test"}
        actions = engine.get_available_actions(char, "exploration")
        assert "search" in actions
        assert "investigate" in actions
