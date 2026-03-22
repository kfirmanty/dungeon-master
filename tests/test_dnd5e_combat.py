"""Tests for D&D 5e combat mechanics."""

import random

import pytest

from dungeonmaster.rules.dnd5e.combat import (
    apply_damage,
    attack_roll,
    death_saving_throw,
    roll_initiative,
)


# --- Initiative ---

class TestRollInitiative:
    def test_initiative_uses_dex(self):
        character = {
            "name": "Quick",
            "abilities": {"dexterity": 18},
        }
        random.seed(42)
        result = roll_initiative(character)
        # DEX 18 → +4
        assert result.modifier == 4
        assert result.total == result.rolls[0] + 4

    def test_low_dex_initiative(self):
        character = {
            "name": "Slow",
            "abilities": {"dexterity": 6},
        }
        random.seed(42)
        result = roll_initiative(character)
        assert result.modifier == -2


# --- Attack Roll ---

class TestAttackRoll:
    @pytest.fixture
    def fighter(self):
        return {
            "name": "Conan",
            "abilities": {"strength": 18, "dexterity": 12},
            "proficiency_bonus": 2,
        }

    @pytest.fixture
    def longsword(self):
        return {
            "name": "Longsword",
            "properties": {"damage": "1d8", "type": "slashing"},
        }

    @pytest.fixture
    def rapier(self):
        return {
            "name": "Rapier",
            "properties": {"damage": "1d8", "type": "piercing", "finesse": "true"},
        }

    @pytest.fixture
    def longbow(self):
        return {
            "name": "Longbow",
            "properties": {"damage": "1d8", "type": "piercing", "range": "150/600"},
        }

    def test_melee_attack_uses_strength(self, fighter, longsword):
        random.seed(42)
        result = attack_roll(fighter, target_ac=15, weapon=longsword)
        # STR 18 → +4, prof +2 = +6 attack modifier
        assert result.attack_roll.modifier == 6

    def test_finesse_uses_higher_of_str_dex(self, fighter, rapier):
        """Finesse weapons use the higher of STR or DEX."""
        random.seed(42)
        result = attack_roll(fighter, target_ac=15, weapon=rapier)
        # STR 18 (+4) > DEX 12 (+1), so uses +4 + prof 2 = +6
        assert result.attack_roll.modifier == 6

    def test_ranged_uses_dexterity(self, fighter, longbow):
        random.seed(42)
        result = attack_roll(fighter, target_ac=15, weapon=longbow)
        # DEX 12 → +1, prof +2 = +3
        assert result.attack_roll.modifier == 3

    def test_hit_when_total_meets_ac(self, fighter, longsword):
        """An attack should hit when the roll total equals or exceeds AC."""
        for seed in range(200):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=15, weapon=longsword)
            if not result.attack_roll.natural_min:
                expected_hit = result.attack_roll.total >= 15
                assert result.hit == expected_hit, f"seed={seed}"

    def test_damage_on_hit(self, fighter, longsword):
        """When an attack hits, damage should be rolled."""
        for seed in range(200):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=10, weapon=longsword)
            if result.hit and not result.critical:
                assert result.damage_roll is not None
                assert result.total_damage > 0

    def test_no_damage_on_miss(self, fighter, longsword):
        """When an attack misses, there should be no damage."""
        for seed in range(200):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=25, weapon=longsword)
            if not result.hit:
                assert result.damage_roll is None
                assert result.total_damage == 0

    def test_natural_1_always_misses(self, fighter, longsword):
        """Natural 1 should always miss, even against low AC."""
        for seed in range(1000):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=5, weapon=longsword)
            if result.attack_roll.natural_min:
                assert result.hit is False
                assert "Miss" in result.description
                return
        pytest.skip("Could not find seed producing natural 1")

    def test_natural_20_always_hits_and_crits(self, fighter, longsword):
        """Natural 20 should always hit and be a critical hit."""
        for seed in range(1000):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=30, weapon=longsword)
            if result.attack_roll.natural_max:
                assert result.hit is True
                assert result.critical is True
                assert "CRITICAL" in result.description
                return
        pytest.skip("Could not find seed producing natural 20")

    def test_critical_hit_does_more_damage(self, fighter, longsword):
        """Critical hits should generally deal more damage than normal hits."""
        normal_damages = []
        crit_damages = []
        for seed in range(2000):
            random.seed(seed)
            result = attack_roll(fighter, target_ac=10, weapon=longsword)
            if result.hit:
                if result.critical:
                    crit_damages.append(result.total_damage)
                else:
                    normal_damages.append(result.total_damage)

        if normal_damages and crit_damages:
            # Average crit damage should be higher than average normal damage
            avg_normal = sum(normal_damages) / len(normal_damages)
            avg_crit = sum(crit_damages) / len(crit_damages)
            assert avg_crit > avg_normal


# --- Apply Damage ---

class TestApplyDamage:
    def test_reduce_hp(self):
        target = {"name": "Goblin", "hp": {"current": 10, "max": 10, "temp": 0}}
        result = apply_damage(target, 4, "slashing")
        assert target["hp"]["current"] == 6
        assert result.damage_dealt == 4
        assert result.target_unconscious is False

    def test_unconscious_at_zero_hp(self):
        target = {"name": "Goblin", "hp": {"current": 5, "max": 10, "temp": 0}}
        result = apply_damage(target, 5, "fire")
        assert target["hp"]["current"] == 0
        assert result.target_unconscious is True
        assert result.target_dead is False

    def test_massive_damage_instant_death(self):
        """If overflow damage >= max HP, target dies instantly."""
        target = {"name": "Goblin", "hp": {"current": 5, "max": 10, "temp": 0}}
        result = apply_damage(target, 15, "necrotic")
        # overflow = 15 - 5 = 10, max_hp = 10, 10 >= 10 → dead
        assert result.target_dead is True

    def test_temp_hp_absorbs_first(self):
        target = {"name": "Hero", "hp": {"current": 20, "max": 20, "temp": 5}}
        result = apply_damage(target, 8, "slashing")
        # 5 temp HP absorbs 5, remaining 3 from current HP
        assert target["hp"]["temp"] == 0
        assert target["hp"]["current"] == 17
        assert result.damage_dealt == 3  # actual damage to real HP

    def test_hp_cannot_go_below_zero(self):
        target = {"name": "Goblin", "hp": {"current": 3, "max": 10, "temp": 0}}
        apply_damage(target, 100, "bludgeoning")
        assert target["hp"]["current"] == 0

    def test_death_saves_reset_on_unconscious(self):
        target = {
            "name": "Hero",
            "hp": {"current": 5, "max": 20, "temp": 0},
            "death_saves": {"successes": 2, "failures": 1},
        }
        apply_damage(target, 5, "piercing")
        assert target["death_saves"] == {"successes": 0, "failures": 0}


# --- Death Saving Throws ---

class TestDeathSavingThrow:
    @pytest.fixture
    def dying_character(self):
        return {
            "name": "Hero",
            "hp": {"current": 0, "max": 20, "temp": 0},
            "death_saves": {"successes": 0, "failures": 0},
        }

    def test_success_on_10_or_higher(self, dying_character):
        for seed in range(500):
            random.seed(seed)
            char = {
                "name": "Hero",
                "hp": {"current": 0, "max": 20, "temp": 0},
                "death_saves": {"successes": 0, "failures": 0},
            }
            dice, outcome = death_saving_throw(char)
            if dice.total >= 10 and not dice.natural_max:
                assert outcome == "success"
                assert char["death_saves"]["successes"] == 1
                return
        pytest.skip("No suitable seed found")

    def test_failure_below_10(self, dying_character):
        for seed in range(500):
            random.seed(seed)
            char = {
                "name": "Hero",
                "hp": {"current": 0, "max": 20, "temp": 0},
                "death_saves": {"successes": 0, "failures": 0},
            }
            dice, outcome = death_saving_throw(char)
            if dice.total < 10 and not dice.natural_min:
                assert outcome == "failure"
                assert char["death_saves"]["failures"] == 1
                return
        pytest.skip("No suitable seed found")

    def test_natural_20_revives(self, dying_character):
        """Natural 20 should restore 1 HP and revive the character."""
        for seed in range(1000):
            random.seed(seed)
            char = {
                "name": "Hero",
                "hp": {"current": 0, "max": 20, "temp": 0},
                "death_saves": {"successes": 0, "failures": 0},
            }
            dice, outcome = death_saving_throw(char)
            if dice.natural_max:
                assert outcome == "revived"
                assert char["hp"]["current"] == 1
                return
        pytest.skip("No seed producing natural 20")

    def test_natural_1_counts_as_two_failures(self, dying_character):
        """Natural 1 on a death save should count as 2 failures."""
        for seed in range(1000):
            random.seed(seed)
            char = {
                "name": "Hero",
                "hp": {"current": 0, "max": 20, "temp": 0},
                "death_saves": {"successes": 0, "failures": 0},
            }
            dice, outcome = death_saving_throw(char)
            if dice.natural_min:
                assert char["death_saves"]["failures"] == 2
                return
        pytest.skip("No seed producing natural 1")

    def test_three_successes_stabilize(self):
        char = {
            "name": "Hero",
            "hp": {"current": 0, "max": 20, "temp": 0},
            "death_saves": {"successes": 2, "failures": 1},
        }
        for seed in range(500):
            random.seed(seed)
            test_char = dict(char)
            test_char["death_saves"] = {"successes": 2, "failures": 1}
            dice, outcome = death_saving_throw(test_char)
            if dice.total >= 10 and not dice.natural_max:
                assert outcome == "stabilized"
                return
        pytest.skip("No suitable seed found")

    def test_three_failures_kill(self):
        char = {
            "name": "Hero",
            "hp": {"current": 0, "max": 20, "temp": 0},
            "death_saves": {"successes": 1, "failures": 2},
        }
        for seed in range(500):
            random.seed(seed)
            test_char = dict(char)
            test_char["death_saves"] = {"successes": 1, "failures": 2}
            dice, outcome = death_saving_throw(test_char)
            if dice.total < 10 and not dice.natural_min:
                assert outcome == "dead"
                return
        pytest.skip("No suitable seed found")
